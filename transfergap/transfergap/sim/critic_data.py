"""Labelled robot-rollout clips for fine-tuning / evaluating a video success critic (Cosmos-Reason2).

Each clip is one simulated pick-and-place episode (UR5e or UR10e, a human-demo-driven plan, with or without the
frozen fix stack) rendered from the third-person camera; the label is the simulator's task success
(metrics.score_episode) — simulator state is used only for the label, never shown to the model except as pixels.
Seeds 2000-2059 were not used by any earlier experiment. Split (fixed here, before any training):
  train = seeds 2000-2039 of the four person-1/person-2 demos; val = seeds 2040-2049 of the same demos;
  test  = seeds 2050-2059 of the same demos  +  ALL seeds of the author's demo (an unseen person/demo).

    PYTHONPATH=. python -m transfergap.sim.critic_data --out runs/critic_data
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
from pathlib import Path

DEMOS = {"p1_notebook": "runs/demos/pexels_8135753_notebook.npz", "p1_markers": "runs/demos/pexels_8135753_markers.npz",
         "p1_notepad": "runs/demos/pexels_8135753_notepad.npz", "p2_box": "runs/demos/pexels_7205253_woman_box_v2.npz",
         "user_box": "runs/demos/live/user_take1_right.npz"}
STACK = ("speed_cap_3", "look_again", "touch_probe_calibration", "speed_cap_2", "safe_path_v2")
SEEDS = range(2000, 2060)


def split(demo, seed):
    if demo == "user_box":
        return "test"
    return "train" if seed < 2040 else ("val" if seed < 2050 else "test")


def job(args):
    demo, robot, cond, seed, out = args
    from ..metrics import score_episode
    from . import errors_demo as E
    from .rollout import run_episode
    name = f"{demo}_{robot}_{cond}_s{seed}"
    path = Path(out) / "clips" / f"{name}.mp4"
    spec = E.parse_demo_spec(DEMOS[demo])
    pert, oracle, _ = E.build_perturbation(spec, seed, "full", base=STACK if cond == "fix" else ())
    ep = run_episode(seed, pert, video_path=str(path), robot=robot, size=(240, 320))
    sc = score_episode(ep)
    return {"clip": f"clips/{name}.mp4", "demo": demo, "robot": robot, "condition": cond, "seed": seed,
            "split": split(demo, seed), "success": bool(sc["success"]), "failure_reasons": sc["failure_reasons"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runs/critic_data")
    a = ap.parse_args()
    (Path(a.out) / "clips").mkdir(parents=True, exist_ok=True)
    jobs = [(d, r, c, s, a.out) for d in DEMOS for r in ("ur5e", "ur10e") for c in ("raw", "fix") for s in SEEDS
            if d != "user_box" or s < 2015]          # the unseen demo: 15 seeds per cell is enough for testing
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    with mp.get_context("spawn").Pool(min(20, mp.cpu_count())) as pool:
        rows = pool.map(job, jobs, chunksize=2)
    with open(Path(a.out) / "labels.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    from collections import Counter
    print(json.dumps({sp: dict(Counter(r["success"] for r in rows if r["split"] == sp)) for sp in ("train", "val", "test")}))


if __name__ == "__main__":
    main()
