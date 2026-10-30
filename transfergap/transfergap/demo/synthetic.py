"""Synthetic human pick-and-place demos (minimum-jerk hand motion) for tests and pipeline development.

These are NOT human data. Every constant is an ASSUMPTION; episodes built from them must carry
source="synthetic" so they can never be reported as a human-demonstration result. The generator returns the
ground-truth keyframes alongside the demo so tests can check the segmenter and retargeter recover them.
"""
from __future__ import annotations

import numpy as np

from .schema import HumanDemo

# ASSUMPTIONS (human-like, not measured)
OBJECT_XYZ = (0.0, 0.0, 0.02)            # 4 cm block centre on the table, demo frame
GOAL_XYZ = (0.25, 0.20, 0.02)
HAND_START = (-0.20, -0.25, 0.25)
APERTURE_OPEN, APERTURE_CLOSED = 0.09, 0.04
DURATIONS_S = {"reach": 0.9, "close": 0.3, "lift": 0.5, "transport": 0.9, "place": 0.5, "open": 0.3,
               "retreat": 0.6}
LIFT_M = 0.15
RELEASE_ABOVE_M = 0.015                 # humans tend to let go slightly above the target


def _minjerk(a, b, n):
    s = np.linspace(0.0, 1.0, n)
    w = 10 * s ** 3 - 15 * s ** 4 + 6 * s ** 5
    return np.asarray(a, float) + w[:, None] * (np.asarray(b, float) - np.asarray(a, float))


def make_demo(seed=0, fps=30.0, grasp_bias_sigma_m=0.006, jitter_sigma_m=0.0, speed=1.0):
    """(HumanDemo, truth). grasp_bias_sigma_m: off-centre human grasp; jitter_sigma_m: per-frame hand-estimation
    noise (white, then 3-frame smoothing), as a monocular estimator would add; speed > 1 = faster human."""
    rng = np.random.default_rng([int(seed), 77])
    obj, goal = np.array(OBJECT_XYZ), np.array(GOAL_XYZ)
    bias = np.r_[rng.normal(0.0, grasp_bias_sigma_m, 2), abs(rng.normal(0.0, grasp_bias_sigma_m / 2))]
    grasp_pt = obj + bias
    release_pt = goal + np.array([0.0, 0.0, RELEASE_ABOVE_M]) + np.r_[bias[:2], 0.0]
    lift_pt = grasp_pt + [0.0, 0.0, LIFT_M]
    over_goal = release_pt + [0.0, 0.0, LIFT_M - RELEASE_ABOVE_M]
    retreat_pt = release_pt + [0.0, 0.0, 0.12]
    D = {k: v / speed for k, v in DURATIONS_S.items()}
    n = lambda d: max(2, int(round(d * fps)))
    legs = [("reach", HAND_START, grasp_pt, "open"), ("close", grasp_pt, grasp_pt, "closing"),
            ("lift", grasp_pt, lift_pt, "closed"), ("transport", lift_pt, over_goal, "closed"),
            ("place", over_goal, release_pt, "closed"), ("open", release_pt, release_pt, "opening"),
            ("retreat", release_pt, retreat_pt, "open")]
    pos, ap, marks = [], [], {}
    for name, a, b, grip in legs:
        k = n(D[name])
        marks[name] = len(pos)
        pos.extend(_minjerk(a, b, k))
        s = np.linspace(0, 1, k)
        ap.extend({"open": np.full(k, APERTURE_OPEN), "closed": np.full(k, APERTURE_CLOSED),
                   "closing": APERTURE_OPEN + s * (APERTURE_CLOSED - APERTURE_OPEN),
                   "opening": APERTURE_CLOSED + s * (APERTURE_OPEN - APERTURE_CLOSED)}[grip])
    pos, ap = np.array(pos), np.array(ap)
    if jitter_sigma_m > 0:
        noise = rng.normal(0.0, jitter_sigma_m, pos.shape)
        noise = (np.roll(noise, 1, 0) + noise + np.roll(noise, -1, 0)) / 3
        pos = pos + noise
        ap = np.clip(ap + rng.normal(0.0, jitter_sigma_m / 2, ap.shape), 0.0, None)
    t = np.arange(len(pos)) / fps
    demo = HumanDemo(t, pos, ap, obj, goal, "synthetic",
                     {"generator": "transfergap.demo.synthetic", "seed": int(seed), "fps": fps,
                      "grasp_bias_sigma_m": grasp_bias_sigma_m, "jitter_sigma_m": jitter_sigma_m,
                      "speed": speed, "all_values_are_assumptions": True})
    truth = {"grasp_offset": (grasp_pt - obj).tolist(), "release_offset": (release_pt - goal).tolist(),
             "grasp_index": marks["close"] + n(D["close"]) // 2, "release_index": marks["open"] + n(D["open"]) // 2,
             "lift_m": LIFT_M, "human_durations_s": D}
    return demo, truth
