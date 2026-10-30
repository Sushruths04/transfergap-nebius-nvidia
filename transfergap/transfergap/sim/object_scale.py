"""Object-size sweep of a demo transfer (CPU only, MuJoCo physics, no rendering).

Same held-out seeds and the same frozen fix stack as `demo_repro`, but the cube is scaled (same density at every size). Idea taken from
HOI-Retarget's object-scale experiments: does the copied style survive when the object is resized? The fix stack was NOT tuned for these
sizes, so a drop at an extreme size is a finding, not a bug.

    python -m transfergap.sim.object_scale --demo runs/local_repro/demo.npz --fixes a,b,c --robots ur5e,ur10e,kairos --out DIR
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import errors_demo as E
from .demo_budget import HELDOUT_SEEDS, _pool, by_cond, cond_table, gap, write_jsonl
from .rollout import run_episode

HALVES = (0.015, 0.02, 0.025, 0.03, 0.035)        # half edge in metres; 0.02 is the default 4 cm cube; gripper opening limits ~0.042


def _job(a):
    spec, seed, robot, fixes, label, half = a
    pert, oracle, _ref = E.build_perturbation(spec, seed, "full", None, fixes)
    ep = run_episode(seed, pert, label=label, oracle=oracle, condition=label, robot=robot, block_half=half)
    ep["block_half_m"] = half
    for s in ep["states"]:
        s.pop("tool_xyz", None)
    ep["perturbation"]["demo_plan"] = {k: v for k, v in ep["perturbation"]["demo_plan"].items() if k != "style"}
    return ep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--fixes", required=True)
    ap.add_argument("--robots", default="ur5e")
    ap.add_argument("--halves", default=",".join(str(h) for h in HALVES))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = E.parse_demo_spec(a.demo)
    fixes = tuple(a.fixes.split(","))
    halves = [float(h) for h in a.halves.split(",")]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {"demo": spec["tag"], "fixes": list(fixes), "seeds": [HELDOUT_SEEDS[0], HELDOUT_SEEDS[-1]], "robots": {}}
    for robot in a.robots.split(","):
        res["robots"][robot] = {}
        for h in halves:
            jobs = [(spec, s, robot, (), "raw", h) for s in HELDOUT_SEEDS] + [(spec, s, robot, fixes, "all_fixes", h) for s in HELDOUT_SEEDS]
            eps = _pool(_job, jobs)
            write_jsonl(out / f"episodes_{robot}_half{h}.jsonl", eps)
            g = by_cond(eps)
            res["robots"][robot][f"{2 * h * 100:.1f}cm"] = {"conditions": cond_table(eps), "gap": gap(g["raw"], g["all_fixes"])}
            c = res["robots"][robot][f"{2 * h * 100:.1f}cm"]["conditions"]
            print(robot, f"{2 * h * 100:.1f} cm", {k: f"{v['successes']}/{v['n']}" for k, v in c.items()}, flush=True)
            (out / "object_scale_summary.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
