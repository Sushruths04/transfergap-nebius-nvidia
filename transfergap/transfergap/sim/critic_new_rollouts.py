"""Labelled clips of the NEW pipeline's demo (not used for any training), for scoring a video critic.

    PYTHONPATH=. python -m transfergap.sim.critic_new_rollouts --demo DIR/pipe/demo.npz --out DIR --seeds 1000-1059

For each robot (UR5e, UR10e) and each condition (raw = no correction, fix = the frozen five-fix stack) one third-person clip per
seed is rendered exactly as in sim/critic_data.py; the label is the simulator's task success (metrics.score_episode). Output:
`clips/*.mp4`, `labels.jsonl` (all rows split "test", the format cosmos_critic_eval.py reads) and `counts.json` (successes per cell,
which must equal the pipeline's repro_summary.json for the same demo and seeds).
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
from collections import Counter
from pathlib import Path

from .critic_data import STACK


def parse_seeds(s):
    lo, hi = (int(x) for x in s.split("-"))
    return range(lo, hi + 1)


def job(args):
    demo, robot, cond, seed, out = args
    from ..metrics import score_episode
    from . import errors_demo as E
    from .rollout import run_episode
    name = f"newdemo_{robot}_{cond}_s{seed}"
    path = Path(out) / "clips" / f"{name}.mp4"
    spec = E.parse_demo_spec(demo)
    pert, _, _ = E.build_perturbation(spec, seed, "full", base=STACK if cond == "fix" else ())
    ep = run_episode(seed, pert, video_path=str(path), robot=robot, size=(240, 320))
    sc = score_episode(ep)
    return {"clip": f"clips/{name}.mp4", "demo": "new_demo", "robot": robot, "condition": cond, "seed": seed,
            "split": "test", "success": bool(sc["success"]), "failure_reasons": sc["failure_reasons"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", default="1000-1059")
    ap.add_argument("--robots", nargs="+", default=["ur5e", "ur10e"])
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    (Path(a.out) / "clips").mkdir(parents=True, exist_ok=True)
    jobs = [(a.demo, r, c, s, a.out) for r in a.robots for c in ("raw", "fix") for s in parse_seeds(a.seeds)]
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    with mp.get_context("spawn").Pool(min(a.workers, mp.cpu_count())) as pool:
        rows = pool.map(job, jobs, chunksize=2)
    with open(Path(a.out) / "labels.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    cnt = {f"{r}/{c}": f"{sum(x['success'] for x in rows if x['robot'] == r and x['condition'] == c)}/"
                       f"{sum(1 for x in rows if x['robot'] == r and x['condition'] == c)}"
           for r in a.robots for c in ("raw", "fix")}
    (Path(a.out) / "counts.json").write_text(json.dumps(cnt, indent=1))
    print(json.dumps(cnt), json.dumps(dict(Counter(r["success"] for r in rows))))


if __name__ == "__main__":
    main()
