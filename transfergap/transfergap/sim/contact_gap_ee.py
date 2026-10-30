"""Grasp-contact gap per robot (CPU, MuJoCo physics, no rendering).

At the END of the `close` phase (fingers have just closed) the distance between the tool pinch point and the object centre is the
grasp-contact gap: how far from the object's centre the robot actually grasped. At the START of `open` the horizontal distance between the
object and the goal is the release gap. Same demo, seeds and frozen fix stack as demo_repro; tool_xyz is kept only inside the worker.
Analogue of the contact-point gap reported by HOI-Retarget (0.5 cm), measured here on a simple cube, not on their data.

    python -m transfergap.sim.contact_gap_ee --demo runs/local_repro/demo.npz --fixes a,b --robots ur5e,ur10e,kairos --out DIR
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from . import errors_demo as E
from .demo_budget import HELDOUT_SEEDS, _pool
from .rollout import run_episode


def _job(a):
    spec, seed, robot, fixes, label = a
    pert, oracle, _ = E.build_perturbation(spec, seed, "full", None, fixes)
    ep = run_episode(seed, pert, label=label, oracle=oracle, condition=label, robot=robot)
    s = ep["states"]
    close = [x for x in s if x["phase"] == "close"]
    opn = [x for x in s if x["phase"] == "open"]
    g = ep["task"]["goal_xyz"]
    out = {"seed": seed, "robot": robot, "cond": label, "ok": bool(s[-1]["released"]) and math.hypot(s[-1]["object_xyz"][0] - g[0], s[-1]["object_xyz"][1] - g[1]) <= ep["task"]["position_tolerance_m"]}
    if close and "tool_xyz" in close[-1]:
        t, o = np.array(close[-1]["tool_xyz"]), np.array(close[-1]["object_xyz"])
        out["grasp_gap_cm"] = float(np.linalg.norm(t - o) * 100)
        out["grasp_gap_xy_cm"] = float(np.linalg.norm((t - o)[:2]) * 100)
    if opn:
        o = np.array(opn[0]["object_xyz"])
        out["release_gap_cm"] = float(math.hypot(o[0] - g[0], o[1] - g[1]) * 100)
    return out


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))] if xs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--fixes", required=True)
    ap.add_argument("--robots", default="ur5e")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = E.parse_demo_spec(a.demo)
    fixes = tuple(a.fixes.split(","))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {}
    for robot in a.robots.split(","):
        rows = _pool(_job, [(spec, s, robot, (), "raw") for s in HELDOUT_SEEDS] + [(spec, s, robot, fixes, "all_fixes") for s in HELDOUT_SEEDS])
        res[robot] = {}
        for c in ("raw", "all_fixes"):
            r = [x for x in rows if x["cond"] == c]
            gg = [x["grasp_gap_cm"] for x in r if "grasp_gap_cm" in x]
            rg = [x["release_gap_cm"] for x in r if "release_gap_cm" in x]
            res[robot][c] = {"n": len(r), "success": sum(x["ok"] for x in r), "grasp_gap_median_cm": q(gg, .5), "grasp_gap_p90_cm": q(gg, .9),
                             "release_gap_median_cm": q(rg, .5), "release_gap_p90_cm": q(rg, .9), "n_with_grasp": len(gg)}
            print(robot, c, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in res[robot][c].items()}, flush=True)
    (out / "contact_gap_ee.json").write_text(json.dumps({"demo": spec["tag"], "fixes": list(fixes), "results": res}, indent=1))


if __name__ == "__main__":
    main()
