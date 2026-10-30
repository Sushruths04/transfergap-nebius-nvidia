"""Stream a planned G1 reach as SONIC VR 3-point targets (planner mode) instead of joint targets.

Why: with the joint-target stream the deployed policy follows commanded wrist-pitch and elbow angles only partly, so
the hand ends 10+ cm from the plan. The VR 3-point input is the interface SONIC is trained for in teleoperation: the
policy gets wrist poses (and keeps the legs balanced with its planner), not joint angles.

Each plan frame is converted to the wrist/neck key frames with the SAME upstream robot model and key-frame offsets
the controller's calibration uses (gear_sonic.utils.teleop.vis.vr3pt_pose_visualizer.get_g1_key_frame_poses), so the
values are in the frame the policy expects without any headset calibration. Open loop: reads only the plan file and
two signalling files (go/stop). Hand closure comes from the plan's Dex3 closure (0 open ... 1 closed).

    .venv_sim/bin/python stream_vr3.py --traj plan.npz --go-file F --stop-file F --done-file F
Deploy must run with --input-type zmq_manager.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import zmq

HAND_CLOSED = np.array([-0.0, -0.7, -0.7, 1.0, 1.5, 1.0, 1.5])      # plan_reach.HAND_CLOSED


def closure(right_hand):
    """Plan Dex3 targets -> trigger value 0..1 (projection on the closed preset)."""
    c = HAND_CLOSED / np.dot(HAND_CLOSED, HAND_CLOSED)
    return np.clip(right_hand @ c, 0.0, 1.0)


def key_frames(traj, sonic_root):
    """Per plan frame: (3, 3) positions and (3, 4) wxyz orientations of [L-wrist, R-wrist, neck]."""
    sys.path.insert(0, str(Path(sonic_root).expanduser()))
    from gear_sonic.data.robot_model.instantiation.g1 import instantiate_g1_robot_model
    from gear_sonic.utils.teleop.vis.vr3pt_pose_visualizer import get_g1_key_frame_poses
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from plan_reach import ISAACLAB_ORDER
    rm = instantiate_g1_robot_model()
    names = list(rm.supplemental_info.body_actuated_joints)
    idx = [ISAACLAB_ORDER.index(n) for n in names]
    jp = traj["joint_pos"].astype(np.float64)
    pos = np.zeros((len(jp), 3, 3))
    ori = np.zeros((len(jp), 3, 4))
    for k in range(len(jp)):
        q = rm.get_configuration_from_actuated_joints(body_actuated_joint_values=jp[k][idx])
        p = get_g1_key_frame_poses(rm, q=q)
        for i, key in enumerate(("left_wrist", "right_wrist")):
            pos[k, i], ori[k, i] = p[key]["position"], p[key]["orientation_wxyz"]
        pos[k, 2] = [0.0, 0.0, 0.05 + 0.35]                 # neck upright: ThreePointPose.TORSO_LINK_OFFSET_Z + NECK_LINK_LENGTH
        ori[k, 2] = [1.0, 0.0, 0.0, 0.0]
    pos[:, 0], ori[:, 0] = pos[0, 0], ori[0, 0]                # left arm stays where it starts (plan only moves the right arm)
    return pos, ori


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", required=True)
    ap.add_argument("--port", type=int, default=5556)
    ap.add_argument("--go-file", required=True)
    ap.add_argument("--stop-file", required=True)
    ap.add_argument("--done-file", required=True)
    ap.add_argument("--fps", type=float, default=50.0)
    ap.add_argument("--sonic-root", default="~/GR00T-WholeBodyControl")
    a = ap.parse_args()
    root = Path(a.sonic_root).expanduser()
    sys.path.insert(0, str(root))
    from gear_sonic.scripts.pico_manager_thread_server import compute_hand_joints_from_inputs, init_hand_ik_solvers
    from gear_sonic.utils.teleop.zmq.zmq_planner_sender import build_command_message, build_planner_message
    traj = dict(np.load(a.traj))
    T = len(traj["joint_pos"])
    pos, ori = key_frames(traj, root)
    trig = np.array([closure(h) for h in traj["right_hand"]])
    lsol, rsol = init_hand_ik_solvers()
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUB)
    sock.bind(f"tcp://*:{a.port}")
    time.sleep(0.3)
    sock.send(build_command_message(start=False, stop=False, planner=False))
    dt, k = 1.0 / a.fps, 0
    go, stop, done = Path(a.go_file), Path(a.stop_file), Path(a.done_file)
    t_next, started, last_start = time.monotonic(), None, 0.0
    while not stop.exists():
        if started is None and go.exists():
            started = time.time()
            print(f"[stream_vr3] go: playing {T} frames", flush=True)
        if started is None and time.time() - last_start > 1.0:          # the deploy leaves damping only on a start command
            sock.send(build_command_message(start=True, stop=False, planner=True))
            last_start = time.time()
        lh, rh = compute_hand_joints_from_inputs(lsol, rsol, 0.0, 0.0, float(trig[k]), 0.0)
        sock.send(build_planner_message(0, [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], speed=-1.0, height=-1.0,
                                        left_hand_position=lh.reshape(-1).astype(np.float32).tolist(),
                                        right_hand_position=rh.reshape(-1).astype(np.float32).tolist(),
                                        vr_3pt_position=pos[k].flatten().tolist(),
                                        vr_3pt_orientation=ori[k].flatten().tolist()))
        if started is not None and k < T - 1:
            k += 1
            if k == T - 1:
                done.write_text(json.dumps({"frames": T, "play_s": time.time() - started}))
                print("[stream_vr3] trajectory finished; holding last frame", flush=True)
        t_next += dt
        time.sleep(max(0.0, t_next - time.monotonic()))
    sock.close(0)
    ctx.term()


if __name__ == "__main__":
    main()
