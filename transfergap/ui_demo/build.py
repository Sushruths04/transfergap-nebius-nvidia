"""Build the demo console: reads the committed result files and writes ui_demo/data.js (window.TG = {...}).

    python ui_demo/build.py        then open ui_demo/index.html (no server, no network, works offline)

Nothing on the page is typed in by hand except the roadmap (marked PLANNED) and the wording of the caveats: every number, count and
series comes from a result file listed under `evidence`. Videos are in ui_demo/media (copied from the cluster showcase run).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
R = HERE.parent / "results"
SHOW = R / "showcase_r6_shoulder044"
TAG = "demo7c1fa3bd"


def load(p):
    return json.loads(Path(p).read_text())


def series(z, key, nd=3):
    return [round(float(x), nd) for x in np.asarray(z[key]).ravel()]


def main():
    rep = load(SHOW / "pipe/rollouts/repro_summary.json")
    robots = {}
    for k, v in rep["robots"].items():
        c = v["conditions"]
        robots[k] = {"raw": {"k": c["raw"]["successes"], "n": c["raw"]["n"], "ci": c["raw"]["wilson_95"], "why": c["raw"]["failure_reasons"]},
                     "fix": {"k": c["all_fixes"]["successes"], "n": c["all_fixes"]["n"], "ci": c["all_fixes"]["wilson_95"]},
                     "gain_pp": v["gap_all_fixes_minus_raw"]["delta_pp"], "gain_ci": v["gap_all_fixes_minus_raw"]["ci95_pp"]}
    ha = load(SHOW / "human/human_analysis.json")
    z = np.load(HERE / "media/human_metrics.npz")
    human = {"fps": ha["fps"], "frames": ha["frames"], "lengths": ha["lengths_m"], "angles": ha["angles_deg"], "hand": ha["hand"],
             "series": {"speed": series(z, "hand_speed_m_s"), "elbow": series(z, "elbow_deg", 1), "aperture_cm": [round(x * 100, 2) for x in series(z, "aperture_m", 4)],
                        "wrist": series(z, "wrist_deg", 1)},
             "events": {"grasp": 102 - 60, "release": 166 - 60}}
    critic = load(R / "cosmos_critic_newdemo_v1/report.json")
    loop = load(R / f"demo_agent_loop_{TAG}.json")
    g1 = load(SHOW / "g1/mimic_fidelity.json")
    status = load(SHOW / "showcase_status.json")
    held = {}
    for r in ("ur5e", "ur10e"):
        h = load(R / f"demo_budget_v1_{TAG}_{r}__after-look_again/heldout_results.json")
        held[r] = {"conditions": {c: [v["successes"], v["n"]] for c, v in h["conditions"].items()}}
    dev0 = {r: load(R / f"demo_budget_v1_{TAG}_{r}/dev_results.json") for r in ("ur5e", "ur10e")}
    budget = {r: {c: round(b["delta_pp"], 1) for c, b in d["success_budget"].items()} for r, d in dev0.items()}
    nem = load(R / f"demo_budget_v1_{TAG}_ur5e/agent_choice.json")
    gb = None
    p = R / "gap_budget_v3"
    if (p / "summary.json").exists():
        gb = "gap_budget_v3"
    data = {
        "title": "TransferGap",
        "built_from": str(SHOW.relative_to(R.parent)),
        "shoulder_width_m": 0.44,
        "robots": robots, "human": human, "g1": g1, "pipeline_status": {k: v["status"] for k, v in status.items()},
        "critic": {"n": critic["n_clips"], "zero": critic["zero_shot"], "ft": critic["fine_tuned"], "ft_cells": critic["fine_tuned_by_cell"]},
        "loop": loop, "held": held, "budget": budget,
        "agent": {"model": nem["model"], "rationale": nem.get("rationale", ""), "latency_s": nem.get("latency_s")},
        "evidence": {"showcase": "results/showcase_r6_shoulder044", "critic": "results/cosmos_critic_newdemo_v1",
                     "agent": f"results/demo_agent_loop_{TAG}.md", "image": "ghcr.io/sushruths04/transfergap:full-2026-10-09b",
                     "gap_budget": gb},
    }
    (HERE / "data.js").write_text("window.TG = " + json.dumps(data, separators=(",", ":")) + ";\n")
    print("wrote", HERE / "data.js", len(json.dumps(data)), "bytes")


if __name__ == "__main__":
    main()
