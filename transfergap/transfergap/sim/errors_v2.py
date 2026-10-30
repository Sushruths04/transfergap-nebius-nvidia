"""Error model for gap_budget_v2: v1's three components plus a kinematics/retargeting stage.

EVERY numeric constant below is an ASSUMPTION for this preliminary study. None was measured on a real
pipeline; they were fixed before any v2 trial was run and are frozen in the protocol JSON before held-out trials.

Differences from v1 (errors.py, left unchanged so v1 stays reproducible):
  * new component "retargeting": the joint targets sent to the arm carry a constant per-seed joint-space offset,
    standing in for an imperfect human-wrist -> robot-joint retargeter. Its oracle is exact IK on the robot model
    (the controller's own damped-least-squares solution with no offset). No cuRobo is involved.
  * every component draws from its OWN seeded RNG stream, keyed by (seed, component). Adding/removing a component
    cannot shift another component's draws, and a seed's calibration direction is an independent uniform draw on
    the sphere (random per seed, never a fixed direction).
  * errors depend only on the seed, never on the robot, so UR5e and UR10e see identical injected errors per seed
    (the same "human demo" transferred to two arms). The same joint-space error moves the longer UR10e's tool
    further, which is a real morphology effect, not a modelling choice.
This module reads no simulator state at all (enforced by tests/test_privileged_guard.py).
"""
from __future__ import annotations

import numpy as np

PROTOCOL_NAME = "gap_budget_v2"
_ROOT = 424242
# ASSUMPTION: monocular-RGB object localisation error on block xy, isotropic Gaussian, per-axis sigma 1.5 cm (as v1).
PERCEPTION_SIGMA_M = 0.015
# ASSUMPTION: retargeting (human wrist trajectory -> robot joint targets) leaves a constant joint-space error,
# i.i.d. Gaussian per joint, sigma 0.5 deg. Order-of-magnitude guess, not measured.
RETARGET_JOINT_SIGMA_RAD = float(np.deg2rad(0.5))
# ASSUMPTION: tool-frame calibration error, direction uniform on the sphere drawn per seed, magnitude ~ U(0, 3 cm).
CALIBRATION_MAX_M = 0.03
# ASSUMPTION: execution speed taken from a human-paced demo; speed factor relative to robot nominal ~ U(1, 4.5).
TIMING_SPEED_RANGE = (1.0, 4.5)
# ASSUMPTION: grip force nominal; no contact/grip component in the budget (nominal grip ~180x block weight).
GRIP_FORCE_SCALE = 1.0

# Correction-menu constants (ASSUMPTIONS)
LOOK_AGAIN_SIGMA_M = 0.004       # perception: re-perceive block from close range, per-axis sigma 0.4 cm
IK_RESOLVE_SIGMA_RAD = float(np.deg2rad(0.05))   # retargeting: re-solve IK on the robot model for the
                                 # retargeted Cartesian targets; residual joint error sigma 0.05 deg per joint
PROBE_SIGMA_M = 0.002            # calibration: touch-probe of a known fixture, per-axis measurement sigma 2 mm
SPEED_CAP = 3.0                  # timing: cap speed factor at 3.0

COMPONENTS = ("perception", "retargeting", "calibration", "timing")   # pipeline order = tie-break order
CONDITIONS = {"full": "none", **{f"oracle_{c}": c for c in COMPONENTS}, "oracle_all": "all"}
CORRECTIONS = {"perception": "look_again", "retargeting": "ik_resolve",
               "calibration": "touch_probe_calibration", "timing": "speed_cap_3"}
_STREAM = {"perception": 1, "retargeting": 2, "calibration": 3, "timing": 4,
           "look_again": 11, "ik_resolve": 12, "probe": 13}


def _rng(seed, stream):
    return np.random.default_rng([int(seed), _ROOT, _STREAM[stream]])


def sample_errors(seed):
    """All random draws for a seed. Each quantity has its own stream, so draws are independent across components."""
    cal = _rng(seed, "calibration")
    direction = cal.normal(size=3)
    direction /= np.linalg.norm(direction)
    calibration = direction * cal.uniform(0.0, CALIBRATION_MAX_M)
    return {"perception_err_xy": _rng(seed, "perception").normal(0.0, PERCEPTION_SIGMA_M, 2),
            "retarget_q_err": _rng(seed, "retargeting").normal(0.0, RETARGET_JOINT_SIGMA_RAD, 6),
            "tcp_offset_vec": calibration,
            "timing_scale": float(_rng(seed, "timing").uniform(*TIMING_SPEED_RANGE)),
            "grip_force_scale": GRIP_FORCE_SCALE,
            "look_again_err_xy": _rng(seed, "look_again").normal(0.0, LOOK_AGAIN_SIGMA_M, 2),
            "ik_resolve_q_err": _rng(seed, "ik_resolve").normal(0.0, IK_RESOLVE_SIGMA_RAD, 6),
            "probe_noise_m": _rng(seed, "probe").normal(0.0, PROBE_SIGMA_M, 3)}


def build_perturbation(seed, condition, correction=None):
    """(perturbation kwargs for ScriptedPickPlace, oracle string). A correction is applied on top of the FULL
    error sample only."""
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")
    oracle = CONDITIONS[condition]
    e = sample_errors(seed)
    zero = {c: oracle in (c, "all") for c in COMPONENTS}
    pert = {"perception_err_xy": [0.0, 0.0] if zero["perception"] else e["perception_err_xy"].tolist(),
            "retarget_q_err": [0.0] * 6 if zero["retargeting"] else e["retarget_q_err"].tolist(),
            "tcp_offset_vec": [0.0, 0.0, 0.0] if zero["calibration"] else e["tcp_offset_vec"].tolist(),
            "timing_scale": 1.0 if zero["timing"] else e["timing_scale"],
            "grip_force_scale": e["grip_force_scale"]}
    if correction is not None:
        if oracle != "none":
            raise ValueError("corrections are applied to the full-error condition only")
        if correction == "look_again":
            pert["look_again_err_xy"] = e["look_again_err_xy"].tolist()
        elif correction == "ik_resolve":
            pert["retarget_q_err"] = e["ik_resolve_q_err"].tolist()   # retargeting error replaced by IK residual
        elif correction == "touch_probe_calibration":
            pert["tcp_probe_noise_m"] = e["probe_noise_m"].tolist()
        elif correction == "speed_cap_3":
            pert["timing_scale"] = min(pert["timing_scale"], SPEED_CAP)
        else:
            raise ValueError(f"unknown correction {correction!r}")
    return pert, oracle


def constants():
    return {"PERCEPTION_SIGMA_M": PERCEPTION_SIGMA_M, "RETARGET_JOINT_SIGMA_RAD": RETARGET_JOINT_SIGMA_RAD,
            "CALIBRATION_MAX_M": CALIBRATION_MAX_M, "CALIBRATION_DIRECTION": "uniform on sphere, per seed",
            "TIMING_SPEED_RANGE": list(TIMING_SPEED_RANGE), "GRIP_FORCE_SCALE": GRIP_FORCE_SCALE,
            "LOOK_AGAIN_SIGMA_M": LOOK_AGAIN_SIGMA_M, "IK_RESOLVE_SIGMA_RAD": IK_RESOLVE_SIGMA_RAD,
            "PROBE_SIGMA_M": PROBE_SIGMA_M, "SPEED_CAP": SPEED_CAP, "all_values_are_assumptions": True}
