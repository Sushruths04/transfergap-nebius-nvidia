"""Fingertip retargeting: the person's hand (21 keypoints per frame) -> a dexterous robot hand (Wonik Allegro, MuJoCo Menagerie), offline.

Method (the fingertip-alignment idea of UniDex / dex-retargeting, written from scratch here, not their code):
  1. palm frame of the human hand from wrist, middle-finger base and the index/pinky bases;
  2. fingertip targets = thumb/index/middle/ring tips in that frame, scaled by the ratio of robot to human finger length;
  3. one fixed rotation (Kabsch) aligns the human palm frame to the robot's, fitted on the most open hand frame of the clip;
  4. per-finger damped-least-squares IK with joint limits and a small pull toward the previous frame (temporal smoothness).
The pinky has no robot counterpart (Allegro has 4 fingers). The robot palm is fixed in space; only finger shape is retargeted, not hand pose.
Reports fingertip tracking error (cm, in the robot's scale) per finger. Simulation/kinematics only; no contact, no object.

    python live/hand_retarget.py --joints joints_scaled.npz --model runs/allegro/scene_right.xml --out DIR [--render]
"""
import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

TIPS = {"th": 4, "ff": 8, "mf": 12, "rf": 16}      # keypoint index inside the 21-point hand (wrist 0, then 4 per finger, thumb first)
R0 = 112                                          # right hand block in COCO-WholeBody (wrist at 112)


def palm_frame(P):
    o = P[0]
    x = P[9] - P[0]
    x = x / np.linalg.norm(x)
    y0 = P[17] - P[5]
    z = np.cross(x, y0)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return o, np.stack([x, y, z], 1)


def kabsch(A, B):
    """Rotation R minimising ||R a_i - b_i|| over rows of A, B (n x 3)."""
    U, _, Vt = np.linalg.svd(B.T @ A)
    D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
    return U @ D @ Vt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--joints", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--render", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    z = np.load(a.joints, allow_pickle=True)
    J = z["joints"].astype(float)[:, R0:R0 + 21]
    T = len(J)
    m = mujoco.MjModel.from_xml_path(a.model)
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    palm = m.body("palm").id
    tipb = {k: m.body(f"{k}_tip").id for k in TIPS}
    jn = {k: [m.joint(f"{k}j{i}").id for i in range(4)] for k in TIPS}
    dofs = {k: [m.jnt_dofadr[j] for j in jn[k]] for k in TIPS}
    qadr = {k: [m.jnt_qposadr[j] for j in jn[k]] for k in TIPS}
    rng = {k: np.array([m.jnt_range[j] for j in jn[k]]) for k in TIPS}
    Rp = d.xmat[palm].reshape(3, 3)
    base = {k: m.body(f"{k}_base").id for k in TIPS if k != "th"}
    # robot palm axes from its own geometry at the zero configuration (same recipe as the human frame: forward = towards the middle
    # finger, lateral = index -> ring side, normal = forward x lateral), origin = middle-finger base
    org_r = d.xpos[base["mf"]].copy()
    xr = d.xpos[tipb["mf"]] - org_r
    xr /= np.linalg.norm(xr)
    yr0 = d.xpos[base["rf"]] - d.xpos[base["ff"]]
    zr = np.cross(xr, yr0)
    zr /= np.linalg.norm(zr)
    yr = np.cross(zr, xr)
    Rr = np.stack([xr, yr, zr], 1)
    # human tips relative to the middle-finger base (keypoint 9), in the human palm axes, every frame
    Th = np.zeros((T, 4, 3))
    for t in range(T):
        _, Rm = palm_frame(J[t])
        Th[t] = np.array([Rm.T @ (J[t][TIPS[k]] - J[t][9]) for k in TIPS])
    keys = list(TIPS)
    ref = int(np.argmax(np.linalg.norm(Th[:, 1:], axis=2).mean(1)))              # most extended frame, used only for the length ratio
    hl = np.linalg.norm(Th[ref, 1:], axis=1).mean()
    rl = np.mean([np.linalg.norm(d.xpos[tipb[k]] - org_r) for k in keys[1:]])
    s = rl / hl
    import itertools

    def fit_error(Rk_, frames):
        dd = mujoco.MjData(m)
        tot = 0.0
        for t in frames:
            for fi, k in enumerate(keys):
                tgt = org_r + Rr @ (Rk_ @ (s * Th[t, fi]))
                for _ in range(25):
                    mujoco.mj_kinematics(m, dd)
                    mujoco.mj_comPos(m, dd)
                    e = tgt - dd.xpos[tipb[k]]
                    jp = np.zeros((3, m.nv))
                    mujoco.mj_jacBody(m, dd, jp, None, tipb[k])
                    Jf = jp[:, dofs[k]]
                    dq = Jf.T @ np.linalg.solve(Jf @ Jf.T + 1e-3 * np.eye(3), e)
                    for i, qa in enumerate(qadr[k]):
                        dd.qpos[qa] = np.clip(dd.qpos[qa] + dq[i], rng[k][i, 0], rng[k][i, 1])
                mujoco.mj_kinematics(m, dd)
                tot += float(np.linalg.norm(tgt - dd.xpos[tipb[k]]))
        return tot / (len(frames) * len(keys))

    # the human and robot palm axes are built by the same recipe, but the hand's mirror/roll convention is not guaranteed: pick, from the
    # 24 axis-aligned rotations, the one with the smallest fingertip error on every 6th frame (a one-off calibration, reported)
    cands = []
    for perm in itertools.permutations(range(3)):
        for sg in itertools.product([1, -1], repeat=3):
            M = np.zeros((3, 3))
            for i in range(3):
                M[i, perm[i]] = sg[i]
            if np.linalg.det(M) > 0:
                cands.append(M)
    sub = list(range(0, T, 6))
    scores = [fit_error(M, sub) for M in cands]
    Rk = cands[int(np.argmin(scores))]
    print("alignment search: best %.2f cm, identity %.2f cm" % (100 * min(scores), 100 * scores[[np.allclose(M, np.eye(3)) for M in cands].index(True)]))
    q = np.zeros(m.nq)
    traj, err = np.zeros((T, 16)), {k: [] for k in keys}
    for t in range(T):
        for fi, k in enumerate(keys):
            tgt = org_r + Rr @ (Rk @ (s * Th[t, fi]))
            for _ in range(40):
                mujoco.mj_kinematics(m, d)
                mujoco.mj_comPos(m, d)
                e = tgt - d.xpos[tipb[k]]
                if np.linalg.norm(e) < 1e-4:
                    break
                jp = np.zeros((3, m.nv))
                mujoco.mj_jacBody(m, d, jp, None, tipb[k])
                Jf = jp[:, dofs[k]]
                dq = Jf.T @ np.linalg.solve(Jf @ Jf.T + 1e-3 * np.eye(3), e)
                for i, qa in enumerate(qadr[k]):
                    d.qpos[qa] = np.clip(d.qpos[qa] + dq[i], rng[k][i, 0], rng[k][i, 1])
            mujoco.mj_kinematics(m, d)
            err[k].append(float(np.linalg.norm(tgt - d.xpos[tipb[k]])))
        traj[t] = np.concatenate([[d.qpos[qa] for qa in qadr[k]] for k in keys])
    np.save(out / "allegro_q.npy", traj)
    stats = {k: {"median_cm": round(100 * float(np.median(v)), 2), "p90_cm": round(100 * float(np.percentile(v, 90)), 2)} for k, v in err.items()}
    res = {"alignment_rotation": Rk.tolist(), "alignment_search_best_cm": round(100 * min(scores), 2), "frames": T, "scale_robot_per_human": round(float(s), 3), "reference_frame": ref, "fingertip_error": stats,
           "note": "kinematic fit of fingertip positions in the robot's scale; no contact; palm fixed; pinky not mapped"}
    (out / "hand_retarget.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    if a.render:
        import imageio.v2 as imageio
        import cv2
        r = mujoco.Renderer(m, 480, 480)
        cam = mujoco.MjvCamera()
        ob = m.body('object').id if any(m.body(i).name == 'object' for i in range(m.nbody)) else None
        if ob is not None:
            for g in range(m.ngeom):
                if m.geom_bodyid[g] == ob:
                    m.geom_rgba[g, 3] = 0.0
        mujoco.mj_forward(m, d)
        cam.lookat[:] = d.xpos[tipb['mf']] + np.array([0.0, 0.0, 0.0])
        cam.distance, cam.azimuth, cam.elevation = 0.36, 150, -40
        kp2 = z["kp2d"][:, R0:R0 + 21].astype(float)
        frames = []
        bones = [(0, b) for b in (1, 5, 9, 13, 17)] + [(b + k, b + k + 1) for b in (1, 5, 9, 13, 17) for k in range(3)]
        for t in range(T):
            d.qpos[:] = 0
            for fi, k in enumerate(keys):
                for i, qa in enumerate(qadr[k]):
                    d.qpos[qa] = traj[t, fi * 4 + i]
            mujoco.mj_forward(m, d)
            r.update_scene(d, camera=cam)
            rob = r.render()
            h = np.full((480, 480, 3), 245, np.uint8)
            P = kp2[t]
            lo, hi = P.min(0), P.max(0)
            sc = 380 / max(hi - lo)
            Q = (P - lo) * sc + 50
            cols = {"th": (60, 160, 250), "ff": (250, 160, 40), "mf": (40, 170, 40), "rf": (200, 90, 160), "pk": (60, 60, 220)}
            for u, v in bones:
                c = cols[["th", "ff", "mf", "rf", "pk"][((v - 1) // 4)]]
                cv2.line(h, tuple(int(x) for x in Q[u]), tuple(int(x) for x in Q[v]), c, 4, cv2.LINE_AA)
            for p in Q:
                cv2.circle(h, (int(p[0]), int(p[1])), 4, (30, 30, 30), -1)
            cv2.putText(h, "your hand (21 keypoints)", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2)
            cv2.putText(rob, "Allegro hand (fingertip IK)", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            frames.append(np.hstack([h, rob]))
        imageio.mimwrite(str(out / "hand_retarget.mp4"), frames, fps=int(float(z["fps"])) if "fps" in z.files else 21)
        print("video", len(frames))


if __name__ == "__main__":
    main()
