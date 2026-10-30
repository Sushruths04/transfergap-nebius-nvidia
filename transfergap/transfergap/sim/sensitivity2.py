"""Second sensitivity study (exploratory): 500-seed rule comparison, continuous perception-error curve, layout shifts,
and budgets with perception error matched to the depth estimator's measured position error.

  python -m transfergap.sim.sensitivity2 run [group ...]     groups: n500 curve layout depth (default: all)
Fresh seeds 6000-6999 (and 7000-7199 for the depth-error measurement, measure_perception.py). No setting is tuned.
"""
import json, os, sys, multiprocessing as mp
from pathlib import Path
import numpy as np
from . import errors_v2 as E
from . import scene as S
from .rollout import run_episode
from ..metrics import score_episode

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs" / "sensitivity_v2"
ARMS = ("ur5e", "ur10e")
CORRS = list(E.CORRECTIONS.values())
BASE = dict(P=E.PERCEPTION_SIGMA_M, R=E.RETARGET_JOINT_SIGMA_RAD, C=E.CALIBRATION_MAX_M, T=E.TIMING_SPEED_RANGE)
NOM = dict(tray=tuple(S.TRAY_XY), block=np.array(S.BLOCK_CENTER, float).tolist())
ORACLES6 = list(E.CONDITIONS)
SETTINGS = {}
for n, sc in {"err_x0.5": {"P": .5, "R": .5, "C": .5, "T": .5}, "perc_x0.25": {"P": .25},
              "perc_x0.25_cal_x2": {"P": .25, "C": 2.0}}.items():
    SETTINGS[n] = dict(group="n500", sc=sc, seeds=(6000, 500), corr=True)
for s in (0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0):
    SETTINGS[f"curve_P{s}"] = dict(group="curve", sc={"P": s}, seeds=(6600, 200), corr=False)
for n, kw in {"tray_far": dict(tray=(0.50, 0.30)), "tray_near": dict(tray=(0.40, 0.16)),
              "block_shift": dict(block=[0.40, -0.20])}.items():
    SETTINGS[n] = dict(group="layout", sc={}, seeds=(6800, 200), corr=True, **kw)
SETTINGS["timing_measured"] = dict(group="timing", sc={}, seeds=(7400, 500), corr=True, trange=(2.01, 9.38))
SETTINGS["depth_nominal"] = dict(group="depth", sc={}, seeds=(7200, 200), corr=False, pabs="nominal")
SETTINGS["depth_calib_0p5deg_5mm"] = dict(group="depth", sc={}, seeds=(7200, 200), corr=False, pabs="calib_0p5deg_5mm")
SETTINGS["depth_calib_1deg_10mm"] = dict(group="depth", sc={}, seeds=(7200, 200), corr=False, pabs="calib_1deg_10mm")


def measured(key):
    return json.loads((ROOT / "runs" / "perception_measured.json").read_text())[key]["rms_axis_m"]


def apply(cfg):
    sc = {k: cfg["sc"].get(k, 1.0) for k in "PRCT"}
    E.PERCEPTION_SIGMA_M = BASE["P"] * sc["P"] if "pabs" not in cfg else measured(cfg["pabs"])
    E.RETARGET_JOINT_SIGMA_RAD = BASE["R"] * sc["R"]
    E.CALIBRATION_MAX_M = BASE["C"] * sc["C"]
    E.TIMING_SPEED_RANGE = tuple(cfg["trange"]) if "trange" in cfg else (1.0, 1.0 + (BASE["T"][1] - 1.0) * sc["T"])
    S.TRAY_XY = tuple(cfg.get("tray", NOM["tray"]))
    S.BLOCK_CENTER = np.array(cfg.get("block", NOM["block"]), float)


def job(a):
    setting, robot, seed, cond, corr = a
    apply(SETTINGS[setting])
    pert, oracle = E.build_perturbation(seed, cond, corr)
    tag = cond if corr is None else f"{cond}+{corr}"
    ep = run_episode(seed, pert, label=tag, oracle=oracle, condition=tag, robot=robot)
    return {"setting": setting, "robot": robot, "seed": seed, "cond": tag, "success": int(score_episode(ep)["success"])}


def run(groups):
    OUT.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    for setting, cfg in SETTINGS.items():
        if cfg["group"] not in groups:
            continue
        a0, n = cfg["seeds"]
        seeds = range(a0, a0 + n)
        for robot in ARMS:
            f = OUT / f"{setting}_{robot}.jsonl"
            jobs = [(setting, robot, s, c, None) for s in seeds for c in ORACLES6]
            if cfg["corr"]:
                jobs += [(setting, robot, s, "full", k) for s in seeds for k in CORRS]
            if f.exists() and sum(1 for _ in f.open()) == len(jobs):
                continue
            with mp.get_context("spawn").Pool(min(28, mp.cpu_count())) as p:
                rows = p.map(job, jobs, chunksize=4)
            f.write_text("\n".join(json.dumps(r) for r in rows))
            print(setting, robot, "full", sum(r["success"] for r in rows if r["cond"] == "full"), "/", n, flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(set(sys.argv[2:]) or {"n500", "curve", "layout", "depth", "timing"})
