"""Closed-loop variant of stream_motion.py: corrects the planned grasp point from the robot's OWN state.

Same wire format, go/stop/done files and 50 Hz pacing as stream_motion.py. The difference: the sim runner
publishes the robot's joint positions and pelvis pose (proprioception: what encoders plus state estimation
give a real robot; never the block, table or any scene object). Each tick this streamer
  1. runs forward kinematics on the measured robot state -> measured grasp point in the world,
  2. compares it with the planned grasp point for this frame (plan made with stance offset 0),
  3. integrates the error into a bounded correction and re-solves the arm IK for (plan + correction),
     expressed in the measured pelvis frame, so a drifting or tilted stance is compensated too.
The target (block position) still comes only from the plan, i.e. from the scene configuration / perception.

    python stream_cl.py --traj plan.npz --go-file F --stop-file F --done-file F --state-port 5601 [--log out.npz]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import zmq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plan_reach import IK_JOINTS, ISAACLAB_ORDER, G1Kin  # noqa: E402


class Corrector:
    def __init__(self, sonic_root, traj, meta, ki=1.5, clamp=0.15, iters=25, pelvis_frame=True):
        self.kin = G1Kin(sonic_root, meta.get("pitch_down", 0.35), meta.get("roll", 0.0))
        self.traj, self.ki, self.clamp, self.iters, self.pelvis_frame = traj, ki, clamp, iters, pelvis_frame
        kin = self.kin
        self.q_default = kin.q_default.copy()
        self.plan_world = np.empty((len(traj["qpos"]), 3))
        for k, q in enumerate(traj["qpos"]):
            kin.d.qpos[:] = q
            kin.mj.mj_kinematics(kin.m, kin.d)
            self.plan_world[k] = kin.grasp_point()
        self.c = np.zeros(3)
        self.q_prev = traj["qpos"][0].astype(float).copy()
        self.last = None

    def measured_point(self, qmeas):
        kin = self.kin
        kin.d.qpos[:len(qmeas)] = qmeas
        kin.mj.mj_kinematics(kin.m, kin.d)
        return kin.grasp_point()

    def step_rr(self, k, qmeas, dt, active, kr=2.0, lim=1.0, damping=1e-2, w_rot=0.25):
        """Resolved-rate loop on the MEASURED pose. The deployed policy only partly follows the commanded arm joints
        (wrist pitch and elbow lose 0.4-0.6 rad), so IK on the commanded pose cannot fix the hand. Instead the task error
        (planned grasp point/orientation minus the measured one) goes through the Jacobian at the measured state and is
        integrated into a bounded per-joint offset on top of the plan: the command moves until the hand actually arrives."""
        kin, plan_q = self.kin, self.traj["qpos"][k].astype(float)
        if qmeas is None or not active:
            return plan_q, None
        mj, m, d = kin.mj, kin.m, kin.d
        d.qpos[:len(qmeas)] = qmeas
        mj.mj_kinematics(m, d)
        mj.mj_comPos(m, d)
        W, p = self.plan_world[k], kin.grasp_point()
        R = d.xmat[kin.wrist].reshape(3, 3)
        quat, er = np.zeros(4), np.zeros(3)
        mj.mju_mat2Quat(quat, (kin.R_target @ R.T).flatten())
        mj.mju_quat2Vel(er, quat, 1.0)
        jp, jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        mj.mj_jac(m, d, jp, jr, p, kin.wrist)
        cols = [kin.dadr[n] for n in IK_JOINTS]
        J = np.vstack([jp[:, cols], w_rot * jr[:, cols]])
        e = np.concatenate([W - p, w_rot * er])
        Wi = np.diag(kin.inv_cost)
        dq = Wi @ J.T @ np.linalg.solve(J @ Wi @ J.T + damping * np.eye(6), e)
        if not hasattr(self, "delta"):
            self.delta = np.zeros(len(IK_JOINTS))
        self.delta = np.clip(self.delta + kr * dt * dq, -lim, lim)
        out = plan_q.copy()
        for n, dl in zip(IK_JOINTS, self.delta):
            a = kin.qadr[n]
            out[a] = np.clip(plan_q[a] + dl, kin.lo[n], kin.hi[n])
        self.last = (W.copy(), p.copy(), self.delta[:3].copy(), float(np.linalg.norm(W - p)))
        return out, self.last

    def step(self, k, qmeas, dt, active):
        """Return the joint command (full mujoco qpos layout of the kinematic model) for plan frame k."""
        kin, plan_q = self.kin, self.traj["qpos"][k].astype(float)
        if qmeas is None or not active:
            self.q_prev = plan_q.copy()
            return plan_q, None
        W = self.plan_world[k]
        M = self.measured_point(qmeas)
        self.c = np.clip(self.c + self.ki * dt * (W - M), -self.clamp, self.clamp)
        # target in the measured pelvis frame (handles stance drift, yaw and tilt)
        Rp = np.zeros(9)
        kin.mj.mju_quat2Mat(Rp, np.asarray(qmeas[3:7], float))
        Rp = Rp.reshape(3, 3)
        T = (Rp.T @ (W + self.c - np.asarray(qmeas[:3])) + self.q_default[:3]) if self.pelvis_frame else (W + self.c)
        q0 = plan_q.copy()
        for n in IK_JOINTS:                                   # warm start from the previous command
            q0[kin.qadr[n]] = self.q_prev[kin.qadr[n]]
        q, err = kin.solve(T, q0, iters=self.iters)
        out = plan_q.copy()
        for n in IK_JOINTS:
            out[kin.qadr[n]] = q[kin.qadr[n]]
        self.q_prev = out.copy()
        self.last = (W.copy(), M.copy(), self.c.copy(), float(err))
        return out, self.last


def main():
    from gear_sonic.utils.teleop.zmq.zmq_planner_sender import pack_pose_message   # needs the sim venv
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", required=True)
    ap.add_argument("--port", type=int, default=5556)
    ap.add_argument("--state-port", type=int, default=5601)
    ap.add_argument("--go-file", required=True)
    ap.add_argument("--stop-file", required=True)
    ap.add_argument("--done-file", required=True)
    ap.add_argument("--fps", type=float, default=50.0)
    ap.add_argument("--sonic-root", default="~/GR00T-WholeBodyControl")
    ap.add_argument("--ki", type=float, default=1.5)
    ap.add_argument("--clamp", type=float, default=0.15)
    ap.add_argument("--mode", choices=["rr", "ik"], default="rr", help="rr = resolved-rate on measured pose; ik = target-shift IK")
    ap.add_argument("--kr", type=float, default=2.0, help="rr loop gain (1/s)")
    ap.add_argument("--lim", type=float, default=1.0, help="rr per-joint offset bound (rad)")
    ap.add_argument("--w-rot", type=float, default=0.25, help="rr orientation weight relative to position (m per rad)")
    ap.add_argument("--start-phase", default="approach", help="correction is active from this phase on")
    ap.add_argument("--no-pelvis-frame", action="store_true", help="integral correction only, no pelvis-pose feed-forward")
    ap.add_argument("--tail-traj", default=None,
                    help="hybrid: from --tail-from on, play this plan's joint targets open loop (blended in)")
    ap.add_argument("--tail-from", default="lift", help="phase where the open-loop tail takes over")
    ap.add_argument("--blend-s", type=float, default=1.0, help="seconds of cross-fade into the tail")
    ap.add_argument("--log", default=None)
    a = ap.parse_args()
    traj = dict(np.load(a.traj))
    meta = json.loads(Path(a.traj).with_suffix(".json").read_text())
    T = len(traj["joint_pos"])
    cor = Corrector(a.sonic_root, traj, meta, a.ki, a.clamp, pelvis_frame=not a.no_pelvis_frame)
    phase = traj["phase"]
    tail = dict(np.load(a.tail_traj)) if a.tail_traj else None
    k_tail = int(np.argmax(phase == a.tail_from)) if tail is not None else None
    if tail is not None:
        assert len(tail["joint_pos"]) == T and (tail["phase"] == phase).all(), "tail plan must have the same phases/timing"
    first_active = int(np.argmax(phase == a.start_phase))
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUB)
    sock.bind(f"tcp://*:{a.port}")
    sub = ctx.socket(zmq.SUB)
    sub.setsockopt(zmq.CONFLATE, 1)
    sub.setsockopt(zmq.SUBSCRIBE, b"")
    sub.connect(f"tcp://127.0.0.1:{a.state_port}")
    dt, fi, k = 1.0 / a.fps, 0, 0
    go, stop, done = Path(a.go_file), Path(a.stop_file), Path(a.done_file)
    t_next, started, qmeas = time.monotonic(), None, None
    prev_jp = traj["joint_pos"][0].copy()
    log = []
    while not stop.exists():
        try:
            qmeas = np.frombuffer(sub.recv(zmq.NOBLOCK), dtype=np.float64)
        except zmq.Again:
            pass
        if started is None and go.exists():
            started = time.time()
            print(f"[stream_cl] go: playing {T} frames, correction from frame {first_active}", flush=True)
        act = started is not None and k >= first_active
        cmd_q, info = cor.step_rr(k, qmeas, dt, act, a.kr, a.lim, w_rot=a.w_rot) if a.mode == "rr" else cor.step(k, qmeas, dt, act)
        jp = np.array([cmd_q[cor.kin.qadr[n]] for n in ISAACLAB_ORDER], np.float32)
        out = {"joint_pos": jp[None], "joint_vel": traj["joint_vel"][k:k + 1].astype(np.float32)}   # plan velocity: smooth, no jitter from the correction
        if tail is not None and k >= k_tail:                    # contact is done: free-space carry runs open loop
            s = min(1.0, (k - k_tail) / max(1.0, a.blend_s * a.fps))
            s = 10 * s**3 - 15 * s**4 + 6 * s**5
            jp = ((1 - s) * jp + s * tail["joint_pos"][k]).astype(np.float32)
            out["joint_pos"] = jp[None]
            out["joint_vel"] = ((1 - s) * out["joint_vel"] + s * tail["joint_vel"][k:k + 1]).astype(np.float32)
        prev_jp = jp
        sock.send(pack_pose_message({
            "joint_pos": out["joint_pos"], "joint_vel": out["joint_vel"],
            "body_quat": np.array([[1.0, 0.0, 0.0, 0.0]], np.float32),
            "frame_index": np.array([fi], np.int64),
            "left_hand_joints": traj["left_hand"][k:k + 1].astype(np.float32),
            "right_hand_joints": traj["right_hand"][k:k + 1].astype(np.float32)}, topic="pose", version=1))
        if info is not None:
            log.append([k, *info[0], *info[1], *info[2], info[3]])
        fi += 1
        if started is not None and k < T - 1:
            k += 1
            if k == T - 1:
                done.write_text(json.dumps({"frames": T, "play_s": time.time() - started}))
                print("[stream_cl] trajectory finished; holding last frame", flush=True)
        t_next += dt
        time.sleep(max(0.0, t_next - time.monotonic()))
    if a.log and log:
        np.savez_compressed(a.log, k=np.array(log)[:, 0], plan_world=np.array(log)[:, 1:4],
                            meas_world=np.array(log)[:, 4:7], correction=np.array(log)[:, 7:10],
                            ik_err=np.array(log)[:, 10])
    sock.close(0)
    sub.close(0)
    ctx.term()


if __name__ == "__main__":
    main()
