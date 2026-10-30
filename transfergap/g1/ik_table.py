"""G1 right-arm + waist IK reachability table (kinematics only, nothing is simulated or stepped).

For a grid of grasp-point targets over the table, solve plan_reach.G1Kin.solve (the IK the G1 plans use) with
  arm_only   waist joints frozen (cost 1e6)
  arm_waist  waist allowed, default cost (20, as in the plans)
  waist_cheap  waist cost 1
at two heights (grasp height and lift height), from the standing default pose, with the hand pitched down as in
the plans. Reports the final position error, the orientation error, the waist angles used and the smallest distance of
any solved joint to its limit. The block and tray regions of the task are marked on the maps.

    python transfergap/g1/ik_table.py --sonic-root ~/GR00T-WholeBodyControl --out results/g1_ik_table_v1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import plan_reach as P
from scene import BLOCK_HALF, BLOCK_JITTER, BLOCK_NOMINAL_XY, TABLE_TOP_Z, TRAY_HALF, TRAY_XY

VARIANTS = {"arm_only": 1e6, "arm_waist": 20.0, "waist_cheap": 1.0}
XS, YS = np.arange(0.18, 0.56, 0.02), np.arange(-0.40, 0.221, 0.02)
HEIGHTS = {"grasp": TABLE_TOP_Z + BLOCK_HALF + 0.012, "lift": TABLE_TOP_Z + BLOCK_HALF + 0.012 + 0.12}   # plan_reach defaults
REACH_TOL_M = 0.01        # a target counts as reachable if the final grasp-point error is below this


def orientation_error(kin):
    R = kin.d.xmat[kin.wrist].reshape(3, 3)
    Re = kin.R_target @ R.T
    return float(np.arccos(np.clip((np.trace(Re) - 1) / 2, -1, 1)))


def solve_grid(kin, cost, z):
    kin.inv_cost = np.array([1 / cost if n.startswith("waist") else 1.0 for n in P.IK_JOINTS])
    out = np.zeros((len(YS), len(XS), 4)); waist = np.zeros((len(YS), len(XS), 3)); margin = np.zeros((len(YS), len(XS)))
    for i, y in enumerate(YS):
        for j, x in enumerate(XS):
            q, err = kin.solve(np.array([x, y, z]), kin.q_default)
            out[i, j, 0] = err
            out[i, j, 1] = orientation_error(kin)
            waist[i, j] = [q[kin.qadr[n]] for n in ("waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint")]
            margins = [min(q[kin.qadr[n]] - kin.lo[n], kin.hi[n] - q[kin.qadr[n]]) for n in P.IK_JOINTS]
            margin[i, j] = min(margins)
    return out, waist, margin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sonic-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pitch-down", type=float, default=0.35)
    a = ap.parse_args()
    kin = P.G1Kin(a.sonic_root, a.pitch_down)
    res, summary = {}, {}
    for hname, z in HEIGHTS.items():
        for vname, cost in VARIANTS.items():
            err, waist, margin = solve_grid(kin, cost, z)
            res[(hname, vname)] = (err, waist, margin)
            ok = err[..., 0] < REACH_TOL_M
            # the task's block region (+- jitter around the nominal block xy) and the tray centre
            bi = [(i, j) for i, y in enumerate(YS) for j, x in enumerate(XS)
                  if abs(x - BLOCK_NOMINAL_XY[0]) <= BLOCK_JITTER + 1e-9 and abs(y - BLOCK_NOMINAL_XY[1]) <= BLOCK_JITTER + 1e-9]
            ti = [(i, j) for i, y in enumerate(YS) for j, x in enumerate(XS) if abs(x - TRAY_XY[0]) < 1e-9 + 0.011 and abs(y - TRAY_XY[1]) < 0.011]
            summary[f"{hname}/{vname}"] = dict(
                reachable_fraction=float(ok.mean()), n_targets=int(ok.size),
                block_region_reachable=f"{sum(ok[i, j] for i, j in bi)}/{len(bi)}",
                tray_centre_reachable=f"{sum(ok[i, j] for i, j in ti)}/{len(ti)}",
                median_pos_err_mm=float(1e3 * np.median(err[..., 0])),
                median_orient_err_deg=float(np.rad2deg(np.median(err[..., 1]))),
                max_abs_waist_rad=[float(np.abs(waist[..., k]).max()) for k in range(3)],
                min_joint_margin_to_limit_rad=float(margin.min()))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ik_summary.json").write_text(json.dumps(dict(reach_tolerance_m=REACH_TOL_M, heights_z=HEIGHTS, xs=XS.tolist(),
                                                      ys=YS.tolist(), pitch_down=a.pitch_down, summary=summary), indent=1))
    np.savez_compressed(out / "grid.npz", xs=XS, ys=YS, **{f"{h}_{v}_{k}": res[(h, v)][n] for (h, v) in res
                                                       for n, k in enumerate(("err_orient", "waist", "margin"))})
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 3, figsize=(15, 8.5), sharex=True, sharey=True)
    for r, hname in enumerate(HEIGHTS):
        for c, vname in enumerate(VARIANTS):
            err = res[(hname, vname)][0][..., 0] * 1e3
            im = ax[r, c].pcolormesh(XS, YS, np.clip(err, 0, 60), shading="nearest", cmap="viridis_r", vmin=0, vmax=60)
            ax[r, c].contour(XS, YS, err, levels=[REACH_TOL_M * 1e3], colors="w", linewidths=1.2)
            ax[r, c].plot(*BLOCK_NOMINAL_XY, "r*", ms=12)
            ax[r, c].add_patch(plt.Rectangle((BLOCK_NOMINAL_XY[0] - BLOCK_JITTER, BLOCK_NOMINAL_XY[1] - BLOCK_JITTER),
                                             2 * BLOCK_JITTER, 2 * BLOCK_JITTER, fill=False, ec="r"))
            ax[r, c].add_patch(plt.Rectangle((TRAY_XY[0] - TRAY_HALF, TRAY_XY[1] - TRAY_HALF), 2 * TRAY_HALF, 2 * TRAY_HALF,
                                             fill=False, ec="c", lw=1.5))
            s = summary[f"{hname}/{vname}"]
            ax[r, c].set_title(f"{hname} height, {vname}: reachable {100*s['reachable_fraction']:.0f}%\n"
                               f"block region {s['block_region_reachable']}, tray centre {s['tray_centre_reachable']}", fontsize=9)
            ax[r, c].set_aspect("equal")
    fig.colorbar(im, ax=ax, label="final grasp-point error (mm, clipped at 60)", shrink=0.7)
    for a_ in ax[1]:
        a_.set_xlabel("x (m, forward of the pelvis)")
    for a_ in ax[:, 0]:
        a_.set_ylabel("y (m)")
    fig.suptitle("G1 right arm + waist IK reachability (white line = 10 mm; red = block region; cyan = tray)")
    fig.savefig(out / "reachability.png", dpi=110)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
