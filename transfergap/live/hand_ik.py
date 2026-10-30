"""Online fingertip retargeting to the Allegro hand (same method as live/hand_retarget.py, packaged for streaming).

    ik = HandIK("runs/allegro/scene_right.xml"); q, err_cm = ik.step(kp21)   # kp21: (21, 3) right-hand keypoints, any rigid frame
Palm-frame fingertip targets scaled by robot/human finger length, a fixed axis alignment (fitted offline on the author's clip,
live/hand_retarget.py: ALIGN), per-finger damped-least-squares IK warm-started from the previous frame. The scale adapts to the
person's hand from the 90th percentile of the mean finger length seen so far (needs ~1 s of an extended hand).
"""
import mujoco
import numpy as np

TIPS = {"th": 4, "ff": 8, "mf": 12, "rf": 16}
ALIGN = np.array([[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]])      # selected on the clip by the 24-rotation search


def palm_axes(P):
    x = P[9] - P[0]
    x = x / np.linalg.norm(x)
    z = np.cross(x, P[17] - P[5])
    z /= np.linalg.norm(z)
    return np.stack([x, np.cross(z, x), z], 1)


class HandIK:
    def __init__(self, xml, align=ALIGN, scale0=0.877):
        self.m = mujoco.MjModel.from_xml_path(xml)
        self.d = mujoco.MjData(self.m)
        mujoco.mj_forward(self.m, self.d)
        m, d = self.m, self.d
        self.keys = list(TIPS)
        self.tipb = {k: m.body(f"{k}_tip").id for k in TIPS}
        j = {k: [m.joint(f"{k}j{i}").id for i in range(4)] for k in TIPS}
        self.dofs = {k: [m.jnt_dofadr[x] for x in j[k]] for k in TIPS}
        self.qadr = {k: [m.jnt_qposadr[x] for x in j[k]] for k in TIPS}
        self.rng = {k: np.array([m.jnt_range[x] for x in j[k]]) for k in TIPS}
        base = {k: m.body(f"{k}_base").id for k in ("ff", "mf", "rf")}
        self.org = d.xpos[base["mf"]].copy()
        xr = d.xpos[self.tipb["mf"]] - self.org
        xr /= np.linalg.norm(xr)
        zr = np.cross(xr, d.xpos[base["rf"]] - d.xpos[base["ff"]])
        zr /= np.linalg.norm(zr)
        self.Rr = np.stack([xr, np.cross(zr, xr), zr], 1)
        self.rl = float(np.mean([np.linalg.norm(d.xpos[self.tipb[k]] - self.org) for k in self.keys[1:]]))
        self.align, self.scale, self.lens = align, scale0, []
        # hide the scene's demo object (menagerie hand scene) when rendering
        if any(m.body(i).name == "object" for i in range(m.nbody)):
            ob = m.body("object").id
            for g in range(m.ngeom):
                if m.geom_bodyid[g] == ob:
                    m.geom_rgba[g, 3] = 0.0

    def step(self, P, iters=25):
        P = np.asarray(P, float)
        R = palm_axes(P)
        Th = np.array([R.T @ (P[TIPS[k]] - P[9]) for k in self.keys])
        self.lens.append(float(np.linalg.norm(Th[1:], axis=1).mean()))
        if len(self.lens) >= 20:
            self.scale = self.rl / float(np.percentile(self.lens[-300:], 90))
        m, d, errs = self.m, self.d, []
        for fi, k in enumerate(self.keys):
            tgt = self.org + self.Rr @ (self.align @ (self.scale * Th[fi]))
            for _ in range(iters):
                mujoco.mj_kinematics(m, d)
                mujoco.mj_comPos(m, d)
                e = tgt - d.xpos[self.tipb[k]]
                if np.linalg.norm(e) < 1e-4:
                    break
                jp = np.zeros((3, m.nv))
                mujoco.mj_jacBody(m, d, jp, None, self.tipb[k])
                Jf = jp[:, self.dofs[k]]
                dq = Jf.T @ np.linalg.solve(Jf @ Jf.T + 1e-3 * np.eye(3), e)
                for i, qa in enumerate(self.qadr[k]):
                    d.qpos[qa] = np.clip(d.qpos[qa] + dq[i], self.rng[k][i, 0], self.rng[k][i, 1])
            mujoco.mj_kinematics(m, d)
            errs.append(float(np.linalg.norm(tgt - d.xpos[self.tipb[k]])) * 100)
        q = np.concatenate([[d.qpos[qa] for qa in self.qadr[k]] for k in self.keys])
        return q, dict(zip(self.keys, errs))
