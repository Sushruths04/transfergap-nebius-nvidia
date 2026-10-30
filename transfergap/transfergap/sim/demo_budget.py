"""Transfer Gap Budget for a HUMAN DEMO, on task success AND style fidelity (protocol demo_budget_v1).

  python -m transfergap.sim.demo_budget dev     --demo synthetic:0|<demo.npz> --robot ur5e|ur10e
  (commit results/<name>/protocol.json and dev_results.json)
  python -m transfergap.sim.demo_budget heldout --demo ... --robot ...
  python -m transfergap.sim.demo_budget compare --demo ...          # matched two-robot table from both summaries

The same demo and the same seeds (block pose + per-seed estimation noise + assumed errors) drive every robot, so
the two arms are compared trial-for-trial. Success is scored by metrics.score_episode; style by
demo.style.style_metrics against the CLEAN retargeted human path anchored at the true block pose (scoring side
only). The correction is chosen on dev by the largest success budget (ties in pipeline order), as gap_budget_v2.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ..demo.style import LEGS, robot_path
from ..metrics import score_episode
from . import errors_demo as E
from .gap_budget import (DEV_SEEDS, HELDOUT_SEEDS, ROOT, _committed, _pool, by_cond, choose_component, cond_table,
                         env_info, gap, git_hash, write_jsonl)
from .rollout import run_episode
from .scene import ROBOTS, Scene


def _suffix(base):
    return "" if not base else "__after-" + "+".join(base)


def res_dir(spec, robot, base=()):
    return ROOT / "results" / f"{E.PROTOCOL_NAME}_{spec['tag']}_{robot}{_suffix(base)}"


def runs_dir(spec, robot, base=()):
    return ROOT / "runs" / f"{E.PROTOCOL_NAME}_{spec['tag']}_{robot}{_suffix(base)}"


def episode_style(ep, ref_plan, goal_xyz):
    """Style metrics of one episode vs the clean retargeted human path (uses logged true poses: scoring side)."""
    block0 = np.asarray(ep["states"][0]["object_xyz"], float)
    ref = robot_path(ref_plan, block0 + ref_plan["grasp_offset"], np.asarray(goal_xyz) + ref_plan["place_offset"])
    from ..demo.style import style_metrics
    legs = {}
    for leg in LEGS:
        rows = [s for s in ep["states"] if s["phase"] == leg]
        if len(rows) < 2:
            return None
        legs[leg] = (np.array([r["t_s"] for r in rows]), np.array([r["tool_xyz"] for r in rows]))
    return style_metrics(ref, legs)


def _job(a):
    spec, seed, cond, corr, robot = a[:5]
    base = tuple(a[5]) if len(a) > 5 else ()
    label = a[6] if len(a) > 6 else None
    pert, oracle, ref = E.build_perturbation(spec, seed, cond, corr, base)
    tag = label or (cond if corr is None else f"{cond}+{corr}")
    ep = run_episode(seed, pert, label=tag, oracle=oracle, condition=tag, robot=robot)
    ep["demo_id"] = spec["tag"]
    ep["style"] = episode_style(ep, ref, Scene(seed, robot).goal_xyz)
    for s in ep["states"]:          # keep files small: tool path only needed for the style metric above
        s.pop("tool_xyz", None)
    ep["perturbation"]["demo_plan"] = {k: v for k, v in ep["perturbation"]["demo_plan"].items() if k != "style"}
    return ep


def style_gap(a, b, key="path_rmse_mean_m", n_boot=2000, seed=0):
    """Paired mean of (a - b) by seed for a style metric, with a bootstrap 95% CI. For path RMSE, positive = b
    (the oracle/corrected run) follows the human path more closely."""
    A = {e["seed"]: e["style"][key] for e in a if e.get("style")}
    B = {e["seed"]: e["style"][key] for e in b if e.get("style")}
    common = sorted(set(A) & set(B))
    d = np.array([A[s] - B[s] for s in common])
    rng = np.random.default_rng(seed)
    boots = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(n_boot)] if len(d) else [np.nan]
    return {"mean": float(d.mean()) if len(d) else None, "ci95": [float(np.quantile(boots, .025)),
            float(np.quantile(boots, .975))], "n": len(d), "metric": key, "sign": "a minus b"}


DIVERGED_M = 0.20   # path RMSE above this = the arm lost the human path entirely (added after dev inspection)


def style_table(groups):
    out = {}
    for cond, rows in groups.items():
        st = [e["style"] for e in rows if e.get("style")]
        rm = [s["path_rmse_mean_m"] for s in st]
        out[cond] = {"n_scored": len(st),
                     **{k: float(np.mean([s[k] for s in st])) for k in
                        ("path_rmse_mean_m", "approach_angle_deg", "lift_height_err_m", "speed_profile_corr")},
                     "path_rmse_median_m": float(np.median(rm)), "n_diverged": int(sum(r > DIVERGED_M for r in rm))}
    return out


STRICT_CHOICE = False   # set by --strict (demo_budget_v1 runs before 2026-10-02 evening used the plain rule)


def restyle_dev(spec, robot, base=()):
    """Recompute dev summaries from the saved dev episodes (no new rollouts)."""
    import json as _j
    eps = [_j.loads(l) for l in (runs_dir(spec, robot, base) / "dev.jsonl").read_text().splitlines()]
    return eps


def stage_dev(spec, robot, eps=None, base=()):
    comps, conds = E.components_for(spec), E.conditions_for(spec)
    if eps is None:
        eps = _pool(_job, [(spec, s, c, None, robot, base) for s in DEV_SEEDS for c in conds])
        write_jsonl(runs_dir(spec, robot, base) / "dev.jsonl", eps)
    groups = by_cond(eps)
    full = groups["full"]
    budget = {c: gap(full, groups[f"oracle_{c}"]) for c in comps}
    sbudget = {c: {"path_rmse_m": style_gap(full, groups[f"oracle_{c}"]),
                   "speed_profile_corr": style_gap(groups[f"oracle_{c}"], full, "speed_profile_corr")}
               for c in comps}
    open_comps = [c for c in comps if E.next_correction(c, base) is not None]
    if STRICT_CHOICE:
        # (added 2026-10-02 after person 2) skip fixes that cannot change anything for this demo (a speed cap at
        # or above the human's own pace) and stages whose dev budget is not positive; if none is left: stop.
        pace = E.build_perturbation(spec, DEV_SEEDS[0], "full", None, base)[0]["timing_scale"]
        def useful(c):
            fix = E.next_correction(c, base)
            if fix.startswith("speed_cap_") and float(fix[len("speed_cap_"):]) >= pace:
                return False
            return budget[c]["delta_pp"] > 0
        open_comps = [c for c in open_comps if useful(c)]
    if open_comps:
        comp = choose_component({c: budget[c] for c in open_comps}, open_comps)
        corr = E.next_correction(comp, base)
    else:
        comp, corr = "none", None
    # Style-feasibility check (added 2026-10-02 after person-2 UR10e: oracle_all 0/60, all forbidden collisions):
    # if replacing EVERY stage by its oracle still fails on dev, the copied plan itself is infeasible and no stage
    # fix can close the gap -> adopt the style-safety projection first.
    oa = groups["oracle_all"]
    oa_rate = sum(score_episode(e)["success"] for e in oa) / len(oa)
    if oa_rate < E.STYLE_FEASIBLE_MIN and not any(b.startswith("safe_path") for b in base):
        comp, corr = "style_feasibility", "safe_path_v2" if STRICT_CHOICE else "safe_path"
    res = {"robot": robot, "demo": spec, "base_corrections": list(base), "seeds": [DEV_SEEDS[0], DEV_SEEDS[-1]],
           "conditions": cond_table(eps),
           "style": style_table(groups), "success_budget": budget, "style_budget": sbudget,
           "oracle_all": gap(full, groups["oracle_all"]), "chosen_component": comp, "chosen_correction": corr,
           "choice_rule": f"argmax success budget over components with an unused fix {open_comps} on dev; ties -> "
                          f"pipeline order; timing fixes climb {list(E.SPEED_LADDER)}"}
    R = res_dir(spec, robot, base)
    R.mkdir(parents=True, exist_ok=True)
    (R / "dev_results.json").write_text(json.dumps(res, indent=1))
    proto = {"protocol": E.PROTOCOL_NAME, "frozen_before_heldout": True, "robot": robot,
             "robot_label": ROBOTS[robot][2], "demo": spec, "base_corrections": list(base),
             "stacking": {"speed_ladder": list(E.SPEED_LADDER), "base_applied_under_every_condition": True},
             "strict_choice": STRICT_CHOICE,
             "components": list(comps), "conditions": conds,
             "corrections": E.CORRECTIONS, "chosen_component": comp,
             "style_summary_note": "path_rmse_median_m and n_diverged (path RMSE > %.2f m) were added to the style "
                                   "summaries after inspecting dev outliers (UR10e IK divergence from the home pose); "
                                   "success scoring and the correction rule were not changed" % DIVERGED_M, "chosen_correction": corr,
             "dev_seeds": [DEV_SEEDS[0], DEV_SEEDS[-1]], "heldout_seeds": [HELDOUT_SEEDS[0], HELDOUT_SEEDS[-1]],
             "heldout_conditions": ["full", f"full+{corr}"], "constants": E.constants(), "env": env_info(),
             "scoring": "success: metrics.score_episode (block_to_tray_v1); style: demo.style.style_metrics vs clean "
                        "retargeted human path", "code_commit_at_freeze": git_hash()}
    (R / "protocol.json").write_text(json.dumps(proto, indent=1))
    write_summary(spec, robot, base)
    print(R.name, {k: round(v["success_rate"], 2) for k, v in res["conditions"].items()})
    print("success budget pp:", {k: round(v["delta_pp"], 1) for k, v in budget.items()}, "->", corr)
    print("style budget (path RMSE cm):", {k: round(100 * v["path_rmse_m"]["mean"], 2) for k, v in sbudget.items()})


def stage_heldout(spec, robot, base=()):
    R = res_dir(spec, robot, base)
    for p in (R / "protocol.json", R / "dev_results.json"):
        if not p.exists() or not _committed(p):
            raise SystemExit(f"{p.name} must be committed (unmodified) before held-out trials are run")
    proto = json.loads((R / "protocol.json").read_text())
    if proto["constants"] != E.constants() or proto["robot"] != robot or proto["demo"] != spec or \
            proto.get("base_corrections", []) != list(base):
        raise SystemExit("frozen protocol does not match the current constants / robot / demo / base corrections")
    corr = proto["chosen_correction"]
    if corr is None:
        raise SystemExit("the diagnosis chose to STOP at this step (no useful fix left); nothing to evaluate")
    agent = None
    ap = R / "agent_choice.json"
    if ap.exists():
        if not _committed(ap):
            raise SystemExit("agent_choice.json must be committed before held-out trials")
        a_ = json.loads(ap.read_text())
        if a_.get("valid") and a_.get("agent_choice") not in (None, corr):
            agent = a_["agent_choice"]
    jobs = [(spec, s, "full", c, robot, base) for s in HELDOUT_SEEDS for c in (None, corr) + ((agent,) if agent else ())]
    if base:
        jobs += [(spec, s, "full", None, robot, (), "raw") for s in HELDOUT_SEEDS]
    eps = _pool(_job, jobs)
    write_jsonl(runs_dir(spec, robot, base) / "heldout.jsonl", eps)
    groups = by_cond(eps)
    a, b = groups["full"], groups[f"full+{corr}"]
    g = gap(a, b)
    res = {"robot": robot, "seeds": [HELDOUT_SEEDS[0], HELDOUT_SEEDS[-1]], "correction": corr,
           "conditions": cond_table(eps), "style": style_table(groups), "paired_gap_corrected_minus_full": g,
           "ci_excludes_zero": g["ci95_pp"][0] > 0 or g["ci95_pp"][1] < 0,
           "style_gap_path_rmse_full_minus_corrected": style_gap(a, b),
           "style_gap_speed_corr_corrected_minus_full": style_gap(b, a, "speed_profile_corr")}
    if agent:
        c_ = groups[f"full+{agent}"]
        res["agent_correction"] = agent
        res["paired_gap_agent_minus_full"] = gap(a, c_)
        res["paired_gap_agent_minus_rule"] = gap(b, c_)
        res["style_gap_path_rmse_rule_minus_agent"] = style_gap(b, c_)
    if base:
        res["cumulative_gap_all_fixes_minus_raw"] = gap(groups["raw"], b)
        res["base_corrections"] = list(base)
    (R / "heldout_results.json").write_text(json.dumps(res, indent=1))
    write_summary(spec, robot, base)
    print(json.dumps({k: res[k] for k in ("paired_gap_corrected_minus_full", "ci_excludes_zero")}, indent=1))


def _pct(t):
    return f"{100*t['success_rate']:.0f}% ({t['successes']}/{t['n']}) [{100*t['wilson_95'][0]:.0f}, {100*t['wilson_95'][1]:.0f}]"


def write_summary(spec, robot, base=()):
    R = res_dir(spec, robot, base)
    dev = json.loads((R / "dev_results.json").read_text())
    held = json.loads((R / "heldout_results.json").read_text()) if (R / "heldout_results.json").exists() else None
    L = [f"# Demo-driven gap budget ({E.PROTOCOL_NAME}), {ROBOTS[robot][2]}, demo `{spec['tag']}` ({spec['kind']})"
         + (f", after adopting {' + '.join(base)}" if base else ""), "",
         "Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), "
         "approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).", "",
         "## Dev seeds 0-59", "", "| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |",
         "|---|---|---|---|---|---|---|"]
    for c, t in dev["conditions"].items():
        s = dev["style"][c]
        L.append(f"| {c} | {_pct(t)} | {100*s['path_rmse_mean_m']:.2f} / {100*s['path_rmse_median_m']:.2f} | "
                 f"{s['n_diverged']} | {s['approach_angle_deg']:.1f} | "
                 f"{100*s['lift_height_err_m']:.2f} | {s['speed_profile_corr']:.2f} |")
    L += ["", "| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |",
          "|---|---|---|---|"]
    for c, b in dev["success_budget"].items():
        sp, sc = dev["style_budget"][c]["path_rmse_m"], dev["style_budget"][c]["speed_profile_corr"]
        L.append(f"| {c} | {b['delta_pp']:+.1f} [{b['ci95_pp'][0]:+.1f}, {b['ci95_pp'][1]:+.1f}] | "
                 f"{100*sp['mean']:+.2f} [{100*sp['ci95'][0]:+.2f}, {100*sp['ci95'][1]:+.2f}] | "
                 f"{sc['mean']:+.2f} [{sc['ci95'][0]:+.2f}, {sc['ci95'][1]:+.2f}] |")
    L += ["", f"Chosen on dev: {dev['chosen_component']} -> {dev['chosen_correction']} ({dev['choice_rule']})."]
    if held:
        g = held["paired_gap_corrected_minus_full"]
        L += ["", "## Held-out seeds 1000-1059", "", "| condition | success | path RMSE cm mean / median | diverged | speed corr |",
              "|---|---|---|---|---|"]
        for c, t in held["conditions"].items():
            s = held["style"][c]
            L.append(f"| {c} | {_pct(t)} | {100*s['path_rmse_mean_m']:.2f} / {100*s['path_rmse_median_m']:.2f} | "
                     f"{s['n_diverged']} | {s['speed_profile_corr']:.2f} |")
        sp = held["style_gap_path_rmse_full_minus_corrected"]
        L += ["", f"Paired success gap (corrected - full): {g['delta_pp']:+.1f} pp, 95% CI [{g['ci95_pp'][0]:+.1f}, "
              f"{g['ci95_pp'][1]:+.1f}], n={g['n']}; CI excludes zero: {held['ci_excludes_zero']}.",
              f"Path RMSE change (full - corrected): {100*sp['mean']:+.2f} cm, 95% CI [{100*sp['ci95'][0]:+.2f}, "
              f"{100*sp['ci95'][1]:+.2f}]."]
        if held.get("agent_correction"):
            ga, gr = held["paired_gap_agent_minus_full"], held["paired_gap_agent_minus_rule"]
            L += [f"Nemotron agent chose `{held['agent_correction']}` (rule chose `{held['correction']}`): agent - full "
                  f"{ga['delta_pp']:+.1f} pp [{ga['ci95_pp'][0]:+.1f}, {ga['ci95_pp'][1]:+.1f}]; agent - rule "
                  f"{gr['delta_pp']:+.1f} pp [{gr['ci95_pp'][0]:+.1f}, {gr['ci95_pp'][1]:+.1f}]."]
        if held.get("cumulative_gap_all_fixes_minus_raw"):
            c = held["cumulative_gap_all_fixes_minus_raw"]
            L += [f"Cumulative (all adopted fixes + this one, vs no fix): {c['delta_pp']:+.1f} pp, 95% CI "
                  f"[{c['ci95_pp'][0]:+.1f}, {c['ci95_pp'][1]:+.1f}], n={c['n']}."]
    L += ["", "Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation "
          "noise is an ASSUMPTION; " + ("the demo is SYNTHETIC (minimum-jerk), not human data; " if spec["kind"] ==
          "synthetic" else "") + "scripted IK controller in MuJoCo; style is measured on the tool pinch point only "
          "(no wrist orientation)."]
    (R / "summary.md").write_text("\n".join(L) + "\n")
    (R / "summary.json").write_text(json.dumps({"kind": "demo_budget", "robot": robot, "demo": spec,
                                                "base_corrections": list(base), "dev": dev, "heldout": held}, indent=1))


def compare(spec):
    rows = []
    for robot in ROBOTS:
        p = res_dir(spec, robot) / "summary.json"
        if p.exists():
            rows.append(json.loads(p.read_text()))
    print(json.dumps([{"robot": r["robot"], "full_success": r["dev"]["conditions"]["full"]["success_rate"],
                       "full_path_rmse_cm": 100 * r["dev"]["style"]["full"]["path_rmse_mean_m"],
                       "budget_pp": {k: v["delta_pp"] for k, v in r["dev"]["success_budget"].items()}}
                      for r in rows], indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "redev", "heldout", "summary", "compare"])
    ap.add_argument("--demo", required=True)
    ap.add_argument("--robot", default="ur5e", choices=sorted(ROBOTS))
    ap.add_argument("--base", default="", help="comma-separated corrections already adopted, in order")
    ap.add_argument("--strict", action="store_true", help="skip no-op fixes and non-positive budgets; may stop")
    a = ap.parse_args()
    global STRICT_CHOICE
    STRICT_CHOICE = a.strict
    spec = E.parse_demo_spec(a.demo)
    base = tuple(x for x in a.base.split(",") if x)
    {"dev": lambda: stage_dev(spec, a.robot, base=base),
     "redev": lambda: stage_dev(spec, a.robot, restyle_dev(spec, a.robot, base), base),
     "heldout": lambda: stage_heldout(spec, a.robot, base),
     "summary": lambda: write_summary(spec, a.robot, base), "compare": lambda: compare(spec)}[a.stage]()


if __name__ == "__main__":
    main()
