"""Render the robots executing a human demo: no correction vs the frozen fix stack, one video per robot and condition.

    python -m transfergap.human.robots_render --demo demo.npz --out DIR --robots ur5e ur10e kairos_mobile [--seed 1000]

Uses exactly the episode builder of the experiments (sim.errors_demo.build_perturbation + sim.rollout.run_episode), so the videos show the
same trials that are counted in the tables for that seed. A single seed is an illustration, not evidence: the evidence is the 60-seed counts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..metrics import score_episode
from ..sim import errors_demo as E
from ..sim.rollout import run_episode

DEFAULT_FIXES = ("speed_cap_3", "look_again", "touch_probe_calibration", "speed_cap_2", "safe_path_v2")


def pick_seed(spec, robot, fixes, start=1000, tries=30):
    """First seed where the uncorrected run fails and the stack succeeds (an informative illustration; reported as such)."""
    for s in range(start, start + tries):
        r = []
        for fx in ((), tuple(fixes)):
            pert, oracle, _ = E.build_perturbation(spec, s, "full", None, fx)
            r.append(bool(score_episode(run_episode(s, pert, oracle=oracle, robot=robot))["success"]))
        if not r[0] and r[1]:
            return s
    return start


def render(demo, out, robots, seed=None, fixes=DEFAULT_FIXES, cameras=("third_person",), size=(360, 480)):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    spec = E.parse_demo_spec(str(demo))
    rows = {}
    for robot in robots:
        seed_r = seed if seed is not None else pick_seed(spec, robot, fixes)
        for cond, fx in (("raw", ()), ("stack", tuple(fixes))):
            pert, oracle, _ = E.build_perturbation(spec, seed_r, "full", None, fx)
            path = out / f"{robot}_{cond}_seed{seed_r}.mp4"
            ep = run_episode(seed_r, pert, video_path=str(path), label=cond, oracle=oracle, condition=cond, robot=robot,
                             cameras=cameras, size=size)
            sc = score_episode(ep)
            rows[f"{robot}/{cond}"] = {"seed": seed_r, "success": bool(sc["success"]), "video": str(path),
                                       "failure_reasons": sc.get("failure_reasons")}
    (out / "render_report.json").write_text(json.dumps({"demo": str(demo), "seed": seed, "fixes": list(fixes), "rows": rows}, indent=1))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--demo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--robots", nargs="+", default=["ur5e", "ur10e", "kairos_mobile"])
    ap.add_argument("--seed", type=int, default=None, help="default: first seed where raw fails and the stack succeeds")
    a = ap.parse_args()
    print(json.dumps(render(a.demo, a.out, a.robots, a.seed), indent=1))


if __name__ == "__main__":
    main()
