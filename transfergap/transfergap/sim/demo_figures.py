"""Style figure: the retargeted human hand path vs each robot's actual tool path (side and top views), for one
held-out seed, with no fix and with the adopted fixes. Analysis only (re-runs the episodes; uses logged poses).

    python -m transfergap.sim.demo_figures --demo runs/demos/pexels_8135753_notebook.npz \
        --fixes speed_cap_3,look_again,touch_probe_calibration --seed 1000 --out results/demo_style_figures
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ..demo.style import LEGS, robot_path
from ..metrics import score_episode
from . import errors_demo as E
from .rollout import run_episode
from .scene import Scene


def episode_paths(spec, seed, robot, base):
    pert, _, ref = E.build_perturbation(spec, seed, "full", None, base)
    ep = run_episode(seed, pert, robot=robot)
    S = ep["states"]
    block0 = np.asarray(S[0]["object_xyz"])
    human = robot_path(ref, block0 + ref["grasp_offset"], Scene(seed, robot).goal_xyz + ref["place_offset"])
    tool = {leg: np.array([s["tool_xyz"] for s in S if s["phase"] == leg]) for leg in LEGS}
    obj = np.array([s["object_xyz"] for s in S])
    return human, tool, obj, score_episode(ep)["success"]


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--fixes", default="")
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = E.parse_demo_spec(a.demo)
    fixes = tuple(x for x in a.fixes.split(",") if x)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    robots, settings = ("ur5e", "ur10e"), ((), fixes)
    fig, axes = plt.subplots(2, 4, figsize=(16, 7.5))
    colors = {"reach": "#1f77b4", "carry": "#d62728", "retreat": "#2ca02c"}
    meta = {}
    for j, (robot, base) in enumerate([(r, b) for r in robots for b in settings]):
        human, tool, obj, ok = episode_paths(spec, a.seed, robot, base)
        for i, (u, v, lab) in enumerate(((1, 2, "y (m)  vs  z (m), side view"), (0, 1, "x (m)  vs  y (m), top view"))):
            ax = axes[i, j]
            for leg in LEGS:
                ax.plot(human[leg][1][:, u], human[leg][1][:, v], "--", color=colors[leg], lw=1.5, alpha=0.8)
                if len(tool[leg]):
                    ax.plot(tool[leg][:, u], tool[leg][:, v], "-", color=colors[leg], lw=2.2)
            ax.plot(obj[:, u], obj[:, v], ":", color="k", lw=1.2)
            ax.set_xlabel(lab.split("  vs  ")[0])
            ax.set_ylabel(lab.split("  vs  ")[1].split(",")[0])
            ax.set_aspect("equal", adjustable="datalim")
            ax.grid(alpha=0.3)
        title = f"{robot.upper()} — {'no fix' if not base else 'after: ' + ' + '.join(base)}\n" \
                f"{'SUCCESS' if ok else 'FAIL'} (held-out seed {a.seed})"
        axes[0, j].set_title(title, fontsize=9)
        meta[f"{robot}|{'+'.join(base) or 'none'}"] = bool(ok)
    fig.suptitle("Dashed = retargeted human hand path (style), solid = robot tool path, dotted = object. "
                 "Blue reach, red carry, green retreat.", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / f"style_paths_{spec['tag']}_seed{a.seed}.png", dpi=130)
    (out / f"style_paths_{spec['tag']}_seed{a.seed}.json").write_text(json.dumps(
        {"demo": spec, "fixes": list(fixes), "seed": a.seed, "success": meta}, indent=1))
    print(meta)


if __name__ == "__main__":
    main()
