"""Style fidelity of G1 rollouts driven by a retargeted human path (plan_reach.py --demo-plan). Laptop side.

Reference = the planned wrist path (the human path expressed at the G1 wrist by the IK in plan_style, with the
frozen stance offset). Measured = the logged right_wrist_xyz (simulator state, scoring only). The streamer start
time is not logged relative to the sim clock, so the measured path is aligned by the single time shift that
minimises the RMSE over the human legs (reach, carry, retreat); the shift is reported. Metrics per rollout:
  path_rmse_m per leg and mean, speed_profile_corr over the three legs, best_shift_s.

    python g1/style_score.py --run RUN_DIR:CONDITION:PLAN_NPZ [--run ...] --out results/<dir>/style.json
PLAN_NPZ may contain {seed} for per-seed plans (as g1/score.py).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

LEGS = ("reach", "carry", "retreat")


def rollout_style(states, plan_npz, fps=50.0):
    z = np.load(plan_npz)
    ref = np.asarray(z["wrist_plan_world"], float)
    phase = np.asarray(z["phase"]).astype(str)
    t_ref = np.arange(len(ref)) / fps
    mask = np.isin(phase, LEGS)
    t_log = np.array([s["t_s"] for s in states], float)
    w_log = np.array([s["right_wrist_xyz"] for s in states], float)

    def at(shift):
        return np.stack([np.interp(t_ref[mask] + shift, t_log, w_log[:, i]) for i in range(3)], axis=1)

    shifts = np.arange(0.0, max(0.1, t_log[-1] - t_ref[mask][-1]), 0.02)
    errs = [np.sqrt(np.mean(np.sum((at(s) - ref[mask]) ** 2, axis=1))) for s in shifts]
    best = float(shifts[int(np.argmin(errs))])
    meas = at(best)
    out = {"best_shift_s": best, "path_rmse_m": {}}
    for leg in LEGS:
        sel = phase[mask] == leg
        out["path_rmse_m"][leg] = float(np.sqrt(np.mean(np.sum((meas[sel] - ref[mask][sel]) ** 2, axis=1))))
    out["path_rmse_mean_m"] = float(np.mean(list(out["path_rmse_m"].values())))
    v_ref = np.linalg.norm(np.gradient(ref[mask], 1 / fps, axis=0), axis=1)
    v_meas = np.linalg.norm(np.gradient(meas, 1 / fps, axis=0), axis=1)
    out["speed_profile_corr"] = float(np.corrcoef(v_ref, v_meas)[0, 1]) if v_meas.std() > 1e-9 else 0.0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="RUN_DIR:CONDITION:PLAN_NPZ")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {}
    for spec in a.run:
        run, cond, plan = spec.split(":")
        rows = []
        for f in sorted(Path(run).glob("seed*_r*.episode.json")):
            ep = json.loads(f.read_text())
            if ep.get("states"):
                rows.append({"rollout": f.name.split(".")[0],
                             **rollout_style(ep["states"], plan.format(seed=ep["seed"]))})
        res[cond] = {"n": len(rows), "path_rmse_mean_m": float(np.mean([r["path_rmse_mean_m"] for r in rows])),
                     "path_rmse_median_m": float(np.median([r["path_rmse_mean_m"] for r in rows])),
                     "speed_profile_corr": float(np.mean([r["speed_profile_corr"] for r in rows])),
                     "rollouts": rows}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: {kk: v[kk] for kk in ("n", "path_rmse_mean_m", "speed_profile_corr")} for k, v in res.items()},
                     indent=1))


if __name__ == "__main__":
    main()
