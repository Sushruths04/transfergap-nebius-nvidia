"""Human demo keyframes -> a robot-agnostic pick-and-place plan (JSON), used by ScriptedPickPlace(demo_plan=...).

The plan is OBJECT-RELATIVE: the robot reuses where the human grasped relative to the object and where the human
released relative to the target, applied at run time to the robot's own perception of the block and to the known
goal. Nothing here reads simulator state; the demo is the only input.

What the plan carries over from the human (and therefore what can go wrong in transfer):
  grasp_offset   human pinch point at grasp minus the object centre (off-centre grasps, estimation bias)
  place_offset   human pinch point at release minus the goal centre (humans often release above the target)
  clear_m        lift height above the grasp height
  timing_scale   robot nominal skill durations / human skill durations (a human-paced replay is faster)
The retargeter applies ONE documented safety rule: z offsets are clamped to >= Z_FLOOR_M so the commanded tool
point never goes below the object centre / goal centre by more than that (a target inside the table would only
measure the clamp, not the transfer).
"""
from __future__ import annotations

import numpy as np

from .segment import keyframes, segment

PLAN_SCHEMA = "transfergap.demo_plan/v1"
# Robot nominal durations (s) of the skills a human demo is matched against; from sim/controller.PHASES:
# reach = approach + descend, lift = lift, transport = transport, place = descend_place.
ROBOT_NOMINAL_S = {"reach": 3.5, "lift": 1.5, "transport": 2.5, "place": 1.5}
Z_FLOOR_M = -0.005
ROBOT_OBJECT_SIZE_M = 0.04   # the robot task's object (4 cm block); see object-normalised offsets below
CLEAR_RANGE_M = (0.05, 0.30)


def yaw_matrix(yaw):
    c, s = np.cos(yaw), np.sin(yaw)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def plan_from_demo(demo, align_yaw=0.0):
    """Plan dict. `align_yaw` (rad) rotates demo-frame offsets into the robot table frame (camera/table alignment)."""
    seg = segment(demo)
    kf = keyframes(demo, seg)
    R = yaw_matrix(align_yaw)
    g = R @ (np.asarray(kf["grasp_pinch"]) - demo.object_xyz)
    r = R @ (np.asarray(kf["release_pinch"]) - demo.goal_xyz)
    # Object-normalised offsets: when the demo states its object's size (motion capture with meshes), grasp and
    # release offsets are scaled by robot object size / human object size, so a hand on the edge of a 50 cm box
    # maps to the edge of a 4 cm block. The hand PATH legs (style) stay in metres. Introduced 2026-10-02 after a
    # HiPHI box-lift demo was infeasible for every condition on dev (hands ~24 cm above the box centre).
    scale = 1.0
    if demo.meta.get("object_size_m"):
        scale = min(1.0, ROBOT_OBJECT_SIZE_M / float(demo.meta["object_size_m"]))
        g, r = g * scale, r * scale
    g[2], r[2] = max(g[2], Z_FLOOR_M), max(r[2], Z_FLOOR_M)
    human = kf["durations_s"]
    human_total = sum(human.values())
    if human_total <= 0:
        raise ValueError("demo skills have zero total duration")
    return {
        "schema": PLAN_SCHEMA,
        "source": demo.source,
        "grasp_offset": [float(x) for x in g],
        "place_offset": [float(x) for x in r],
        "clear_m": float(np.clip(kf["peak_height_above_grasp_m"], *CLEAR_RANGE_M)),
        "timing_scale": float(sum(ROBOT_NOMINAL_S.values()) / human_total),
        "human_durations_s": human,
        "segments": kf["segments"],
        "align_yaw_rad": float(align_yaw),
        "offset_scale": float(scale),
    }


def exact_plan(clear_m=0.20):
    """The retargeting oracle: grasp the object centre, release at the goal centre, nominal lift height."""
    return {"schema": PLAN_SCHEMA, "source": "oracle", "grasp_offset": [0.0, 0.0, 0.0],
            "place_offset": [0.0, 0.0, 0.004], "clear_m": float(clear_m), "timing_scale": 1.0}
