"""KAIROS on its mobile base in MuJoCo: drive the planar base, then pick and place with the arm, all in one scene.

    python -m transfergap.sim.kairos_mobile demo --out runs/kairos_mobile_demo [--seed 0] [--start -1.3 -0.9 0.9]

The model is `kairos_mobile` (scene.py / kairos_model.mount_on_base): Summit XLS chassis, four visual omni wheels, UR10e +
Robotiq 2F-140 on the top plate. The base is a planar holonomic body: three position servos on a velocity- and
acceleration-limited setpoint (BaseDrive). Wheel/floor contact and wheel motors are NOT simulated; the wheels spin with the
omni-wheel kinematics for show. Once parked at the origin, the task and the controller are the same as for the fixed arm
(`kairos`), whose results are unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from . import kairos_model as KM
from .controller import ScriptedPickPlace
from .rollout import CTRL_HZ, make_camera, make_renderer, render_views
from .scene import Scene

V_MAX, W_MAX, A_MAX, ALPHA_MAX = 0.8, 0.9, 0.7, 1.2          # m/s, rad/s, m/s^2, rad/s^2 (below the XLS's rated limits)
POS_TOL, YAW_TOL = 0.01, 0.01


class BaseDrive:
    """Holonomic base command interface: drive(vx, vy, wz) in the ROBOT frame, or go_to(x, y, yaw) in the world frame."""

    def __init__(self, scene: Scene):
        m = scene.model
        j = lambda n: m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)]
        a = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n + "_servo")
        self.s = scene
        self.qadr = [j(n) for n in KM.BASE_JOINTS]
        self.act = [a(n) for n in KM.BASE_JOINTS]
        self.wadr = [j(f"kb_wheel_{w}_joint") for w, _, _ in KM.WHEELS]
        self.target = self.pose().copy()
        self.vel = np.zeros(3)                 # current robot-frame velocity (vx, vy, wz)

    def pose(self):
        return np.array([self.s.data.qpos[a] for a in self.qadr])

    def place(self, x, y, yaw):
        """Teleport the base (initial condition only) and hold it there."""
        for a, v in zip(self.qadr, (x, y, yaw)):
            self.s.data.qpos[a] = v
        self.target = np.array([x, y, yaw], float)
        self.vel[:] = 0
        self._ctrl()
        mujoco.mj_forward(self.s.model, self.s.data)

    def _ctrl(self):
        for a, v in zip(self.act, self.target):
            self.s.data.ctrl[a] = v

    def drive(self, vx, vy, wz, dt):
        """Advance the setpoint by one control tick toward the commanded robot-frame velocity (limits applied)."""
        want = np.array([vx, vy, wz], float)
        lim = np.array([V_MAX, V_MAX, W_MAX])
        want = np.clip(want, -lim, lim)
        sp = np.hypot(want[0], want[1])
        if sp > V_MAX:
            want[:2] *= V_MAX / sp
        step = np.array([A_MAX, A_MAX, ALPHA_MAX]) * dt
        self.vel += np.clip(want - self.vel, -step, step)
        c, s = np.cos(self.target[2]), np.sin(self.target[2])
        self.target += dt * np.array([c * self.vel[0] - s * self.vel[1], s * self.vel[0] + c * self.vel[1], self.vel[2]])
        self._ctrl()
        lx, ly = KM.WHEEL_XY                    # 4-wheel omni/mecanum kinematics (visual only): wheel speed from the body twist
        for adr, (_, sx, sy) in zip(self.wadr, KM.WHEELS):
            w = (self.vel[0] - sx * sy * self.vel[1] - sy * (lx + ly) * self.vel[2]) / KM.WHEEL_R
            self.s.data.qpos[adr] += w * dt

    def go_to(self, goal, dt, speed_gain=1.2):
        """One tick of a P controller toward the world-frame pose; True once inside the tolerance and nearly stopped."""
        err = np.asarray(goal, float) - self.target
        err[2] = (err[2] + np.pi) % (2 * np.pi) - np.pi
        c, s = np.cos(self.target[2]), np.sin(self.target[2])
        e_r = np.array([c * err[0] + s * err[1], -s * err[0] + c * err[1], err[2]])
        # braking distance limit so the base stops on the goal instead of overshooting
        vmax = np.sqrt(2 * A_MAX * max(np.hypot(e_r[0], e_r[1]) - 0.5 * POS_TOL, 0.0))
        cmd = speed_gain * e_r
        sp = np.hypot(cmd[0], cmd[1])
        if sp > vmax:
            cmd[:2] *= vmax / max(sp, 1e-9)
        cmd[2] = np.clip(cmd[2], -np.sqrt(2 * ALPHA_MAX * abs(err[2])) if abs(err[2]) > YAW_TOL else 0, np.sqrt(2 * ALPHA_MAX * abs(err[2])))
        self.drive(*cmd, dt)
        return bool(np.hypot(err[0], err[1]) < POS_TOL and abs(err[2]) < YAW_TOL and np.linalg.norm(self.vel) < 0.02)


def _hold_arm(scene):
    scene.data.ctrl[:6] = scene.home_q


def demo(out, seed=0, start=(-1.3, -0.9, 0.9), size=(480, 640), cams=("wide", "third_person")):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    sc = Scene(seed, "kairos_mobile")
    m, d = sc.model, sc.data
    drv = BaseDrive(sc)
    drv.place(*start)
    _hold_arm(sc)
    sub = round(1 / (m.opt.timestep * CTRL_HZ))
    dt = 1 / CTRL_HZ
    rend = make_renderer(sc, size)
    camobjs = [make_camera(c) for c in cams]
    frames, log = [], {"phases": []}
    tick = [0]

    def advance():
        for _ in range(sub):
            mujoco.mj_step(m, d)
        tick[0] += 1
        if rend is not None and tick[0] % (CTRL_HZ // 25) == 0:
            frames.append(render_views(rend, d, camobjs))

    # 1) drive to the parking pose in front of the table (arm stays folded at home)
    n = 0
    while not drv.go_to((0.0, 0.0, 0.0), dt) and n < 60 * CTRL_HZ:
        _hold_arm(sc)
        advance()
        n += 1
    log["phases"].append({"phase": "drive_to_table", "seconds": round(n * dt, 2), "final_pose": drv.pose().round(4).tolist(),
                          "parked_within_tolerance": bool(np.hypot(*drv.pose()[:2]) < 2 * POS_TOL and abs(drv.pose()[2]) < 2 * YAW_TOL)})
    for _ in range(CTRL_HZ):                    # settle with the base held
        drv.drive(0, 0, 0, dt)
        _hold_arm(sc)
        advance()
    # 2) pick and place with the arm (same controller as every other robot; the base holds its setpoint)
    ctl = ScriptedPickPlace(sc)
    n = 0
    while not ctl.done and n < 120 * CTRL_HZ:
        ctl.step(dt)
        drv.drive(0, 0, 0, dt)
        advance()
        n += 1
    blk, goal = sc.block_pos(), sc.goal_xyz
    placed = bool(np.hypot(*(blk[:2] - goal[:2])) < 0.04 and abs(blk[2] - goal[2]) < 0.02)
    log["phases"].append({"phase": "pick_and_place", "seconds": round(n * dt, 2), "block_xyz": blk.round(4).tolist(),
                          "goal_xyz": goal.round(4).tolist(), "placed_on_tray": placed})
    # 3) drive away backwards and sideways (shows free planar motion with the arm folded again)
    drv.target = drv.pose().copy()
    n = 0
    for _ in range(int(2.0 * CTRL_HZ)):
        sc.data.ctrl[:6] = sc.home_q
        drv.drive(-0.5, -0.3, 0.4, dt)
        advance()
        n += 1
    log["phases"].append({"phase": "drive_away", "seconds": round(n * dt, 2), "final_pose": drv.pose().round(3).tolist()})
    if rend is not None:
        rend.close()
    video = None
    if frames:
        import imageio.v2 as imageio
        video = str(out / "kairos_mobile_demo.mp4")
        imageio.mimwrite(video, frames, fps=25)
    log.update({"robot": "kairos_mobile", "seed": seed, "start_pose": list(start), "video": video,
                "model": {"base": "Summit XLS chassis (lab URDF), planar servo base", "wheels": "visual only",
                          "arm": "UR10e + Robotiq 2F-140", "arm_base_height_above_floor_m": round(-KM.FLOOR_Z, 4)}})
    (out / "demo_report.json").write_text(json.dumps(log, indent=1))
    return log


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("demo")
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--start", type=float, nargs=3, default=[-1.3, -0.9, 0.9], metavar=("X", "Y", "YAW"))
    a = ap.parse_args()
    print(json.dumps(demo(a.out, a.seed, tuple(a.start)), indent=1))


if __name__ == "__main__":
    main()
