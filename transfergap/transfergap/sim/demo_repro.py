"""Independent reproduction of a demo_budget result (e.g. in a Nebius Serverless Job): held-out seeds, no fix vs
the adopted fix stack, for each robot; compares with the committed summary if present.

    python -m transfergap.sim.demo_repro --demo runs/demos/pexels_8135753_notebook.npz \
        --fixes speed_cap_3,look_again,touch_probe_calibration --out <dir>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import errors_demo as E
from .demo_budget import HELDOUT_SEEDS, _job, _pool, by_cond, cond_table, gap, res_dir, write_jsonl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--fixes", required=True)
    ap.add_argument("--robots", default="ur5e,ur10e")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = E.parse_demo_spec(a.demo)
    fixes = tuple(a.fixes.split(","))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {"demo": spec, "fixes": list(fixes), "seeds": [HELDOUT_SEEDS[0], HELDOUT_SEEDS[-1]], "robots": {}}
    for robot in a.robots.split(","):
        jobs = [(spec, s, "full", None, robot, (), "raw") for s in HELDOUT_SEEDS] + \
               [(spec, s, "full", None, robot, fixes, "all_fixes") for s in HELDOUT_SEEDS]
        eps = _pool(_job, jobs)
        write_jsonl(out / f"episodes_{robot}.jsonl", eps)
        g = by_cond(eps)
        r = {"conditions": cond_table(eps), "gap_all_fixes_minus_raw": gap(g["raw"], g["all_fixes"])}
        committed = res_dir(spec, robot, fixes[:-1]) / "heldout_results.json"
        if committed.exists():
            c = json.loads(committed.read_text())
            r["committed_cumulative_gap"] = c.get("cumulative_gap_all_fixes_minus_raw")
            r["reproduced_exactly"] = (r["committed_cumulative_gap"] or {}).get("delta_pp") == \
                r["gap_all_fixes_minus_raw"]["delta_pp"]
        res["robots"][robot] = r
    (out / "repro_summary.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: {"gap_pp": v["gap_all_fixes_minus_raw"]["delta_pp"],
                          "reproduced_exactly": v.get("reproduced_exactly")} for k, v in res["robots"].items()}))


if __name__ == "__main__":
    main()
