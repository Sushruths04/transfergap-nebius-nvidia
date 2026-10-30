"""Independent recount of the sensitivity study and the fresh-seed demo table from raw saved files.
Reads ../transfergap/results/sensitivity_v1/*.jsonl (one row per episode) and fresh_demos_v1/summary.json."""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parents[1] / "transfergap" / "results"
SET = ["base", "err_x0.5", "err_x2", "block_3cm", "block_5cm", "jitter_5cm", "perc_x0.25", "perc_x0.25_cal_x2"]
COMP = ["perception", "retargeting", "calibration", "timing"]
CORR = {"perception": "look_again", "retargeting": "ik_resolve", "calibration": "touch_probe_calibration", "timing": "speed_cap_3"}
out = {}
for s in SET:
    for arm in ("ur5e", "ur10e"):
        m = {}
        for l in (R / "sensitivity_v1" / f"{s}_{arm}.jsonl").read_text().splitlines():
            r = json.loads(l); m.setdefault(r["cond"], {})[r["seed"]] = r["success"]
        seeds = sorted(m["full"]); assert len(seeds) == 200 and all(sorted(v) == seeds for v in m.values()) and len(m) == 10
        d = lambda c: [m[c][x] - m["full"][x] for x in seeds]
        bud = {c: 100 * sum(d(f"oracle_{c}")) / 200 for c in COMP}
        cor = {c: [d(f"full+{CORR[c]}")[i] for i in range(200)] for c in COMP}
        dev = max(COMP, key=lambda c: sum(d(f"oracle_{c}")[:60]))        # first-in-order tie-break, as in the paper
        ev = {c: 100 * sum(cor[c][60:]) / 140 for c in COMP}
        out[f"{s}/{arm}"] = {"full": sum(m["full"].values()), "budget_pp": bud, "largest": max(COMP, key=lambda c: bud[c]),
                             "rule_pick_on_dev60": dev, "eval140_pp": {"rule": ev[dev], "always_look_again": ev["perception"],
                             "mean_of_four": sum(ev.values()) / 4, "hindsight_best": max(ev.values())}}
f = json.loads((R / "fresh_demos_v1" / "summary.json").read_text())
out["fresh_demos"] = {k: {c: [v["conditions"][c].get("successes", v["conditions"][c].get("k")), v["conditions"][c]["n"]] for c in ("raw", "stack")} | {"gap_pp": v["gap"]["delta_pp"], "ci": v["gap"]["ci95_pp"]} for k, v in f["rows"].items()}
Path(__file__).with_name("recount_sensitivity.json").write_text(json.dumps(out, indent=1))
for k, v in out.items():
    print(k, json.dumps(v if k == "fresh_demos" else {a: (round(b, 1) if isinstance(b, float) else b) for a, b in {**v, "budget_pp": {c: round(x, 1) for c, x in v["budget_pp"].items()}, "eval140_pp": {c: round(x, 1) for c, x in v["eval140_pp"].items()}}.items()}))
