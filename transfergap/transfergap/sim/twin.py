"""Scene twin: the real task geometry (your objects, their sizes and positions) as a validated description the simulator can build.

The default simulator scene (a 4 cm red cube and a green tray 34 cm apart) is NOT the author's scene, and the demo's carry leg is warped onto it
(demo/style.py: robot_path). A twin replaces that fixed layout with measured numbers. It is a JSON file:

    {"schema": "transfergap.twin/v1", "name": "...", "source": "tape | marker | detector", "measured_on": "YYYY-MM-DD",
     "object": {"size_m": [length, width, height], "mass_kg": 0.05, "xy_m": [x, y]},
     "target": {"inner_size_m": [length, width], "wall_height_m": 0.08, "xy_m": [x, y]},
     "table":  {"top_z_m": 0.0},
     "placement": {"yaw_deg": 0.0, "anchor_xy_m": [0.45, 0.0]},
     "jitter_m": 0.01}

`xy_m` are in the TABLE frame you measured (any origin, x and y along the table edges). `placement` says how the table frame sits in the robot's frame
(the midpoint between object and target goes to `anchor_xy_m`, the table is rotated by `yaw_deg` about it), so the same measurements can be reached by
every robot. Distances and sizes are preserved exactly; only the pose of the whole table relative to the robot base is a choice. The object is built as a
box whose long side lies along the robot x axis, so the fingers close across its SHORT horizontal side (the real grasp orientation is not copied).
`jitter_m` is the per-seed position spread (default 1 cm, the measurement uncertainty of a tape).

Use: `TG_TWIN=/path/twin.json` (read by sim.scene.Scene when no twin is passed) or `Scene(..., twin=load(path))`.
Every number is yours; nothing here invents sizes. `validate(twin, robot)` lists what the robot cannot do with it (gripper opening, reach).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

SCHEMA = "transfergap.twin/v1"
DEFAULT_MASS_DENSITY = 600.0          # kg/m3, wood-like, used only when no mass is given
OPENING_M = {"ur5e": 0.085, "ur10e": 0.085, "kairos": 0.128, "kairos_mobile": 0.128}
REACH_M = {"ur5e": 0.85, "ur10e": 1.30, "kairos": 1.30, "kairos_mobile": 1.30}


def _vec(x, n, name):
    try:
        v = np.asarray(x, float)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be {n} numbers in metres, got {x!r} (did you leave a FILL_ME in the template?)") from None
    if v.shape != (n,) or not np.isfinite(v).all():
        raise ValueError(f"{name} must be {n} finite numbers, got {x!r}")
    return v


def load(src):
    """Read and normalise a twin (path, dict or JSON text). Raises ValueError with the field name on bad input."""
    if isinstance(src, (str, Path)) and Path(str(src)).exists():
        raw = Path(src).read_text()
        d = json.loads(raw)
    elif isinstance(src, (str, bytes)):
        raw = src if isinstance(src, str) else src.decode()
        d = json.loads(raw)
    else:
        d = dict(src)
        raw = json.dumps(d, sort_keys=True)
    if d.get("schema") != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA!r}")
    o, t = d["object"], d["target"]
    size = _vec(o["size_m"], 3, "object.size_m")
    if (size <= 0.005).any() or (size > 0.30).any():
        raise ValueError("object.size_m must be between 5 mm and 30 cm")
    tin = _vec(t["inner_size_m"], 2, "target.inner_size_m")
    if (tin <= size[:2].min()).any() or (tin > 0.60).any():
        raise ValueError("target.inner_size_m must be larger than the object's smaller side and at most 60 cm")
    out = {
        "schema": SCHEMA, "name": d.get("name", "twin"), "source": d.get("source", "unspecified"),
        "measured_on": d.get("measured_on"),
        "object": {"size_m": size.tolist(), "mass_kg": float(o.get("mass_kg", DEFAULT_MASS_DENSITY * float(np.prod(size)))),
                   "mass_given": "mass_kg" in o, "xy_m": _vec(o["xy_m"], 2, "object.xy_m").tolist()},
        "target": {"inner_size_m": tin.tolist(), "wall_height_m": float(t.get("wall_height_m", 0.05)),
                   "wall_thickness_m": float(t.get("wall_thickness_m", 0.005)), "floor_thickness_m": float(t.get("floor_thickness_m", 0.004)),
                   "xy_m": _vec(t["xy_m"], 2, "target.xy_m").tolist()},
        "table": {"top_z_m": float(d.get("table", {}).get("top_z_m", 0.0))},
        "placement": {"yaw_deg": float(d.get("placement", {}).get("yaw_deg", 0.0)),
                      "anchor_xy_m": _vec(d.get("placement", {}).get("anchor_xy_m", [0.45, 0.0]), 2, "placement.anchor_xy_m").tolist()},
        "jitter_m": float(d.get("jitter_m", 0.01)),
    }
    out["sha256"] = hashlib.sha256(json.dumps({k: v for k, v in out.items() if k != "sha256"}, sort_keys=True).encode()).hexdigest()[:12]
    return out


def from_env():
    p = os.environ.get("TG_TWIN")
    return load(p) if p else None


def _rot(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])


def robot_frame(twin):
    """Object and target centre in the robot frame (m): the table is rotated by placement.yaw about the object-target midpoint, which goes to the anchor."""
    o, t = np.asarray(twin["object"]["xy_m"], float), np.asarray(twin["target"]["xy_m"], float)
    mid = (o + t) / 2
    R = _rot(twin["placement"]["yaw_deg"])
    anchor = np.asarray(twin["placement"]["anchor_xy_m"], float)
    return {"object_xy": anchor + R @ (o - mid), "target_xy": anchor + R @ (t - mid)}


def carry_vector(twin):
    """Object -> target vector in the robot frame (xy, metres)."""
    f = robot_frame(twin)
    return f["target_xy"] - f["object_xy"]


def box_half_extents(twin):
    """Half extents (x, y, z) of the object box as built: long horizontal side along x, short side along y (the closing direction)."""
    sx, sy, sz = twin["object"]["size_m"]
    lo, hi = sorted([sx, sy])
    return np.array([hi / 2, lo / 2, sz / 2])


def validate(twin, robot=None):
    """Problems a robot has with this twin (empty list = none found)."""
    why = []
    hx, hy, hz = box_half_extents(twin)
    f = robot_frame(twin)
    if robot in OPENING_M and 2 * hy > OPENING_M[robot] - 0.015:
        why.append(f"object closing width {2 * hy * 100:.1f} cm does not clear the {robot} gripper opening ({OPENING_M[robot] * 100:.1f} cm) by 1.5 cm")
    if robot in REACH_M:
        for k, xy in f.items():
            if np.hypot(*xy) > 0.85 * REACH_M[robot]:
                why.append(f"{k} at {np.hypot(*xy) * 100:.0f} cm from the base is beyond 85% of the {robot} reach ({REACH_M[robot] * 100:.0f} cm)")
            if np.hypot(*xy) < 0.30:
                why.append(f"{k} at {np.hypot(*xy) * 100:.0f} cm from the base is too close to the arm base (under 30 cm)")
    if twin["target"]["wall_height_m"] < 0.3 * twin["object"]["size_m"][2]:
        why.append("target wall is lower than 30% of the object height: it will not hold the object")
    return why
