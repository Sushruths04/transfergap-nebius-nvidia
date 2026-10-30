"""Diagnostics: how well did SONIC track the streamed reference? (analysis only, run after a rollout)

Aligns the logged robot qpos (RUN/TAG.diag.npz) with the planned trajectory at the moment the
streamer started (episode t_go_s) and reports, per motion phase, the right-wrist position error in
the pelvis frame and the mean absolute right-arm joint error, plus the best-fitting time lag.

    python transfergap/g1/track_error.py --traj RUN/reach_nominal.npz --run-dir RUN --tag seed0_r0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from scene import build_spec

ARM = ["right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint", "right_elbow_joint",
       "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint", "waist_yaw_joint",
       "waist_roll_joint", "waist_pitch_joint"]


def wrist_in_pelvis(m, d, q):
    d.qpos[:len(q)] = q
    mujoco.mj_kinematics(m, d)
    pel, w = m.body("pelvis").id, m.body("right_wrist_yaw_link").id
    R = d.xmat[pel].reshape(3, 3)
    return R.T @ (d.xpos[w] - d.xpos[pel])


def analyse(sonic_root, traj, run, tag):
    m = build_spec(sonic_root, with_block=False).compile()
    d = mujoco.MjData(m)
    t = np.load(traj)
    ep = json.loads((Path(run) / f"{tag}.episode.json").read_text())
    dg = np.load(Path(run) / f"{tag}.diag.npz")
    plan_q, phase = t["qpos"], t["phase"]
    adr = [m.jnt_qposadr[m.joint(n).id] for n in ARM]
    act_t, act_q = dg["t"], dg["qpos"]
    t_go = ep["t_go_s"]
    plan_w = np.array([wrist_in_pelvis(m, d, q) for q in plan_q])
    act_w = np.array([wrist_in_pelvis(m, d, q) for q in act_q])
    best = None
    for lag in np.arange(0.0, 1.5, 0.02):                 # tracking delay estimate
        idx = np.searchsorted(act_t, t_go + lag + np.arange(len(plan_q)) / 50.0)
        idx = np.clip(idx, 0, len(act_t) - 1)
        err = np.linalg.norm(act_w[idx] - plan_w, axis=1).mean()
        if best is None or err < best[1]:
            best = (lag, err, idx)
    lag, _, idx = best
    out = {"lag_s": round(float(lag), 2), "phases": {}}
    # where the (open-hand) grasp point actually was at the end of the descend phase, vs the block's start
    from plan_reach import G1Kin
    kin = G1Kin(sonic_root)
    k_end = int(np.where(phase == "descend")[0][-1])
    kin.d.qpos[:] = act_q[idx[k_end]]
    mujoco.mj_kinematics(kin.m, kin.d)
    block0 = np.array([*ep["block_xy_initial"], ep["states"][0]["object_xyz"][2]])
    out["grasp_point_minus_block_at_descend_end_world"] = np.round(kin.grasp_point() - block0, 3).tolist()
    out["pelvis_xy_at_descend_end"] = np.round(act_q[idx[k_end]][:2], 3).tolist()
    for ph in dict.fromkeys(phase):
        sel = phase == ph
        we = np.linalg.norm(act_w[idx[sel]] - plan_w[sel], axis=1)
        je = np.abs(act_q[idx[sel]][:, adr] - plan_q[sel][:, adr]).mean(0)
        out["phases"][str(ph)] = {"wrist_err_m_mean": round(float(we.mean()), 3),
                                  "wrist_err_m_end": round(float(we[-1]), 3),
                                  "wrist_err_vec_end_pelvis": np.round(act_w[idx[sel]][-1] - plan_w[sel][-1], 3).tolist(),
                                  "joint_abs_err_rad": {n.replace("_joint", ""): round(float(v), 2) for n, v in zip(ARM, je)}}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sonic-root", default="~/GR00T-WholeBodyControl")
    ap.add_argument("--traj", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    print(json.dumps(analyse(a.sonic_root, a.traj, a.run_dir, a.tag), indent=1))
