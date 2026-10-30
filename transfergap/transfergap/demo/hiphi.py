"""HiPHI motion-capture package (motion_actor.bvh + object_tracks/*.csv + metadata.json) -> HumanDemo. CPU only.

HiPHI format (docs/data_format.md of noitomrobotics/HiPHI): BVH right-handed Y-up, centimetres, every joint has
CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation (Euler degrees, applied Z then X then Y),
~90 Hz; object tracks in the same Y-up world frame in METRES with XYZW quaternions, one row per BVH frame.
LICENSE: ModalityNet Open Research License (non-commercial; no redistribution of raw data). Converted demos are
derived from raw data and are therefore kept out of git (runs/, demo_input/ are gitignored).

Conversion
  * forward kinematics of the BVH; fingertip = the End Site under <Side>HandThumb3 / <Side>HandIndex3
  * pinch = midpoint of the two fingertips, aperture = their distance; the grasping hand is the one whose pinch
    point comes closest to the tracked object
  * Y-up -> Z-up: (x, y, z) -> (x, -z, y); then shifted so the object's initial origin sits at OBJECT_HALF_M above
    z = 0 (ASSUMPTION: object origin at its centre; only absolute heights depend on it, offsets do not)
  * object_xyz = tracked object position at the grasp; goal_xyz = tracked object position at the release — both
    MEASURED (unlike the monocular GEM-X path, the human's off-centre grasp is observable here)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from .schema import HumanDemo

OBJECT_HALF_M = 0.02


PAD_S = 1.0                 # seconds kept before the grasp and after the release of the first cycle
MOVE_SPEED = 0.05           # m/s: the tracked object counts as moving above this speed
MIN_STILL_S = 0.3           # a pause shorter than this does not end a carry


def first_cycle(obj, t):
    """(grasp, release) frame indices of the first carry: the object starts moving, and the first time it then
    stays still for MIN_STILL_S."""
    dt = float(np.median(np.diff(t)))
    moving = np.linalg.norm(np.gradient(obj, t, axis=0), axis=1) > MOVE_SPEED
    idx = np.flatnonzero(moving)
    if not idx.size:
        raise ValueError("tracked object never moves")
    g = int(idx[0])
    still, need = 0, max(1, int(round(MIN_STILL_S / dt)))
    for i in range(g, len(moving)):
        still = still + 1 if not moving[i] else 0
        if still >= need:
            return g, i - need
    return g, int(idx[-1])


class Joint:
    def __init__(self, name, parent, offset):
        self.name, self.parent, self.offset = name, parent, np.asarray(offset, float)
        self.channels, self.end_offset, self.children = [], None, []


def parse_bvh(text):
    """(joints in file order, frame_time, motion array [F, n_channels])."""
    toks = text.split()
    i, joints, stack = 0, [], []
    while toks[i] != "MOTION":
        t = toks[i]
        if t in ("ROOT", "JOINT"):
            j = Joint(toks[i + 1], stack[-1] if stack else None, [0, 0, 0])
            if j.parent is not None:
                j.parent.children.append(j)
            joints.append(j)
            stack.append(j)
            i += 2
        elif t == "End":
            i += 2                                    # "End Site"
            assert toks[i] == "{" and toks[i + 1] == "OFFSET"
            stack[-1].end_offset = np.array(toks[i + 2:i + 5], float)
            i += 6                                    # { OFFSET x y z }
        elif t == "OFFSET":
            stack[-1].offset = np.array(toks[i + 1:i + 4], float)
            i += 4
        elif t == "CHANNELS":
            n = int(toks[i + 1])
            stack[-1].channels = toks[i + 2:i + 2 + n]
            i += 2 + n
        elif t == "}":
            stack.pop()
            i += 1
        else:
            i += 1
    i += 1
    assert toks[i] == "Frames:"
    n_frames = int(toks[i + 1])
    assert toks[i + 2] == "Frame" and toks[i + 3] == "Time:"
    frame_time = float(toks[i + 4])
    vals = np.array(toks[i + 5:], float)
    n_ch = sum(len(j.channels) for j in joints)
    return joints, frame_time, vals[: n_frames * n_ch].reshape(n_frames, n_ch)


def _rot(axis, deg):
    a = np.deg2rad(deg)
    c, s = np.cos(a), np.sin(a)
    o, z = np.ones_like(a), np.zeros_like(a)
    if axis == "X":
        m = [[o, z, z], [z, c, -s], [z, s, c]]
    elif axis == "Y":
        m = [[c, z, s], [z, o, z], [-s, z, c]]
    else:
        m = [[c, -s, z], [s, c, z], [z, z, o]]
    return np.moveaxis(np.array(m), [0, 1], [-2, -1])          # (F, 3, 3)


def forward_kinematics(joints, motion):
    """World positions (F, 3) for every joint name and every End Site ("<parent>_End"), in BVH units (cm)."""
    F = motion.shape[0]
    pos, rot, col = {}, {}, 0
    for j in joints:
        ch = {c: motion[:, col + k] for k, c in enumerate(j.channels)}
        col += len(j.channels)
        local_t = np.stack([ch.get("Xposition", np.full(F, j.offset[0])), ch.get("Yposition", np.full(F, j.offset[1])),
                            ch.get("Zposition", np.full(F, j.offset[2]))], axis=1)
        R = np.broadcast_to(np.eye(3), (F, 3, 3)).copy()
        for c in j.channels:                                  # rotations in declared channel order
            if c.endswith("rotation"):
                R = R @ _rot(c[0], ch[c])
        if j.parent is None:
            pos[j.name], rot[j.name] = local_t, R
        else:
            pr = rot[j.parent.name]
            pos[j.name] = pos[j.parent.name] + np.einsum("fij,fj->fi", pr, local_t)
            rot[j.name] = pr @ R
        if j.end_offset is not None:
            pos[j.name + "_End"] = pos[j.name] + np.einsum("fij,j->fi", rot[j.name], j.end_offset)
    return pos


def y_up_to_z_up(x):
    x = np.asarray(x, float)
    return np.stack([x[..., 0], -x[..., 2], x[..., 1]], axis=-1)


def read_track(path, mesh_center_cm=None):
    """Object position per frame (metres, Y-up). With mesh_center_cm, the mesh bounding-box centre is returned
    instead of the object origin: v_world = R(q) @ (0.01 * v_cm) + p (HiPHI docs, section 3)."""
    with open(path) as f:
        rows = list(csv.DictReader(f))
    p = np.array([[float(r["px"]), float(r["py"]), float(r["pz"])] for r in rows])
    if mesh_center_cm is None:
        return p
    q = np.array([[float(r["qx"]), float(r["qy"]), float(r["qz"]), float(r["qw"])] for r in rows])
    return p + quat_rotate(q, 0.01 * np.asarray(mesh_center_cm, float))


def quat_rotate(q, v):
    """Rotate vector v by unit quaternions q (N, 4) in XYZW order."""
    xyz, w = q[:, :3], q[:, 3:4]
    t = 2.0 * np.cross(xyz, np.broadcast_to(v, xyz.shape))
    return v + w * t + np.cross(xyz, t)


def mesh_center_cm(obj_path):
    return mesh_bbox_cm(obj_path)[0]


def mesh_bbox_cm(obj_path):
    """(bounding-box centre, extents) of an OBJ mesh, centimetres, object-local frame."""
    v = np.array([[float(x) for x in line.split()[1:4]] for line in open(obj_path) if line.startswith("v ")])
    return (v.min(0) + v.max(0)) / 2, v.max(0) - v.min(0)


BIMANUAL_GAP_M = 0.15        # both hands count as grasping when each is within this of the closer hand's distance


def load_package(pkg_dir, side=None, mesh_dir=None):
    """HumanDemo from one HiPHI motion package directory. side: "Right", "Left", "both" or None (auto: "both" when
    both hands are about equally close to the object at the grasp, else the closer hand). mesh_dir: folder with
    HiPHI object_meshes/ to use the mesh centre instead of the object origin."""
    pkg = Path(pkg_dir)
    meta = json.loads((pkg / "metadata.json").read_text())
    joints, dt, motion = parse_bvh((pkg / "motion_actor.bvh").read_text())
    P = forward_kinematics(joints, motion)
    tracks = sorted((pkg / "object_tracks").glob("*.csv"))
    if not tracks:
        raise ValueError(f"{pkg.name}: no object track (not a human-object interaction package)")
    center = extents = None
    if mesh_dir is not None:
        mesh = next((o.get("mesh_path") for o in meta.get("objects", []) if o.get("trajectory_path", "").endswith(
            tracks[0].name)), None)
        if mesh and (Path(mesh_dir) / Path(mesh).name).exists():
            center, extents = mesh_bbox_cm(Path(mesh_dir) / Path(mesh).name)
    obj = y_up_to_z_up(read_track(tracks[0], center))         # metres
    if len(obj) != motion.shape[0]:
        raise ValueError("object track and BVH frame counts differ")
    hands = {}
    for s in ("Right", "Left"):
        thumb = y_up_to_z_up(P[f"{s}HandThumb3_End"]) / 100.0
        index = y_up_to_z_up(P[f"{s}HandIndex3_End"]) / 100.0
        pinch = (thumb + index) / 2
        hands[s] = (pinch, np.linalg.norm(thumb - index, axis=1), float(np.min(np.linalg.norm(pinch - obj, axis=1))))
    t0 = np.arange(len(obj)) * dt
    g0, _ = first_cycle(obj, t0)
    dist = {s: float(np.linalg.norm(hands[s][0][g0] - obj[g0])) for s in hands}
    if side is None:
        side = "both" if abs(dist["Left"] - dist["Right"]) < BIMANUAL_GAP_M else min(dist, key=dist.get)
    if side == "both":
        pinch = (hands["Left"][0] + hands["Right"][0]) / 2
        aperture = np.linalg.norm(hands["Left"][0] - hands["Right"][0], axis=1)
        closest = float(np.min(np.linalg.norm(pinch - obj, axis=1)))
    else:
        pinch, aperture, closest = hands[side]
    shift = np.array([0.0, 0.0, obj[0, 2] - OBJECT_HALF_M])
    pinch, obj = pinch - shift, obj - shift
    t = np.arange(len(pinch)) * dt
    grasp_i, release_i = first_cycle(obj, t)
    a, b = max(0, grasp_i - int(round(PAD_S / dt))), min(len(t), release_i + int(round(PAD_S / dt)) + 1)
    pinch, aperture, t = pinch[a:b], aperture[a:b], t[a:b] - t[a]
    obj_c = obj[a:b]
    return HumanDemo(t, pinch, aperture, obj_c[grasp_i - a], obj_c[release_i - a], "hiphi_mocap",
                     {"motion_id": meta.get("motion_id"), "frame_lu": meta.get("frame_lu"),
                      "text_annotation": meta.get("text_annotation"), "actor_id": meta.get("actor_id"),
                      "side": side, "closest_pinch_to_object_m": closest, "object_track": tracks[0].name,
                      "hand_to_object_at_grasp_m": dist, "object_point": "mesh centre" if center is not None
                      else "object origin",
                      **({"object_size_m": float(0.01 * np.max(extents))} if extents is not None else {}),
                      "events": {"grasp": grasp_i - a, "release": release_i - a},
                      "cycle_frames_in_package": [a, b], "events_from": "tracked object starts/stops moving",
                      "fps": 1.0 / dt,
                      "license": "ModalityNet Open Research License (non-commercial, no redistribution)"})


def object_track_z_up(pkg_dir):
    """The tracked object path in the same shifted demo frame as load_package (for scoring/visualisation)."""
    tracks = sorted((Path(pkg_dir) / "object_tracks").glob("*.csv"))
    obj = y_up_to_z_up(read_track(tracks[0]))
    return obj - [0.0, 0.0, obj[0, 2] - OBJECT_HALF_M]
