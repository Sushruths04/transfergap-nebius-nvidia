"""Real-time mode, G1 side, "virtual VR headset": webcam body keypoints (live/hands_pub.py) -> SONIC's VR 3-point
teleop (planner keeps the legs balanced; the upper body follows the person's wrists and neck; the right Dex3 hand
closes when the person pinches). Replaces the full-body SMPL stream for table-top manipulation, where a monocular
estimate of hidden or still legs makes the whole-body tracker fall.

    # VM, SONIC root, its sim venv; deploy must run with --input-type zmq_manager; hands_pub WITHOUT --stream-sonic
    .venv_sim/bin/python ~/transfergap_g1/live/g1_vr3pt.py --hands http://127.0.0.1:8092/hands.jsonl

What is reused from upstream (gear_sonic, pin b042411): ThreePointPose calibration (zero-pose FK reference of the G1,
neck-orientation and wrist offsets), build_command_message / build_planner_message, the Dex3 hand IK from trigger
values. What is ours: the 3-point poses come from monocular body keypoints instead of a headset. Position = joint
relative to the hips in the person's body frame (x forward, y left, z up; facing from the hip line). Wrist frame =
(wrist -> middle-finger base, index base -> pinky base); neck frame = (neck -> head, right -> left shoulder). These
frames differ from the headset's by a constant rotation, which the calibration (captured while the person stands
still with arms hanging at the sides, matching the robot's zero pose) removes.
UNVERIFIED until the first VM run.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

import numpy as np
import zmq
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub import read_jsonl  # noqa: E402

CALIB_S = 1.5          # capture window after the countdown
COUNTDOWN_S = 3.0
# Live safe-path rule (same idea as demo.style.safe_project for the arms): the copied wrists never go below the
# height of the block's top above the table. g1/scene.py: table top 0.72 m, block 4 cm; G1 standing pelvis ~0.79 m
# (g1/plan_reach.py), wrist ~6 cm above the fingertips -> 0.72 + 0.04 + 0.06 - 0.79 = 0.03 m above the pelvis.
# Added 2026-10-02 after the G1 copied a person pressing both hands into the desk and tipped over.
WRIST_ZMIN = 0.03
CLOSE_M, OPEN_M = 0.04, 0.06


def demo_frame(v):                       # SOMA y-up -> z-up (as transfergap.demo.gemx.soma_to_demo_frame)
    v = np.asarray(v, float)
    return np.array([v[0], -v[2], v[1]])


def _unit(v):
    return v / max(np.linalg.norm(v), 1e-9)


def frame_from(x_dir, y_hint):
    x = _unit(x_dir)
    z = _unit(np.cross(x, y_hint))
    y = np.cross(z, x)
    return np.stack([x, y, z], 1)


def three_point(J):
    """(3, 7) [L-wrist, R-wrist, neck], rows [x, y, z, qw, qx, qy, qz], hips-relative, person body frame."""
    left = J["LeftLeg"] - J["RightLeg"]
    left[2] = 0.0
    left = _unit(left)
    up = np.array([0.0, 0.0, 1.0])
    B = np.stack([np.cross(left, up), left, up])           # rows: forward, left, up (world -> body)
    out = np.zeros((3, 7))
    for k, (side, s) in enumerate((("Left", 1.0), ("Right", -1.0))):
        w = J[f"{side}Hand"]
        Rw = frame_from(J[f"{side}HandMiddle1"] - w, s * (J[f"{side}HandIndex1"] - J[f"{side}HandPinky1"]))
        out[k, :3] = B @ (w - J["Hips"])
        out[k, 3:] = R.from_matrix(B @ Rw).as_quat(scalar_first=True)
    Rn = frame_from(J["Head"] - J["Neck1"], J["LeftShoulder"] - J["RightShoulder"])
    out[2, :3] = B @ (J["Neck1"] - J["Hips"])
    out[2, 3:] = R.from_matrix(B @ Rn).as_quat(scalar_first=True)
    return out


def arms_down(C):
    """Calibration pose check on the raw 3-point samples (hips-relative body frame): both wrists near hip height and
    not held forward (G1 zero-pose reference = arms hanging)."""
    w = np.median(C[:, :2, :3], 0)
    return bool(np.all(w[:, 2] < 0.20) and np.all(w[:, 0] < 0.25))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hands", default="http://127.0.0.1:8092/hands.jsonl")
    ap.add_argument("--port", type=int, default=5556)
    ap.add_argument("--hz", type=float, default=50.0)
    ap.add_argument("--alpha", type=float, default=0.4, help="smoothing of the 3-point targets per input frame")
    ap.add_argument("--cmds", default="http://127.0.0.1:8091/cmds.json", help="viewer commands (recalibrate button)")
    ap.add_argument("--wrist-zmin", type=float, default=WRIST_ZMIN,
                    help="lowest wrist target height relative to the pelvis (m); live safe-path rule")
    ap.add_argument("--track-neck", action="store_true", help="copy the person's torso/neck lean (off: upright)")
    ap.add_argument("--vmax", type=float, default=1.0, help="max wrist target speed (m/s)")
    ap.add_argument("--auto-calib", action="store_true", help="calibrate on the first poses (no button, no check)")
    a = ap.parse_args()
    sys.path.insert(0, ".")
    from gear_sonic.scripts.pico_manager_thread_server import (ThreePointPose, compute_hand_joints_from_inputs,
                                                               init_hand_ik_solvers)
    from gear_sonic.utils.teleop.zmq.zmq_planner_sender import build_command_message, build_planner_message
    tp = ThreePointPose(log_prefix="webcam3pt")
    lsol, rsol = init_hand_ik_solvers()
    sock = zmq.Context().socket(zmq.PUB)
    sock.bind(f"tcp://*:{a.port}")
    time.sleep(0.3)
    sock.send(build_command_message(start=False, stop=False, planner=False))
    sock.send(build_planner_message(0, [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], -1.0, -1.0))
    st = {"raw": None, "calib": [], "t0": time.time(), "closed": False, "n": 0, "armed": a.auto_calib}
    lock = threading.Lock()

    def on_msg(msg):
        if "_error" in msg:
            return
        J = {k: demo_frame(v) for k, v in msg["joints"].items()}
        try:
            p = three_point(J)
        except KeyError as e:
            print(f"[g1_vr3pt] hands_pub does not publish joint {e}; update live/hands_pub.py JOINTS", flush=True)
            return
        ap_ = float(np.linalg.norm(J["RightHandThumbEnd"] - J["RightHandIndexEnd"]))
        with lock:
            st["closed"] = ap_ < CLOSE_M if not st["closed"] else ap_ < OPEN_M
            if st["raw"] is None:
                st["raw"] = p
            else:                                           # EMA on positions, slerp-like on quaternions
                q0, q1 = st["raw"][:, 3:], p[:, 3:].copy()
                q1[np.sum(q0 * q1, 1) < 0] *= -1
                m = (1 - a.alpha) * st["raw"] + a.alpha * np.c_[p[:, :3], q1]
                m[:, 3:] /= np.linalg.norm(m[:, 3:], axis=1, keepdims=True)
                st["raw"] = m
            st["n"] += 1
            if not tp.is_calibrated and st["armed"] and time.time() >= st["t0"]:
                st["calib"].append(p)

    threading.Thread(target=read_jsonl, args=(a.hands, on_msg), daemon=True).start()
    print("[g1_vr3pt] waiting for poses; stand still, arms hanging at your sides (calibration)", flush=True)
    started, last_start, prev = False, 0.0, None
    last_poll, calib_count = 0.0, None

    def recalibrate():
        tp._calibration_neck_quat_inv = None
        tp._calibration_lwrist_offset = tp._calibration_rwrist_offset = None
        tp._calibration_lwrist_rot_offset = tp._calibration_rwrist_rot_offset = None
        nonlocal prev
        prev = None
        with lock:
            st["calib"], st["t0"], st["armed"] = [], time.time() + COUNTDOWN_S, True
        print("[g1_vr3pt] recalibrating in 3 s: stand straight, arms hanging at your sides", flush=True)
    dt = 1.0 / a.hz
    while True:
        t = time.time()
        if t - last_poll > 0.5:                              # recalibrate button on the viewer page
            last_poll = t
            try:
                import json as _json
                import urllib.request
                n = _json.loads(urllib.request.urlopen(a.cmds, timeout=0.3).read()).get("g1calib", 0)
                if calib_count is not None and n != calib_count:
                    recalibrate()
                calib_count = n
            except Exception:
                pass
        with lock:
            raw, closed = (None if st["raw"] is None else st["raw"].copy()), st["closed"]
            ready = st["armed"] and t - st["t0"] >= CALIB_S and len(st["calib"]) >= 5
            calib = list(st["calib"]) if (ready and not tp.is_calibrated) else None
            if calib is not None:
                st["armed"] = False
        if calib is not None and not arms_down(np.array(calib)):
            print("[g1_vr3pt] calibration rejected: arms were not hanging down; click again", flush=True)
            calib = None
        if calib is not None:
            C = np.array(calib)
            ref = np.c_[np.median(C[:, :, :3], 0), [R.from_quat(C[:, k, 3:], scalar_first=True).mean()
                                                     .as_quat(scalar_first=True) for k in range(3)]]
            tp._override_robot_q = np.zeros(29)
            tp._capture_calibration(ref)
            print("[g1_vr3pt] calibrated", flush=True)
        if not (raw is not None and tp.is_calibrated):
            # Until calibrated: planner mode, standing idle. The deploy only leaves damping mode on a start command
            # and may not be listening yet when we launch, so (re)send it once a second until calibration.
            if time.time() - last_start > 1.0:
                sock.send(build_command_message(start=True, stop=False, planner=True))
                last_start = time.time()
            sock.send(build_planner_message(0, [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], -1.0, -1.0))
        else:
            if not started:
                started = True
                print("[g1_vr3pt] VR 3-point streaming started", flush=True)
            v3 = tp._apply_calibration(raw)
            v3[:2, 2] = np.maximum(v3[:2, 2], a.wrist_zmin)
            if not a.track_neck:
                v3[2, 3:] = [1.0, 0.0, 0.0, 0.0]
            if prev is not None:                              # rate limit the wrist targets
                step = v3[:2, :3] - prev[:2, :3]
                n = np.linalg.norm(step, axis=1, keepdims=True)
                v3[:2, :3] = prev[:2, :3] + step * np.minimum(1.0, a.vmax * dt / np.maximum(n, 1e-9))
            prev = v3.copy()
            lh, rh = compute_hand_joints_from_inputs(lsol, rsol, 0.0, 0.0, 1.0 if closed else 0.0, 0.0)
            sock.send(build_planner_message(0, [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], speed=-1.0, height=-1.0,
                                            left_hand_position=lh.reshape(-1).astype(np.float32).tolist(),
                                            right_hand_position=rh.reshape(-1).astype(np.float32).tolist(),
                                            vr_3pt_position=v3[:, :3].flatten().tolist(),
                                            vr_3pt_orientation=v3[:, 3:].flatten().tolist()))
        time.sleep(max(0.0, dt - (time.time() - t)))


if __name__ == "__main__":
    main()
