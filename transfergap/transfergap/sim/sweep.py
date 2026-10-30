"""python -m transfergap.sim.sweep --n 30 --out runs/sim/sweep.jsonl [--robot ur5e|ur10e] [--only baseline target_offset_m=0.02 ...]"""
from __future__ import annotations

import argparse
import os
import json
import multiprocessing as mp
from pathlib import Path

from ..metrics import summarize
from .perturb import PERTURBATIONS
from .rollout import run_episode
from .scene import DEFAULT_ROBOT, ROBOTS


def _job(args):
    seed, label, robot = args
    return run_episode(seed, PERTURBATIONS[label], label=label, robot=robot)


def main(argv=None):
    os.environ.setdefault("OMP_NUM_THREADS", "1")   # inherited by spawned workers; avoids BLAS oversubscription
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=30, help="seeds per perturbation")
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*", default=None, choices=list(PERTURBATIONS))
    ap.add_argument("--procs", type=int, default=max(1, (mp.cpu_count() or 2) - 2))
    ap.add_argument("--robot", default=DEFAULT_ROBOT, choices=sorted(ROBOTS))
    ap.add_argument("--video", help="also render one baseline seed-0 mp4 here")
    args = ap.parse_args(argv)
    labels = args.only or list(PERTURBATIONS)
    jobs = [(seed, lab, args.robot) for lab in labels for seed in range(args.n)]
    with mp.get_context("spawn").Pool(args.procs) as pool:
        episodes = pool.map(_job, jobs, chunksize=2)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(ep) + "\n" for ep in episodes))
    print(f"wrote {len(episodes)} episodes to {out}")
    for g in summarize(episodes)["groups"]:
        lo, hi = g["success_wilson_95"]
        print(f"{g['method']:<40} {g['successes']:>3}/{g['episodes']:<3} = {g['success_rate']:.2f}  [{lo:.2f},{hi:.2f}]")
    if args.video:
        ep = run_episode(0, PERTURBATIONS["baseline"], video_path=args.video, label="baseline", robot=args.robot)
        print("video:", ep["video"] or "SKIPPED (no working GL backend)")


if __name__ == "__main__":
    main()
