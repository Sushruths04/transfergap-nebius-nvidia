"""Independent recount + bootstrap intervals for sensitivity_v2 (raw one-row-per-episode files).
Groups: n500 (rule comparison, dev = first 100 seeds, eval = remaining 400), curve (perception-error sweep, budgets only),
layout (tray/block shifts), depth (perception error matched to the measured depth-estimator error).
Writes recount_v2.json and figures/scale_curve.pdf."""
import json
from pathlib import Path
import numpy as np
R = Path(__file__).resolve().parents[1] / "transfergap" / "results" / "sensitivity_v2"
COMP = ["perception", "retargeting", "calibration", "timing"]
CORR = {"perception": "look_again", "retargeting": "ik_resolve", "calibration": "touch_probe_calibration", "timing": "speed_cap_3"}
rng = np.random.default_rng(7)
B = 4000


def load(setting, arm):
    m = {}
    for l in (R / f"{setting}_{arm}.jsonl").read_text().splitlines():
        r = json.loads(l); m.setdefault(r["cond"], {})[r["seed"]] = r["success"]
    seeds = sorted(m["full"])
    assert all(sorted(v) == seeds for v in m.values())
    return seeds, {c: np.array([v[s] for s in seeds]) for c, v in m.items()}


def ci(v):
    idx = rng.integers(0, len(v), (B, len(v)))
    b = v[idx].mean(axis=1)
    return [100 * float(np.quantile(b, .025)), 100 * float(np.quantile(b, .975))]


def budgets(a):
    d = {c: a[f"oracle_{c}"] - a["full"] for c in COMP}
    return d, {c: [100 * float(v.mean()), *ci(v)] for c, v in d.items()}


out = {}
for setting in sorted({p.name.rsplit("_", 1)[0] for p in R.glob("*.jsonl")}):
    for arm in ("ur5e", "ur10e"):
        f = R / f"{setting}_{arm}.jsonl"
        if not f.exists():
            continue
        seeds, a = load(setting, arm)
        d, bud = budgets(a)
        row = {"n": len(seeds), "full": int(a["full"].sum()), "budget_pp": bud, "oracle_all_pp": 100 * float((a["oracle_all"] - a["full"]).mean()),
               "largest": max(COMP, key=lambda c: bud[c][0])}
        top, second = sorted(COMP, key=lambda c: -bud[c][0])[:2]
        gap = d[top] - d[second]
        row["top_minus_second_pp"] = [100 * float(gap.mean()), *ci(gap)]
        if f"full+{CORR['perception']}" in a:
            nd = 100 if len(seeds) == 500 else 60
            cor = {c: a[f"full+{CORR[c]}"] - a["full"] for c in COMP}
            pick = max(COMP, key=lambda c: d[c][:nd].sum())
            ev = {c: v[nd:] for c, v in cor.items()}
            hind = max(COMP, key=lambda c: ev[c].mean())
            diff = ev[pick] - ev["perception"]
            row["rule"] = {"dev_n": nd, "pick": pick, "rule_pp": [100 * float(ev[pick].mean()), *ci(ev[pick])],
                           "always_look_again_pp": [100 * float(ev["perception"].mean()), *ci(ev["perception"])],
                           "rule_minus_look_again_pp": [100 * float(diff.mean()), *ci(diff)],
                           "hindsight_best": hind, "hindsight_pp": 100 * float(ev[hind].mean()),
                           "rule_minus_hindsight_pp": [100 * float((ev[pick] - ev[hind]).mean()), *ci(ev[pick] - ev[hind])]}
        out[f"{setting}/{arm}"] = row
Path(__file__).with_name("recount_v2.json").write_text(json.dumps(out, indent=1))
for k, v in out.items():
    print(k, "full", v["full"], "/", v["n"], "largest", v["largest"], {c: round(x[0], 1) for c, x in v["budget_pp"].items()},
          "top-2nd", [round(x, 1) for x in v["top_minus_second_pp"]], ("rule " + json.dumps({a: (round(b, 1) if isinstance(b, float) else ([round(x, 1) for x in b] if isinstance(b, list) else b)) for a, b in v["rule"].items()})) if "rule" in v else "")
# figure: perception-error curve
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sc = [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
if all((R / f"curve_P{s}_ur5e.jsonl").exists() and (R / f"curve_P{s}_ur10e.jsonl").exists() for s in sc):
    fig, axs = plt.subplots(1, 2, figsize=(5.3, 1.55), sharey=True)
    col = {"perception": "#0072B2", "retargeting": "#999999", "calibration": "#D55E00", "timing": "#009E73"}
    for ax, arm in zip(axs, ("ur5e", "ur10e")):
        for c in COMP:
            y = [out[f"curve_P{s}/{arm}"]["budget_pp"][c][0] for s in sc]
            ax.plot([s * 1.5 for s in sc], y, marker="o", ms=3, lw=1.2, color=col[c], label=c)
        ax.set_xscale("log"); ax.set_xlabel("injected perception $\\sigma$ (cm)", fontsize=7, labelpad=1); ax.set_title(arm.replace("ur", "UR"), fontsize=8)
        ax.axvline(1.5, color="k", ls=":", lw=.6); ax.set_xticks([0.15, 0.4, 0.75, 1.5, 3.0]); ax.set_xticklabels(["0.15", "0.4", "0.75", "1.5", "3"])
        ax.tick_params(labelsize=6.5, pad=1.5); ax.axhline(0, color="k", lw=.4)
    axs[0].set_ylabel("budget (pp)", fontsize=7, labelpad=1); axs[0].legend(fontsize=6, frameon=False, loc="upper left", handlelength=1.2, labelspacing=0.2)
    fig.tight_layout(); fig.savefig(Path(__file__).parent / "figures" / "scale_curve.pdf"); print("figure written")
