"""GEM-X/SOMA joint positions (from tools/gemx_export_joints.py) -> HumanDemo, CPU only.

Frame: SOMA world is right-handed, y up (GEM-X/SOMA convention). The demo frame is z up with the table at z = 0:
(x, y, z)_soma -> (x, -z, y)_demo, then shifted so the table plane is z = 0.

What a monocular body estimate can and cannot give (stated, not hidden):
  * pinch point = midpoint of <Side>HandThumbEnd and <Side>HandIndexEnd; aperture = their distance.
  * there is NO object detector in this path. The object centre is taken under the pinch point at the grasp and
    the goal centre under the pinch point at the release, both at table height + OBJECT_HALF_M (ASSUMPTION). The
    human's off-centre grasp is therefore unobservable here (grasp_offset ~ 0); the path, approach direction, lift
    and speed profile — the style legs — are observed.
  * table height = lowest pinch height during the grasp window minus OBJECT_HALF_M (ASSUMPTION: the fingers close
    around the object's middle).
"""
from __future__ import annotations

import json

import numpy as np

from .schema import HumanDemo
from .segment import segment

OBJECT_HALF_M = 0.02


def soma_to_demo_frame(x):
    x = np.asarray(x, float)
    return np.stack([x[..., 0], -x[..., 2], x[..., 1]], axis=-1)


def demo_from_joints(joints, joint_names, fps, side="Right", meta=None, window=None, events=None,
                     object_height="lowest_hand"):
    """window = (first, last) frame of the clip to keep; events = {"grasp": f, "release": f} in CLIP frames
    (e.g. annotated by inspecting the video), used instead of the aperture threshold.
    object_height: "lowest_hand" (default, used by every demo before 2026-10-02 evening): the table is under the
    lowest hand point of the grasp-release window and the object/goal rest on it. "hand_at_grasp": the object is
    where the hand closes and the goal is where it opens (pick and place heights may differ, e.g. a box lifted off
    a stack); added after the lowest-hand rule put the grasp ~4 cm above the object for such a demo."""
    names = [str(n) for n in joint_names]
    if window is not None:
        a, b = int(window[0]), int(window[1]) + 1
        joints = np.asarray(joints)[a:b]
        if events is not None:
            events = {k: int(v) - a for k, v in events.items()}
    idx = lambda n: names.index(n)
    J = soma_to_demo_frame(joints)
    if side == "both":            # two-handed carry: midpoint of the two hands' pinch points, aperture = hand gap
        hp = {s_: (J[:, idx(f"{s_}HandThumbEnd")] + J[:, idx(f"{s_}HandIndexEnd")]) / 2 for s_ in ("Left", "Right")}
        pinch, aperture = (hp["Left"] + hp["Right"]) / 2, np.linalg.norm(hp["Left"] - hp["Right"], axis=1)
    else:
        thumb, index = J[:, idx(f"{side}HandThumbEnd")], J[:, idx(f"{side}HandIndexEnd")]
        pinch, aperture = (thumb + index) / 2, np.linalg.norm(thumb - index, axis=1)
    t = np.arange(len(pinch)) / float(fps)
    # provisional demo to find the grasp/release window, then fix the table plane and the object/goal centres
    ev_meta = {"events": events} if events is not None else {}
    tmp = HumanDemo(t, pinch, aperture, pinch[0], pinch[-1], "gemx_soma", ev_meta)
    seg = segment(tmp)
    if object_height == "hand_at_grasp":
        table_z = float(pinch[seg.grasp, 2]) - OBJECT_HALF_M
        pinch = pinch - [0.0, 0.0, table_z]
        obj, goal = pinch[seg.grasp].copy(), pinch[seg.release].copy()
    else:
        table_z = float(pinch[seg.grasp:seg.release + 1, 2].min()) - OBJECT_HALF_M
        pinch = pinch - [0.0, 0.0, table_z]
        obj = np.r_[pinch[seg.grasp, :2], OBJECT_HALF_M]
        goal = np.r_[pinch[seg.release, :2], OBJECT_HALF_M]
    m = {"side": side, "fps": float(fps), "object_from": "pinch at grasp (no object detector)",
         "goal_from": "pinch at release", "table_z_soma_up": table_z, "OBJECT_HALF_M": OBJECT_HALF_M,
         "object_height": object_height,
         **ev_meta, **({"clip_window_frames": list(window)} if window is not None else {}), **(meta or {})}
    return HumanDemo(t, pinch, aperture, obj, goal, "gemx_soma", m)


def load_joints_npz(path, side="Right", window=None, events=None, meta=None, object_height="lowest_hand"):
    z = np.load(path, allow_pickle=False)
    if str(z["frame"]) != "soma_world_y_up":
        raise ValueError(f"unexpected frame {z['frame']!r}")
    return demo_from_joints(z["joints"], z["joint_names"], float(z["fps"]), side,
                            {**json.loads(str(z["meta"])), **(meta or {})}, window, events, object_height)
