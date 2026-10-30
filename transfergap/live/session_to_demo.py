"""Live session -> HumanDemo: the pick-and-place a person just performed in front of the webcam becomes a demo for
the offline pipeline (feasibility pre-check, gap budget, fixes, held-out verification).

    PYTHONPATH=. python live/session_to_demo.py runs/live/<stem> --out runs/demos/live_<name>.npz [--cycle 0]

Inputs: <stem>_joints.npz (received SOMA joints + capture times) and <stem>_robot.npz (the live gripper command per
frame) from live/arm_live.py. Frames arrive unevenly, so joints are resampled to RESAMPLE_FPS on the capture clock.
Grasp/release = the frames where the person's live gripper command closed and opened (what they intended, seen
live on screen), used as segmenter events like the hand-annotated Pexels events. --cycle picks which
close->open cycle; the clip window is the cycle plus PAD_S on both sides. Object = pinch at grasp (no object
detector, as for the Pexels demos).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from transfergap.demo.gemx import demo_from_joints

RESAMPLE_FPS = 25.0
PAD_S = 1.5


def cycles(closed):
    c = np.asarray(closed, bool)
    starts = np.flatnonzero(~c[:-1] & c[1:]) + 1
    out = []
    for s in starts:
        ends = np.flatnonzero(~c[s:])
        if ends.size:
            out.append((int(s), int(s + ends[0])))
    return out


def session_demo(stem, cycle=0, object_height="hand_at_grasp"):
    J = np.load(f"{stem}_joints.npz", allow_pickle=False)
    R = np.load(f"{stem}_robot.npz", allow_pickle=False)
    t = J["t_cap"] - J["t_cap"][0]
    keep = np.r_[True, np.diff(t) > 1e-4]
    t, joints, closed = t[keep], J["joints"][keep], R["closed"][keep]
    cyc = cycles(closed)
    if len(cyc) <= cycle:
        raise SystemExit(f"session has {len(cyc)} close->open cycles; cannot use cycle {cycle}")
    g, r = cyc[cycle]
    a, b = max(0.0, t[g] - PAD_S), min(t[-1], t[r] + PAD_S)
    tu = np.arange(a, b, 1.0 / RESAMPLE_FPS)
    ju = np.stack([np.stack([np.interp(tu, t, joints[:, k, i]) for i in range(3)], -1)
                   for k in range(joints.shape[1])], 1)
    ev = {"grasp": int(round((t[g] - a) * RESAMPLE_FPS)), "release": int(round((t[r] - a) * RESAMPLE_FPS))}
    meta = {"source_session": Path(stem).name, "cycle": cycle, "events_from": "live gripper command (pinch)",
            "resampled_fps": RESAMPLE_FPS, "n_cycles_in_session": len(cyc)}
    return demo_from_joints(ju, J["joint_names"], RESAMPLE_FPS, "Right", meta, None, ev, object_height)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stem")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cycle", type=int, default=0)
    ap.add_argument("--object-height", default="hand_at_grasp", choices=["hand_at_grasp", "lowest_hand"])
    a = ap.parse_args()
    d = session_demo(a.stem, a.cycle, a.object_height)
    d.save(a.out)
    print(json.dumps({"out": a.out, "frames": len(d.t), "duration_s": round(float(d.t[-1]), 2), **d.meta}, indent=1))


if __name__ == "__main__":
    main()
