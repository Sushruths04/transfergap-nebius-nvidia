"""Paper figures and number macros for the Transfer Gap Budget short paper.

Reads ONLY result files; no number in the paper or a figure is typed by hand.
  transfergap/results/gap_budget_v2_{ur5e,ur10e}/{summary,protocol}.json   main result (two arms)
  transfergap/results/gap_budget_v1/{dev_results,heldout_results,protocol}.json   pilot run (UR5e)
  transfergap/results/FREEZE_HASHES.md   recorded (pre-rewrite) -> published commit hashes
  paper/data/diagnosis_dev_snapshot.json   LLM-vs-rule diagnosis on dev seeds (see below)

The diagnosis run directory (transfergap/runs/diagnose/<stamp>/) is gitignored, so the numbers the paper
quotes are copied into paper/data/diagnosis_dev_snapshot.json by
  python paper/make_figures.py --diagnose-run <path to runs/diagnose/<stamp>>
which reads report.json + nemotron_super_receipt.json and keeps only the fields below (no key, no prompt).
Without the flag the committed snapshot is used.

Run from anywhere (paths are resolved relative to this file), e.g.
  transfergap/.venv/bin/python paper/make_figures.py
Writes paper/figures/*.pdf (+ .png previews) and paper/figures/numbers.tex.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
RESULTS = REPO / "transfergap" / "results"
V1 = RESULTS / "gap_budget_v1"
V2 = {"ur5e": RESULTS / "gap_budget_v2_ur5e", "ur10e": RESULTS / "gap_budget_v2_ur10e"}
FREEZE_MD = RESULTS / "FREEZE_HASHES.md"
DIAG_SNAPSHOT = HERE / "data" / "diagnosis_dev_snapshot.json"
OUT = HERE / "figures"

ROBOT_LABEL = {"ur5e": "UR5e", "ur10e": "UR10e"}
PREFIX = {"ur5e": "five", "ur10e": "ten"}      # macro prefixes, e.g. \fiveHoGap, \tenBudAll
COMPS = ["perception", "retargeting", "calibration", "timing"]

# Okabe-Ito (colour-blind safe); robot identity also carried by hatch, legend and axis labels.
BLUE, ORANGE, GREY, INK, MUTED = "#0072B2", "#E69F00", "#8C8C8C", "#222222", "#666666"
COL = {"ur5e": BLUE, "ur10e": ORANGE}
HATCH = {"ur5e": "", "ur10e": "////"}
plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6, "xtick.color": INK, "ytick.color": INK,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#E3E3E3", "grid.linewidth": 0.5,
    "axes.axisbelow": True, "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "hatch.linewidth": 0.5, "hatch.color": "white",
})


def jload(p):
    return json.loads(Path(p).read_text())


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=200)
    plt.close(fig)


def errbars(vals, cis):
    # max(0, .) only absorbs float round-off (e.g. Wilson upper 99.9999...% at 60/60)
    return [[max(0.0, v - c[0]) for v, c in zip(vals, cis)], [max(0.0, c[1] - v) for v, c in zip(vals, cis)]]


# ---------------------------------------------------------------- figures (v2, two arms)

def fig_v2(v2):
    """(a) dev gap budget per stage, both arms; (b) held-out before/after per arm."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.9, 2.25), gridspec_kw={"width_ratios": [1.75, 1]})
    w = 0.38
    groups = COMPS + ["all four"]
    for j, r in enumerate(v2):
        dev = v2[r]["summary"]["dev"]
        b, it = dev["budget"], dev["interaction"]
        vals = [b[c]["delta_pp"] for c in COMPS] + [it["oracle_all_recovery_pp"]]
        cis = [b[c]["ci95_pp"] for c in COMPS] + [it["oracle_all"]["ci95_pp"]]
        xs = [i + (j - 0.5) * w for i in range(len(groups))]
        a1.bar(xs, vals, width=w * 0.92, color=COL[r], hatch=HATCH[r], yerr=errbars(vals, cis), capsize=2,
               error_kw={"elinewidth": 0.7, "ecolor": INK}, label=ROBOT_LABEL[r])
        for x, v, c in zip(xs, vals, cis):
            a1.text(x, max(c[1], 0) + 1.0, f"{v:+.1f}", ha="center", va="bottom", fontsize=5.5, color=INK)
        s = it["sum_of_single_recoveries_pp"]
        x4 = xs[-1]
        a1.plot([x4 - w / 2, x4 + w / 2], [s, s], color=INK, lw=1.0, ls=(0, (2, 1)))
    a1.plot([], [], color=INK, lw=1.0, ls=(0, (2, 1)), label="sum of singles")
    a1.axhline(0, color=INK, lw=0.6)
    a1.set_xticks(range(len(groups)), groups)
    a1.set_ylim(-20, 72)
    a1.set_ylabel("recovered success (pp)\npaired bootstrap 95% CI")
    n = v2["ur5e"]["summary"]["dev"]["budget"]["perception"]["n"]
    s0, s1 = v2["ur5e"]["summary"]["dev"]["seeds"]
    a1.set_title(f"(a) Dev gap budget $B_k$ (seeds {s0}-{s1}, n={n} paired per arm)", loc="left")
    a1.legend(loc="upper left", fontsize=6.5, frameon=False, ncol=3, handlelength=1.6)

    xt, labels = [], []
    for j, r in enumerate(v2):
        h = v2[r]["summary"]["heldout"]
        keys = ["full", f"full+{h['correction']}"]
        y = [100 * h["conditions"][k]["success_rate"] for k in keys]
        ci = [[100 * x for x in h["conditions"][k]["wilson_95"]] for k in keys]
        xs = [3 * j, 3 * j + 1]
        a2.bar(xs, y, width=0.8, color=[GREY, COL[r]], yerr=errbars(y, ci), capsize=2,
               error_kw={"elinewidth": 0.7, "ecolor": INK})
        for x, k in zip(xs, keys):
            c = h["conditions"][k]
            a2.text(x, 2, f"{c['successes']}/{c['n']}", ha="center", va="bottom", fontsize=6, color="white")
        g = h["paired_gap_corrected_minus_full"]
        a2.text(3 * j + 0.5, 101, f"{ROBOT_LABEL[r]}: {g['delta_pp']:+.1f} pp\n[{g['ci95_pp'][0]:+.1f}, {g['ci95_pp'][1]:+.1f}]",
                ha="center", va="bottom", fontsize=6, color=INK)
        xt += xs
        labels += ["full", "+look-\nagain"]
    a2.set_xticks(xt, labels, fontsize=6.5)
    a2.set_ylim(0, 122)
    a2.set_yticks([0, 20, 40, 60, 80, 100])
    a2.set_ylabel("success (%), Wilson 95% CI")
    h0 = v2["ur5e"]["summary"]["heldout"]["seeds"]
    a2.set_title(f"(b) Held-out seeds {h0[0]}-{h0[1]}", loc="left")
    fig.tight_layout(w_pad=1.2)
    save(fig, "gap_budget_v2")


# ---------------------------------------------------------------- macros

def freeze_map():
    """recorded (pre-rewrite) short hash -> published short hash, from FREEZE_HASHES.md."""
    out = {}
    for line in FREEZE_MD.read_text().splitlines():
        m = re.match(r"\|\s*`([0-9a-f]{7})`\s*\|\s*`([0-9a-f]{7})`\s*\|", line)
        if m:
            out[m.group(1)] = m.group(2)
    assert out, "no hash rows parsed from FREEZE_HASHES.md"
    return out


def macro_name(s):
    return "".join(ch for ch in s.title() if ch.isalpha())


class Macros:
    def __init__(self, header):
        self.lines = [header]
        self.names = set()

    def __call__(self, name, val):
        assert re.fullmatch(r"[A-Za-z]+", name), name
        assert name not in self.names, f"duplicate macro {name}"
        self.names.add(name)
        self.lines.append(f"\\newcommand{{\\{name}}}{{{val}}}")

    def write(self, path):
        path.write_text("\n".join(self.lines) + "\n")


pct = lambda x: f"{100 * x:.0f}"  # noqa: E731
pp = lambda x: f"{x:+.1f}".replace("-", "$-$")  # noqa: E731  (typographic minus in text)


def cond_macros(m, p, t):
    m(p + "K", t["successes"]); m(p + "N", t["n"]); m(p + "Pct", pct(t["success_rate"]))
    m(p + "Lo", pct(t["wilson_95"][0])); m(p + "Hi", pct(t["wilson_95"][1]))


def gap_macros(m, p, g):
    m(p, pp(g["delta_pp"])); m(p + "Lo", pp(g["ci95_pp"][0])); m(p + "Hi", pp(g["ci95_pp"][1]))


def v2_macros(m, r, summ, proto, fmap):
    P = PREFIX[r]
    dev, held = summ["dev"], summ["heldout"]
    for cond, t in dev["conditions"].items():
        cond_macros(m, P + "Dev" + macro_name(cond.replace("oracle_", "o ")), t)
    for comp in COMPS:
        gap_macros(m, P + "Bud" + macro_name(comp), dev["budget"][comp])
    it = dev["interaction"]
    gap_macros(m, P + "BudAll", it["oracle_all"])
    m(P + "BudSum", pp(it["sum_of_single_recoveries_pp"])); m(P + "BudSumMinusAll", pp(it["sum_minus_all_pp"]))
    m(P + "BudIntAbs", f"{abs(it['sum_minus_all_pp']):.1f}")
    for cond, t in held["conditions"].items():
        p = P + ("HoFull" if cond == "full" else "HoCorr")
        cond_macros(m, p, t)
        fr = t["failure_reasons"]
        m(p + "NoLift", fr.get("no_lift", 0)); m(p + "NotPlaced", fr.get("not_released_and_settled_at_goal", 0))
    gap_macros(m, P + "HoGap", held["paired_gap_corrected_minus_full"])
    rt = dev["retarget_tool_error_descriptive"]
    m(P + "RetMedCm", f"{100 * rt['median_m']:.2f}"); m(P + "RetPNinetyCm", f"{100 * rt['p90_m']:.2f}")
    m(P + "RetMaxCm", f"{100 * rt['max_m']:.2f}")
    m(P + "Choice", dev["chosen_correction"].replace("_", "-"))
    m(P + "CodeCommit", fmap[proto["code_commit_at_freeze"][:7]])
    m(P + "FreezeCommit", fmap[summ["git_commit"][:7]])      # commit holding protocol.json + dev results


def v2_constants(m, proto):
    c = proto["constants"]
    m("cPercSigmaCm", f"{100 * c['PERCEPTION_SIGMA_M']:.1f}")
    m("cRetSigmaDeg", f"{c['RETARGET_JOINT_SIGMA_RAD'] * 180 / 3.141592653589793:.1f}")
    m("cCalMaxCm", f"{100 * c['CALIBRATION_MAX_M']:.0f}")
    m("cSpeedLo", f"{c['TIMING_SPEED_RANGE'][0]:.1f}"); m("cSpeedHi", f"{c['TIMING_SPEED_RANGE'][1]:.1f}")
    m("cLookSigmaCm", f"{100 * c['LOOK_AGAIN_SIGMA_M']:.1f}")
    m("cIkSigmaDeg", f"{c['IK_RESOLVE_SIGMA_RAD'] * 180 / 3.141592653589793:.2f}")
    m("cProbeSigmaMm", f"{1000 * c['PROBE_SIGMA_M']:.0f}")
    m("cSpeedCap", f"{c['SPEED_CAP']:.1f}")


def v1_macros(m, dev, held, proto, fmap):
    cond_macros(m, "pilotDevFull", dev["conditions"]["full"])
    vals = {round(v["delta_pp"], 6) for v in dev["budget"].values()}
    assert len(vals) == 1, "pilot text says the three single budgets tie"
    m("pilotBudSingle", pp(next(iter(vals))))
    m("pilotBudAll", pp(dev["interaction"]["oracle_all_recovery_pp"]))
    m("pilotBudSum", pp(dev["interaction"]["sum_of_single_recoveries_pp"]))
    for cond, t in held["conditions"].items():
        cond_macros(m, "pilotHo" + ("Full" if cond == "full" else "Corr"), t)
    gap_macros(m, "pilotHoGap", held["paired_gap_corrected_minus_full"])
    m("pilotCodeCommit", fmap[proto["code_commit_at_freeze"][:7]])


def diag_macros(m, d):
    m("diagDate", d["date"]); m("diagN", d["n_dev_seeds"]); m("diagLatency", f"{d['latency_s']:.1f}")
    m("diagModel", d["model_name"])
    for who, P in (("rule_based", "diagRule"), ("nemotron_super", "diagLlm")):
        x = d["by_diagnoser"][who]
        m(P + "Tag", x["tag_tex"]); m(P + "K", x["corrected_successes"]); m(P + "FullK", x["full_successes"])
        gap_macros(m, P + "Gap", x["paired_gap"])
    m("diagValidated", "yes" if d["validated"] else "no")


# ---------------------------------------------------------------- diagnosis snapshot

def tex_tag(tag):
    return tag.replace("_", r"\_")


def snapshot_diagnosis(run_dir):
    run_dir = Path(run_dir)
    rep, rc = jload(run_dir / "report.json"), jload(run_dir / "nemotron_super_receipt.json")
    assert rep["split"] == "dev" and rep["heldout_touched"] is False
    assert rc["status"] == "succeeded" and rc["validated"] is True
    ev = rep["dev_evaluation"]
    by = {}
    for who, tag in ev["by_diagnoser"].items():
        r = ev["by_correction"][tag]
        by[who] = {"tag": tag, "tag_tex": tex_tag(tag), "full_successes": r["full"]["successes"],
                   "corrected_successes": r["corrected"]["successes"], "n": r["corrected"]["n"],
                   "paired_gap": r["paired_gap_corrected_minus_full"], "ci_excludes_zero": r["ci_excludes_zero"]}
    snap = {"source": f"transfergap/runs/diagnose/{run_dir.name}/ (gitignored) report.json + receipt",
            "date": rc["created_at"][:10], "created_at": rc["created_at"], "trace_sha256": rep["trace_sha256"],
            "trace_note": "trace built from gap_budget_v1 UR5e dev episodes (three stages, tied budgets)",
            "requested_model": rc["requested_model"], "returned_model": rc["returned_model"],
            "model_name": "Nemotron 3 Super", "endpoint_host": rc["endpoint_host"],
            "latency_s": rc["latency_s"], "validated": rc["validated"],
            "n_live_calls": 1, "n_dev_seeds": len(rep["seeds"]), "by_diagnoser": by}
    DIAG_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    DIAG_SNAPSHOT.write_text(json.dumps(snap, indent=1) + "\n")
    print("wrote", DIAG_SNAPSHOT)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnose-run", help="refresh paper/data/diagnosis_dev_snapshot.json from a run dir")
    args = ap.parse_args()
    if args.diagnose_run:
        snapshot_diagnosis(args.diagnose_run)

    fmap = freeze_map()
    v2 = {r: {"summary": jload(p / "summary.json"), "protocol": jload(p / "protocol.json")} for r, p in V2.items()}
    for r, d in v2.items():
        pr, s = d["protocol"], d["summary"]
        assert pr["frozen_before_heldout"] and pr["chosen_correction"] == s["heldout"]["correction"]
        assert pr["robot"] == r and s["dev"]["chosen_correction"] == pr["chosen_correction"]
    assert v2["ur5e"]["protocol"]["constants"] == v2["ur10e"]["protocol"]["constants"]
    # main.tex quotes one code commit and one freeze commit for both arms
    assert v2["ur5e"]["protocol"]["code_commit_at_freeze"] == v2["ur10e"]["protocol"]["code_commit_at_freeze"]
    assert v2["ur5e"]["summary"]["git_commit"] == v2["ur10e"]["summary"]["git_commit"]
    dev1, held1, proto1 = jload(V1 / "dev_results.json"), jload(V1 / "heldout_results.json"), jload(V1 / "protocol.json")
    assert proto1["frozen_before_heldout"] and proto1["chosen_correction"] == held1["correction"]
    diag = jload(DIAG_SNAPSHOT)

    fig_v2(v2)
    m = Macros("% AUTO-GENERATED by paper/make_figures.py from transfergap/results/ and "
               "paper/data/diagnosis_dev_snapshot.json -- do not edit.")
    for r, d in v2.items():
        v2_macros(m, r, d["summary"], d["protocol"], fmap)
    v2_constants(m, v2["ur5e"]["protocol"])
    v1_macros(m, dev1, held1, proto1, fmap)
    diag_macros(m, diag)
    m.write(OUT / "numbers.tex")
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
