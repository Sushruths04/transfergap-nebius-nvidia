"""Per-rollout features at the start of the hand-close phase (plan frame 300 of 50 Hz), read-only on logged files.

Used by results/g1_pelvis_drift_v1. Definitions (fixed in that protocol):
  offset_cm = measured grasp point (cl.npz meas_world, from the robot's own joints and pelvis pose) minus the block position
              from the sim state at that time, in cm, with the 74 cm table-top/block-centre height removed from z.
  drift_cm  = horizontal distance of the pelvis from its start position (world origin) at that frame, in cm.
The extraction script behind results/g1_hybrid_failure_analysis_v1 was not kept; this is a reimplementation with its own
definitions, so it is re-derived on the 120 dev rollouts instead of reusing that analysis' numbers.
"""
import argparse, json
from pathlib import Path
import numpy as np

CLOSE_FRAME = 300
BLOCK_CENTRE_Z = 0.74


def feats(run_dir, seed):
    d = Path(run_dir)
    e = json.loads((d / f"seed{seed}_r0.episode.json").read_text())
    c = np.load(d / f"seed{seed}_r0.cl.npz", allow_pickle=True)
    s = e["states"]
    t = np.array([x["t_s"] for x in s])
    i = int(np.argmin(abs(t - (e["t_go_s"] + CLOSE_FRAME / 50.0))))
    off = (np.asarray(c["meas_world"][CLOSE_FRAME]) - np.asarray(s[i]["object_xyz"])) * 100.0
    off[2] -= 0.0   # object_xyz is already the block centre; no height removal needed
    return dict(seed=seed, dx=float(off[0]), dy=float(off[1]), dz=float(off[2]),
                drift_cm=float(np.linalg.norm(np.asarray(s[i]["pelvis_xyz"])[:2]) * 100.0),
                lift_cm=float((max(x["object_xyz"][2] for x in s) - s[0]["object_xyz"][2]) * 100.0))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("run_dir"); ap.add_argument("seeds"); a = ap.parse_args()
    lo, hi = map(int, a.seeds.split("-"))
    print(json.dumps([feats(a.run_dir, s) for s in range(lo, hi + 1)]))
