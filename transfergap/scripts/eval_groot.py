"""Closed-loop evaluation of a fine-tuned GR00T-N1.5 policy in the MuJoCo scene, scored by the same scorer as every other result.

Run in the gr00t env (needs mujoco, the transfergap package on PYTHONPATH, EGL):
    python scripts/eval_groot.py --ckpt DIR --robot ur10e --seeds 6000-6029 --out OUT.json [--mixed | --block-half H --n-distractors N]
Per 25 Hz step: render front (third-person) + wrist 224x224 images, send them with the joint positions and the last gripper command to the policy,
get a 16-step action chunk (6 joint targets + gripper 0..1), execute with the same temporal ensemble as eval_bc.py (chunk[1] is the next command).
Sequential (one GPU policy); prints a progress line per episode.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
T_TICKS = 856
SIZE = (224, 224)
TASK = "pick up the red cube and place it in the green tray"


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - h) / d, 3), round((c + h) / d, 3)]


CLOSE_CAM = {"lookat": [0.45, 0.05, 0.08], "distance": 0.95, "azimuth": 129.5, "elevation": -25.0}     # closer front view: the cube is about twice as large in the image


def front_cam():
    """TG_FRONT_CAM=closeup selects the closer front camera; default is the usual third-person camera."""
    import os
    from transfergap.sim.rollout import make_camera
    return make_camera(CLOSE_CAM if os.environ.get("TG_FRONT_CAM") == "closeup" else "third_person")


def codec(img):
    """h264 yuv420p crf 20 round trip of one frame, like the training videos (gen_groot_data.py)."""
    import subprocess
    h, w = img.shape[:2]
    enc = subprocess.run(["/usr/bin/ffmpeg", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-i", "-", "-pix_fmt", "yuv420p", "-vcodec", "libx264",
                          "-crf", "20", "-frames:v", "1", "-f", "h264", "-"], input=np.ascontiguousarray(img).tobytes(), capture_output=True).stdout
    dec = subprocess.run(["/usr/bin/ffmpeg", "-loglevel", "error", "-f", "h264", "-i", "-", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], input=enc, capture_output=True).stdout
    return np.frombuffer(dec, np.uint8).reshape(h, w, 3).copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--robot", default="ur10e")
    ap.add_argument("--seeds", default="6000-6029")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mixed", action="store_true")
    ap.add_argument("--block-half", type=float, default=None)
    ap.add_argument("--n-distractors", type=int, default=0)
    ap.add_argument("--save-frames", default=None, help="dir: save every 4th front image of each episode as PNG (debug)")
    ap.add_argument("--codec", action="store_true", help="pass each frame through the training-data codec (h264 yuv420p crf 20, one intra frame)")
    ap.add_argument("--diag", action="store_true", help="print the pinch-to-cube offset when the gripper command first exceeds 0.5 and the closest approach")
    ap.add_argument("--look", type=int, default=0, help="execute chunk[look] of the latest chunk (no ensemble) instead of the ensemble; 0 = off")
    ap.add_argument("--gain", type=float, default=1.0, help="scale the joint step toward the predicted target: s + gain*(target - s)")
    ap.add_argument("--exec", default="ensemble", choices=["ensemble", "first"])
    a = ap.parse_args()
    import mujoco
    from gr00t.experiment.data_config import load_data_config
    from gr00t.model.policy import Gr00tPolicy
    from transfergap.metrics import score_episode
    from transfergap.sim.rollout import CTRL_HZ, TASK as TASKCFG, make_camera, make_renderer
    from transfergap.sim.scene import BLOCK_HALF, Scene, sample_block_xy, sample_distractors
    dc = load_data_config("so100_dualcam")
    policy = Gr00tPolicy(model_path=a.ckpt, embodiment_tag="new_embodiment", modality_config=dc.modality_config(), modality_transform=dc.transform(), device="cuda")
    lo, hi = map(int, a.seeds.split("-"))
    results = []
    for seed in range(lo, hi + 1):
        t0 = time.time()
        bh, nd = a.block_half, a.n_distractors
        if a.mixed:
            from mixed_cfg import cfg
            bh, nd = cfg(seed)
        bh = bh or BLOCK_HALF
        dis = sample_distractors(seed, nd, sample_block_xy(seed), bh) if nd else ()
        scene = Scene(seed, a.robot, bh, 0.0, dis)
        m, d = scene.model, scene.data
        sub = round(1 / (m.opt.timestep * CTRL_HZ))
        renderer = make_renderer(scene, SIZE)
        cams = [front_cam(), make_camera("wrist")]
        d.ctrl[:6] = d.qpos[scene.arm_qadr]
        d.ctrl[6] = 0.0
        act, prev_g, states, chunks, pj = np.array(d.ctrl[:7], np.float32), 0.0, [], [], -1
        act[6] = 0.0
        forbidden = fallen = touching = False
        closed_at, mind, maxz = None, 9.0, 0.0
        for tick in range(T_TICKS):
            if tick % 4 == 0:
                pj += 1
                imgs = []
                for cam in cams:
                    renderer.update_scene(d, camera=cam)
                    im = renderer.render().copy()
                    imgs.append(codec(im) if a.codec else im)
                obs = {"video.front": imgs[0][None], "video.wrist": imgs[1][None],
                       "state.single_arm": d.qpos[scene.arm_qadr][None].astype(np.float64), "state.gripper": np.array([[prev_g]], np.float64),
                       "annotation.human.task_description": [TASK]}
                if a.save_frames and pj % 10 == 0:
                    import imageio
                    Path(a.save_frames).mkdir(parents=True, exist_ok=True)
                    imageio.imwrite(f"{a.save_frames}/s{seed}_p{pj:03d}.png", np.concatenate(imgs, 1))
                res = policy.get_action(obs)
                ch = np.concatenate([np.asarray(res["action.single_arm"]), np.asarray(res["action.gripper"]).reshape(-1, 1)], 1)      # (16, 7), gripper 0..1
                chunks.append((pj, ch))
                if a.look:
                    act = chunks[-1][1][min(a.look, 15)].copy()
                elif a.exec == "first":
                    act = chunks[-1][1][1].copy()
                else:
                    num, den = 0.0, 0.0
                    for j, c0 in chunks[-8:]:
                        k = 1 + pj - j
                        if k < c0.shape[0]:
                            w = np.exp(-0.15 * (pj - j))
                            num, den = num + w * c0[k], den + w
                    act = (num / den) if den else chunks[-1][1][1].copy()
                if a.gain != 1.0:
                    cur = d.qpos[scene.arm_qadr]
                    act[:6] = cur + a.gain * (act[:6] - cur)
                prev_g = float(np.clip(act[6], 0, 1))
                if a.save_frames and pj % 5 == 0:
                    print(f"  pj={pj} grip_cmd={prev_g:.2f} chunk_grip={np.round(ch[::4,6],2).tolist()} q={np.round(d.qpos[scene.arm_qadr],2).tolist()}", flush=True)
                act[6] = prev_g * 255.0
            if a.diag:
                off = scene.block_pos() - d.site_xpos[scene.pinch_site]
                mind, maxz = min(mind, float(np.linalg.norm(off))), max(maxz, float(scene.block_pos()[2]))
                if closed_at is None and act[6] > 127:
                    closed_at = (tick, np.round(off * 100, 1).tolist())
            d.ctrl[:7] = act[:7]
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
        renderer.close()
        ep = {"schema_version": 1, "source": "simulation", "trial_id": f"seed{seed}", "demo_id": "groot_n15", "scene_id": f"block_to_tray_seed{seed}", "seed": int(seed),
              "robot": scene.robot_label, "method": "groot_n15_finetuned", "sensor": "rgb", "protocol_id": "block_to_tray_v1", "frame_id": "world", "units": "m",
              "task": {"goal_xyz": scene.goal_xyz.tolist(), **TASKCFG}, "states": states, "perturbation": {}, "video": None}
        sc = score_episode(ep)
        results.append({"seed": seed, "success": bool(sc["success"]), "reasons": sc.get("failure_reasons"), "seconds": round(time.time() - t0, 1)})
        if a.diag:
            print(f"  DIAG seed {seed}: close at tick/offset_cm(block-pinch xyz) {closed_at}; closest approach {mind*100:.1f} cm; max block z {maxz:.3f}", flush=True)
        print(f"seed {seed} success={results[-1]['success']} ({results[-1]['seconds']} s)", flush=True)
        k = sum(r["success"] for r in results)
        Path(a.out).write_text(json.dumps({"ckpt": a.ckpt, "robot": a.robot, "exec": a.exec, "block_half": a.block_half, "n_distractors": a.n_distractors, "mixed": a.mixed,
                                           "n": len(results), "success": k, "ci95": wilson(k, len(results)), "per_seed": results}, indent=1))
    print("DONE", sum(r["success"] for r in results), "/", len(results))


if __name__ == "__main__":
    main()
