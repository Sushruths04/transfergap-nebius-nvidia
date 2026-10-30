"""Error model for demo_budget_v1: the robot is driven by a HUMAN DEMO through style-preserving retargeting.

Components (pipeline order = tie-break order):
  perception   ASSUMED, as gap_budget_v2: block xy belief error, per-axis sigma 1.5 cm (errors_v2 stream)
  retargeting  MEASURED from the demo pipeline: the robot follows the plan built from the ESTIMATED human hand path
               (clean demo + per-seed hand-pose-estimation noise). Oracle = plan built from the clean demo. Only
               available when the clean demo is known (synthetic demos); for a real demo the estimate IS the input,
               so this component is dropped (see components_for()).
  calibration  ASSUMED, as gap_budget_v2: tool-frame offset, random direction per seed, magnitude U(0, 3 cm)
  timing       MEASURED from the demo: the robot executes the human's skill durations (plan timing_scale).
               Oracle = robot-nominal durations (timing_scale 1.0). The human's within-leg speed profile shape is
               kept in both cases; only the absolute pace differs.
Corrections: perception -> look_again; retargeting -> smooth_demo (moving-average low-pass of the estimated hand
path before retargeting); calibration -> touch_probe_calibration; timing -> speed_cap_3.
This module reads no simulator state (tests/test_privileged_guard.py style check in tests/test_demo_budget.py).
"""
from __future__ import annotations

import hashlib
import json

import numpy as np

from ..demo.schema import HumanDemo
from ..demo.style import safe_project, safe_project_v2, style_plan_from_demo
from ..demo.synthetic import make_demo
from . import errors_v2

PROTOCOL_NAME = "demo_budget_v1"
_ROOT = 515151
# ASSUMPTION: monocular hand-pose estimation noise on the pinch point, per-axis sigma 1 cm, white per frame then
# 3-frame smoothed (as make_demo's jitter model). Order-of-magnitude for monocular hand estimators; not measured.
HAND_EST_SIGMA_M = 0.010
SMOOTH_WINDOW_S = 0.20           # correction: moving-average window on the estimated pinch path
SPEED_CAP = errors_v2.SPEED_CAP
ALL_COMPONENTS = ("perception", "retargeting", "calibration", "timing")
CORRECTIONS = {"perception": "look_again", "retargeting": "smooth_demo",
               "calibration": "touch_probe_calibration", "timing": "speed_cap_3"}
STYLE_FEASIBLE_MIN = 0.9   # dev oracle_all success below this => the copied style is infeasible (choose safe_path)
SPEED_LADDER = ("speed_cap_3", "speed_cap_2", "speed_cap_1.5")   # timing fixes, applied in this order when stacking


def next_correction(component, base=()):
    """The correction for `component` that is not yet in the stacked `base`, or None if that component's menu is
    exhausted (timing climbs SPEED_LADDER; the others have a single fix)."""
    base = tuple(base)
    if component == "timing":
        return next((c for c in SPEED_LADDER if c not in base), None)
    c = CORRECTIONS[component]
    return None if c in base else c


def _apply(pert, name, spec, seed, e):
    if name == "look_again":
        pert["look_again_err_xy"] = e["look_again_err_xy"].tolist()
    elif name == "smooth_demo":
        pert["demo_plan"] = style_plan_from_demo(_smooth_path(estimated_demo(spec, seed), SMOOTH_WINDOW_S))
    elif name == "touch_probe_calibration":
        pert["tcp_probe_noise_m"] = e["probe_noise_m"].tolist()
    elif name == "safe_path":                      # style-safety projection of the copied human path
        pert["demo_plan"] = safe_project(pert["demo_plan"])
    elif name == "safe_path_v2":                   # ... with a lift-first retreat
        pert["demo_plan"] = safe_project_v2(pert["demo_plan"])
    elif name.startswith("speed_cap_") and name in SPEED_LADDER:
        pert["timing_scale"] = min(pert["timing_scale"], float(name[len("speed_cap_"):]))
    else:
        raise ValueError(f"unknown correction {name!r}")


def components_for(demo_spec):
    return ALL_COMPONENTS if demo_spec["kind"] == "synthetic" else tuple(c for c in ALL_COMPONENTS if c != "retargeting")


def conditions_for(demo_spec):
    comps = components_for(demo_spec)
    return {"full": "none", **{f"oracle_{c}": c for c in comps}, "oracle_all": "all"}


def parse_demo_spec(text):
    """'synthetic:<seed>' or a path to a HumanDemo .npz (a real demo)."""
    if text.startswith("synthetic:"):
        return {"kind": "synthetic", "seed": int(text.split(":", 1)[1]), "tag": "syn" + text.split(":", 1)[1]}
    raw = open(text, "rb").read()
    return {"kind": "file", "path": text, "sha256": hashlib.sha256(raw).hexdigest(),
            "tag": "demo" + hashlib.sha256(raw).hexdigest()[:8]}


def clean_demo(spec):
    if spec["kind"] == "synthetic":
        return make_demo(seed=spec["seed"])[0]
    return HumanDemo.load(spec["path"])


def _smooth_path(demo, window_s):
    n = max(1, int(round(window_s * demo.fps)))
    k = np.ones(n) / n
    pad = n // 2
    xp = np.pad(demo.pinch, [(pad, n - 1 - pad), (0, 0)], mode="edge")
    p = np.stack([np.convolve(xp[:, i], k, mode="valid") for i in range(3)], axis=1)
    return HumanDemo(demo.t, p, demo.aperture, demo.object_xyz, demo.goal_xyz, demo.source,
                     {**demo.meta, "smoothed_window_s": window_s})


def estimated_demo(spec, seed):
    """The demo as the pipeline sees it for this seed. Synthetic: clean demo + per-seed estimation noise."""
    if spec["kind"] != "synthetic":
        return clean_demo(spec)
    clean = clean_demo(spec)
    rng = np.random.default_rng([int(seed), _ROOT, 1])
    noise = rng.normal(0.0, HAND_EST_SIGMA_M, clean.pinch.shape)
    noise = (np.roll(noise, 1, 0) + noise + np.roll(noise, -1, 0)) / 3
    return HumanDemo(clean.t, clean.pinch + noise, clean.aperture, clean.object_xyz, clean.goal_xyz, clean.source,
                     {**clean.meta, "estimation_noise_sigma_m": HAND_EST_SIGMA_M, "noise_seed": int(seed)})


def plans(spec, seed):
    """(plan the robot uses in the full condition, clean reference plan for style scoring)."""
    ref = style_plan_from_demo(clean_demo(spec))
    return style_plan_from_demo(estimated_demo(spec, seed)), ref


def build_perturbation(spec, seed, condition, correction=None, base=()):
    """(perturbation kwargs incl. demo_plan, oracle string, reference plan). `base` = corrections already adopted
    (applied first, in order, under every condition); a single oracle then removes its component's error; the new
    `correction` is only allowed on the full condition."""
    conds = conditions_for(spec)
    if condition not in conds:
        raise ValueError(f"unknown condition {condition!r} for this demo")
    oracle = conds[condition]
    zero = lambda c: oracle in (c, "all")
    e = errors_v2.sample_errors(seed)
    plan, ref = plans(spec, seed)
    pert = {"demo_plan": plan, "perception_err_xy": e["perception_err_xy"].tolist(),
            "tcp_offset_vec": e["tcp_offset_vec"].tolist(), "timing_scale": float(plan["timing_scale"])}
    for name in base:
        _apply(pert, name, spec, seed, e)
    if zero("retargeting") and "retargeting" in components_for(spec):
        pert["demo_plan"] = ref
        for name in base:                  # keep plan-shaping fixes already adopted (bug fix 2026-10-02: the oracle
            if name.startswith("safe_path"):   # used to drop them, which made oracle_all wrong with safe_path)
                _apply(pert, name, spec, seed, e)
    if zero("perception"):
        pert["perception_err_xy"] = [0.0, 0.0]
        pert.pop("look_again_err_xy", None)
    if zero("calibration"):
        pert["tcp_offset_vec"] = [0.0, 0.0, 0.0]
        pert.pop("tcp_probe_noise_m", None)
    if zero("timing"):
        pert["timing_scale"] = 1.0
    if correction is not None:
        if oracle != "none":
            raise ValueError("corrections are applied to the full-error condition only")
        _apply(pert, correction, spec, seed, e)
    return pert, oracle, ref


_LADDER_IN_CONSTANTS = False   # v1 protocols were frozen without it; stacked runs record it in protocol["stacking"]


def constants():
    return json.loads(json.dumps({"HAND_EST_SIGMA_M": HAND_EST_SIGMA_M, "SMOOTH_WINDOW_S": SMOOTH_WINDOW_S,
                                  "SPEED_CAP": SPEED_CAP, **({"SPEED_LADDER": list(SPEED_LADDER)} if _LADDER_IN_CONSTANTS else {}), "v2_constants_for_perception_calibration":
                                  errors_v2.constants(), "all_values_are_assumptions": True}))
