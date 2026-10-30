"""Render the object-size story: the same seed at several cube sizes, raw copy vs frozen fix stack (GPU/EGL, higher resolution).

    MUJOCO_GL=egl python -m transfergap.sim.object_scale_render --demo demo.npz --out DIR --robots ur5e ur10e --halves 0.015,0.025,0.035 --seed 1000
A single seed per cell is an illustration; the evidence is the 60-seed counts in results/object_scale_v1.
"""
import argparse
import json
from pathlib import Path

from ..metrics import score_episode
from . import errors_demo as E
from .rollout import run_episode

FIXES = ("speed_cap_3", "look_again", "touch_probe_calibration", "speed_cap_2", "safe_path_v2")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--robots", nargs="+", default=["ur5e", "ur10e"])
    ap.add_argument("--halves", default="0.015,0.025,0.035")
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--size", nargs=2, type=int, default=[720, 960])
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    spec = E.parse_demo_spec(a.demo)
    rows = {}
    for robot in a.robots:
        for h in [float(x) for x in a.halves.split(",")]:
            for cond, fx in (("raw", ()), ("stack", FIXES)):
                pert, oracle, _ = E.build_perturbation(spec, a.seed, "full", None, fx)
                p = out / f"{robot}_{2 * h * 100:.0f}cm_{cond}_seed{a.seed}.mp4"
                ep = run_episode(a.seed, pert, video_path=str(p), label=cond, oracle=oracle, condition=cond, robot=robot,
                                 cameras=("third_person",), size=tuple(a.size), block_half=h)
                sc = score_episode(ep)
                rows[p.name] = {"success": bool(sc["success"]), "failure_reasons": sc.get("failure_reasons")}
                print(p.name, rows[p.name], flush=True)
    (out / "render_report.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
