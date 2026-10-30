"""Large-sample confirmation of the arm gap budget (protocol gap_budget_v3).

  python -m transfergap.sim.gap_budget_large protocol   # write results/gap_budget_v3/protocol.json (commit it)
  python -m transfergap.sim.gap_budget_large run        # refuses unless protocol.json is committed and unmodified

Fresh seeds 3000-3499 (disjoint from dev 0-59, held-out 1000-1059 and the sweep 2000-2029), both arms, under the
frozen v2 error model. Conditions: full, the four single oracles, oracle_all, and full + each of the four
corrections. This answers three things the 60-seed study could not: (1) whether the budget ranking and the
sign of the interaction term replicate with tighter intervals, with a bootstrap interval ON the interaction
term; (2) whether the correction chosen on dev seeds is also the best of all four, run held-out; (3) the same
for both arms with identical per-seed errors.
"""
from __future__ import annotations

import argparse
import json
import subprocess

import numpy as np

from ..metrics import score_episode
from . import errors_v2 as E
from .gap_budget import ROOT, _committed, _pool, by_cond, cond_table, git_hash, write_jsonl, _job

SEEDS = list(range(3000, 3500))
ROBOT_LIST = ("ur5e", "ur10e")
NAME = "gap_budget_v3"
RES = ROOT / "results" / NAME
RUNS = ROOT / "runs" / NAME
CORRS = list(E.CORRECTIONS.values())
BOOT = 5000

HYPOTHESES = {
    "H1": "On both arms, paired success of full+look_again minus full has a 95% bootstrap interval above zero "
          "(replication of the gap_budget_v2 held-out result with 500 fresh seeds).",
    "H2": "The correction chosen on dev seeds (look_again, perception) is the largest gain of the four corrections "
          "on each arm. This is reported either way; it is not a pass/fail bar.",
    "H3": "The sign of the interaction term (sum of single budgets minus oracle_all) differs between the arms, as in "
          "gap_budget_v2. Reported with a bootstrap 95% interval on each arm; if both intervals include zero the "
          "earlier sign flip is not supported.",
    "H4": "Retargeting budget at the assumed 0.5 degree joint error is indistinguishable from zero on both arms.",
}


def _arr(eps):
    return {e["seed"]: int(score_episode(e)["success"]) for e in eps}


def _boot(fn, n, rng):
    idx = rng.integers(0, n, size=(BOOT, n))
    vals = np.array([fn(i) for i in idx])
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def analyse(eps, robot):
    g = by_cond(eps)
    seeds = SEEDS
    cache = {c: _arr(g[c]) for c in g}                       # score each episode once
    s = {c: np.array([cache[c][k] for k in seeds]) for c in g}
    full = s["full"]
    rng = np.random.default_rng(12345)
    out = {"robot": robot, "n": len(seeds), "conditions": cond_table(eps)}
    singles = {c: s[f"oracle_{c}"] - full for c in E.COMPONENTS}
    allv = s["oracle_all"] - full
    out["budget_pp"] = {c: {"delta_pp": 100 * float(v.mean()),
                            "ci95_pp": [100 * x for x in _boot(lambda i, v=v: v[i].mean(), len(seeds), rng)]}
                        for c, v in singles.items()}
    out["oracle_all_pp"] = {"delta_pp": 100 * float(allv.mean()),
                            "ci95_pp": [100 * x for x in _boot(lambda i: allv[i].mean(), len(seeds), rng)]}
    tot = sum(singles.values())
    inter = tot - allv                       # per seed: sum of singles minus oracle_all
    out["interaction_pp"] = {"sum_minus_all_pp": 100 * float(inter.mean()),
                             "ci95_pp": [100 * x for x in _boot(lambda i: inter[i].mean(), len(seeds), rng)]}
    cor = {}
    for comp, name in E.CORRECTIONS.items():
        d = s[f"full+{name}"] - full
        cor[name] = {"component": comp, "successes": int(s[f"full+{name}"].sum()),
                     "delta_pp": 100 * float(d.mean()),
                     "ci95_pp": [100 * x for x in _boot(lambda i, d=d: d[i].mean(), len(seeds), rng)]}
    out["corrections"] = cor
    out["full_successes"] = int(full.sum())
    best = max(cor, key=lambda k: cor[k]["delta_pp"])
    out["best_correction"] = best
    return out


def stage_protocol():
    RES.mkdir(parents=True, exist_ok=True)
    proto = {"protocol": NAME, "seeds": [SEEDS[0], SEEDS[-1]], "n_seeds": len(SEEDS), "robots": list(ROBOT_LIST),
             "error_model": "errors_v2 (frozen constants below)", "constants": E.constants(),
             "conditions": list(E.CONDITIONS) + [f"full+{c}" for c in CORRS],
             "dev_choice_from_gap_budget_v2": "look_again (perception) on both arms",
             "hypotheses": HYPOTHESES, "bootstrap": {"samples": BOOT, "seed": 12345, "unit": "seed"},
             "disjoint_from": {"dev": [0, 59], "heldout_v2": [1000, 1059], "sweep": [2000, 2029]},
             "code_commit_at_freeze": git_hash(),
             "rule": "No threshold or error constant is changed after seeing results; all four corrections are reported."}
    (RES / "protocol.json").write_text(json.dumps(proto, indent=1))
    print("wrote", RES / "protocol.json")


def stage_run():
    p = RES / "protocol.json"
    if not p.exists() or not _committed(p):
        raise SystemExit("protocol.json must be committed (unmodified) before the run")
    proto = json.loads(p.read_text())
    if proto["constants"] != json.loads(json.dumps(E.constants())):
        raise SystemExit("error-model constants differ from the frozen protocol")
    summary = {"kind": "gap_budget_multi_arm", "protocol": NAME, "arms": {}}
    for robot in ROBOT_LIST:
        jobs = [(s, c, None, "v2", robot) for s in SEEDS for c in E.CONDITIONS]
        jobs += [(s, "full", name, "v2", robot) for s in SEEDS for name in CORRS]
        f = RUNS / f"{robot}.jsonl"
        if f.exists() and sum(1 for _ in f.open()) == len(jobs):   # a finished run of this arm is reused (resume)
            eps = [json.loads(l) for l in f.open()]
        else:
            eps = _pool(_job, jobs)
            write_jsonl(f, eps)
        summary["arms"][robot] = analyse(eps, robot)
        print(robot, "full", summary["arms"][robot]["full_successes"], "/", len(SEEDS), flush=True)
    summary["code_commit_at_run"] = git_hash()
    (RES / "summary.json").write_text(json.dumps(summary, indent=1))
    write_md(summary)


def write_md(summary):
    L = [f"# {NAME}: 500 fresh seeds per arm, all corrections held-out", "",
         "Protocol and hypotheses: `protocol.json` (committed before the run). Seeds 3000-3499, paired by seed.", ""]
    for robot, a in summary["arms"].items():
        L += [f"## {robot}", "", f"full: {a['full_successes']}/{a['n']}", "",
              "| stage | budget pp | 95% CI |", "|---|---|---|"]
        for c, v in a["budget_pp"].items():
            L.append(f"| {c} | {v['delta_pp']:+.1f} | [{v['ci95_pp'][0]:+.1f}, {v['ci95_pp'][1]:+.1f}] |")
        o, i = a["oracle_all_pp"], a["interaction_pp"]
        L += [f"| oracle_all | {o['delta_pp']:+.1f} | [{o['ci95_pp'][0]:+.1f}, {o['ci95_pp'][1]:+.1f}] |", "",
              f"Interaction (sum of singles minus oracle_all): {i['sum_minus_all_pp']:+.1f} pp, "
              f"95% CI [{i['ci95_pp'][0]:+.1f}, {i['ci95_pp'][1]:+.1f}]", "",
              "| correction (held-out) | successes | gain pp | 95% CI |", "|---|---|---|---|"]
        for n, v in a["corrections"].items():
            L.append(f"| {n} ({v['component']}) | {v['successes']}/{a['n']} | {v['delta_pp']:+.1f} | "
                     f"[{v['ci95_pp'][0]:+.1f}, {v['ci95_pp'][1]:+.1f}] |")
        L += ["", f"Largest gain: {a['best_correction']}", ""]
    (RES / "summary.md").write_text("\n".join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["protocol", "run"])
    {"protocol": stage_protocol, "run": stage_run}[ap.parse_args().stage]()


if __name__ == "__main__":
    main()
