"""Verified data engine, step 1: roll out ONE human demo on one or more robots over many seeds with the frozen fix stack and write
per-episode joint-state / action traces plus the physics verdict and failure reasons (CPU, MuJoCo, no rendering).

    python scripts/export_dataset.py --demo demo.npz --robots ur5e,ur10e,kairos --seeds 1000-1019 --out runs/dataset_v1
Every episode is kept with its label (success / why it failed); `scripts/to_lerobot.py` converts the verified successes to a LeRobot-style
parquet dataset. Nothing here is a trained policy; it is training DATA derived from one demonstration.
"""
import argparse
import json
from pathlib import Path

from transfergap.metrics import score_episode
from transfergap.sim import errors_demo as E
from transfergap.sim.rollout import run_episode

FIXES = ("speed_cap_3", "look_again", "touch_probe_calibration", "speed_cap_2", "safe_path_v2")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--robots", default="ur5e")
    ap.add_argument("--seeds", default="1000-1019")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lo, hi = map(int, a.seeds.split("-"))
    spec = E.parse_demo_spec(a.demo)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta = {"demo": spec["tag"], "fixes": list(FIXES), "episodes": []}
    for robot in a.robots.split(","):
        for seed in range(lo, hi + 1):
            pert, oracle, _ = E.build_perturbation(spec, seed, "full", None, FIXES)
            tr = []
            ep = run_episode(seed, pert, oracle=oracle, robot=robot, trace=tr)
            sc = score_episode(ep)
            name = f"{robot}_seed{seed}"
            (out / f"{name}.json").write_text(json.dumps({"robot": robot, "seed": seed, "trace": tr}))
            meta["episodes"].append({"name": name, "robot": robot, "seed": seed, "success": bool(sc["success"]),
                                     "failure_reasons": sc.get("failure_reasons"), "steps": len(tr)})
            print(name, meta["episodes"][-1]["success"], len(tr), flush=True)
    (out / "index.json").write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
