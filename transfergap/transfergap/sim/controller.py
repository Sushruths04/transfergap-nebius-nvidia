"""Scripted pick-and-place: damped-least-squares IK on the tool point (mj_jac), real contact grasping only."""
from __future__ import annotations

import mujoco
import numpy as np

from .scene import OPENING_M, YAW_CLEARANCE_M

R_DOWN = np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1.]])   # tool z down, fingers close along world x
# (name, target, duration_s, gripper_closed): target is a callable of (block_xyz_belief, goal_xyz)
HOVER, CLEAR = 0.12, 0.20
PHASES = [
    ("approach", lambda b, g: b + [0, 0, HOVER], 2.0, False),
    ("descend", lambda b, g: b + [0, 0, 0.0], 1.5, False),
    ("close", lambda b, g: b + [0, 0, 0.0], 0.8, True),
    ("lift", lambda b, g: b + [0, 0, CLEAR], 1.5, True),
    ("transport", lambda b, g: g + [0, 0, CLEAR], 2.5, True),
    ("descend_place", lambda b, g: g + [0, 0, 0.004], 1.5, True),
    ("open", lambda b, g: g + [0, 0, 0.004], 0.8, False),
    ("retreat", lambda b, g: g + [0, 0, HOVER + 0.05], 1.5, False),
    ("settle", lambda b, g: g + [0, 0, HOVER + 0.05], 0.8, False),
]


class ScriptedPickPlace:
    """Perturbation knobs (all default to no error):
    target_offset_m    legacy: block-belief error magnitude, random xy direction from seed
    perception_err_xy  explicit belief error vector (m), overrides target_offset_m
    tcp_offset_m       legacy: tool-frame calibration error magnitude, RANDOM 3D direction from seed
    tcp_offset_vec     explicit tool-frame calibration error vector (m), overrides tcp_offset_m
    grip_force_scale   scales gripper actuator force limit
    timing_scale       >1 executes phases faster
    look_again_err_xy  if given, re-perceive the block after the approach phase with this error vector
    tcp_probe_noise_m  if given, do one touch-probe of a known fixture (noise vector, m) and subtract the
                       measured tool-point offset
    demo_plan          a transfergap.demo_plan/v1 dict (transfergap.demo.retarget / .style). Without a "style" block
                       the fixed phases are kept but aimed at block + grasp_offset and goal + place_offset with the
                       demo's lift height; with a "style" block the tool follows the retargeted human hand path
                       (reach, carry, retreat legs at the human's leg timing x plan timing_scale / timing_scale)
    retarget_q_err     joint-space retargeting error (6-vector, rad): the joint targets sent to the arm are the
                       controller's own IK solution plus this constant offset, as if the motion had been
                       retargeted from a human wrist trajectory by an imperfect retargeter. None/zeros = the
                       kinematics oracle (exact IK on the robot model).

    PRIVILEGED-STATE RULE: the block pose is read only inside perceive(). Nothing here reads success,
    scoring, contacts or block velocity (enforced by tests/test_privileged_guard.py).
    """

    def __init__(self, scene, target_offset_m=0., tcp_offset_m=0., grip_force_scale=1., timing_scale=1.,
                 perception_err_xy=None, tcp_offset_vec=None, look_again_err_xy=None, tcp_probe_noise_m=None,
                 retarget_q_err=None, demo_plan=None, goal_belief_xyz=None, look_again_fn=None,
                 place_look_fn=None):
        self.s, m = scene, scene.model
        if tcp_offset_vec is not None:
            self.tcp = np.asarray(tcp_offset_vec, float)
        else:
            u = np.random.default_rng(scene.seed + 20_000).normal(size=3)
            self.tcp = tcp_offset_m * u / np.linalg.norm(u)
        if tcp_probe_noise_m is not None:
            self.touch_probe(tcp_probe_noise_m)
        self.timing = timing_scale
        self.set_grasp_yaw(0.0)
        if perception_err_xy is None:
            ang = np.random.default_rng(scene.seed + 10_000).uniform(0, 2 * np.pi)
            perception_err_xy = target_offset_m * np.array([np.cos(ang), np.sin(ang)])
        self.belief = self.perceive(perception_err_xy)
        # where the controller believes the tray target is; default = the scene's goal (unchanged behaviour). A sensor
        # based pipeline (sim/perception.py) overrides it from its own estimate.
        self.goal_b = np.asarray(scene.goal_xyz if goal_belief_xyz is None else goal_belief_xyz, float)
        self.look_again_err = None if look_again_err_xy is None else np.asarray(look_again_err_xy, float)
        # sensor-based look-again from close range: fn(scene) -> {"block_xyz", "yaw"}; it must not read ground truth.
        # If it raises RuntimeError (nothing found) the earlier belief is kept and the failure is recorded.
        self.look_again_fn, self.look_again_log = look_again_fn, None
        # look at the tray from close range at the end of the carry: fn(scene) -> {"info": {"tray_xy", "floor_z"}}.
        # The goal belief is shifted to the new tray centre; its height by the change in estimated floor height.
        self.place_look_fn, self.place_look_log, self.floor0 = place_look_fn, None, None
        m.actuator_forcerange[scene.grip_act] *= grip_force_scale
        self.ik = mujoco.MjData(m)
        self.q = np.array(scene.home_q, float)
        self.lo, self.hi = m.actuator_ctrlrange[:6].T
        self.dq_ret = np.zeros(6) if retarget_q_err is None else np.asarray(retarget_q_err, float).reshape(6)
        self.grip = 0.0
        self.ik.qpos[scene.arm_qadr] = scene.data.qpos[scene.arm_qadr]   # arm joints only, never block state
        self.tgt0 = self.tool_point()
        self.pi, self.t_in = 0, 0.0
        self.done = False
        self.plan = demo_plan
        self.phases = PHASES if demo_plan is None else self._demo_phases(demo_plan)

    def _demo_phases(self, plan):
        go, po = np.asarray(plan["grasp_offset"], float), np.asarray(plan["place_offset"], float)
        clear = float(plan.get("clear_m", CLEAR))
        if "style" not in plan:
            return [("approach", lambda b, g: b + go + [0, 0, HOVER], 2.0, False),
                    ("descend", lambda b, g: b + go, 1.5, False),
                    ("close", lambda b, g: b + go, 0.8, True),
                    ("lift", lambda b, g: b + go + [0, 0, clear], 1.5, True),
                    ("transport", lambda b, g: g + po + [0, 0, clear], 2.5, True),
                    ("descend_place", lambda b, g: g + po, 1.5, True),
                    ("open", lambda b, g: g + po, 0.8, False),
                    ("retreat", lambda b, g: g + po + [0, 0, HOVER + 0.05], 1.5, False),
                    ("settle", lambda b, g: g + po + [0, 0, HOVER + 0.05], 0.8, False)]
        from ..demo.style import robot_path
        stretch = float(plan.get("timing_scale", 1.0))      # human leg time x stretch = robot-nominal leg time
        legs = lambda b, g: robot_path(plan, b + go, g + po)

        def leg(name, closed):
            dur = stretch * float(plan["style"]["legs"][name]["t_s"][-1])
            return (name, ("path", name, legs), max(dur, 0.2), closed)
        return [("align", lambda b, g: legs(b, g)["reach"][1][0], 2.0, False), leg("reach", False),
                ("close", lambda b, g: b + go, 0.8, True), leg("carry", True),
                ("open", lambda b, g: g + po, 0.8, False), leg("retreat", False),
                ("settle", lambda b, g: legs(b, g)["retreat"][1][-1], 0.8, False)]

    def set_grasp_yaw(self, yaw, width_m=None):
        """Rotate the tool about world z by yaw (rad) so the fingers close across a block face that is rotated by yaw.
        Cube symmetry: the angle is wrapped to (-45, 45] degrees. 0 = the original axis-aligned grasp.
        With width_m (the perceived cube side) the rotation is applied only when it is needed: if the cube, seen at that
        yaw across an axis-aligned grasp (width x (|cos| + |sin|)), still clears the gripper opening by
        YAW_CLEARANCE_M, the tool stays axis-aligned and the fingers square the cube up as they close."""
        y = (float(yaw) + np.pi / 4) % (np.pi / 2) - np.pi / 4
        opening = OPENING_M.get(self.s.robot)
        if width_m is not None and opening is not None and width_m * (abs(np.cos(y)) + abs(np.sin(y))) <= opening - YAW_CLEARANCE_M:
            y = 0.0
        c, s_ = np.cos(y), np.sin(y)
        self.grasp_yaw = y
        self.R_goal = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1.]]) @ R_DOWN

    def perceive(self, err_xy):
        """The ONLY place the block pose is read: simulator ground truth plus a perception error on xy.
        Zero error = the perception oracle."""
        return self.s.block_pos() + np.array([err_xy[0], err_xy[1], 0.0])

    def touch_probe(self, noise_m):
        """Calibration correction: one touch of a fixture at a known pose. The probe reports the tool-frame
        offset between the real contact point and the controller's model of it (= minus the calibration
        error) with measurement noise; we add that to the model. Probe motion/time is NOT simulated."""
        measured = -self.tcp + np.asarray(noise_m, float)
        self.tcp = self.tcp + measured

    @property
    def phase(self):
        return self.phases[self.pi][0]

    def tool_point(self, d=None):
        d = d or self.ik
        mujoco.mj_kinematics(self.s.model, d)
        return d.xpos[self.s.tool_body] + d.xmat[self.s.tool_body].reshape(3, 3) @ (self.s.pinch_off + self.tcp)

    def ik_step(self, target, iters=4, damping=1e-3, rot_w=0.6):
        s, m, d = self.s, self.s.model, self.ik
        for _ in range(iters):
            d.qpos[s.arm_qadr] = self.q
            mujoco.mj_kinematics(m, d)
            mujoco.mj_comPos(m, d)
            R = d.xmat[s.tool_body].reshape(3, 3)
            p = d.xpos[s.tool_body] + R @ (s.pinch_off + self.tcp)
            jp, jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
            mujoco.mj_jac(m, d, jp, jr, p, s.tool_body)
            err = np.r_[target - p, rot_w * 0.5 * sum(np.cross(R[:, i], self.R_goal[:, i]) for i in range(3))]
            J = np.vstack([jp, rot_w * jr])[:, s.arm_dof]
            dq = J.T @ np.linalg.solve(J @ J.T + damping * np.eye(6), err)
            self.q = np.clip(self.q + dq, self.lo, self.hi)

    def step(self, dt):
        """Advance the script by dt of control time; writes ctrl. Returns nothing."""
        s, d = self.s, self.s.data
        name, tfun, dur, closed = self.phases[self.pi]
        dur /= self.timing
        a = min(self.t_in / dur, 1.0)
        if isinstance(tfun, tuple):                 # follow a retargeted human leg at the human's own timing
            ts, xs = tfun[2](self.belief, self.goal_b)[tfun[1]]
            u = a * ts[-1]
            goal = xs[-1]
            self.ik_step(np.array([np.interp(u, ts, xs[:, i]) for i in range(3)]))
        else:
            goal = tfun(self.belief, self.goal_b)
            a = a * a * (3 - 2 * a)
            self.ik_step(self.tgt0 + a * (goal - self.tgt0))
        self.grip = float(np.clip(self.grip + (1 if closed else -1) * dt / (0.5 / min(self.timing, 1.0)), 0, 1))
        d.ctrl[:6] = np.clip(self.q + self.dq_ret, self.lo, self.hi)   # retargeting error acts on the command
        d.ctrl[s.grip_act] = 255 * self.grip
        self.t_in += dt
        if self.t_in >= dur:
            self.tgt0, self.t_in = goal, 0.0
            if self.pi + 1 < len(self.phases):
                if name in ("approach", "align") and self.look_again_err is not None:
                    self.belief = self.perceive(self.look_again_err)   # look-again from close range
                if name in ("transport", "carry") and self.place_look_fn is not None:
                    try:
                        inf = self.place_look_fn(self.s)["info"]
                        dz = 0.0 if self.floor0 is None else inf["floor_z"] - self.floor0
                        self.goal_b = np.array([*inf["tray_xy"], self.goal_b[2] + dz])
                        self.place_look_log = dict(ok=True)
                    except RuntimeError as e:
                        self.place_look_log = dict(ok=False, error=str(e)[:100])
                if name in ("approach", "align") and self.look_again_fn is not None:
                    try:
                        est = self.look_again_fn(self.s)
                        self.belief = np.asarray(est["block_xyz"], float)
                        if est.get("yaw") is not None:
                            self.set_grasp_yaw(est["yaw"], est.get("width_m"))
                        self.look_again_log = dict(ok=True, **est.get("info", {}).get("log", {}))
                    except RuntimeError as e:
                        self.look_again_log = dict(ok=False, error=str(e)[:100])
                self.pi += 1
            else:
                self.done = True

