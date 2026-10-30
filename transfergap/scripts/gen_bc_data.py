"""Behaviour-cloning data from the verified data engine: scripted fix-stack episodes of ONE human demo, with per-step camera images.

For each (robot, seed): run the episode, and every 4th control tick (25 Hz) store third-person + wrist images (96x128 each, side by side),
the arm joint positions q (6) and the commanded action (6 joint targets + gripper 0..255). Only episodes the physics scorer calls successful
are kept. One npz per episode. Run with MUJOCO_GL=egl (render env).

    python scripts/gen_bc_data.py --demo demo.npz --robot ur5e --seeds 2000-2299 --out DIR --workers 14
"""
import argparse
import multiprocessing as mp
from pathlib import Path

import numpy as np

FIXES = ("speed_cap_3", "look_again", "touch_probe_calibration", "speed_cap_2", "safe_path_v2")
SIZE = (96, 128)


def job(a):
    demo, robot, seed, out, mixed = a
    from transfergap.metrics import score_episode
    from transfergap.sim import errors_demo as E
    from transfergap.sim.rollout import make_camera, make_renderer, render_views, run_episode
    spec = E.parse_demo_spec(demo)
    pert, oracle, _ = E.build_perturbation(spec, seed, "full", None, FIXES)
    st = {"r": None, "cams": None, "img": [], "q": [], "a": []}

    def cb(scene, d, tick):
        if tick % 4:
            return
        if st["r"] is None:
            st["r"] = make_renderer(scene, SIZE)
            st["cams"] = [make_camera(c) for c in ("third_person", "wrist")]
            st["arm"], st["nu"] = scene.arm_qadr, int(scene.model.nu)
        st["img"].append(render_views(st["r"], d, st["cams"]))
        st["q"].append(d.qpos[st["arm"]].copy())
        st["a"].append(d.ctrl[:7].copy())      # 6 arm joint targets + gripper; the mobile base (extra actuators after index 6) stays parked

    kw = {}
    if mixed:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from mixed_cfg import cfg
        from transfergap.sim.scene import sample_block_xy, sample_distractors
        bh, nd = cfg(seed)
        kw = {"block_half": bh, "distractors": sample_distractors(seed, nd, sample_block_xy(seed), bh) if nd else ()}
    ep = run_episode(seed, pert, oracle=oracle, robot=robot, obs_cb=cb, **kw)
    if not score_episode(ep)["success"]:
        return (seed, False)
    np.savez_compressed(Path(out) / f"{robot}_{seed}.npz", img=np.stack(st["img"]), q=np.stack(st["q"]).astype(np.float32), a=np.stack(st["a"]).astype(np.float32))
    return (seed, True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--robot", default="ur5e")
    ap.add_argument("--seeds", default="2000-2299")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--mixed", action="store_true", help="per-seed random cube size (3-7 cm) and 0 or 3 distractors (scripts/mixed_cfg.py)")
    a = ap.parse_args()
    lo, hi = map(int, a.seeds.split("-"))
    Path(a.out).mkdir(parents=True, exist_ok=True)
    with mp.get_context("spawn").Pool(a.workers) as pool:
        res = pool.map(job, [(a.demo, a.robot, s, a.out, a.mixed) for s in range(lo, hi + 1)], chunksize=1)
    print("episodes", len(res), "kept", sum(ok for _, ok in res))


if __name__ == "__main__":
    main()
