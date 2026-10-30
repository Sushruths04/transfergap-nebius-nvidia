"""How closely a G1 copied a person: the G1's right wrist (relative to its pelvis) against the person's right wrist (relative to the hips).

    python -m transfergap.human.mimic_fidelity --joints pose_scaled.npz --episode seed0_r0.episode.json [--side Right]

The replay starts at an unknown time after the sim is ready, so the person's signal is slid over the G1's (0-15 s) and the offset with the best summed
correlation is used; per G1 axis the best-matching person axis is reported (Pearson r, one-to-one axis assignment) with the ratio of the motion ranges. This measures wrist-path
similarity only (not the hand, not the legs) and it is a fit over a free offset and an axis assignment, so r is optimistic by construction: read it as
"does the G1 move its wrist like the person" and compare with the shuffled-time baseline printed next to it.
"""
from __future__ import annotations

import argparse
import itertools
import json

import numpy as np

from .analyze import R_HIP, L_HIP, SIDE


def _z(x):
    return (x - x.mean(0)) / np.maximum(x.std(0), 1e-9)


def fidelity(joints, fps, episode, side="Right", max_offset_s=15.0):
    J = np.asarray(joints, float)
    wr = J[:, SIDE[side]["wr"]] - (J[:, L_HIP] + J[:, R_HIP]) / 2
    st = episode["states"]
    t = np.array([s["t_s"] for s in st])
    g = np.array([s["right_wrist_xyz"] for s in st], float) - np.array([s["pelvis_xyz"] for s in st], float)
    tp = np.arange(len(wr)) / fps
    best = None
    for off in np.arange(0.0, max_offset_s, 0.1):
        m = (t >= off) & (t <= off + tp[-1])
        if m.sum() < 50:
            continue
        P = np.stack([np.interp(t[m] - off, tp, wr[:, k]) for k in range(3)], 1)
        C = _z(g[m]).T @ _z(P) / m.sum()                      # G1 axis x person axis correlations
        score = max(sum(abs(C[a, p[a]]) for a in range(3)) for p in itertools.permutations(range(3)))
        if best is None or score > best[0]:
            best = (score, off, m, P, C)
    _, off, m, P, C = best
    rng = np.random.default_rng(0)
    base = []
    for _ in range(200):                                         # time-shuffled baseline with the same axis assignment freedom
        sh = P[rng.permutation(len(P))]
        Cs = _z(g[m]).T @ _z(sh) / m.sum()
        base.append(max(sum(abs(Cs[a, p[a]]) for a in range(3)) for p in itertools.permutations(range(3))) / 3)
    perm = max(itertools.permutations(range(3)), key=lambda p: sum(abs(C[a, p[a]]) for a in range(3)))   # one-to-one axis assignment
    rows = []
    for a, name in enumerate("xyz"):
        b = perm[a]
        rows.append({"g1_axis": name, "person_axis": b, "pearson_r": round(float(C[a, b]), 3),
                     "range_ratio_g1_over_person": round(float(np.ptp(g[m][:, a]) / max(np.ptp(P[:, b]), 1e-9)), 2)})
    return {"offset_s": round(float(off), 1), "samples": int(m.sum()), "axes": rows,
            "mean_abs_r": round(float(np.mean([abs(C[a, perm[a]]) for a in range(3)])), 3), "shuffled_baseline_mean_abs_r_p95": round(float(np.percentile(base, 95)), 3)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--joints", required=True)
    ap.add_argument("--episode", required=True)
    ap.add_argument("--side", default="Right")
    a = ap.parse_args()
    z = np.load(a.joints, allow_pickle=False)
    print(json.dumps(fidelity(z["joints"], float(z["fps"]), json.load(open(a.episode)), a.side), indent=1))


if __name__ == "__main__":
    main()
