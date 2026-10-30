"""Depth perception in the loop: estimator accuracy and pick-and-place success when the controller's belief comes
from a simulated depth camera instead of the ground truth. DEV sweep (seeds 0-9 by default): used to find failures
and set nothing in stone; a held-out run with a frozen protocol comes after.

    PYTHONPATH=. MUJOCO_GL=egl python -m transfergap.sim.perception_eval --robot kairos --out results/perception_dev_v1

Conditions per (robot, block size): `truth_belief` (the controller as before, reads the block pose in perceive())
and `depth_sigma_<mm>` (belief from sim/perception.py with Gaussian depth noise). Success = the repo scorer.
Ground truth is used HERE only to measure the estimate's error; the estimator never sees it.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from .. import metrics
from .perception import Perceiver
from .rollout import run_episode
from .scene import BLOCK_HALF, Scene

MAX_WIDTH_M = {"ur5e": 0.085, "ur10e": 0.085, "kairos": 0.128}     # gripper opening (kairos: measured pad gap, 128.5 mm)
SIZES = (0.015, 0.02, 0.025, 0.03, 0.035)                           # block half sizes: 3 to 7 cm cubes
SIGMAS_M = (0.0, 0.002, 0.005)


def parse_range(s):
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def accuracy_case(robot, seed, half, sigma):
    scene = Scene(seed, robot, half)
    est = Perceiver(MAX_WIDTH_M[robot], sigma_m=sigma)(scene)
    b = est["info"]["block"]
    return dict(xy_mm=float(1e3 * np.hypot(*(est["block_xyz"][:2] - scene.block_pos()[:2]))),
                z_mm=float(1e3 * abs(est["block_xyz"][2] - scene.block_pos()[2])),
                goal_xy_mm=float(1e3 * np.hypot(*(est["goal_xyz"][:2] - scene.goal_xyz[:2]))),
                goal_z_mm=float(1e3 * abs(est["goal_xyz"][2] - scene.goal_xyz[2])),
                height_mm=float(1e3 * (b["height"] - 2 * half)), width_x_mm=float(1e3 * (b["extent_x"] - 2 * half)))


def episode_success(robot, seed, half, sigma):
    perceiver = None if sigma is None else Perceiver(MAX_WIDTH_M[robot], sigma_m=sigma)
    try:
        ep = run_episode(seed, robot=robot, block_half=half, perceiver=perceiver)
    except RuntimeError as e:                                       # perception failed: counts as a failure, recorded
        return dict(success=False, reasons=["perception_failed"], error=str(e)[:120], final_error_m=None)
    sc = metrics.score_episode(ep)
    return dict(success=bool(sc["success"]), reasons=sc["failure_reasons"], final_error_m=sc["final_object_error_m"])


def summarize(vals):
    a = np.array(vals, float)
    return dict(median=float(np.median(a)), p95=float(np.percentile(a, 95)), max=float(a.max()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--robot", default="kairos", choices=sorted(MAX_WIDTH_M))
    ap.add_argument("--seeds", default="0-9")
    ap.add_argument("--sizes", type=float, nargs="*", default=list(SIZES))
    ap.add_argument("--sigmas-mm", type=float, nargs="*", default=[1e3 * s for s in SIGMAS_M])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    seeds = parse_range(a.seeds)
    res = dict(robot=a.robot, seeds=seeds, status="DEV sweep, not held-out", sizes_half_m=a.sizes, cells={})
    t0 = time.time()
    for half in a.sizes:
        for sig_mm in [None] + list(a.sigmas_mm):
            name = "truth_belief" if sig_mm is None else f"depth_sigma_{sig_mm:g}mm"
            sigma = None if sig_mm is None else sig_mm / 1e3
            rows = [episode_success(a.robot, s, half, sigma) for s in seeds]
            cell = dict(n=len(rows), success=int(sum(r["success"] for r in rows)),
                        failures=sorted({x for r in rows for x in r["reasons"]}))
            if sigma is not None:
                acc = [accuracy_case(a.robot, s, half, sigma) for s in seeds]
                cell["estimate_error"] = {k: summarize([r[k] for r in acc]) for k in acc[0]}
            res["cells"][f"half{half:g}/{name}"] = cell
            print(f"{a.robot} block {2e3*half:.0f} mm {name}: {cell['success']}/{cell['n']} {cell['failures']}  "
                  f"({time.time()-t0:.0f}s)", flush=True)
    out = Path(a.out) / a.robot
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(res, indent=1))
    L = [f"# Depth perception in the loop, DEV sweep ({a.robot}, seeds {a.seeds})", "",
         "Block cube side in mm; success = repo scorer; estimate error = median / p95 / max in mm against ground truth "
         "(measurement only).", "", "| block | condition | success | block xy | block z | goal xy | height err |",
         "|---|---|---|---|---|---|---|"]
    for k, c in res["cells"].items():
        e = c.get("estimate_error")
        f = lambda m: "-" if e is None else f"{e[m]['median']:.1f} / {e[m]['p95']:.1f} / {e[m]['max']:.1f}"
        half, name = k.split("/")
        L.append(f"| {2e3*float(half[4:]):.0f} | {name} | {c['success']}/{c['n']} | {f('xy_mm')} | {f('z_mm')} | "
                 f"{f('goal_xy_mm')} | {f('height_mm')} |")
    (out / "summary.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
