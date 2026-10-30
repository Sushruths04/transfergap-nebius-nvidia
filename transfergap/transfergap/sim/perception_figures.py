"""Proof figures and videos for the depth-perception tests: what the estimator saw, what it picked, what it rejected and
why, against the ground truth (drawn for comparison only; the estimator never sees it), and the episode video.

    PYTHONPATH=. MUJOCO_GL=egl python -m transfergap.sim.perception_figures --robot ur5e --condition depth_combined \
        --seed 3 --half 0.03 --out results/perception_figures_v1

Writes <out>/<robot>_<condition>_seed<k>.png (top-view RGB | levelled height map with clusters | text) and, with
--video, an mp4 of the whole pick-and-place (third-person + overhead views).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

from .. import metrics  # noqa: E402
from . import perception_hard_eval as H  # noqa: E402
from .perception import Perceiver, reject_reason  # noqa: E402
from .perception_eval import MAX_WIDTH_M  # noqa: E402
from .rollout import run_episode  # noqa: E402
from .scene import Scene, sample_block_xy, sample_block_yaw, sample_distractors  # noqa: E402


def rect_corners(o):
    a = o["yaw"]
    ax = np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])
    h = o["extent"] / 2
    return np.array([[-h[0], -h[1]], [h[0], -h[1]], [h[0], h[1]], [-h[0], h[1]]]) @ ax + o["centre_xy"]


def make_figure(robot, condition, seed, half, out):
    c = {**H.BASE, **H.CONDITIONS[condition]}
    bxy = sample_block_xy(seed, c["jitter"])
    yaw = sample_block_yaw(seed) if c["yaw"] else 0.0
    dis = sample_distractors(seed, c["n_distr"], bxy, half)
    scene = Scene(seed, robot, half, yaw, dis, c["jitter"])
    per = Perceiver(MAX_WIDTH_M[robot], sigma_m=c["sigma"], calib_rot_deg=c["calib_rot"], calib_trans_mm=c["calib_trans"],
                    dropout=c["dropout"], flying=c["flying"], keep_cloud=True)
    err, est, info = None, None, None
    meas = H.Measured(per, c["arm"], c["use_yaw"], False)
    if c["arm"] is not None:
        meas._park_arm(scene)                      # first look with the arm in view; kept parked for the RGB panel
    try:
        est = per(scene)
    except RuntimeError as e:
        err = str(e)
    info = per.last
    import mujoco
    r = mujoco.Renderer(scene.model, 480, 640)
    r.update_scene(scene.data, camera="top")
    rgb = r.render().copy()
    r.close()
    if c["arm"] is not None:
        scene.reset()
    if est is not None and not c["use_yaw"]:
        est = {**est, "yaw": None}
    fig, ax = plt.subplots(1, 3, figsize=(17, 5.2), gridspec_kw=dict(width_ratios=[1, 1.15, 0.8]))
    ax[0].imshow(rgb)
    ax[0].set_title("overhead camera (RGB, for the human; the estimator uses depth only)", fontsize=9)
    ax[0].axis("off")
    ax[1].set_aspect("equal")
    if info is not None and "cloud" in info:
        P, valid = info["cloud"], info["valid"]
        h = P[..., 2] - info["table_z"]
        x0, x1, y0, y1, cell = 0.2, 0.65, -0.3, 0.32, 0.004
        nx, ny = int((x1 - x0) / cell), int((y1 - y0) / cell)
        sel = valid & (P[..., 0] >= x0) & (P[..., 0] < x1) & (P[..., 1] >= y0) & (P[..., 1] < y1)
        ix = np.clip(((P[..., 0][sel] - x0) / cell).astype(int), 0, nx - 1)
        iy = np.clip(((P[..., 1][sel] - y0) / cell).astype(int), 0, ny - 1)
        grid = np.full((ny, nx), np.nan)
        for gx, gy, hh in zip(ix, iy, h[sel]):                    # highest point per 4 mm cell
            if not np.isfinite(grid[gy, gx]) or hh > grid[gy, gx]:
                grid[gy, gx] = hh
        sc = ax[1].imshow(np.clip(grid, -0.02, 0.12), origin="lower", extent=(x0, x1, y0, y1), cmap="viridis",
                          interpolation="nearest")
        fig.colorbar(sc, ax=ax[1], fraction=0.04, label="height above fitted table plane (m)")
        blk, tray = info["block"], info["tray"]
        for o in info["objs"]:
            why = reject_reason(o, MAX_WIDTH_M[robot])
            is_blk, is_tray = o is blk, o is tray
            col = "lime" if is_blk else "cyan" if is_tray else "red"
            ax[1].add_patch(Polygon(rect_corners(o), fill=False, ec=col, lw=1.8))
            lab = "BLOCK" if is_blk else "TRAY" if is_tray else (why or "candidate")
            tx, ty = o["centre_xy"] + [0, 0.012 + 0.5 * o["extent"].max()]
            if 0.2 < tx < 0.65 and -0.3 < ty < 0.32:
                ax[1].text(tx, ty, lab, color=col, fontsize=6.5, ha="center", bbox=dict(fc="black", alpha=0.5, pad=1))
    ax[1].plot(*scene.block_pos()[:2], "wx", ms=9, mew=2, label="true block (comparison only)")
    ax[1].plot(*scene.goal_xyz[:2], "w+", ms=11, mew=2, label="true tray centre")
    ax[1].legend(loc="lower left", fontsize=6)
    ax[1].set_xlim(0.2, 0.65)
    ax[1].set_ylim(-0.3, 0.32)
    ax[1].set_title("levelled depth map (world xy): green chosen block, cyan tray, red rejected", fontsize=8)
    ax[2].axis("off")
    L = [f"{robot}  {condition}", f"seed {seed}, cube {2e3*half:.0f} mm, true yaw {np.rad2deg(yaw):.0f} deg", ""]
    if est is None:
        L += ["PERCEPTION FAILED:", err or ""]
    if est is not None:
        L += ["block xy error  %.1f mm" % (1e3 * np.hypot(*(est["block_xyz"][:2] - scene.block_pos()[:2]))),
              "block z error   %.1f mm" % (1e3 * abs(est["block_xyz"][2] - scene.block_pos()[2])),
              "yaw error       %.1f deg" % abs(np.rad2deg(H.WRAP(per.last["block"]["yaw"] - scene.block_yaw))),
              "tray xy error   %.1f mm" % (1e3 * np.hypot(*(est["goal_xyz"][:2] - scene.goal_xyz[:2]))),
              f"clusters found {info['n_clusters']}, depth noise measured {1e3*info['sigma_est']:.1f} mm"]
    L += ["", "stressors: " + ", ".join(f"{k}={v}" for k, v in H.CONDITIONS[condition].items()) if H.CONDITIONS[condition]
          else "stressors: none"]
    ax[2].text(0, 1, "\n".join(L), va="top", family="monospace", fontsize=8)
    Path(out).mkdir(parents=True, exist_ok=True)
    f = Path(out) / f"{robot}_{condition}_seed{seed}.png"
    fig.tight_layout()
    fig.savefig(f, dpi=110)
    plt.close(fig)
    return f


def make_video(robot, condition, seed, half, out):
    c = {**H.BASE, **H.CONDITIONS[condition]}
    bxy = sample_block_xy(seed, c["jitter"])
    yaw = sample_block_yaw(seed) if c["yaw"] else 0.0
    dis = sample_distractors(seed, c["n_distr"], bxy, half)
    per = H.Measured(Perceiver(MAX_WIDTH_M[robot], sigma_m=c["sigma"], calib_rot_deg=c["calib_rot"],
                               calib_trans_mm=c["calib_trans"], dropout=c["dropout"], flying=c["flying"]),
                     c["arm"], c["use_yaw"], c["retry"])
    wrist = H.WristLook(robot, c) if c["wrist"] else None
    tray = H.WristLook(robot, c, tray=True) if c["tray_look"] else None
    Path(out).mkdir(parents=True, exist_ok=True)
    f = Path(out) / f"{robot}_{condition}_seed{seed}.mp4"
    ep = run_episode(seed, robot=robot, block_half=half, perceiver=per, block_yaw=yaw, distractors=dis,
                     block_jitter=c["jitter"], look_again=wrist, place_look=tray, video_path=str(f),
                     cameras=("third_person", "top"))
    return f, metrics.score_episode(ep)["success"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--robot", default="ur5e", choices=sorted(MAX_WIDTH_M))
    ap.add_argument("--condition", required=True, choices=sorted(H.CONDITIONS))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--half", type=float, default=0.03)
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print(make_figure(a.robot, a.condition, a.seed, a.half, a.out))
    if a.video:
        print(make_video(a.robot, a.condition, a.seed, a.half, a.out))


if __name__ == "__main__":
    main()
