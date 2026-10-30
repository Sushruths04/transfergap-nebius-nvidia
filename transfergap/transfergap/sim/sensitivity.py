"""Sensitivity of the Transfer Gap Budget to the assumed error scale and to the layout (exploratory, seeds 4000-4199).

  python -m transfergap.sim.sensitivity run     # all settings, both arms, 10 conditions each
  python -m transfergap.sim.sensitivity analyse
Settings: base; error scale x0.5 and x2 (perception sigma, joint sigma, calibration max, timing excess scaled;
correction constants unchanged); layout: 3 cm block, 5 cm block, block jitter +/-5 cm. No setting is tuned.
"""
import json, os, sys, multiprocessing as mp
from pathlib import Path
import numpy as np
from . import errors_v2 as E
from . import scene as S
from .rollout import run_episode
from ..metrics import score_episode

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs" / "sensitivity"
SEEDS = list(range(4000, 4200))
ARMS = ("ur5e", "ur10e")
SETTINGS = {"base": {}, "err_x0.5": {"scale": 0.5}, "err_x2": {"scale": 2.0},
            "block_3cm": {"half": 0.015}, "block_5cm": {"half": 0.025}, "jitter_5cm": {"jitter": 0.05},
            "perc_x0.25": {"sc": {"P": 0.25}}, "perc_x0.25_cal_x2": {"sc": {"P": 0.25, "C": 2.0}}}
CORRS = list(E.CORRECTIONS.values())
BASE = dict(P=E.PERCEPTION_SIGMA_M, R=E.RETARGET_JOINT_SIGMA_RAD, C=E.CALIBRATION_MAX_M, T=E.TIMING_SPEED_RANGE)


def apply_scale(s, sc=None):
    sc = {k: s for k in "PRCT"} | (sc or {})
    E.PERCEPTION_SIGMA_M = BASE["P"] * sc["P"]
    E.RETARGET_JOINT_SIGMA_RAD = BASE["R"] * sc["R"]
    E.CALIBRATION_MAX_M = BASE["C"] * sc["C"]
    E.TIMING_SPEED_RANGE = (1.0, 1.0 + (BASE["T"][1] - 1.0) * sc["T"])


def job(a):
    setting, robot, seed, cond, corr = a
    cfg = SETTINGS[setting]
    apply_scale(cfg.get("scale", 1.0), cfg.get("sc"))
    pert, oracle = E.build_perturbation(seed, cond, corr)
    tag = cond if corr is None else f"{cond}+{corr}"
    ep = run_episode(seed, pert, label=tag, oracle=oracle, condition=tag, robot=robot,
                     block_half=cfg.get("half", S.BLOCK_HALF), block_jitter=cfg.get("jitter", S.BLOCK_JITTER))
    return {"setting": setting, "robot": robot, "seed": seed, "cond": tag, "success": int(score_episode(ep)["success"])}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    for setting in SETTINGS:
        for robot in ARMS:
            f = OUT / f"{setting}_{robot}.jsonl"
            jobs = [(setting, robot, s, c, None) for s in SEEDS for c in E.CONDITIONS]
            jobs += [(setting, robot, s, "full", n) for s in SEEDS for n in CORRS]
            if f.exists() and sum(1 for _ in f.open()) == len(jobs):
                continue
            with mp.get_context("spawn").Pool(min(96, mp.cpu_count())) as p:
                rows = p.map(job, jobs, chunksize=4)
            f.write_text("\n".join(json.dumps(r) for r in rows))
            print(setting, robot, "full", sum(r["success"] for r in rows if r["cond"] == "full"), "/", len(SEEDS), flush=True)


def analyse():
    rng = np.random.default_rng(1)
    res = {}
    for setting in SETTINGS:
        for robot in ARMS:
            rows = [json.loads(l) for l in (OUT / f"{setting}_{robot}.jsonl").read_text().splitlines()]
            m = {}
            for r in rows:
                m.setdefault(r["cond"], {})[r["seed"]] = r["success"]
            a = {c: np.array([m[c][s] for s in SEEDS]) for c in m}
            full = a["full"]
            bud = {c: a[f"oracle_{c}"] - full for c in E.COMPONENTS}
            cor = {E.CORRECTIONS[c]: a[f"full+{E.CORRECTIONS[c]}"] - full for c in E.COMPONENTS}
            def ci(v):
                b = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(2000)]
                return [100 * float(np.quantile(b, .025)), 100 * float(np.quantile(b, .975))]
            dev, ev = slice(0, 60), slice(60, None)           # rule comparison: choose on first 60 seeds, evaluate on the rest
            pick = max(E.COMPONENTS, key=lambda c: bud[c][dev].mean())
            gains = {n: 100 * float(v[ev].mean()) for n, v in cor.items()}
            res[f"{setting}/{robot}"] = {
                "full": int(full.sum()), "n": len(SEEDS),
                "budget_pp": {c: [100 * float(v.mean()), *ci(v)] for c, v in bud.items()},
                "oracle_all_pp": 100 * float((a["oracle_all"] - full).mean()),
                "largest_budget": max(E.COMPONENTS, key=lambda c: bud[c].mean()),
                "corr_gain_pp": {n: [100 * float(v.mean()), *ci(v)] for n, v in cor.items()},
                "rule_eval_pp": {"budget_pick": gains[E.CORRECTIONS[pick]], "picked": pick,
                                 "always_look_again": gains["look_again"], "random_mean": float(np.mean(list(gains.values()))),
                                 "hindsight_best": max(gains.values())}}
    (OUT / "summary.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(k, "full", v["full"], "largest", v["largest_budget"], {c: round(x[0], 1) for c, x in v["budget_pp"].items()},
              "rule", {a: (round(b, 1) if not isinstance(b, str) else b) for a, b in v["rule_eval_pp"].items()})


if __name__ == "__main__":
    {"run": run, "analyse": analyse}[sys.argv[1]]()
