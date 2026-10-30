"""Figure and number macros for the 500-seed confirmation (results/gap_budget_v3). Reads only results/gap_budget_v3/summary.json.
Writes figures/gap_budget_v3.pdf and figures/v3_numbers.tex (macros prefixed vFive / vTen)."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
S = json.loads((HERE.parent / "transfergap" / "results" / "gap_budget_v3" / "summary.json").read_text())
ARM = {"ur5e": ("vFive", "UR5e", "#1f77b4"), "ur10e": ("vTen", "UR10e", "#e08214")}
STAGES = ["perception", "retargeting", "calibration", "timing"]
CORR = {"look_again": "LookAgain", "ik_resolve": "IkResolve", "touch_probe_calibration": "TouchProbe", "speed_cap_3": "SpeedCap"}
CLAB = {"look_again": "look-\nagain", "ik_resolve": "IK\nre-solve",
        "touch_probe_calibration": "touch\nprobe", "speed_cap_3": "speed\ncap"}

def f1(x): return f"{x:.1f}"
mac = []
def m(name, val): mac.append(f"\\newcommand{{\\{name}}}{{{val}}}")
for arm, a in S["arms"].items():
    p = ARM[arm][0]
    m(p + "N", a["n"]); m(p + "FullK", a["full_successes"])
    for st, v in a["budget_pp"].items():
        n = p + "Bud" + st.capitalize(); m(n, f1(v["delta_pp"])); m(n + "Lo", f1(v["ci95_pp"][0])); m(n + "Hi", f1(v["ci95_pp"][1]))
    o = a["oracle_all_pp"]; m(p + "BudAll", f1(o["delta_pp"])); m(p + "BudAllLo", f1(o["ci95_pp"][0])); m(p + "BudAllHi", f1(o["ci95_pp"][1]))
    i = a["interaction_pp"]; m(p + "Inter", f1(i["sum_minus_all_pp"])); m(p + "InterLo", f1(i["ci95_pp"][0])); m(p + "InterHi", f1(i["ci95_pp"][1]))
    for c, v in a["corrections"].items():
        n = p + "Corr" + CORR[c]; m(n, f1(v["delta_pp"])); m(n + "Lo", f1(v["ci95_pp"][0])); m(n + "Hi", f1(v["ci95_pp"][1])); m(n + "K", v["successes"])
(HERE / "figures" / "v3_numbers.tex").write_text("\n".join(mac) + "\n")

plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 2, figsize=(6.4, 1.25), gridspec_kw={"width_ratios": [5, 4]})
def panel(axx, keys, getter, labels, title):
    w = 0.38
    for j, (arm, a) in enumerate(S["arms"].items()):
        col = ARM[arm][2]
        vals = [getter(a, k) for k in keys]
        xs = [i + (j - 0.5) * w for i in range(len(keys))]
        d = [v["delta_pp"] for v in vals]
        err = [[v["delta_pp"] - v["ci95_pp"][0] for v in vals], [v["ci95_pp"][1] - v["delta_pp"] for v in vals]]
        axx.bar(xs, d, w, yerr=err, color=col, capsize=1.5, error_kw={"lw": 0.7}, label=ARM[arm][1])
    axx.axhline(0, color="k", lw=0.5); axx.set_xticks(range(len(keys))); axx.set_xticklabels(labels, fontsize=8)
    axx.tick_params(axis="both", pad=1, length=2)
    axx.set_title(title, fontsize=8, loc="left", pad=3)
panel(ax[0], STAGES + ["all"], lambda a, k: a["oracle_all_pp"] if k == "all" else a["budget_pp"][k],
      ["percep.", "retarget.", "calib.", "timing", "all\n(joint)"], "(a) Oracle gains")
panel(ax[1], list(CORR), lambda a, k: a["corrections"][k], [CLAB[k] for k in CORR], "(b) Held-out correction gains")
ax[0].legend(frameon=False, fontsize=7, loc="upper left", bbox_to_anchor=(0.0, 1.0), handlelength=1, labelspacing=0.15, borderaxespad=0.2); ax[0].set_ylabel("paired gain, pp", labelpad=2)
ax[0].set_yticks([0, 20, 40, 60]); ax[1].set_yticks([0, 10, 20, 30])
fig.tight_layout(); fig.savefig(HERE / "figures" / "gap_budget_v3.pdf"); fig.savefig(HERE / "figures" / "gap_budget_v3.png", dpi=150)
print("ok")
