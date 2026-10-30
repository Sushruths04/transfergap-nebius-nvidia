"""One G1 rollout in the upstream GEAR-SONIC MuJoCo sim, with our task overlay, logging and a third-person video.

This replaces only the entry point (gear_sonic/scripts/run_sim_loop.py). The physics, PD torque
computation and DDS bridge are the upstream BaseSimulator/DefaultEnv, unmodified; the scene path is
redirected through the ROBOT_SCENE config key to the overlay written by scene.py.

Harness differences from the upstream entry point, all on the simulator side:
  * the elastic band is lowered to standing height and released by timer once the controller sends
    commands (upstream: the operator presses 7/9 in the viewer);
  * DefaultEnv.check_fall no longer calls reset() (a reset would teleport the block mid-episode);
    a fall is logged and ends the rollout instead.
Simulator state read here is only written to the episode log. Nothing is sent to the controller or
to the motion streamer except the "ready" file, which says the band is released (no state values).

Run from the GR00T-WholeBodyControl root with its .venv_sim:
    MUJOCO_GL=egl python ~/transfergap_g1/g1/sim_runner.py --seed 0 --rollout 0 --run-dir RUN
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scene import BLOCK_HALF, TABLE_TOP_Z, goal_xyz, sample_block_xy, write_scene  # noqa: E402
from video import Mp4Writer  # noqa: E402

LOG_HZ, VIDEO_FPS = 50, 25
BAND_LOWER_S, BAND_RELEASE_S, READY_S = (1.0, 3.0), 4.0, 5.0     # seconds after first controller command
STAND_PELVIS_Z = 0.76
HAND_KEYS = ("right_wrist", "left_wrist", "right_hand", "left_hand")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--rollout", type=int, default=0)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--max-record-s", type=float, default=40.0)
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--state-port", type=int, default=0,
                    help="closed-loop mode: publish the robot's own qpos (proprioception only) on 127.0.0.1:<port>")
    ap.add_argument("--mjpeg-port", type=int, default=0,
                    help="real-time mode: also serve the rendered view as MJPEG on 127.0.0.1:<port>/g1.mjpg")
    a = ap.parse_args()
    run = Path(a.run_dir)
    run.mkdir(parents=True, exist_ok=True)
    tag = f"seed{a.seed}_r{a.rollout}"
    scene_xml = run / f"scene_seed{a.seed}.xml"
    write_scene(os.getcwd(), scene_xml, a.seed)

    from gear_sonic.utils.mujoco_sim.base_sim import BaseSimulator
    from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
    from gear_sonic.utils.mujoco_sim.simulator_factory import init_channel

    cfg = SimLoopConfig(enable_offscreen=False, enable_onscreen=False)
    wbc = cfg.load_wbc_yaml()
    wbc["ENV_NAME"] = cfg.env_name
    wbc["ROBOT_SCENE"] = str(scene_xml.resolve())       # absolute path: pathlib join keeps it as is
    init_channel(config=wbc)
    sim = BaseSimulator(config=wbc, env_name=cfg.env_name, onscreen=False, offscreen=False)
    env = sim.sim_env
    m, d = env.mj_model, env.mj_data
    fell = {"robot": False}

    def check_fall():                                    # upstream resets the scene here
        env.fall = bool(d.qpos[2] < 0.2)
        fell["robot"] |= bool(d.qpos[2] < 0.45)
    env.check_fall = check_fall

    B = mujoco.mjtObj.mjOBJ_BODY
    block = mujoco.mj_name2id(m, B, "block")
    pelvis = mujoco.mj_name2id(m, B, "pelvis")
    env_geoms = {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n) for n in
                 ["table"] + ["tray_floor"] + [f"tray_wall{i}" for i in range(4)]}
    robot_bodies = {b for b in range(1, m.nbody) if b != block}
    hand_bodies = {b for b in robot_bodies if any(k in mujoco.mj_id2name(m, B, b) for k in HAND_KEYS)}
    rhand_tip = mujoco.mj_name2id(m, B, "right_wrist_yaw_link")
    block_qadr = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "block_free")]

    def contacts():
        hand_block = other_block = forbidden = False
        for c in d.contact[:d.ncon]:
            for ga, gb in ((c.geom1, c.geom2), (c.geom2, c.geom1)):
                ba, bb = m.geom_bodyid[ga], m.geom_bodyid[gb]
                if ba in robot_bodies and bb == block:
                    if ba in hand_bodies:
                        hand_block = True
                    else:
                        other_block = True
                if ba in robot_bodies and ba not in hand_bodies and (gb in env_geoms):
                    forbidden = True
        return hand_block, hand_block or other_block, other_block or forbidden

    renderer = writer = hub = state_pub = None
    if a.state_port:
        import zmq
        state_pub = zmq.Context.instance().socket(zmq.PUB)
        state_pub.bind(f"tcp://127.0.0.1:{a.state_port}")
    if not a.no_video:
        writer = Mp4Writer(run / f"{tag}.mp4", 1280, 480, VIDEO_FPS)   # third-person | close-up
    if a.mjpeg_port:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "live"))
        from hub import Hub
        hub = Hub(a.mjpeg_port)
    if writer is not None or hub is not None:
        renderer = mujoco.Renderer(m, 480, 640)
    bridge = env.unitree_bridge
    band = getattr(env, "elastic_band", None)
    dt = env.sim_dt
    steps_log, steps_vid = round(1 / (LOG_HZ * dt)), round(1 / (VIDEO_FPS * dt))
    t_ctrl = t_release = None
    states, n = [], 0
    diag_t, diag_q = [], []                              # full robot qpos at the log rate (diagnostics only)
    hb_any = forb_latched = fallen_latched = False
    hb_interval = touch_interval = False
    stop_file, ready_file, go_file = run / f"{tag}.stop", run / f"{tag}.ready", run / f"{tag}.go"
    t_go = None
    wall0 = time.time()
    try:
        while True:
            t0 = time.monotonic()
            env.sim_step()
            n += 1
            if t_ctrl is None:
                if any(bridge.low_cmd.motor_cmd[i].kp > 0 for i in range(bridge.num_body_motor)):
                    t_ctrl = d.time
                    print(f"[runner] controller active at sim t={d.time:.2f}", flush=True)
                elif time.time() - wall0 > 300:
                    raise SystemExit("controller never started")
            else:
                el = d.time - t_ctrl
                if band is not None and band.enable:
                    lo, hi = BAND_LOWER_S
                    frac = min(max((el - lo) / (hi - lo), 0.0), 1.0)
                    band.length = -frac * (band.point[2] - STAND_PELVIS_Z)
                    if el >= BAND_RELEASE_S:
                        band.enable = False
                        t_release = d.time
                        print(f"[runner] band released at sim t={d.time:.2f}", flush=True)
                if el >= READY_S and not ready_file.exists():
                    ready_file.write_text("ready\n")
            if state_pub is not None and n % steps_log == 0:       # robot joints + pelvis pose only, no scene objects
                state_pub.send(np.ascontiguousarray(d.qpos[:block_qadr], dtype=np.float64).tobytes())
            if t_release is not None:
                hb, rb, forb = contacts()
                hb_interval |= hb
                touch_interval |= rb
                hb_any |= hb
                forb_latched |= forb
                bpos = d.xpos[block]
                fallen_latched |= bool(bpos[2] < TABLE_TOP_Z - 0.1) or fell["robot"]
                if n % steps_log == 0:
                    if t_go is None and go_file.exists():
                        t_go = d.time - t_release        # streamer starts the motion (alignment only)
                    vel = np.zeros(6)
                    mujoco.mj_objectVelocity(m, d, B, block, vel, 0)
                    states.append({"t_s": round(d.time - t_release, 4), "object_xyz": bpos.tolist(),
                                   "object_velocity": vel[3:].tolist(), "released": not touch_interval,
                                   "forbidden_collision": forb_latched, "fallen": fallen_latched,
                                   "hand_block_contact": hb_interval, "pelvis_xyz": d.xpos[pelvis].tolist(),
                                   "right_wrist_xyz": d.xpos[rhand_tip].tolist()})
                    hb_interval = touch_interval = False
                    diag_t.append(d.time - t_release)
                    diag_q.append(d.qpos[:block_qadr].copy())
                done = stop_file.exists() or (d.time - t_release) > a.max_record_s or fell["robot"]
                if done and len(states) >= 2:
                    break
            if renderer is not None and (t_release is not None or hub is not None) and n % steps_vid == 0:
                frame = []
                for cam in ("third_person", "closeup"):
                    renderer.update_scene(d, camera=cam)
                    frame.append(renderer.render())
                frame = np.concatenate(frame, axis=1)
                if writer is not None and t_release is not None:
                    writer.write(frame)
                if hub is not None:
                    hub.put_jpeg("g1", np.ascontiguousarray(frame[::2, ::2]))   # half size for the tunnel
            sleep = dt - (time.monotonic() - t0)
            if sleep > 0:
                time.sleep(sleep)
    finally:
        if writer is not None:
            writer.close()
        if renderer is not None:
            renderer.close()
    rt = (time.time() - wall0) / max(d.time, 1e-6)
    ep = {"seed": a.seed, "rollout": a.rollout, "block_xy_initial": sample_block_xy(a.seed).tolist(),
          "goal_xyz": goal_xyz().tolist(), "block_half": BLOCK_HALF, "robot_fell": fell["robot"],
          "any_hand_block_contact": hb_any, "t_go_s": t_go, "wall_per_sim_s": rt,
          "video": f"{tag}.mp4" if writer is not None else None, "states": states}
    np.savez_compressed(run / f"{tag}.diag.npz", t=np.array(diag_t), qpos=np.array(diag_q),
                        qpos_names=np.array([m.joint(j).name for j in range(m.njnt) if m.jnt_qposadr[j] < block_qadr]))
    (run / f"{tag}.episode.json").write_text(json.dumps(ep))
    print(f"[runner] wrote {tag}: {len(states)} states, robot_fell={fell['robot']}, "
          f"hand_contact={hb_any}, wall/sim={rt:.2f}", flush=True)
    os._exit(0)                                          # DDS threads otherwise keep the process alive


if __name__ == "__main__":
    main()
