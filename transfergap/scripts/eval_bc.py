"""Closed-loop evaluation of a behaviour-cloned policy in the MuJoCo scene, scored by the SAME scorer as every other result.

    python scripts/eval_bc.py --ckpt policy_vision.pt --robot ur5e --seeds 6000-6059 --out OUT.json --workers 12
The policy sees what it was trained on (vision: images + joint positions; lowdim: joint positions + block offset + time) and sets the joint
position targets and the gripper command at 25 Hz; no scripted controller is involved. Episodes last 8.56 s like the demonstrations.
Also runs the scripted fix-stack on the same seeds as a reference.
"""
import argparse
import json
import math
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

FIXES = ("speed_cap_3", "look_again", "touch_probe_calibration", "speed_cap_2", "safe_path_v2")
T_TICKS = 856
SIZE = (96, 128)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - h) / d, 3), round((c + h) / d, 3)]


def policy_episode(a):
    ckpt, robot, seed, demo, exec_mode, video_dir, record_dir, bh, nd = a
    import mujoco
    import torch
    from train_bc import K, Net
    from transfergap.metrics import score_episode
    from transfergap.sim.rollout import CTRL_HZ, TASK, make_camera, make_renderer, render_views
    from transfergap.sim.scene import Scene, sample_block_xy
    torch.set_num_threads(1)
    ck = torch.load(ckpt, map_location="cpu")
    st, mode = ck["stats"], ck["mode"]
    net = Net(mode, qdim=ck["qdim"])
    net.load_state_dict(ck["model"])
    net.eval()
    from transfergap.sim.scene import BLOCK_HALF, sample_distractors
    if bh == "mixed":
        from mixed_cfg import cfg
        bh, nd = cfg(seed)
    bh = bh or BLOCK_HALF
    dis = sample_distractors(seed, nd, sample_block_xy(seed), bh) if nd else ()
    scene = Scene(seed, robot, bh, 0.0, dis)
    m, d = scene.model, scene.data
    sub = round(1 / (m.opt.timestep * CTRL_HZ))
    nu = int(m.nu)
    renderer = make_renderer(scene, SIZE) if mode == "vision" else None
    cams = [make_camera(c) for c in ("third_person", "wrist")] if mode == "vision" else None
    off = (np.asarray(sample_block_xy(seed), np.float32) - np.array([0.45, -0.12], np.float32)) * 30.0
    qm, qs = np.array(st["q_mean"][:6], np.float32), np.array(st["q_std"][:6], np.float32)
    am, asd = np.array(st["a_mean"], np.float32), np.array(st["a_std"], np.float32)
    vr = make_renderer(scene, (360, 480)) if video_dir else None
    vcam = make_camera("third_person") if video_dir else None
    vframes = []
    d.ctrl[:6] = d.qpos[scene.arm_qadr]
    d.ctrl[6:nu] = 0.0
    rec = {"img": [], "q": [], "pg": []}
    act, prev_g, states, chunks, pj = np.array(d.ctrl[:7], np.float32), 0.0, [], [], -1
    forbidden = fallen = touching = False
    for tick in range(T_TICKS):
        if tick % 4 == 0:
            pj += 1
            s = np.concatenate([(d.qpos[scene.arm_qadr].astype(np.float32) - qm) / qs, [prev_g]]).astype(np.float32)
            if mode == "lowdim":
                s = np.concatenate([s, off, [tick / T_TICKS]]).astype(np.float32)
            if ck.get("multi"):
                oh = np.zeros(3, np.float32)
                oh[("ur5e", "ur10e", "kairos").index(robot)] = 1.0
                s = np.concatenate([s, oh]).astype(np.float32)
            raw_img = render_views(renderer, d, cams) if mode == "vision" else None
            img = torch.from_numpy(raw_img)[None] if mode == "vision" else None
            if record_dir:                                       # DAgger: the state the POLICY visited (image, joints, its own previous gripper command)
                rec["img"].append(raw_img.copy())
                rec["q"].append(d.qpos[scene.arm_qadr].astype(np.float32))
                rec["pg"].append(prev_g)
            if exec_mode == "open4" and pj % 4 != 1 and chunks:
                pass                                             # keep executing the stored chunk (open loop for 4 policy steps)
            else:
                with torch.no_grad():
                    ch = net(img, torch.from_numpy(s)[None])[0].numpy() * asd + am   # chunk[0] is the command that PRODUCED this observation; chunk[1] the next one
                chunks.append((pj, ch))
            if exec_mode == "first":
                act = chunks[-1][1][1].copy()
            elif exec_mode == "open4":
                j, ch0 = chunks[-1]
                act = ch0[min(1 + pj - j, ch0.shape[0] - 1)].copy()
            else:                                                # temporal ensemble over the chunks that already cover this step
                num, den = 0.0, 0.0
                for j, ch0 in chunks[-8:]:
                    k = 1 + pj - j
                    if k < ch0.shape[0]:
                        w = np.exp(-0.15 * (pj - j))
                        num, den = num + w * ch0[k], den + w
                act = (num / den) if den else chunks[-1][1][1].copy()
            act[6] = float(np.clip(act[6], 0, 255))
            prev_g = act[6] / 255.0
        d.ctrl[:7] = act[:7]                                 # the mobile base (if any) keeps its parked set-point
        if vr is not None and tick % 4 == 0:
            vr.update_scene(d, camera="third_person")
            vframes.append(vr.render().copy())
        for _ in range(sub):
            mujoco.mj_step(m, d)
            f, t = scene.contact_flags()
            pos = scene.block_pos()
            forbidden |= f
            touching = t
            fallen |= bool(pos[2] < 0.0)
            forbidden |= bool(np.hypot(*(pos[:2] - [0.3, 0])) > 0.6 and pos[2] < 0.05)
        if (tick + 1) % (CTRL_HZ // 50) == 0:
            states.append({"t_s": round(d.time, 6), "object_xyz": scene.block_pos().tolist(), "object_velocity": scene.block_vel().tolist(),
                           "released": bool(not touching), "forbidden_collision": bool(forbidden), "fallen": bool(fallen), "phase": "policy"})
    ep = {"schema_version": 1, "source": "simulation", "trial_id": f"seed{seed}", "demo_id": "bc_policy", "scene_id": f"block_to_tray_seed{seed}", "seed": int(seed),
          "robot": scene.robot_label, "method": f"bc_{mode}", "sensor": "rgb" if mode == "vision" else "oracle", "protocol_id": "block_to_tray_v1", "frame_id": "world",
          "units": "m", "task": {"goal_xyz": scene.goal_xyz.tolist(), **TASK}, "states": states, "perturbation": {}, "video": None}
    sc = score_episode(ep)
    if record_dir and rec["img"]:
        nom = np.load(Path(record_dir) / f"nominal_{robot}_{seed}.npz")["a"]       # the scripted run of this seed: the expert's target at each time step
        n = min(len(rec["img"]), len(nom))
        np.savez_compressed(Path(record_dir) / f"dagger_{robot}_{seed}.npz", img=np.stack(rec["img"][:n]), q=np.stack(rec["q"][:n]),
                            pg=np.array(rec["pg"][:n], np.float32), a=nom[:n].astype(np.float32), ok=np.array(bool(sc["success"])))
    if vframes:
        import subprocess
        h, w = vframes[0].shape[:2]
        out = str(Path(video_dir) / f"{robot}_seed{seed}_{'success' if sc['success'] else 'fail'}.mp4")
        pr = subprocess.Popen(["/usr/bin/ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", "25", "-i", "-",
                               "-pix_fmt", "yuv420p", "-vcodec", "libx264", "-crf", "24", out], stdin=subprocess.PIPE)
        for fr in vframes:
            pr.stdin.write(np.ascontiguousarray(fr).tobytes())
        pr.stdin.close()
        pr.wait()
    return {"seed": seed, "success": bool(sc["success"]), "reasons": sc.get("failure_reasons")}


def scripted_episode(a):
    robot, seed, demo, bh, nd = a
    from transfergap.metrics import score_episode
    from transfergap.sim import errors_demo as E
    from transfergap.sim.rollout import run_episode
    from transfergap.sim.scene import BLOCK_HALF, sample_block_xy, sample_distractors
    if bh == "mixed":
        from mixed_cfg import cfg
        bh, nd = cfg(seed)
    bh = bh or BLOCK_HALF
    dis = sample_distractors(seed, nd, sample_block_xy(seed), bh) if nd else ()
    spec = E.parse_demo_spec(demo)
    pert, oracle, _ = E.build_perturbation(spec, seed, "full", None, FIXES)
    return {"seed": seed, "success": bool(score_episode(run_episode(seed, pert, oracle=oracle, robot=robot, block_half=bh, distractors=dis))["success"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--robot", default="ur5e")
    ap.add_argument("--seeds", default="6000-6059")
    ap.add_argument("--demo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--skip-scripted", action="store_true")
    ap.add_argument("--video-dir", default=None)
    ap.add_argument("--mixed", action="store_true", help="per-seed random cube size and distractors, same distribution as gen_bc_data --mixed")
    ap.add_argument("--block-half", type=float, default=None, help="cube half edge in m (default 0.02); out-of-distribution test")
    ap.add_argument("--n-distractors", type=int, default=0, help="static distractor objects on the table; out-of-distribution test")
    ap.add_argument("--record-dir", default=None, help="DAgger: save the visited states with the nominal (scripted) targets as labels; needs nominal_<robot>_<seed>.npz files here")
    ap.add_argument("--video-n", type=int, default=4, help="record the first N seeds")
    ap.add_argument("--exec", default="first", choices=["first", "open4", "ensemble"], help="how the predicted chunk is executed")
    a = ap.parse_args()
    lo, hi = map(int, a.seeds.split("-"))
    seeds = list(range(lo, hi + 1))
    ctx = mp.get_context("spawn")
    with ctx.Pool(a.workers) as pool:
        pol = pool.map(policy_episode, [(a.ckpt, a.robot, s, a.demo, a.exec, a.video_dir if (a.video_dir and s < lo + a.video_n) else None, a.record_dir, "mixed" if a.mixed else a.block_half, a.n_distractors) for s in seeds], chunksize=1)
        scr = [] if a.skip_scripted else pool.map(scripted_episode, [(a.robot, s, a.demo, "mixed" if a.mixed else a.block_half, a.n_distractors) for s in seeds], chunksize=1)
    k = sum(r["success"] for r in pol)
    res = {"block_half": a.block_half, "n_distractors": a.n_distractors, "exec": a.exec, "ckpt": a.ckpt, "robot": a.robot, "seeds": [lo, hi], "n": len(pol), "policy_success": k, "policy_ci95": wilson(k, len(pol)),
           "scripted_success": sum(r["success"] for r in scr) if scr else None, "failure_reasons": {}, "per_seed": pol}
    for r in pol:
        for x in (r["reasons"] or []):
            res["failure_reasons"][x] = res["failure_reasons"].get(x, 0) + 1
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k_: v for k_, v in res.items() if k_ != "per_seed"}))


if __name__ == "__main__":
    main()
