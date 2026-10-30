"""Convert raw G1 rollout logs to repo-schema episodes and score them in tiers (touch / grasp / place).

Raw logs (RUN/seed{S}_r{R}.episode.json, written by sim_runner.py at 50 Hz) are reduced to 10 Hz
episodes: per-window contact flags are OR-ed, `released` is AND-ed, latched flags keep their last
value. Scoring then uses only the written episodes, so results/ is reproducible from the JSONL.

Tiers per rollout (simulator labels only):
  touch  any hand-block contact (wrist or Dex3 hand links touching the block)
  grasp  block raised >= min_lift_m above its start while a hand touches it
  place  transfergap.metrics.score_episode success: lifted, released and settled inside the tray
         for settle_duration_s, no forbidden collision, nothing fallen

    python g1/score.py --run RUN_DIR:CONDITION:ORACLE:TRAJ_META [--run ...] --out results/g1_contact_v1
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from transfergap.metrics import score_episode, summarize, wilson_interval  # noqa: E402

PROTOCOL = "g1_block_to_tray_v1"
TASK = {"position_tolerance_m": 0.05,      # block centre within the tray floor (inner half 0.07 - block half 0.02)
        "min_lift_m": 0.05, "settle_duration_s": 0.5, "max_settle_speed_m_s": 0.02}
ROBOT, METHOD, DEMO = "g1_sonic", "sonic_zmq_v1_stream", "ik_keyframe_reach_v1"
OUT_HZ, IN_HZ = 10, 50


def reduce_states(states, factor=IN_HZ // OUT_HZ):
    out = []
    for i in range(0, len(states) - factor + 1, factor):
        w = states[i:i + factor]
        last = w[-1]
        out.append({"t_s": round(last["t_s"], 3),
                    "object_xyz": [round(v, 5) for v in last["object_xyz"]],
                    "object_velocity": [round(v, 5) for v in last["object_velocity"]],
                    "released": all(s["released"] for s in w),
                    "forbidden_collision": any(s["forbidden_collision"] for s in w),
                    "fallen": any(s["fallen"] for s in w),
                    "hand_block_contact": any(s["hand_block_contact"] for s in w),
                    "pelvis_xyz": [round(v, 4) for v in last["pelvis_xyz"]]})
    return out


def to_episode(raw, condition, oracle, traj_meta):
    seed, r = raw["seed"], raw["rollout"]
    return {"schema_version": 1, "source": "simulation", "trial_id": f"seed{seed}_r{r}", "demo_id": DEMO,
            "scene_id": f"{PROTOCOL}_seed{seed}", "seed": int(seed), "rollout": int(r), "robot": ROBOT,
            "method": f"{METHOD}[{condition}]", "sensor": "oracle", "oracle": oracle,
            "target_source": "simulator_ground_truth" if oracle == "perception" else "fixed_task_target",
            "condition": condition,
            "protocol_id": PROTOCOL, "frame_id": "world", "units": "m",
            "task": {"goal_xyz": raw["goal_xyz"], **TASK},
            "block_xy_initial": raw["block_xy_initial"], "target_xy_world": traj_meta.get("target_xy_world"),
            "robot_fell": raw["robot_fell"], "video": raw.get("video"),
            "states": reduce_states(raw["states"])}


def tiers(ep):
    s, task = ep["states"], ep["task"]
    z0 = s[0]["object_xyz"][2]
    touch = any(x["hand_block_contact"] for x in s)
    grasp = any(x["hand_block_contact"] and x["object_xyz"][2] - z0 >= task["min_lift_m"] for x in s)
    res = score_episode(ep)
    return {"touch": touch, "grasp": grasp, "place": res["success"],
            "max_lift_m": round(max(x["object_xyz"][2] for x in s) - z0, 4),
            "block_displacement_xy_m": round(math.dist(s[-1]["object_xyz"][:2], s[0]["object_xyz"][:2]), 4),
            "failure_reasons": res["failure_reasons"], "final_object_error_m": round(res["final_object_error_m"], 4)}


def rate(k, n):
    return {"k": k, "n": n, "rate": round(k / n, 3), "wilson_95": [round(v, 3) for v in wilson_interval(k, n)]}


def summarise_condition(eps):
    rows = [(ep, tiers(ep)) for ep in eps]
    n = len(rows)
    out = {"rollouts": n, "trials": len({ep["seed"] for ep, _ in rows})}
    for t in ("touch", "grasp", "place"):
        out[f"{t}_rollout_rate"] = rate(sum(r[t] for _, r in rows), n)
    by_seed = defaultdict(list)
    for ep, r in rows:
        by_seed[ep["seed"]].append(r)
    for t in ("touch", "grasp", "place"):
        any_k = sum(any(r[t] for r in rs) for rs in by_seed.values())
        out[f"{t}_trial_any_rollout"] = rate(any_k, len(by_seed))
        mixed = sum(0 < sum(r[t] for r in rs) < len(rs) for rs in by_seed.values())
        out[f"{t}_trials_with_mixed_outcomes"] = mixed     # nondeterminism across repeated rollouts
    reasons = defaultdict(int)
    for _, r in rows:
        for x in r["failure_reasons"]:
            reasons[x] += 1
    out["place_failure_reasons"] = dict(reasons)
    out["robot_fell"] = sum(ep["robot_fell"] for ep, _ in rows)
    out["max_lift_m_median"] = sorted(r["max_lift_m"] for _, r in rows)[n // 2]
    out["per_rollout"] = [{"seed": ep["seed"], "rollout": ep["rollout"], **{k: r[k] for k in
                           ("touch", "grasp", "place", "max_lift_m", "block_displacement_xy_m", "failure_reasons")}}
                          for ep, r in sorted(rows, key=lambda x: (x[0]["seed"], x[0]["rollout"]))]
    return out


def _fmt(r):
    lo, hi = r["wilson_95"]
    return f"{100 * r['rate']:.0f}% ({r['k']}/{r['n']}) [{100 * lo:.0f}, {100 * hi:.0f}]"


def markdown(summary):
    L = [f"# G1 contact attempt v1 ({summary['robot']}), protocol `{summary['protocol_id']}`", "",
         "Tier rates per rollout with Wilson 95% intervals [%]. Rollouts of one seed share the scene, so the",
         "per-rollout intervals overstate independence; the per-trial table counts seeds where any of the",
         "repeated rollouts reached the tier. Simulator labels only.", "",
         "| condition | oracle | rollouts | touch | grasp (lift >= 5 cm in hand) | place (in tray, settled) |",
         "|---|---|---|---|---|---|"]
    for c, r in summary["conditions"].items():
        L.append(f"| {c} | {r['oracle']} | {r['rollouts']} ({r['trials']} seeds) | {_fmt(r['touch_rollout_rate'])} | "
                 f"{_fmt(r['grasp_rollout_rate'])} | {_fmt(r['place_rollout_rate'])} |")
    L += ["", "| condition | touch, any rollout | grasp, any rollout | place, any rollout | "
          "seeds with mixed place outcomes | robot fell | place failure reasons |", "|---|---|---|---|---|---|---|"]
    for c, r in summary["conditions"].items():
        reasons = ", ".join(f"{k}:{v}" for k, v in sorted(r["place_failure_reasons"].items())) or "-"
        L.append(f"| {c} | {_fmt(r['touch_trial_any_rollout'])} | {_fmt(r['grasp_trial_any_rollout'])} | "
                 f"{_fmt(r['place_trial_any_rollout'])} | {r['place_trials_with_mixed_outcomes']} | "
                 f"{r['robot_fell']} | {reasons} |")
    L += ["", "Per rollout (seed.rollout tiers T/G/P, max lift cm, block xy displacement cm, reasons):", ""]
    for c, r in summary["conditions"].items():
        items = []
        for x in r["per_rollout"]:
            t = ("T" if x["touch"] else "-") + ("G" if x["grasp"] else "-") + ("P" if x["place"] else "-")
            why = f" ({','.join(x['failure_reasons'])})" if x["failure_reasons"] else ""
            items.append(f"{x['seed']}.{x['rollout']} {t} {100 * x['max_lift_m']:.1f} "
                         f"{100 * x['block_displacement_xy_m']:.1f}{why}")
        L.append(f"- {c}: " + "; ".join(items))
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True,
                    help="RUN_DIR:CONDITION:ORACLE:TRAJ_META_JSON (repeatable)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", default="100-109", help="expected seed range")
    ap.add_argument("--rollouts", type=int, default=3, help="rollouts per seed")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    all_eps, conds = [], {}
    s0, s1 = map(int, a.seeds.split("-"))
    expected = {(seed, rollout) for seed in range(s0, s1 + 1) for rollout in range(a.rollouts)}
    for spec in a.run:
        run, cond, oracle, meta = spec.split(":")         # META may contain {seed} for per-seed plans
        eps, metas = [], {}
        seen = set()
        for p in sorted(Path(run).glob("seed*_r*.episode.json")):
            raw = json.loads(p.read_text())
            key = (raw["seed"], raw["rollout"])
            if key in seen:
                raise ValueError(f"duplicate G1 rollout {key} in {run}")
            seen.add(key)
            mp = meta.format(seed=raw["seed"])
            metas.setdefault(mp, json.loads(Path(mp).read_text()))
            eps.append(to_episode(raw, cond, oracle, metas[mp]))
        if seen != expected:
            raise ValueError(f"incomplete G1 condition {cond}: missing={sorted(expected - seen)}, "
                             f"extra={sorted(seen - expected)}")
        traj_meta = metas[min(metas)] if len(metas) == 1 else {"per_seed_plans": sorted(metas)}
        (out / f"episodes_{cond}.jsonl").write_text("".join(json.dumps(e) + "\n" for e in eps))
        all_eps += eps
        conds[cond] = {"oracle": oracle, "plan": traj_meta, **summarise_condition(eps)}
    report = summarize(all_eps)            # repo-level success (= place tier); validates every episode
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = ""
    summary = {"kind": "g1_contact", "protocol_id": PROTOCOL, "task": TASK, "robot": ROBOT,
               "code_commit_at_scoring": commit,
               "conditions": conds, "metrics_summarize": report}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    (out / "summary.md").write_text(markdown(summary))
    print(json.dumps({c: {k: f"{v['k']}/{v['n']}" for k, v in s.items()
                          if k.endswith("rate") or k.endswith("any_rollout")} for c, s in conds.items()}, indent=1))


if __name__ == "__main__":
    main()
