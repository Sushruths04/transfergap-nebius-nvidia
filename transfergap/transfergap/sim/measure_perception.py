"""Measures the depth estimator's block-position error (xy) against ground truth, nominal and under camera-calibration error.
Seeds 7000-7199, both arms, 4 cm block. Writes runs/perception_measured.json.   python -m transfergap.sim.measure_perception"""
import json
from pathlib import Path
import numpy as np
from .perception import Perceiver
from .perception_eval import MAX_WIDTH_M
from .scene import Scene, BLOCK_HALF

CONDS = {"nominal": {}, "calib_0p5deg_5mm": dict(calib_rot_deg=0.5, calib_trans_mm=5.0),
         "calib_1deg_10mm": dict(calib_rot_deg=1.0, calib_trans_mm=10.0), "calib_2deg_20mm": dict(calib_rot_deg=2.0, calib_trans_mm=20.0)}


def main():
    ROOT = Path(__file__).resolve().parents[2]
    out = {}
    for key, kw in CONDS.items():
        errs = []
        for robot in ("ur5e", "ur10e"):
            for seed in range(7000, 7200):
                sc = Scene(seed, robot, BLOCK_HALF)
                try:
                    est = Perceiver(MAX_WIDTH_M[robot], sigma_m=0.002, **kw)(sc)
                    errs.append(np.asarray(est["block_xyz"][:2]) - sc.block_pos()[:2])
                except Exception:
                    errs.append(np.array([np.nan, np.nan]))
        e = np.array(errs)
        ok = np.isfinite(e).all(axis=1)
        e = e[ok]
        out[key] = {"n": int(len(errs)), "n_valid": int(ok.sum()), "rms_axis_m": float(np.sqrt((e ** 2).mean())),
                    "mean_xy_m": e.mean(axis=0).tolist(), "p95_norm_m": float(np.quantile(np.linalg.norm(e, axis=1), .95))}
        print(key, out[key], flush=True)
    (ROOT / "runs").mkdir(exist_ok=True)
    (ROOT / "runs" / "perception_measured.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
