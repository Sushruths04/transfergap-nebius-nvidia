"""Three-embodiment summary figure from committed results (no new rollouts): one real human demo (Pexels 8135753)
driving UR5e, UR10e and G1. (a) arm held-out success along the diagnosis-chosen fix chain, Wilson 95% CI;
(b) G1 place rate by execution speed; (c) style: path RMSE to the retargeted human path.

    python -m transfergap.sim.matched_figure --out results/matched_three_embodiments
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..metrics import wilson_interval
from .gap_budget import ROOT

TAG = "demo1bc4be60"
CHAIN = [((), "speed_cap_3"), (("speed_cap_3",), "look_again"),
         (("speed_cap_3", "look_again"), "touch_probe_calibration"),
         (("speed_cap_3", "look_again", "touch_probe_calibration"), "speed_cap_2")]


def arm_chain(robot):
    pts = []
    for i, (base, fix) in enumerate(CHAIN):
        d = ROOT / "results" / (f"demo_budget_v1_{TAG}_{robot}" + ("" if not base else "__after-" + "+".join(base)))
        h = json.loads((d / "heldout_results.json").read_text())
        if i == 0:
            t = h["conditions"]["full"]
            pts.append(("no fix", t["successes"], t["n"], h["style"]["full"]["path_rmse_mean_m"]))
        t = h["conditions"][f"full+{fix}"]
        pts.append(("+ " + fix, t["successes"], t["n"], h["style"][f"full+{fix}"]["path_rmse_mean_m"]))
    return pts


def g1_rows():
    s = json.loads((ROOT / "results" / "g1_style_v1" / "summary.json").read_text())
    st = json.loads((ROOT / "results" / "g1_style_v1" / "style.json").read_text())
    rows = []
    for cond, label in (("style_human_pace", "human pace"), ("style_speed_cap_3", "speed cap 3x"),
                        ("style_nominal_pace", "robot pace")):
        c = s["conditions"][cond]["place_rollout_rate"]
        rows.append((label, c["k"], c["n"], st[cond]["path_rmse_median_m"]))
    return rows


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    arms = {r: arm_chain(r) for r in ("ur5e", "ur10e")}
    g1 = g1_rows()
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.8), gridspec_kw={"width_ratios": [2.2, 1, 1.4]})
    for r, c, off in (("ur5e", "#1f77b4", -0.08), ("ur10e", "#ff7f0e", 0.08)):
        xs = [i + off for i in range(len(arms[r]))]
        ys = [k / n for _, k, n, _ in arms[r]]
        lo = [max(0.0, y - wilson_interval(k, n)[0]) for y, (_, k, n, _) in zip(ys, arms[r])]
        hi = [max(0.0, wilson_interval(k, n)[1] - y) for y, (_, k, n, _) in zip(ys, arms[r])]
        ax[0].errorbar(xs, ys, yerr=[lo, hi], marker="o", capsize=3, color=c, label=r.upper())
    ax[0].set_xticks(range(len(arms["ur5e"])), [p[0] for p in arms["ur5e"]], rotation=15, fontsize=8)
    ax[0].set_ylim(-0.03, 1.05)
    ax[0].set_ylabel("held-out success (n=60, Wilson 95%)")
    ax[0].set_title("(a) Arms: diagnosis-chosen fixes, one at a time", fontsize=10)
    ax[0].legend()
    ys = [k / n for _, k, n, _ in g1]
    err = [[max(0.0, y - wilson_interval(k, n)[0]) for y, (_, k, n, _) in zip(ys, g1)],
           [max(0.0, wilson_interval(k, n)[1] - y) for y, (_, k, n, _) in zip(ys, g1)]]
    ax[1].bar(range(3), ys, yerr=err, capsize=3, color="#2ca02c")
    ax[1].set_xticks(range(3), [g[0] for g in g1], fontsize=8)
    ax[1].set_ylim(0, 1.05)
    ax[1].set_title("(b) G1 humanoid: place rate (30 rollouts)", fontsize=10)
    labels = ["UR5e no fix", "UR5e 4 fixes", "UR10e no fix", "UR10e 4 fixes", "G1 human pace", "G1 robot pace"]
    vals = [arms["ur5e"][0][3], arms["ur5e"][-1][3], arms["ur10e"][0][3], arms["ur10e"][-1][3], g1[0][3], g1[2][3]]
    ax[2].barh(range(6), [100 * v for v in vals], color=["#1f77b4", "#1f77b4", "#ff7f0e", "#ff7f0e", "#2ca02c",
                                                        "#2ca02c"], alpha=0.85)
    ax[2].set_yticks(range(6), labels, fontsize=8)
    ax[2].invert_yaxis()
    ax[2].set_xlabel("path RMSE to the human's retargeted hand path (cm)")
    ax[2].set_title("(c) Style: how closely the robot follows the human", fontsize=10)
    fig.suptitle("One real human video (Pexels 8135753) → three robots. Simulation (MuJoCo; G1 under GEAR-SONIC).",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "matched_three_embodiments.png", dpi=130)
    (out / "matched_three_embodiments.json").write_text(json.dumps(
        {"arms": {r: [{"step": s, "k": k, "n": n, "path_rmse_m": p} for s, k, n, p in v] for r, v in arms.items()},
         "g1": [{"condition": s, "k": k, "n": n, "path_rmse_median_m": p} for s, k, n, p in g1],
         "note": "arm style = mean path RMSE of the tool point; G1 style = median wrist path RMSE"}, indent=1))
    print("ok")


if __name__ == "__main__":
    main()
