"""One episode -> transfergap episode dict (metrics.validate_episode compatible), optional mp4."""
from __future__ import annotations

import os

import mujoco
import numpy as np

from .controller import ScriptedPickPlace
from .scene import BLOCK_HALF, BLOCK_JITTER, DEFAULT_ROBOT, Scene

CTRL_HZ, LOG_HZ = 100, 50                      # logging >= 50 Hz
TASK = {"position_tolerance_m": 0.03, "min_lift_m": 0.05, "settle_duration_s": 0.5,
        "max_settle_speed_m_s": 0.02}          # frozen for protocol block_to_tray_v1
PROTOCOL, METHOD = "block_to_tray_v1", "scripted_ik"


def make_renderer(scene, size=(480, 640)):
    """Return a mujoco.Renderer, trying EGL then OSMesa then GLFW; None if no GL backend works."""
    for gl in ("egl", "osmesa", "glfw"):
        os.environ["MUJOCO_GL"] = gl
        try:
            return mujoco.Renderer(scene.model, *size)
        except Exception:
            continue
    return None


def make_camera(spec):
    """A named model camera (str) or a free camera dict {lookat, distance, azimuth, elevation}."""
    if isinstance(spec, str):
        return spec
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = spec["lookat"]
    cam.distance, cam.azimuth, cam.elevation = spec["distance"], spec["azimuth"], spec["elevation"]
    return cam


def render_views(renderer, data, cams):
    """One frame; several views are placed side by side."""
    views = []
    for cam in cams:
        renderer.update_scene(data, camera=cam)
        views.append(renderer.render().copy())
    return views[0] if len(views) == 1 else np.concatenate(views, axis=1)


def run_episode(seed, perturbation=None, video_path=None, label=None, oracle=None, condition=None,
                robot=DEFAULT_ROBOT, cameras=("third_person",), size=(480, 640), block_half=BLOCK_HALF, perceiver=None,
                block_yaw=0.0, distractors=(), block_jitter=BLOCK_JITTER, look_again=None,
                place_look=None, trace=None, obs_cb=None):
    """perceiver(scene) -> {"block_xyz": ..., "goal_xyz": ...}: when given, the controller's beliefs come from this
    sensor-based estimate instead of the ground truth (sim/perception.py); the scorer still uses the true goal."""
    p = dict(perturbation or {})
    scene = Scene(seed, robot, block_half, block_yaw, distractors, block_jitter)
    m, d = scene.model, scene.data
    ctl = ScriptedPickPlace(scene, look_again_fn=look_again, place_look_fn=place_look, **p)
    if perceiver is not None:
        est = perceiver(scene)
        ctl.belief = np.asarray(est["block_xyz"], float)
        ctl.goal_b = np.asarray(est["goal_xyz"], float)
        ctl.floor0 = (est.get("info") or {}).get("floor_z")
        if est.get("yaw") is not None:                     # estimated block yaw -> grasp orientation
            ctl.set_grasp_yaw(est["yaw"], est.get("width_m"))
    sub = round(1 / (m.opt.timestep * CTRL_HZ))
    log_every = CTRL_HZ // LOG_HZ
    renderer = make_renderer(scene, size) if video_path else None
    cams = [make_camera(c) for c in cameras]
    frames, states, tick = [], [], 0
    forbidden = fallen = touching = False   # forbidden/fallen latch between samples and stay set
    video = None
    while not ctl.done:
        ctl.step(1 / CTRL_HZ)
        for _ in range(sub):
            mujoco.mj_step(m, d)
            f, t = scene.contact_flags()
            pos = scene.block_pos()
            forbidden |= f
            touching = t
            fallen |= bool(pos[2] < 0.0)
            forbidden |= bool(np.hypot(*(pos[:2] - [0.3, 0])) > 0.6 and pos[2] < 0.05)  # knocked off table
        released = ctl.phase in ("open", "retreat", "settle") and not touching
        if trace is not None:        # data-engine hook (default off): one record per control tick, never read by the controller
            trace.append({"t": float(d.time), "q": d.qpos[scene.arm_qadr].tolist(), "ctrl": d.ctrl[:int(m.nu)].tolist(), "phase": ctl.phase})
        if obs_cb is not None:       # data-engine hook (default off): called once per control tick after the physics step
            obs_cb(scene, d, tick)
        tick += 1
        if tick % log_every == 0:
            st = {"t_s": round(d.time, 6), "object_xyz": scene.block_pos().tolist(),
                  "object_velocity": scene.block_vel().tolist(), "released": bool(released),
                  "forbidden_collision": bool(forbidden), "fallen": bool(fallen), "phase": ctl.phase}
            if ctl.plan is not None:   # true pinch point, logged for style scoring only (never read by the controller)
                R = d.xmat[scene.tool_body].reshape(3, 3)
                st["tool_xyz"] = (d.xpos[scene.tool_body] + R @ scene.pinch_off).tolist()
            states.append(st)
            if renderer is not None and tick % (CTRL_HZ // 25 * 1) == 0:
                frames.append(render_views(renderer, d, cams))
    if renderer is not None:
        renderer.close()
    if video_path and frames:
        import imageio.v2 as imageio
        imageio.mimwrite(video_path, frames, fps=25)
        video = str(video_path)
    tag = label or "baseline"
    ep = {"schema_version": 1, "source": "simulation", "trial_id": f"seed{seed}", "demo_id": "scripted_ik_demo",
          "scene_id": f"block_to_tray_seed{seed}", "seed": int(seed), "robot": scene.robot_label,
          "method": f"{METHOD}[{tag}]", "sensor": "oracle", "protocol_id": PROTOCOL, "frame_id": "world",
          "units": "m", "task": {"goal_xyz": scene.goal_xyz.tolist(), **TASK}, "states": states,
          "perturbation": p, "video": video}
    if oracle is not None:
        ep["oracle"] = oracle
    if condition is not None:
        ep["condition"] = condition
    return ep
