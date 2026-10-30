"""Synthesise a G1 reach-grasp-place reference motion (joint space) for SONIC protocol v1 streaming.

Kinematics only: the G1 model is posed with mj_kinematics, never stepped. The hand targets come from
the task constants in scene.py (the *nominal* block position a demonstration would show, or an
explicit --target-xy), never from a running simulation. The output is a 50 Hz trajectory:
  joint_pos  [T, 29]  absolute joint angles, IsaacLab order (what SONIC v1 expects)
  joint_vel  [T, 29]
  left_hand  [T, 7], right_hand [T, 7]  Dex3 joint targets in the model's hand-joint order
  phase      [T]      phase label per frame (for logs only)

Run with the upstream sim venv:
    python transfergap/g1/plan_reach.py --sonic-root ~/GR00T-WholeBodyControl --out runs/reach_nominal.npz
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from scene import BLOCK_HALF, BLOCK_NOMINAL_XY, TABLE_TOP_Z, TRAY_FLOOR, TRAY_XY, build_spec

FPS = 50
# GR00T-WholeBodyControl gear_sonic/envs/env_utils/joint_utils.py G1_ISAACLab_ORDER
ISAACLAB_ORDER = [
    "left_hip_pitch_joint", "right_hip_pitch_joint", "waist_yaw_joint", "left_hip_roll_joint",
    "right_hip_roll_joint", "waist_roll_joint", "left_hip_yaw_joint", "right_hip_yaw_joint",
    "waist_pitch_joint", "left_knee_joint", "right_knee_joint", "left_shoulder_pitch_joint",
    "right_shoulder_pitch_joint", "left_ankle_pitch_joint", "right_ankle_pitch_joint",
    "left_shoulder_roll_joint", "right_shoulder_roll_joint", "left_ankle_roll_joint",
    "right_ankle_roll_joint", "left_shoulder_yaw_joint", "right_shoulder_yaw_joint", "left_elbow_joint",
    "right_elbow_joint", "left_wrist_roll_joint", "right_wrist_roll_joint", "left_wrist_pitch_joint",
    "right_wrist_pitch_joint", "left_wrist_yaw_joint", "right_wrist_yaw_joint"]
# gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/policy_parameters.hpp default_angles (standing pose)
DEFAULT_ANGLES = {
    "left_hip_pitch_joint": -0.312, "left_knee_joint": 0.669, "left_ankle_pitch_joint": -0.363,
    "right_hip_pitch_joint": -0.312, "right_knee_joint": 0.669, "right_ankle_pitch_joint": -0.363,
    "left_shoulder_pitch_joint": 0.2, "left_shoulder_roll_joint": 0.2, "left_elbow_joint": 0.6,
    "right_shoulder_pitch_joint": 0.2, "right_shoulder_roll_joint": -0.2, "right_elbow_joint": 0.6}
IK_JOINTS = ["waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint", "right_shoulder_pitch_joint",
             "right_shoulder_roll_joint", "right_shoulder_yaw_joint", "right_elbow_joint",
             "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint"]
WAIST_COST = 20.0   # relative cost of waist motion in the IK (whole-body balance is SONIC's job, keep the torso upright)
RIGHT_HAND = ["right_hand_thumb_0_joint", "right_hand_thumb_1_joint", "right_hand_thumb_2_joint",
              "right_hand_middle_0_joint", "right_hand_middle_1_joint", "right_hand_index_0_joint",
              "right_hand_index_1_joint"]
# Right-hand Dex3 targets. CLOSED is the upstream "middle" close preset of
# gear_sonic/utils/teleop/solver/hand/g1_gripper_ik_solver.py (_get_middle_close_q_desired, side R),
# i.e. what the PICO trigger sends. PREGRASP swings the thumb out (thumb_1 toward its open limit).
HAND_OPEN = np.zeros(7)
HAND_PREGRASP = np.array([0.0, 0.6, 0.0, 0.0, 0.0, 0.0, 0.0])
HAND_CLOSED = -np.array([0.0, 0.7, 0.7, -1.0, -1.5, -1.0, -1.5])


def finger_points(m, d, mujoco):
    """World positions of thumb, index and middle distal geoms (centres)."""
    def gc(body):
        b = m.body(body).id
        gs = [g for g in range(m.ngeom) if m.geom_bodyid[g] == b and m.geom_contype[g]]
        return d.geom_xpos[gs[0]].copy()
    return gc("right_hand_thumb_2_link"), gc("right_hand_index_1_link"), gc("right_hand_middle_1_link")


class G1Kin:
    def __init__(self, sonic_root, pitch_down=0.35, roll=0.0):
        import mujoco
        self.mj = mujoco
        self.m = m = build_spec(sonic_root, with_block=False).compile()
        self.d = mujoco.MjData(m)
        self.qadr = {m.joint(j).name: m.jnt_qposadr[j] for j in range(m.njnt)}
        self.dadr = {m.joint(j).name: m.jnt_dofadr[j] for j in range(m.njnt)}
        self.lo = {m.joint(j).name: m.jnt_range[j][0] for j in range(m.njnt)}
        self.hi = {m.joint(j).name: m.jnt_range[j][1] for j in range(m.njnt)}
        self.wrist = m.body("right_wrist_yaw_link").id
        self.inv_cost = np.array([1 / WAIST_COST if n.startswith("waist") else 1.0 for n in IK_JOINTS])
        q = self.d.qpos
        q[:] = 0
        q[3] = 1
        for n, v in DEFAULT_ANGLES.items():
            q[self.qadr[n]] = v
        q[2] = 0.793
        mujoco.mj_kinematics(m, self.d)
        foot = min(self.d.xpos[m.body(b).id][2] for b in ("left_ankle_roll_link", "right_ankle_roll_link"))
        q[2] += 0.036 - foot            # zero-pose ankle_roll height: feet flat on the floor
        self.q_default = q.copy()
        # grasp point = midpoint of thumb tip and the two finger tips, expressed in the wrist frame (open hand)
        self.set_hand(HAND_OPEN)
        mujoco.mj_kinematics(m, self.d)
        t, i, mid = finger_points(m, self.d, mujoco)
        gp = 0.5 * (t + 0.5 * (i + mid))
        R = self.d.xmat[self.wrist].reshape(3, 3)
        self.gp_local = R.T @ (gp - self.d.xpos[self.wrist])
        # target hand orientation: wrist frame with every arm/waist joint at zero, then pitched down
        q0 = self.q_default.copy()
        for n in IK_JOINTS:
            q0[self.qadr[n]] = 0
        self.d.qpos[:] = q0
        mujoco.mj_kinematics(m, self.d)
        self.R0 = R0 = self.d.xmat[self.wrist].reshape(3, 3).copy()
        self.set_orientation(pitch_down, roll)
        self.d.qpos[:] = self.q_default
        mujoco.mj_kinematics(m, self.d)

    def set_orientation(self, pitch_down, roll):
        R0 = self.R0
        c, s = np.cos(pitch_down), np.sin(pitch_down)
        Ry = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        c, s = np.cos(roll), np.sin(roll)
        Rx = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])   # roll about the world x axis (forearm direction)
        self.R_target = Ry @ Rx @ R0

    def set_hand(self, h):
        for n, v in zip(RIGHT_HAND, h):
            self.d.qpos[self.qadr[n]] = v

    def grasp_point(self):
        R = self.d.xmat[self.wrist].reshape(3, 3)
        return self.d.xpos[self.wrist] + R @ self.gp_local

    def solve(self, target, q_init, iters=200, w_rot=0.25, damping=1e-3):
        mj, m, d = self.mj, self.m, self.d
        d.qpos[:] = q_init
        cols = [self.dadr[n] for n in IK_JOINTS]
        jp, jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        for _ in range(iters):
            mj.mj_kinematics(m, d)
            mj.mj_comPos(m, d)
            p = self.grasp_point()
            R = d.xmat[self.wrist].reshape(3, 3)
            ep = target - p
            Re = self.R_target @ R.T
            quat = np.zeros(4)
            mj.mju_mat2Quat(quat, Re.flatten())
            er = np.zeros(3)
            mj.mju_quat2Vel(er, quat, 1.0)
            if np.linalg.norm(ep) < 5e-4 and np.linalg.norm(er) < 1e-2:
                break
            mj.mj_jac(m, d, jp, jr, p, self.wrist)
            J = np.vstack([jp[:, cols], w_rot * jr[:, cols]])
            e = np.concatenate([ep, w_rot * er])
            Wi = np.diag(self.inv_cost)                # weighted DLS: the waist is expensive to move
            dq = Wi @ J.T @ np.linalg.solve(J @ Wi @ J.T + damping * np.eye(6), e)
            for n, v in zip(IK_JOINTS, dq):
                a = self.qadr[n]
                d.qpos[a] = np.clip(d.qpos[a] + 0.5 * v, self.lo[n], self.hi[n])
        mj.mj_kinematics(m, d)
        return d.qpos.copy(), float(np.linalg.norm(target - self.grasp_point()))


def min_jerk(n):
    s = np.linspace(0, 1, n)
    return 10 * s**3 - 15 * s**4 + 6 * s**5


def plan(sonic_root, target_xy=None, grasp_dz=0.012, lift=0.12, pitch_down=0.35, stance_offset=(0.0, 0.0),
         roll=0.0, grasp_dxy=(0.0, 0.0), carry_offset=(0.0, 0.0, 0.0), settle=0.0):
    """carry_offset: constant shift (m, world xyz) of the carry/place targets (over the tray, lowering), measured on
    development rollouts: with the block gripped the hand-held block lands at a repeatable offset from the plan.
    stance_offset: where the robot's pelvis is assumed to stand (world xy) relative to the origin.
    The kinematic model keeps the pelvis at the origin, so world targets are shifted by -stance_offset."""
    kin = G1Kin(sonic_root, pitch_down, roll)
    bx, by = (BLOCK_NOMINAL_XY if target_xy is None else np.asarray(target_xy)) - np.asarray(stance_offset)
    bz = TABLE_TOP_Z + BLOCK_HALF
    tx, ty = np.asarray(TRAY_XY) - np.asarray(stance_offset)
    gz = TABLE_TOP_Z + TRAY_FLOOR + BLOCK_HALF
    grasp = np.array([bx + grasp_dxy[0], by + grasp_dxy[1], bz + grasp_dz])
    pre = grasp + [0, 0, 0.10]
    lifted = grasp + [0, 0, lift]
    # settle: extra seconds spent in the slow end of the descent so a feedback loop can converge before the hand closes
    co = np.asarray(carry_offset, float)
    over = np.array([tx, ty, lifted[2]]) + co
    place = np.array([tx, ty, gz + grasp_dz + 0.02]) + co
    # (phase, cartesian target or None = hold, duration s, hand from, hand to)
    segs = [("hold", None, 2.0, HAND_OPEN, HAND_OPEN),
            ("approach", pre, 2.5, HAND_OPEN, HAND_PREGRASP),
            ("descend", grasp, 1.5 + settle, HAND_PREGRASP, HAND_PREGRASP),
            ("close", None, 1.2, HAND_PREGRASP, HAND_CLOSED),
            ("lift", lifted, 1.5, HAND_CLOSED, HAND_CLOSED),
            ("transport", over, 2.0, HAND_CLOSED, HAND_CLOSED),
            ("lower", place, 1.5, HAND_CLOSED, HAND_CLOSED),
            ("release", None, 1.0, HAND_CLOSED, HAND_OPEN),
            ("retreat", place + [0, 0, 0.12], 1.5, HAND_OPEN, HAND_OPEN),
            ("return", "home", 2.0, HAND_OPEN, HAND_OPEN),
            ("hold_end", None, 2.0, HAND_OPEN, HAND_OPEN)]
    q = kin.q_default.copy()
    kin.d.qpos[:] = q
    kin.mj.mj_kinematics(kin.m, kin.d)
    p = kin.grasp_point()
    qs, hands, phases, errs = [], [], [], {}
    for name, tgt, dur, h0, h1 in segs:
        n = int(round(dur * FPS))
        s = min_jerk(n)
        if isinstance(tgt, str):                      # joint-space return to the default pose
            qa = q.copy()
            for k in range(n):
                qs.append(qa + s[k] * (kin.q_default - qa))
            q = kin.q_default.copy()
            kin.d.qpos[:] = q
            kin.mj.mj_kinematics(kin.m, kin.d)
            p = kin.grasp_point()
        elif tgt is None:
            qs.extend([q.copy()] * n)
        else:
            worst = 0.0
            for k in range(n):                        # straight Cartesian line, IK warm-started per frame
                q, err = kin.solve(p + s[k] * (tgt - p), q)
                worst = max(worst, err) if k == n - 1 else worst
                qs.append(q.copy())
            errs[name] = worst
            p = tgt.copy()
        hands.extend(h0 + s[k] * (h1 - h0) for k in range(n))
        phases.extend([name] * n)
    qs = np.array(qs)
    jp = np.stack([qs[:, kin.qadr[n]] for n in ISAACLAB_ORDER], 1).astype(np.float32)
    jv = np.gradient(jp, 1 / FPS, axis=0).astype(np.float32)
    meta = {"fps": FPS, "frames": len(jp), "stance_offset": list(map(float, stance_offset)),
            "target_xy_world": [float(bx + stance_offset[0]), float(by + stance_offset[1])],
            "target_xy_robot": [float(bx), float(by)], "grasp_dz": grasp_dz,
            "lift": lift, "pitch_down": pitch_down, "roll": roll,
            "grasp_dxy": list(map(float, grasp_dxy)), "carry_offset": list(map(float, carry_offset)), "settle_s": settle,
            "final_ik_error_m": errs,
            "waypoints": {"pre": pre.tolist(), "grasp": grasp.tolist(), "lifted": lifted.tolist(),
                          "over": over.tolist(), "place": place.tolist()}}
    return dict(joint_pos=jp, joint_vel=jv, right_hand=np.array(hands, np.float32),
                left_hand=np.zeros((len(jp), 7), np.float32), phase=np.array(phases),
                qpos=qs.astype(np.float32)), meta


def plan_style(sonic_root, demo_plan, timing_scale, target_xy=None, grasp_dz=0.012, pitch_down=0.35,
               stance_offset=(0.0, 0.0), roll=0.0, grasp_dxy=(0.0, 0.0)):
    """Like plan(), but the hand FOLLOWS THE RETARGETED HUMAN PATH (transfergap.demo.style.robot_path): reach,
    carry and retreat legs at the human's leg timing x demo_plan["timing_scale"] / timing_scale. Robot-side rules
    kept from plan(): an initial min-jerk move to the start of the human reach, a 1.2 s hand-close dwell at the
    grasp, a 1.0 s release dwell, return home. The release height comes from the human (place_offset z)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from transfergap.demo.style import robot_path
    kin = G1Kin(sonic_root, pitch_down, roll)
    so = np.asarray(stance_offset, float)
    bx, by = (BLOCK_NOMINAL_XY if target_xy is None else np.asarray(target_xy)) - so
    tx, ty = np.asarray(TRAY_XY) - so
    bz, gz = TABLE_TOP_Z + BLOCK_HALF, TABLE_TOP_Z + TRAY_FLOOR + BLOCK_HALF
    grasp = np.array([bx + grasp_dxy[0], by + grasp_dxy[1], bz + grasp_dz])
    place = np.array([tx, ty, gz + grasp_dz + max(float(demo_plan["place_offset"][2]), 0.02)])
    legs = robot_path(demo_plan, grasp, place)
    stretch = float(demo_plan.get("timing_scale", 1.0)) / float(timing_scale)
    q = kin.q_default.copy()
    kin.d.qpos[:] = q
    kin.mj.mj_kinematics(kin.m, kin.d)
    p = kin.grasp_point()
    qs, hands, phases, wrist, errs = [], [], [], [], {}

    def emit(name, targets, h0, h1):
        nonlocal q, p
        n = len(targets)
        s = min_jerk(n)
        worst = 0.0
        for k, tgt in enumerate(targets):
            if tgt is None:
                pass
            elif isinstance(tgt, str):
                q = q + (kin.q_default - q) * (1.0 / max(1, n - k))
            else:
                q, err = kin.solve(tgt, q)
                worst = max(worst, err)
            kin.d.qpos[:] = q
            kin.mj.mj_kinematics(kin.m, kin.d)
            qs.append(q.copy())
            hands.append(h0 + s[k] * (h1 - h0))
            phases.append(name)
            wrist.append(kin.d.xpos[kin.wrist] + [so[0], so[1], 0.0])
        errs[name] = worst
        p = kin.grasp_point()

    def leg(name):
        t, x = legs[name]
        n = max(2, int(round(t[-1] * stretch * FPS)))
        u = np.linspace(0, t[-1], n)
        return [np.array([np.interp(v, t, x[:, i]) for i in range(3)]) for v in u]

    n = lambda d: int(round(d * FPS))
    emit("hold", [None] * n(2.0), HAND_OPEN, HAND_OPEN)
    start = legs["reach"][1][0]
    s = min_jerk(n(2.5))
    emit("align", [p + sk * (start - p) for sk in s], HAND_OPEN, HAND_PREGRASP)
    emit("reach", leg("reach"), HAND_PREGRASP, HAND_PREGRASP)
    emit("close", [None] * n(1.2), HAND_PREGRASP, HAND_CLOSED)
    emit("carry", leg("carry"), HAND_CLOSED, HAND_CLOSED)
    emit("release", [None] * n(1.0), HAND_CLOSED, HAND_OPEN)
    emit("retreat", leg("retreat"), HAND_OPEN, HAND_OPEN)
    emit("return", ["home"] * n(2.0), HAND_OPEN, HAND_OPEN)
    emit("hold_end", [None] * n(2.0), HAND_OPEN, HAND_OPEN)
    qs = np.array(qs)
    jp = np.stack([qs[:, kin.qadr[nm]] for nm in ISAACLAB_ORDER], 1).astype(np.float32)
    jv = np.gradient(jp, 1 / FPS, axis=0).astype(np.float32)
    ref = {k: (np.asarray(t) * stretch, np.asarray(x) + [so[0], so[1], 0.0]) for k, (t, x) in legs.items()}
    meta = {"fps": FPS, "frames": len(jp), "motion": "retargeted human path (demo style)",
            "demo_source": demo_plan.get("source"), "timing_scale": float(timing_scale), "stretch": stretch,
            "stance_offset": list(map(float, so)), "grasp_dz": grasp_dz, "pitch_down": pitch_down, "roll": roll,
            "grasp_world": (grasp + [so[0], so[1], 0]).tolist(), "place_world": (place + [so[0], so[1], 0]).tolist(),
            "final_ik_error_m": errs}
    return dict(joint_pos=jp, joint_vel=jv, right_hand=np.array(hands, np.float32),
                left_hand=np.zeros((len(jp), 7), np.float32), phase=np.array(phases), qpos=qs.astype(np.float32),
                wrist_plan_world=np.array(wrist, np.float32),
                **{f"ref_{k}_t": v[0] for k, v in ref.items()}, **{f"ref_{k}_xyz": v[1] for k, v in ref.items()}), meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sonic-root", default="~/GR00T-WholeBodyControl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--target-xy", type=float, nargs=2, default=None,
                    help="grasp target xy; default = nominal block position from scene.py")
    ap.add_argument("--grasp-dz", type=float, default=0.012)
    ap.add_argument("--pitch-down", type=float, default=0.35)
    ap.add_argument("--roll", type=float, default=0.0)
    ap.add_argument("--grasp-dxy", type=float, nargs=2, default=(0.0, 0.0))
    ap.add_argument("--carry-offset", type=float, nargs=3, default=(0.0, 0.0, 0.0),
                    help="constant shift of the carry/place targets, calibrated on development rollouts")
    ap.add_argument("--settle", type=float, default=0.0, help="extra seconds in the descent before the hand closes")
    ap.add_argument("--stance-offset", type=float, nargs=2, default=(0.0, 0.0),
                    help="calibrated standing pelvis xy (frozen constant, measured in dev rollouts)")
    ap.add_argument("--demo-plan", default=None, help="style plan JSON (transfergap.demo.style); follow the human path")
    ap.add_argument("--timing-scale", type=float, default=1.0, help="robot speed factor for --demo-plan")
    a = ap.parse_args()
    if a.demo_plan:
        traj, meta = plan_style(a.sonic_root, json.loads(Path(a.demo_plan).read_text()), a.timing_scale,
                                a.target_xy, a.grasp_dz, a.pitch_down, a.stance_offset, a.roll, a.grasp_dxy)
    else:
        traj, meta = plan(a.sonic_root, a.target_xy, a.grasp_dz, pitch_down=a.pitch_down,
                          stance_offset=a.stance_offset, roll=a.roll, grasp_dxy=a.grasp_dxy, carry_offset=a.carry_offset, settle=a.settle)
    meta["argv"] = vars(a)
    np.savez(a.out, **traj)
    Path(a.out).with_suffix(".json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))
