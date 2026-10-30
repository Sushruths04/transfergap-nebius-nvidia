"""Offline, frame-exact two-arm replay of a recorded person (no network, no real-time constraint): exported GEM-X
joints -> the live retargeting of live/arm_live.py (LiveHand) -> two UR arms (left hand | right hand) in MuJoCo ->
mp4. Calibration as the guided live mode: neutral = the first --neutral-s seconds (person standing, arms down);
anchor per hand = the frame where that hand touches its object (--anchor-right / --anchor-left, clip frames), so
touching the object maps to the robot's block.

    PYTHONPATH=. python live/arm_replay.py --joints runs/demos/live/user_take1_joints.npz --fps 21.4 \
        --anchor-right 862 --anchor-left 766 --out runs/videos/user_take1_two_arms.mp4
"""
import argparse
import json

import imageio
import mujoco
import numpy as np

from arm_live import CTRL_HZ, ArmSim, LiveHand, overlay


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--joints", required=True)
    ap.add_argument("--fps", type=float, required=True)
    ap.add_argument("--anchor-right", type=int, required=True)
    ap.add_argument("--anchor-left", type=int, required=True)
    ap.add_argument("--neutral-s", type=float, default=2.0)
    ap.add_argument("--gain", type=float, default=0.8)
    ap.add_argument("--robot", default="ur5e")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    z = np.load(a.joints, allow_pickle=False)
    names = [str(n) for n in z["joint_names"]]
    X = z["joints"]
    msg = lambda f: {"joints": {n: X[f, i].tolist() for i, n in enumerate(names)}}
    hands = {s: LiveHand(a.gain, alpha=0.6, auto=False, side=s) for s in ("Left", "Right")}
    anchors = {"Right": a.anchor_right, "Left": a.anchor_left}
    for s, h in hands.items():                       # calibration from the clip itself (offline)
        from transfergap.demo.gemx import soma_to_demo_frame
        rel = lambda f: h.body_rel({k: soma_to_demo_frame(np.array(v)) for k, v in msg(f)["joints"].items()}, s)
        n0 = int(a.neutral_s * a.fps)
        h.neutral = np.median([rel(f) for f in range(n0)], axis=0)
        h.anchor = np.median([rel(f) for f in range(anchors[s] - 2, anchors[s] + 3)], axis=0)
        h.msg = "live"
    sims = {s: ArmSim(a.robot) for s in hands}
    rend = {s: mujoco.Renderer(sims[s].m, 360, 480) for s in hands}
    sub = int(round(1.0 / CTRL_HZ / sims["Right"].m.opt.timestep))
    ticks = max(1, int(round(CTRL_HZ / a.fps)))
    frames = []
    for f in range(len(X)):
        imgs = []
        for s in ("Left", "Right"):
            h, sim = hands[s], sims[s]
            h.update(msg(f))
            for _ in range(ticks):
                sim.control(h.target, h.closed, 1.0 / CTRL_HZ)
                for _ in range(sub):
                    mujoco.mj_step(sim.m, sim.d)
            rend[s].update_scene(sim.d, camera="third_person")
            imgs.append(overlay(rend[s].render(), [f"your {s.upper()} hand", f"grip {'CLOSED' if h.closed else 'open'}",
                                                   sim.task_label(), f"t = {f / a.fps:4.1f} s"]))
        frames.append(np.concatenate(imgs, axis=1))
    imageio.mimwrite(a.out, frames, fps=a.fps)
    print(json.dumps({"out": a.out, "frames": len(frames),
                      "final_task": {s: sims[s].task_label() for s in sims}}))


if __name__ == "__main__":
    main()
