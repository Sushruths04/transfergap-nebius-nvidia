"""GR00T-format (LeRobot v2.0 + meta/modality.json) dataset from the scripted fix-stack rollouts of ONE human demonstration, one robot.

Two 224x224 camera videos per episode (`front` = third-person, `wrist`), 25 Hz; observation.state = 6 joint positions + last gripper command (0..1);
action = 6 joint position targets + gripper command (0..1). Only physics-verified successes are kept. Mapped onto the built-in `so100_dualcam`
data config of Isaac-GR00T N1.5 (state.single_arm / state.gripper, action.single_arm / action.gripper, video.front / video.wrist).

    MUJOCO_GL=egl python scripts/gen_groot_data.py --demo demo.npz --robot ur10e --seeds 2000-2199 --out DIR --workers 14 [--mixed]
"""
import argparse
import json
import multiprocessing as mp
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

FIXES = ("speed_cap_3", "look_again", "touch_probe_calibration", "speed_cap_2", "safe_path_v2")
SIZE = (224, 224)
TASK = "pick up the red cube and place it in the green tray"


CLOSE_CAM = {"lookat": [0.45, 0.05, 0.08], "distance": 0.95, "azimuth": 129.5, "elevation": -25.0}     # closer front view: the cube is about twice as large in the image


def front_cam():
    """TG_FRONT_CAM=closeup selects the closer front camera; default is the usual third-person camera."""
    import os
    from transfergap.sim.rollout import make_camera
    return make_camera(CLOSE_CAM if os.environ.get("TG_FRONT_CAM") == "closeup" else "third_person")


def mp4(path, frames):
    h, w = frames[0].shape[:2]
    p = subprocess.Popen(["/usr/bin/ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", "25", "-i", "-",
                          "-pix_fmt", "yuv420p", "-vcodec", "libx264", "-crf", "20", str(path)], stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(np.ascontiguousarray(f).tobytes())
    p.stdin.close()
    p.wait()


def job(a):
    demo, robot, seed, tmp, mixed = a
    import pyarrow as pa
    import pyarrow.parquet as pq
    from transfergap.metrics import score_episode
    from transfergap.sim import errors_demo as E
    from transfergap.sim.rollout import make_camera, make_renderer, run_episode
    spec = E.parse_demo_spec(demo)
    pert, oracle, _ = E.build_perturbation(spec, seed, "full", None, FIXES)
    st = {"r": None, "front": [], "wrist": [], "q": [], "a": []}

    def cb(scene, d, tick):
        if tick % 4:
            return
        if st["r"] is None:
            st["r"] = make_renderer(scene, SIZE)
            st["cams"] = [front_cam(), make_camera("wrist")]
            st["arm"] = scene.arm_qadr
        for key, cam in zip(("front", "wrist"), st["cams"]):
            st["r"].update_scene(d, camera=cam)
            st[key].append(st["r"].render().copy())
        st["q"].append(d.qpos[st["arm"]].astype(np.float32).copy())
        st["a"].append(d.ctrl[:7].astype(np.float32).copy())

    kw = {}
    if mixed:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from mixed_cfg import cfg
        from transfergap.sim.scene import sample_block_xy, sample_distractors
        bh, nd = cfg(seed)
        kw = {"block_half": bh, "distractors": sample_distractors(seed, nd, sample_block_xy(seed), bh) if nd else ()}
    ep = run_episode(seed, pert, oracle=oracle, robot=robot, obs_cb=cb, **kw)
    if not score_episode(ep)["success"]:
        return (seed, 0)
    q, act = np.stack(st["q"]), np.stack(st["a"]).copy()
    act[:, 6] /= 255.0
    state = np.concatenate([q, np.concatenate([[0.0], act[:-1, 6]])[:, None]], 1).astype(np.float32)     # last gripper command as the gripper state
    T = len(q)
    mp4(Path(tmp) / f"{seed}_front.mp4", st["front"])
    mp4(Path(tmp) / f"{seed}_wrist.mp4", st["wrist"])
    pq.write_table(pa.table({"observation.state": list(state), "action": list(act.astype(np.float32)), "timestamp": (np.arange(T) / 25.0).tolist()}), Path(tmp) / f"{seed}.parquet")
    return (seed, T)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--robot", default="ur10e")
    ap.add_argument("--seeds", default="2000-2199")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--mixed", action="store_true")
    a = ap.parse_args()
    import pyarrow as pa
    import pyarrow.parquet as pq
    lo, hi = map(int, a.seeds.split("-"))
    out = Path(a.out)
    tmp = out / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    with mp.get_context("spawn").Pool(a.workers) as pool:
        res = pool.map(job, [(a.demo, a.robot, s, str(tmp), a.mixed) for s in range(lo, hi + 1)], chunksize=1)
    good = [(s, T) for s, T in res if T]
    for d in ("data/chunk-000", "videos/chunk-000/observation.images.front", "videos/chunk-000/observation.images.wrist", "meta"):
        (out / d).mkdir(parents=True, exist_ok=True)
    gi, eps = 0, []
    for i, (seed, T) in enumerate(good):
        t = pq.read_table(tmp / f"{seed}.parquet").to_pydict()
        t.update({"annotation.human.task_description": [0] * T, "task_index": [0] * T, "episode_index": [i] * T, "index": list(range(gi, gi + T))})
        pq.write_table(pa.table(t), out / "data/chunk-000" / f"episode_{i:06d}.parquet")
        for cam in ("front", "wrist"):
            shutil.move(str(tmp / f"{seed}_{cam}.mp4"), out / f"videos/chunk-000/observation.images.{cam}" / f"episode_{i:06d}.mp4")
        eps.append({"episode_index": i, "tasks": [TASK], "length": T, "seed": seed})
        gi += T
    shutil.rmtree(tmp)
    vinfo = {"video.fps": 25.0, "video.height": 224, "video.width": 224, "video.channels": 3, "video.codec": "h264", "video.pix_fmt": "yuv420p", "video.is_depth_map": False, "has_audio": False}
    feat = {"observation.images.front": {"dtype": "video", "shape": [224, 224, 3], "names": ["height", "width", "channel"], "video_info": vinfo},
            "observation.images.wrist": {"dtype": "video", "shape": [224, 224, 3], "names": ["height", "width", "channel"], "video_info": vinfo},
            "observation.state": {"dtype": "float32", "shape": [7], "names": [f"j{k}" for k in range(6)] + ["gripper"]},
            "action": {"dtype": "float32", "shape": [7], "names": [f"j{k}" for k in range(6)] + ["gripper"]},
            "timestamp": {"dtype": "float64", "shape": [1]}, "annotation.human.task_description": {"dtype": "int64", "shape": [1]},
            "task_index": {"dtype": "int64", "shape": [1]}, "episode_index": {"dtype": "int64", "shape": [1]}, "index": {"dtype": "int64", "shape": [1]}}
    info = {"codebase_version": "v2.0", "robot_type": a.robot, "total_episodes": len(good), "total_frames": gi, "total_tasks": 1, "total_videos": 2 * len(good), "total_chunks": 1,
            "chunks_size": 1000, "fps": 25.0, "splits": {"train": f"0:{len(good)}"}, "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
            "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4", "features": feat}
    (out / "meta/info.json").write_text(json.dumps(info, indent=1))
    (out / "meta/episodes.jsonl").write_text("".join(json.dumps(e) + "\n" for e in eps))
    (out / "meta/tasks.jsonl").write_text(json.dumps({"task_index": 0, "task": TASK}) + "\n")
    (out / "meta/modality.json").write_text(json.dumps({"state": {"single_arm": {"start": 0, "end": 6}, "gripper": {"start": 6, "end": 7}},
                                                         "action": {"single_arm": {"start": 0, "end": 6}, "gripper": {"start": 6, "end": 7}},
                                                         "video": {"front": {"original_key": "observation.images.front"}, "wrist": {"original_key": "observation.images.wrist"}},
                                                         "annotation": {"human.task_description": {"original_key": "task_index"}}}, indent=1))
    print("episodes", len(good), "frames", gi)


if __name__ == "__main__":
    main()
