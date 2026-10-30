"""Post-hoc per-trial check: did the kinematic pre-check (IK error of the plan actually executed, frozen 2 cm
threshold from results/feasibility_precheck_v1/protocol.json) separate the G1 rollouts that grasped from those that
did not? Reads the per-seed plan metadata written by plan_reach.py at run time (gitignored runs/g1_style/plans_*)
and the committed episode logs. Run from transfergap/:
    .venv/bin/python g1/precheck_vs_outcome.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from score import tiers  # noqa: E402

IK_ERR_MAX_M = 0.02
RUNS = [  # (label, plan folder + prefix, episode log)
    ("person 1, human pace", "runs/g1_style/plans_style/human", "results/g1_style_v1/episodes_style_human_pace.jsonl"),
    ("person 1, speed cap 3", "runs/g1_style/plans_style/cap3", "results/g1_style_v1/episodes_style_speed_cap_3.jsonl"),
    ("person 1, robot pace", "runs/g1_style/plans_style/nominal",
     "results/g1_style_v1/episodes_style_nominal_pace.jsonl"),
    ("person 2, her pace", "runs/g1_style/plans_style_woman/human",
     "results/g1_style_person2_v1/episodes_p2_raw_her_pace.jsonl"),
    ("person 2, robot pace", "runs/g1_style/plans_style_woman/nominal",
     "results/g1_style_person2_v1/episodes_p2_raw_robot_pace.jsonl"),
    ("person 2 + safe_path_v2, robot pace", "runs/g1_style/plans_style_womansafe/nominal",
     "results/g1_style_person2_v1/episodes_p2_safe_path_v2_robot_pace.jsonl"),
]


def main():
    rows = []
    for label, plans, log in RUNS:
        cells = {True: [0, 0, 0], False: [0, 0, 0]}          # flagged -> [rollouts, grasped, placed]
        flagged_seeds = set()
        for line in open(log):
            e = json.loads(line)
            m = json.loads(Path(f"{plans}_seed{e['seed']}.json").read_text())["final_ik_error_m"]
            flag = max(m[k] for k in ("reach", "carry", "retreat")) > IK_ERR_MAX_M
            if flag:
                flagged_seeds.add(e["seed"])
            t = tiers(e)
            c = cells[flag]
            c[0] += 1
            c[1] += bool(t["grasp"])
            c[2] += bool(t["place"])
        rows.append({"run": label, "flagged_seeds": sorted(flagged_seeds),
                     "flagged": dict(zip(("rollouts", "grasped", "placed"), cells[True])),
                     "not_flagged": dict(zip(("rollouts", "grasped", "placed"), cells[False]))})
    out = Path("results/feasibility_precheck_v1")
    (out / "g1_per_trial.json").write_text(json.dumps(rows, indent=1) + "\n")
    f = lambda c: f"{c['grasped']}/{c['rollouts']} grasp, {c['placed']}/{c['rollouts']} place" if c["rollouts"] else "-"
    md = ["# G1: pre-check verdict of the executed plan vs rollout outcome (post-hoc, frozen 2 cm threshold)", "",
          "| run | flagged seeds | flagged rollouts | not-flagged rollouts |", "|---|---|---|---|"]
    md += [f"| {r['run']} | {', '.join(map(str, r['flagged_seeds'])) or '-'} | {f(r['flagged'])} | "
           f"{f(r['not_flagged'])} |" for r in rows]
    tot = {k: [sum(r[k][x] for r in rows) for x in ("rollouts", "grasped", "placed")] for k in ("flagged", "not_flagged")}
    md += ["", f"All runs: flagged {tot['flagged'][1]}/{tot['flagged'][0]} grasped; "
               f"not flagged {tot['not_flagged'][1]}/{tot['not_flagged'][0]} grasped (human-pace runs fail for a "
               "different reason: speed)."]
    (out / "g1_per_trial.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
