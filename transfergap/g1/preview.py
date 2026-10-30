"""Kinematic playback of a planned trajectory (no physics) to mp4, to check the reference before streaming it.

    MUJOCO_GL=egl python transfergap/g1/preview.py --traj runs/reach_nominal.npz --out runs/reach_preview.mp4
"""
from __future__ import annotations

import argparse

import mujoco
import numpy as np

from scene import build_spec
from video import Mp4Writer

ap = argparse.ArgumentParser()
ap.add_argument("--sonic-root", default="~/GR00T-WholeBodyControl")
ap.add_argument("--traj", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--camera", default="third_person")
a = ap.parse_args()

m = build_spec(a.sonic_root, a.seed).compile()
d = mujoco.MjData(m)
t = np.load(a.traj)
qpos = t["qpos"]
names = ["right_hand_thumb_0_joint", "right_hand_thumb_1_joint", "right_hand_thumb_2_joint",
         "right_hand_middle_0_joint", "right_hand_middle_1_joint", "right_hand_index_0_joint",
         "right_hand_index_1_joint"]
r = mujoco.Renderer(m, 480, 640)
w = Mp4Writer(a.out, 640, 480, fps=25)
nq_robot = qpos.shape[1]
for k in range(0, len(qpos), 2):                       # 50 Hz -> 25 fps
    d.qpos[:nq_robot] = qpos[k]
    for n, v in zip(names, t["right_hand"][k]):
        d.qpos[m.jnt_qposadr[m.joint(n).id]] = v
    mujoco.mj_kinematics(m, d)
    mujoco.mj_camlight(m, d)               # camera poses are not updated by mj_kinematics
    r.update_scene(d, camera=a.camera)
    w.write(r.render())
w.close()
r.close()
print(a.out)
