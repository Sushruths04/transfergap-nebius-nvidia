"""Real-time mode, arm side: follow the live human hand (hands.jsonl from live/hands_pub.py) with a UR arm in MuJoCo,
render it, and serve the view as MJPEG. CPU only; run it on the same host as hands_pub.py so latency is measured on
one clock (on the VM, MUJOCO_GL=egl).

    cd transfergap && MUJOCO_GL=egl PYTHONPATH=. python live/arm_live.py --hands http://127.0.0.1:8092/hands.jsonl \
        --robot ur5e --port 8091
    # then open http://127.0.0.1:8091/ (viewer: camera | robot | G1, live latency) through ssh -L 8091,8092,8093

Live retargeting (per frame, nothing read from the simulator):
  * SOMA joints -> demo frame (transfergap.demo.gemx.soma_to_demo_frame), then into the person's BODY frame
    (forward, left, up) from the hip line, relative to the right shoulder, so the mapping does not depend on where
    the camera stands;
  * calibration: the median body-frame hand position over the first --calib-s seconds is the neutral pose, mapped
    to the robot's READY point above the table; afterwards target = READY + gain * (hand - neutral), clipped to the
    table workspace, exponentially smoothed;
  * gripper: thumb-index distance with hysteresis (--grip aperture), or raise the left hand above the head
    (--grip left_up) when the monocular finger estimate is too noisy.
Simulator state (block position) is used only for the on-screen task label, never by the controller.
On exit (Ctrl-C) the session is saved to runs/live/: the received joints in the exporter format (so the live session
can be replayed into the offline pipeline as a HumanDemo), the robot tool path and per-frame latency.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub import Hub, read_jsonl  # noqa: E402
from transfergap.demo.gemx import soma_to_demo_frame  # noqa: E402
from transfergap.sim.controller import R_DOWN  # noqa: E402
from transfergap.sim.scene import BLOCK_HALF, TRAY_XY, Scene  # noqa: E402

READY = np.array([0.45, 0.0, 0.18])
YAW_MAX = np.pi / 3                          # largest tool yaw copied from the hand (60 deg)
LO, HI = np.array([0.25, -0.35, 0.005]), np.array([0.70, 0.40, 0.45])
CTRL_HZ = 50


BLOCK = np.array([0.45, -0.12, 0.02])     # nominal block centre of the arm scene (sim/scene.py BLOCK_CENTER)
COUNTDOWN_S, CAPTURE_S = 3.0, 1.5


SOFT_M = 0.03


def soft_clip(v, lo, hi, m=SOFT_M):
    """Identity inside [lo + m, hi - m]; within m of an edge it bends smoothly (tanh) and never passes the edge."""
    v = np.asarray(v, float).copy()
    a, b = lo + m, hi - m
    low, high = v < a, v > b
    v[low] = (a - m * np.tanh((a - v) / m))[low]
    v[high] = (b + m * np.tanh((v - b) / m))[high]
    return v


def body_basis(J):
    """Rows = the person's (forward, left, up) unit vectors in the demo frame, from the hip line (same as body_rel)."""
    left = J["LeftLeg"] - J["RightLeg"]
    left = left.copy()
    left[2] = 0.0
    left /= max(np.linalg.norm(left), 1e-6)
    up = np.array([0.0, 0.0, 1.0])
    return np.stack([np.cross(left, up), left, up])


def pinch_yaw(J, side, min_aperture_m=0.02):
    """Yaw (rad, wrapped to (-pi/2, pi/2]) of the thumb-index closing axis in the person's body frame, seen from above:
    0 = fingers close along the person's forward axis, +pi/2 = across (left-right). None while the fingers are too
    close for the direction to be reliable. The two-finger gripper is symmetric under a half turn, hence the wrap.
    Used only with --orient: the robot tool is turned about the vertical so ITS fingers close along the same axis."""
    v = body_basis(J) @ (J[f"{side}HandIndexEnd"] - J[f"{side}HandThumbEnd"])
    if float(np.hypot(v[0], v[1])) < min_aperture_m:
        return None
    y = float(np.arctan2(v[1], v[0]))
    return (y + np.pi / 2) % np.pi - np.pi / 2


class LiveHand:
    """Turns hands.jsonl messages into a robot tool target + gripper command.
    Guided calibration (default): request("neutral") = arms hanging down (checked), request("table") = right hand
    touching the object on the person's table -> that hand position maps to the robot's block, and the robot target is
    BLOCK + gain * (hand - touch point), softly limited to the workspace. auto=True keeps the original behaviour
    (neutral = first calib_s seconds, target = READY + gain * (hand - neutral))."""

    def __init__(self, gain=1.0, calib_s=2.0, alpha=0.5, grip="aperture", close_m=0.04, open_m=0.06, auto=True,
                 side="Right", orient=False, orient_sign=1.0):
        self.side = side
        self.orient, self.orient_sign, self.yaw = orient, orient_sign, 0.0
        self.gain, self.calib_s, self.alpha, self.grip_mode = gain, calib_s, alpha, grip
        self.close_m, self.open_m, self.auto = close_m, open_m, auto
        self.calib, self.neutral, self.t0 = [], None, None
        self.anchor, self.pending = None, None
        self.target, self.closed = READY.copy(), False
        self.last = None
        self.msg = "auto-calibrating: hold still" if auto else "click 1) arms down to calibrate"

    @staticmethod
    def body_rel(J, side="Right"):
        left = J["LeftLeg"] - J["RightLeg"]
        left[2] = 0.0
        left /= max(np.linalg.norm(left), 1e-6)
        up = np.array([0.0, 0.0, 1.0])
        fwd = np.cross(left, up)
        pinch = 0.5 * (J[f"{side}HandThumbEnd"] + J[f"{side}HandIndexEnd"])
        return np.stack([fwd, left, up]) @ (pinch - J[f"{side}Arm"])

    def request(self, kind):
        if kind == "table" and self.neutral is None:
            self.msg = "do step 1 (arms down) first"
            return
        self.pending = {"kind": kind, "t": time.time() + COUNTDOWN_S, "samples": []}

    def _guided(self, rel, now):
        p = self.pending
        if now < p["t"]:
            what = "arms DOWN at your sides" if p["kind"] == "neutral" else "right fingertips ON the object"
            self.msg = f"{what}: {p['t'] - now:.0f}..."
            return
        p["samples"].append(rel)
        self.msg = "hold still..."
        if now - p["t"] < CAPTURE_S:
            return
        m = np.median(np.array(p["samples"]), axis=0)
        self.pending = None
        if p["kind"] == "neutral":
            if m[2] < -0.30 and abs(m[0]) < 0.25:
                self.neutral, self.anchor = m, None
                self.msg = "step 1 OK. now click 2) touch the object"
            else:
                self.msg = f"arms not down (hand {100 * -m[2]:.0f} cm below shoulder, need >30): try again"
        else:
            self.anchor = m
            self.msg = "calibrated: live"

    def update(self, msg):
        J = {k: soma_to_demo_frame(np.array(v)) for k, v in msg["joints"].items()}
        rel = self.body_rel(J, self.side)
        now = time.time()
        if self.pending is not None:
            self._guided(rel, now)
        if self.neutral is None:
            if self.auto:
                self.t0 = self.t0 or now
                self.calib.append(rel)
                if now - self.t0 >= self.calib_s and len(self.calib) >= 5:
                    self.neutral = np.median(np.array(self.calib), axis=0)
                    self.msg = "live (auto-calibrated)"
            return
        if self.anchor is not None:
            tgt = soft_clip(BLOCK + self.gain * (rel - self.anchor), LO, HI)
        elif self.auto:
            tgt = np.clip(READY + self.gain * (rel - self.neutral), LO, HI)
        else:
            tgt = soft_clip(READY + self.gain * (rel - self.neutral), LO, HI)
        self.target = self.alpha * tgt + (1 - self.alpha) * self.target
        if self.orient:                                   # wrist/pinch axis -> tool yaw (clipped, smoothed); None = keep the last
            y = pinch_yaw(J, self.side)
            if y is not None:
                self.yaw = 0.7 * self.yaw + 0.3 * float(np.clip(self.orient_sign * y, -YAW_MAX, YAW_MAX))
        if self.grip_mode == "left_up":
            self.closed = bool(J["LeftHand"][2] > J["Head"][2])
        else:
            ap = float(np.linalg.norm(J[f"{self.side}HandThumbEnd"] - J[f"{self.side}HandIndexEnd"]))
            self.closed = ap < self.close_m if not self.closed else ap < self.open_m
        self.last = msg


class ArmSim:
    def __init__(self, robot, seed=0):
        self.s = Scene(seed=seed, robot=robot)
        self.m, self.d = self.s.model, self.s.data
        self.ik = mujoco.MjData(self.m)
        self.q = np.array(self.s.home_q, float)
        self.lo, self.hi = self.m.actuator_ctrlrange[:6].T
        self.grip = 0.0

    def tool(self, d):
        R = d.xmat[self.s.tool_body].reshape(3, 3)
        return d.xpos[self.s.tool_body] + R @ self.s.pinch_off, R

    def ik_step(self, target, iters=10, damping=1e-3, rot_w=0.6, yaw=0.0):
        c, s_ = np.cos(yaw), np.sin(yaw)
        R_des = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1.0]]) @ R_DOWN
        s, m, d = self.s, self.m, self.ik
        jp, jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        for _ in range(iters):
            d.qpos[s.arm_qadr] = self.q
            mujoco.mj_kinematics(m, d)
            mujoco.mj_comPos(m, d)
            p, R = self.tool(d)
            mujoco.mj_jac(m, d, jp, jr, p, s.tool_body)
            err = np.r_[target - p, rot_w * 0.5 * sum(np.cross(R[:, i], R_des[:, i]) for i in range(3))]
            J = np.vstack([jp, rot_w * jr])[:, s.arm_dof]
            self.q = np.clip(self.q + J.T @ np.linalg.solve(J @ J.T + damping * np.eye(6), err), self.lo, self.hi)

    def control(self, target, closed, dt, yaw=0.0):
        self.ik_step(target, yaw=yaw)
        self.grip = float(np.clip(self.grip + (1 if closed else -1) * dt / 0.5, 0, 1))
        self.d.ctrl[:6] = self.q
        self.d.ctrl[self.s.grip_act] = 255 * self.grip

    def task_label(self):
        """Display only (simulator state): where is the block?"""
        b = self.s.block_pos()
        if abs(b[0] - TRAY_XY[0]) < 0.07 and abs(b[1] - TRAY_XY[1]) < 0.07 and b[2] < 0.05:
            return "block in tray"
        return "block lifted" if b[2] > BLOCK_HALF + 0.03 else "block on table"


def overlay(rgb, lines):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return rgb
    im = Image.fromarray(rgb)
    dr = ImageDraw.Draw(im)
    for i, t in enumerate(lines):
        dr.text((10, 10 + 16 * i), t, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    return np.asarray(im)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hands", default="http://127.0.0.1:8092/hands.jsonl")
    ap.add_argument("--robot", default="ur5e", choices=["ur5e", "ur10e", "kairos", "kairos_mobile"])
    ap.add_argument("--port", type=int, default=8091)
    ap.add_argument("--render-fps", type=float, default=15.0)
    ap.add_argument("--size", default="480x360", help="per arm view; two views side by side")
    ap.add_argument("--gain", type=float, default=0.8, help="robot metres per human metre")
    ap.add_argument("--auto-calib", action="store_true", help="old behaviour: calibrate on the first seconds")
    ap.add_argument("--calib-s", type=float, default=2.0)
    ap.add_argument("--grip", default="aperture", choices=["aperture", "left_up"])
    ap.add_argument("--seconds", type=float, default=0, help="stop after N s (0 = until Ctrl-C)")
    ap.add_argument("--out", default="runs/live")
    ap.add_argument("--single", action="store_true", help="right hand only (no left-hand arm)")
    ap.add_argument("--orient", action="store_true", help="copy the thumb-index closing axis (hand yaw) to the tool yaw; sign unverified until tested with a person")
    ap.add_argument("--orient-sign", type=float, default=1.0, help="-1 flips the yaw direction")
    a = ap.parse_args()
    w, h = map(int, a.size.split("x"))
    hub = Hub(a.port, index_html=Path(__file__).parent / "viewer.html")
    hand = LiveHand(a.gain, a.calib_s, grip=a.grip, auto=a.auto_calib, orient=a.orient, orient_sign=a.orient_sign)
    sim = ArmSim(a.robot)
    lhand = None if a.single else LiveHand(a.gain, a.calib_s, grip=a.grip, auto=a.auto_calib, side="Left", orient=a.orient, orient_sign=a.orient_sign)
    lsim = None if a.single else ArmSim(a.robot)
    lock = threading.Lock()
    rec = {"t_cap": [], "t_rx": [], "t_applied": [], "joints": [], "tool": [], "target": [], "closed": []}
    state = {"rx": 0, "err": None}

    def on_msg(msg):
        if "_error" in msg:
            state["err"] = msg["_error"]
            return
        with lock:
            state["err"] = None
            hand.update(msg)
            if lhand is not None:
                lhand.update(msg)
            state["rx"] += 1
            state["pending"] = (msg, time.time())

    threading.Thread(target=read_jsonl, args=(a.hands, on_msg), daemon=True).start()
    renderer = mujoco.Renderer(sim.m, h, w)
    lrenderer = None if lsim is None else mujoco.Renderer(lsim.m, h, w)
    dt_ctrl, n_sub = 1.0 / CTRL_HZ, int(round(1.0 / CTRL_HZ / sim.m.opt.timestep))
    t_start, t_render, lat = time.time(), 0.0, []
    resets, calibs, tcalibs = 0, 0, 0
    print(f"[arm_live] viewer http://127.0.0.1:{a.port}/  robot {a.robot}; waiting for {a.hands}", flush=True)
    try:
        while not a.seconds or time.time() - t_start < a.seconds:
            t0 = time.time()
            if hub.cmd.get("reset", 0) != resets:
                resets = hub.cmd["reset"]
                for sm in (sim, lsim):
                    if sm is not None:
                        sm.s.reset()
                        sm.q, sm.grip = np.array(sm.s.home_q, float), 0.0
            if hub.cmd.get("g1calib", 0) != calibs:          # viewer step 1: arms down (arm and G1)
                calibs = hub.cmd["g1calib"]
                with lock:
                    hand.request("neutral")
                    if lhand is not None:
                        lhand.request("neutral")
            if hub.cmd.get("tablecalib", 0) != tcalibs:      # viewer step 2: touch the object
                tcalibs = hub.cmd["tablecalib"]
                with lock:
                    hand.request("table")
                    if lhand is not None:
                        lhand.request("table")
            with lock:
                target, closed, yaw = hand.target.copy(), hand.closed, hand.yaw
                pending = state.pop("pending", None)
            sim.control(target, closed, dt_ctrl, yaw)
            for _ in range(n_sub):
                mujoco.mj_step(sim.m, sim.d)
            if lsim is not None:
                with lock:
                    ltarget, lclosed, lyaw = lhand.target.copy(), lhand.closed, lhand.yaw
                lsim.control(ltarget, lclosed, dt_ctrl, lyaw)
                for _ in range(n_sub):
                    mujoco.mj_step(lsim.m, lsim.d)
            tool = sim.tool(sim.d)[0]
            if pending is not None and hand.neutral is not None:
                msg, t_rx = pending
                now = time.time()
                lat.append(now - msg["t_cap"])
                for k, v in (("t_cap", msg["t_cap"]), ("t_rx", t_rx), ("t_applied", now), ("joints", msg["joints"]),
                             ("tool", tool.tolist()), ("target", target.tolist()), ("closed", closed)):
                    rec[k].append(v)
            if time.time() - t_render >= 1.0 / a.render_fps:
                t_render = time.time()
                renderer.update_scene(sim.d, camera="third_person")
                l_ms = 1000 * np.median(lat[-30:]) if lat else float("nan")
                trk = [np.linalg.norm(np.subtract(a_, b_)) for a_, b_ in zip(rec["target"][-30:], rec["tool"][-30:])]
                trk_cm = 100 * float(np.median(trk)) if trk else float("nan")
                status = {"robot": a.robot, "calibrated": hand.neutral is not None, "rx": state["rx"],
                          "message": hand.msg, "anchored": hand.anchor is not None,
                          "latency_ms_median30": round(l_ms, 1), "tracking_err_cm_median30": round(trk_cm, 1),
                          "grip_closed": closed, "tool_yaw_deg": round(float(np.degrees(yaw)), 1), "orient": a.orient,
                          "task": sim.task_label(), "hands_fps": (hand.last or {}).get("fps"),
                          "error": state["err"]}
                hub.put_json("status", status)
                txt = [f"{a.robot}  {hand.msg}",
                       f"camera->robot latency {l_ms:5.0f} ms   grip {'CLOSED' if closed else 'open'}",
                       f"robot lags the hand path by {trk_cm:4.1f} cm (median, last 30 frames)",
                       f"{status['task']}"]
                img = overlay(renderer.render(), txt)
                if lrenderer is not None:
                    lrenderer.update_scene(lsim.d, camera="third_person")
                    limg = overlay(lrenderer.render(), [f"LEFT hand  {lhand.msg}",
                                                        f"grip {'CLOSED' if lhand.closed else 'open'}  {lsim.task_label()}"])
                    img = np.concatenate([limg, overlay(img, ["", "", "", "", "RIGHT hand"])], axis=1)
                hub.put_jpeg("robot", img)
            time.sleep(max(0.0, dt_ctrl - (time.time() - t0)))
    except KeyboardInterrupt:
        pass
    finally:
        if rec["joints"]:
            out = Path(a.out)
            out.mkdir(parents=True, exist_ok=True)
            names = list(rec["joints"][0])
            joints = np.array([[f[n] for n in names] for f in rec["joints"]], float)
            fps = (len(rec["t_cap"]) - 1) / max(rec["t_cap"][-1] - rec["t_cap"][0], 1e-6)
            stem = out / time.strftime("session_%Y%m%d_%H%M%S")
            np.savez_compressed(f"{stem}_joints.npz", joints=joints, joint_names=np.array(names), fps=fps,
                                frame="soma_world_y_up", t_cap=np.array(rec["t_cap"]),
                                meta=json.dumps({"source": "live session", "robot": a.robot, "note":
                                                 "subset of SOMA joints; fps = mean received rate (uneven)"}))
            np.savez_compressed(f"{stem}_robot.npz", **{k: np.array(v) for k, v in rec.items() if k != "joints"})
            L = np.array(rec["t_applied"]) - np.array(rec["t_cap"])
            print(f"\n[arm_live] saved {stem}_*.npz: {len(L)} frames, camera->robot latency median "
                  f"{1000 * np.median(L):.0f} ms, p90 {1000 * np.percentile(L, 90):.0f} ms, rx {fps:.1f} fps")
        renderer.close()
        if lrenderer is not None:
            lrenderer.close()


if __name__ == "__main__":
    main()
