"""Error model for the "transferred" (human demo -> robot) condition, plus oracle substitution and corrections.

EVERY numeric constant below is an ASSUMPTION for this preliminary study. None was measured on a real
pipeline; they are chosen to be plausible and are frozen in the protocol JSON before held-out trials.
Errors are sampled per seed from a seeded RNG, so a condition is fully determined by (seed, condition).
"""
from __future__ import annotations

import numpy as np

# ASSUMPTION: monocular-RGB object localisation error on block xy, isotropic Gaussian, per-axis sigma 1.5 cm.
PERCEPTION_SIGMA_M = 0.015
# ASSUMPTION: tool-frame calibration error, random 3D direction (uniform on the sphere), magnitude ~ U(0, 3 cm).
CALIBRATION_MAX_M = 0.03
# ASSUMPTION: execution speed taken from a human-paced demo; speed factor relative to robot nominal ~ U(1, 4.5).
TIMING_SPEED_RANGE = (1.0, 4.5)
# ASSUMPTION: grip force nominal. The contact oracle is NOT separately informative here (nominal grip is
# ~180x the block weight), so there is no grip component in the budget.
GRIP_FORCE_SCALE = 1.0

# Correction-menu constants (ASSUMPTIONS)
LOOK_AGAIN_SIGMA_M = 0.004   # perception: re-perceive block from close range, per-axis sigma 0.4 cm
PROBE_SIGMA_M = 0.002        # calibration: touch-probe of a known fixture, per-axis measurement sigma 2 mm
SPEED_CAP = 3.0              # timing: cap speed factor at 3.0

COMPONENTS = ("perception", "calibration", "timing")   # oracle components, in tie-break order
CONDITIONS = {                                          # condition -> oracle string
    "full": "none",
    "oracle_perception": "perception",
    "oracle_calibration": "calibration",
    "oracle_timing": "timing",
    "oracle_all": "all",
}
CORRECTIONS = {"perception": "look_again", "calibration": "touch_probe_calibration", "timing": "speed_cap_3"}


def sample_errors(seed):
    """All random draws for a seed, in fixed order, so every condition/correction sees identical values."""
    rng = np.random.default_rng([int(seed), 424242])
    perception = rng.normal(0.0, PERCEPTION_SIGMA_M, 2)
    direction = rng.normal(size=3)
    direction /= np.linalg.norm(direction)
    calibration = direction * rng.uniform(0.0, CALIBRATION_MAX_M)
    speed = rng.uniform(*TIMING_SPEED_RANGE)
    look_again = rng.normal(0.0, LOOK_AGAIN_SIGMA_M, 2)      # only used if the look-again correction is on
    probe = rng.normal(0.0, PROBE_SIGMA_M, 3)                # only used if the probe correction is on
    return {"perception_err_xy": perception, "tcp_offset_vec": calibration, "timing_scale": float(speed),
            "grip_force_scale": GRIP_FORCE_SCALE, "look_again_err_xy": look_again, "probe_noise_m": probe}


def build_perturbation(seed, condition, correction=None):
    """(perturbation kwargs for ScriptedPickPlace, oracle string). correction in {None, 'look_again',
    'touch_probe_calibration', 'speed_cap_3'} is applied on top of the FULL error sample."""
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")
    oracle = CONDITIONS[condition]
    e = sample_errors(seed)
    zero_p, zero_c, zero_t = (oracle in (c, "all") for c in COMPONENTS)
    pert = {"perception_err_xy": [0.0, 0.0] if zero_p else e["perception_err_xy"].tolist(),
            "tcp_offset_vec": [0.0, 0.0, 0.0] if zero_c else e["tcp_offset_vec"].tolist(),
            "timing_scale": 1.0 if zero_t else e["timing_scale"],
            "grip_force_scale": e["grip_force_scale"]}
    if correction is not None:
        if oracle != "none":
            raise ValueError("corrections are applied to the full-error condition only")
        if correction == "look_again":
            pert["look_again_err_xy"] = e["look_again_err_xy"].tolist()
        elif correction == "touch_probe_calibration":
            pert["tcp_probe_noise_m"] = e["probe_noise_m"].tolist()
        elif correction == "speed_cap_3":
            pert["timing_scale"] = min(pert["timing_scale"], SPEED_CAP)
        else:
            raise ValueError(f"unknown correction {correction!r}")
    return pert, oracle


def constants():
    return {"PERCEPTION_SIGMA_M": PERCEPTION_SIGMA_M, "CALIBRATION_MAX_M": CALIBRATION_MAX_M,
            "TIMING_SPEED_RANGE": list(TIMING_SPEED_RANGE), "GRIP_FORCE_SCALE": GRIP_FORCE_SCALE,
            "LOOK_AGAIN_SIGMA_M": LOOK_AGAIN_SIGMA_M, "PROBE_SIGMA_M": PROBE_SIGMA_M, "SPEED_CAP": SPEED_CAP,
            "all_values_are_assumptions": True}
