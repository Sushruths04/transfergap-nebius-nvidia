"""Simulator-state scoring. Model opinions never define benchmark success."""
from __future__ import annotations

import math
import random
from statistics import mean


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def vector3(value):
    return isinstance(value, (list, tuple)) and len(value) == 3 and all(map(finite_number, value))


def validate_episode(ep):
    if ep.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    for key in ("trial_id", "demo_id", "scene_id", "robot", "method", "sensor", "protocol_id", "frame_id"):
        if not isinstance(ep.get(key), str) or not ep[key].strip():
            raise ValueError(f"Missing nonempty {key}")
    if ep.get("source") not in {"fixture", "simulation", "hardware"}:
        raise ValueError("source must be fixture, simulation, or hardware")
    for key in ("oracle", "condition"):   # optional; oracle names which pipeline stage was replaced by ground truth
        if key in ep and (not isinstance(ep[key], str) or not ep[key].strip()):
            raise ValueError(f"{key}, when present, must be a nonempty string")
    if type(ep.get("seed")) is not int:
        raise ValueError("seed must be an integer")
    if ep.get("sensor") not in {"rgb", "rgbd", "oracle"}:
        raise ValueError("sensor must be rgb, rgbd, or oracle")
    if ep.get("units") != "m":
        raise ValueError("object positions must be in metres")
    task = ep.get("task", {})
    if not vector3(task.get("goal_xyz")):
        raise ValueError("task.goal_xyz must be a finite 3-vector")
    for key in ("position_tolerance_m", "min_lift_m", "settle_duration_s", "max_settle_speed_m_s"):
        if not finite_number(task.get(key)) or task[key] <= 0:
            raise ValueError(f"task.{key} must be positive and finite")
    states = ep.get("states", [])
    if len(states) < 2:
        raise ValueError("At least two timestamped states are required")
    previous = -math.inf
    for state in states:
        t = state.get("t_s")
        if not finite_number(t) or t < 0 or t <= previous:
            raise ValueError("Timestamps must be finite, nonnegative, strictly increasing")
        previous = t
        if not vector3(state.get("object_xyz")) or not vector3(state.get("object_velocity")):
            raise ValueError("Finite object position and velocity are required")
        for key in ("released", "forbidden_collision", "fallen"):
            if type(state.get(key)) is not bool:
                raise ValueError(f"{key} must be an explicit boolean")
    reference = ep.get("reference")
    if reference is not None:
        if len(reference) != len(states):
            raise ValueError("Reference and rollout must use the same sample times")
        for ref, state in zip(reference, states):
            if ref.get("t_s") != state["t_s"] or not vector3(ref.get("object_xyz")):
                raise ValueError("Reference must contain finite positions at identical sample times")


def score_episode(ep):
    validate_episode(ep)
    states, task = ep["states"], ep["task"]
    goal = task["goal_xyz"]
    lifted = max(s["object_xyz"][2] for s in states) - states[0]["object_xyz"][2] >= task["min_lift_m"]
    collision = any(s["forbidden_collision"] for s in states)
    fallen = any(s["fallen"] for s in states)
    # Use a contiguous suffix, including a sample at/before the dwell boundary.
    suffix_start = states[-1]["t_s"]
    for state in reversed(states):
        settled = (math.dist(state["object_xyz"], goal) <= task["position_tolerance_m"]
                   and math.dist(state["object_velocity"], (0, 0, 0)) <= task["max_settle_speed_m_s"]
                   and state["released"])
        if not settled:
            break
        suffix_start = state["t_s"]
    held_s = states[-1]["t_s"] - suffix_start
    placed = held_s + 1e-9 >= task["settle_duration_s"]
    reasons = []
    if not lifted:
        reasons.append("no_lift")
    if not placed:
        reasons.append("not_released_and_settled_at_goal")
    if collision:
        reasons.append("forbidden_collision")
    if fallen:
        reasons.append("fallen")
    reference = ep.get("reference")
    rmse = None
    if reference is not None:
        rmse = math.sqrt(mean(math.dist(a["object_xyz"], b["object_xyz"]) ** 2
                              for a, b in zip(states, reference)))
    return {
        "success": not reasons,
        "failure_reasons": reasons,
        "final_object_error_m": math.dist(states[-1]["object_xyz"], goal),
        "object_position_sample_rmse_m": rmse,
        "settled_duration_s": held_s,
        "elapsed_s": states[-1]["t_s"] - states[0]["t_s"],
    }


_FROZEN_TASK_KEYS = ("position_tolerance_m", "min_lift_m", "settle_duration_s", "max_settle_speed_m_s")


def validate_protocol_consistency(episodes):
    """A protocol_id freezes scoring thresholds, frame and units; only goal_xyz may vary per scene.

    Pooling episodes that silently changed tolerance/timing/frame/units under one protocol_id
    can mix incompatible success definitions into a single report or paired comparison.
    """
    frozen = {}
    for ep in episodes:
        pid = ep["protocol_id"]
        signature = tuple(ep["task"][k] for k in _FROZEN_TASK_KEYS) + (ep["frame_id"], ep["units"])
        previous = frozen.get(pid)
        if previous is not None and previous != signature:
            raise ValueError(f"protocol_id {pid!r} has inconsistent tolerances/timing/frame/units "
                              "across trials; freeze scoring settings per protocol before reporting")
        frozen[pid] = signature


def wilson_interval(successes, total, z=1.959963984540054):
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("Invalid binomial counts")
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return [max(0.0, center - margin), min(1.0, center + margin)]


def summarize(episodes, allow_fixtures=False):
    episodes = list(episodes)
    if not episodes:
        raise ValueError("No episodes")
    if any(ep.get("source") == "fixture" for ep in episodes) and not allow_fixtures:
        raise ValueError("Fixture data requires --allow-fixtures; it is not model performance")
    groups, seen = {}, set()
    for ep in episodes:
        result = score_episode(ep)  # validates the episode, including task/protocol fields, first
        # oracle is part of the group key: episodes with different oracle substitutions are never pooled
        key = tuple(ep[k] for k in ("source", "protocol_id", "robot", "method", "sensor")) + (ep.get("oracle"),)
        identity = key + tuple(ep[k] for k in ("demo_id", "scene_id", "seed", "trial_id"))
        if identity in seen:
            raise ValueError("Duplicate episode in report")
        seen.add(identity)
        groups.setdefault(key, []).append(result)
    validate_protocol_consistency(episodes)
    reports = []
    for key, rows in sorted(groups.items()):
        n, successes = len(rows), sum(r["success"] for r in rows)
        reports.append(dict(zip(("source", "protocol_id", "robot", "method", "sensor", "oracle"), key),
                            episodes=n, successes=successes, success_rate=successes / n,
                            success_wilson_95=wilson_interval(successes, n)))
    return {"contains_fixtures": any(ep["source"] == "fixture" for ep in episodes), "groups": reports}


def paired_gap(left, right, bootstrap_samples=2000):
    """B minus A in percentage points; paired resampling of independent trial blocks.

    Inputs must each be one condition. Repeated frames are never resampled as trials.
    Use one trial per independent scene/demo block for inferential claims.
    """
    def index(items):
        result, conditions = {}, set()
        for ep in items:
            validate_episode(ep)
            # oracle must be uniform within a side (no silent pooling); it MAY differ between sides
            conditions.add(tuple(ep[k] for k in ("source", "protocol_id", "robot", "method", "sensor")) + (ep.get("oracle"),))
            key = tuple(ep[k] for k in ("demo_id", "scene_id", "seed", "trial_id"))
            if key in result:
                raise ValueError("Duplicate matched trial")
            result[key] = ep
        if len(conditions) != 1:
            raise ValueError("Each side must contain exactly one condition")
        return result
    a, b = index(left), index(right)
    if not a or a.keys() != b.keys():
        raise ValueError("Both conditions must have the same nonempty trial set")
    validate_protocol_consistency(list(a.values()) + list(b.values()))
    if bootstrap_samples < 100:
        raise ValueError("Use at least 100 bootstrap samples")
    differences = []
    for key in sorted(a):
        x, y = a[key], b[key]
        for field in ("source", "protocol_id", "task", "frame_id", "units"):
            if x[field] != y[field]:
                raise ValueError(f"Mismatched {field}: cannot compare trials")
        differences.append(int(score_episode(y)["success"]) - int(score_episode(x)["success"]))
    rng = random.Random(0)
    samples = sorted(100 * mean(rng.choices(differences, k=len(differences)))
                     for _ in range(bootstrap_samples))
    return {"paired_trials": len(differences), "success_gap_b_minus_a_pp": 100 * mean(differences),
            "paired_bootstrap_95_pp": [samples[int(.025 * (len(samples) - 1))],
                                       samples[int(.975 * (len(samples) - 1))]],
            "interval_note": "Descriptive for small n; assumes independent trial blocks."}
