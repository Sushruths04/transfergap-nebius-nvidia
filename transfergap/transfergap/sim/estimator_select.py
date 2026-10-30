"""Per-demo pose-estimator selection (pose_estimator_bakeoff_v2): treat the human pose estimator as one more stage
of the transfer gap and choose it per demo x arm on DEV seeds, then verify on held-out seeds.

Candidates: gemx, fast_sam_3d_body (demos built in v1, runs/demos/bakeoff/) and fast_sam_3d_body_smooth = the same
Fast SAM demo after the pipeline's existing moving-average correction (errors_demo._smooth_path, SMOOTH_WINDOW_S,
fixed since demo_budget_v1). Selection: highest dev success with the demo's frozen v5 stack; ties -> the protocol's
candidate order (incumbent first). Held-out: the selected candidate vs gemx, paired by seed.

    PYTHONPATH=. python -m transfergap.sim.estimator_select dev      # writes dev_selection.json (commit it)
    PYTHONPATH=. python -m transfergap.sim.estimator_select heldout  # refuses unless protocol + selection committed
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..demo.schema import HumanDemo
from . import errors_demo as E

OUT = Path("results/pose_estimator_bakeoff_v2")


def demo_path(cand, clip):
    if cand == "fast_sam_3d_body_smooth":
        p = Path(f"runs/demos/bakeoff/fast_sam_3d_body_smooth_{clip}.npz")
        if not p.exists():
            d = HumanDemo.load(f"runs/demos/bakeoff/fast_sam_3d_body_{clip}.npz")
            E._smooth_path(d, E.SMOOTH_WINDOW_S).save(p)
        return str(p)
    return f"runs/demos/bakeoff/{cand}_{clip}.npz"


def _rate(eps, cond):
    from .gap_budget import by_cond
    from ..metrics import score_episode
    rows = by_cond(eps)[cond]
    return sum(score_episode(e)["success"] for e in rows), len(rows)


def dev():
    from .demo_budget import DEV_SEEDS, _job, _pool
    from .gap_budget import _committed
    P = json.loads((OUT / "protocol.json").read_text())
    if not _committed((OUT / "protocol.json").resolve()):
        raise SystemExit("protocol.json must be committed before the dev run")
    seeds = list(range(P["dev_seeds"][0], P["dev_seeds"][1] + 1))
    sel = {}
    for clip, cfg in P["demos"].items():
        for robot in P["robots"]:
            scores = {}
            for cand in P["candidates"]:
                spec = E.parse_demo_spec(demo_path(cand, clip))
                eps = _pool(_job, [(spec, s, "full", None, robot, tuple(cfg["stack"]), "stack") for s in seeds])
                scores[cand] = _rate(eps, "stack")
            best = max(P["candidates"], key=lambda c: (scores[c][0], -P["candidates"].index(c)))
            sel[f"{clip}|{robot}"] = {"dev": {c: f"{k}/{n}" for c, (k, n) in scores.items()}, "selected": best}
            print(clip, robot, sel[f"{clip}|{robot}"], flush=True)
    (OUT / "dev_selection.json").write_text(json.dumps(sel, indent=1) + "\n")


def heldout():
    from .demo_budget import HELDOUT_SEEDS, _job, _pool, by_cond, gap
    from .gap_budget import _committed
    for f in ("protocol.json", "dev_selection.json"):
        if not _committed((OUT / f).resolve()):
            raise SystemExit(f"{f} must be committed before held-out")
    P = json.loads((OUT / "protocol.json").read_text())
    sel = json.loads((OUT / "dev_selection.json").read_text())
    rows, tot = [], {"gemx": [0, 0], "selected": [0, 0]}
    for key, v in sel.items():
        clip, robot = key.split("|")
        stack = tuple(P["demos"][clip]["stack"])
        res = {}
        for name, cand in (("gemx", "gemx"), ("selected", v["selected"])):
            spec = E.parse_demo_spec(demo_path(cand, clip))
            res[name] = _pool(_job, [(spec, s, "full", None, robot, stack, name) for s in HELDOUT_SEEDS])
        k0, n0 = _rate(res["gemx"], "gemx")
        k1, n1 = _rate(res["selected"], "selected")
        tot["gemx"][0] += k0; tot["gemx"][1] += n0; tot["selected"][0] += k1; tot["selected"][1] += n1
        same = lambda eps: [{**e, "demo_id": "pose_estimator_bakeoff"} for e in eps]   # pair by seed across demos
        g = gap(same(by_cond(res["gemx"])["gemx"]), same(by_cond(res["selected"])["selected"]))
        rows.append({"demo": clip, "robot": robot, "selected": v["selected"], "dev": v["dev"],
                     "gemx": f"{k0}/{n0}", "selected_heldout": f"{k1}/{n1}", "gap_selected_minus_gemx": g})
        print(clip, robot, v["selected"], f"{k0}/{n0} -> {k1}/{n1}", flush=True)
    (OUT / "heldout_results.json").write_text(json.dumps({"rows": rows, "total": tot}, indent=1) + "\n")
    L = ["# Per-demo pose-estimator selection — pose_estimator_bakeoff_v2 (held-out)", "",
         "| demo | arm | dev (gemx / fsam / fsam smooth, n=20) | selected | held-out gemx | held-out selected | "
         "gap pp [95% CI] |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        g = r["gap_selected_minus_gemx"]
        L.append(f"| {r['demo']} | {r['robot']} | {' / '.join(r['dev'].values())} | {r['selected']} | {r['gemx']} | "
                 f"{r['selected_heldout']} | {g['delta_pp']:+.1f} [{g['ci95_pp'][0]:+.1f}, {g['ci95_pp'][1]:+.1f}] |")
    L += ["", f"Total held-out: gemx {tot['gemx'][0]}/{tot['gemx'][1]}, per-demo selected "
              f"{tot['selected'][0]}/{tot['selected'][1]}."]
    (OUT / "summary.md").write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "heldout"])
    a = ap.parse_args()
    dev() if a.stage == "dev" else heldout()


if __name__ == "__main__":
    main()
