"""Verified data engine, step 3: render camera video for each verified episode of scripts/export_dataset.py (GPU/EGL, TG_HQ optional).
Re-runs the same seed with the same fixes (the simulation is deterministic, checked: identical outcomes across reruns), so the frames match the
saved joint traces; writes one mp4 per episode (third_person + wrist camera side by side) and a manifest.

    MUJOCO_GL=egl python scripts/render_dataset.py --demo demo.npz --index runs/dataset_v1/index.json --out DIR --workers 8
"""
import argparse
import json
import multiprocessing as mp
from pathlib import Path

FIXES = ("speed_cap_3", "look_again", "touch_probe_calibration", "speed_cap_2", "safe_path_v2")


def job(a):
    demo, name, robot, seed, out = a
    from transfergap.metrics import score_episode
    from transfergap.sim import errors_demo as E
    from transfergap.sim.rollout import run_episode
    spec = E.parse_demo_spec(demo)
    pert, oracle, _ = E.build_perturbation(spec, seed, "full", None, FIXES)
    p = Path(out) / f"{name}.mp4"
    ep = run_episode(seed, pert, video_path=str(p), oracle=oracle, robot=robot, cameras=("third_person", "wrist"), size=(240, 320))
    return {"name": name, "video": p.name, "success": bool(score_episode(ep)["success"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    idx = json.loads(Path(a.index).read_text())
    jobs = [(a.demo, e["name"], e["robot"], e["seed"], a.out) for e in idx["episodes"] if e["success"]]
    with mp.get_context("spawn").Pool(a.workers) as pool:
        rows = pool.map(job, jobs, chunksize=1)
    (Path(a.out) / "manifest.json").write_text(json.dumps(rows, indent=1))
    print("rendered", len(rows), "replayed successes", sum(r["success"] for r in rows))


if __name__ == "__main__":
    main()
