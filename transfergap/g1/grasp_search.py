"""Kinematic grasp-pose search for the Dex3 hand (no physics, no rollouts).

For candidate hand orientations (pitch, roll) and grasp-point offsets, solve the arm IK onto a block
placed at the planner's target and check, on the static model:
  open (pre-grasp) hand:  no hand geom penetrates the table or the block
  closed hand:            thumb and (index or middle) penetrate the block (a squeeze), no table penetration
Each candidate is also checked with the block shifted by +/-1 cm in x and y; the score is the number
of shifted placements that still pass (robustness), then mean squeeze depth. Prints the best few.

    python transfergap/g1/grasp_search.py --stance-offset -0.075 0.005
"""
from __future__ import annotations

import argparse
import itertools
import json

import mujoco
import numpy as np

from plan_reach import HAND_CLOSED, HAND_PREGRASP, RIGHT_HAND, G1Kin
from scene import BLOCK_HALF, BLOCK_NOMINAL_XY, TABLE_TOP_Z, build_spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sonic-root", default="~/GR00T-WholeBodyControl")
    ap.add_argument("--stance-offset", type=float, nargs=2, default=(0.0, 0.0))
    ap.add_argument("--top", type=int, default=8)
    a = ap.parse_args()
    kin = G1Kin(a.sonic_root)
    m = build_spec(a.sonic_root, 0).compile()
    d = mujoco.MjData(m)
    G = mujoco.mjtObj.mjOBJ_GEOM
    table = mujoco.mj_name2id(m, G, "table")
    block_geom = mujoco.mj_name2id(m, G, "block_geom")
    ba = m.jnt_qposadr[m.joint("block_free").id]
    hand_geoms = {k: [g for g in range(m.ngeom) if m.geom_contype[g] and m.body(m.geom_bodyid[g]).name.startswith(k)]
                  for k in ("right_hand_thumb", "right_hand_index", "right_hand_middle", "right_hand", "right_wrist")}
    all_hand = hand_geoms["right_hand"] + hand_geoms["right_wrist"]
    nrob = len(kin.q_default)
    hadr = [m.jnt_qposadr[m.joint(n).id] for n in RIGHT_HAND]
    fromto = np.zeros(6)

    def dist(g1, g2):
        return mujoco.mj_geomDistance(m, d, g1, g2, 0.05, fromto)

    def pose(qrob, hand, bxy):
        d.qpos[:nrob] = qrob
        d.qpos[hadr] = hand
        d.qpos[ba:ba + 3] = [*bxy, TABLE_TOP_Z + BLOCK_HALF]
        d.qpos[ba + 3:ba + 7] = [1, 0, 0, 0]
        mujoco.mj_kinematics(m, d)

    def check(qrob, bxy):
        pose(qrob, HAND_PREGRASP, bxy)
        if min(dist(g, table) for g in all_hand) < -0.002 or min(dist(g, block_geom) for g in all_hand) < -0.002:
            return None
        pose(qrob, HAND_CLOSED, bxy)
        if min(dist(g, table) for g in all_hand) < -0.004:
            return None
        th = min(dist(g, block_geom) for g in hand_geoms["right_hand_thumb"])
        fi = min(min(dist(g, block_geom) for g in hand_geoms[k]) for k in ("right_hand_index", "right_hand_middle"))
        return min(-th, -fi) if th < 0 and fi < 0 else None

    target = np.asarray(BLOCK_NOMINAL_XY) - np.asarray(a.stance_offset)    # robot-frame block position
    results = []
    for pitch, roll, dx, dy, dz in itertools.product(np.arange(-0.2, 0.81, 0.2), np.arange(-0.6, 0.61, 0.2),
                                                     [-0.02, 0.0, 0.02], [-0.02, 0.0, 0.02],
                                                     [0.0, 0.015, 0.03, 0.045]):
        kin.set_orientation(pitch, roll)
        g = np.array([target[0] + dx, target[1] + dy, TABLE_TOP_Z + BLOCK_HALF + dz])
        q, err = kin.solve(g, kin.q_default)
        if err > 0.005:
            continue
        sq = [check(q, target + np.array(s)) for s in
              [(0, 0), (0.01, 0), (-0.01, 0), (0, 0.01), (0, -0.01)]]
        if sq[0] is None:
            continue
        ok = [s for s in sq if s is not None]
        results.append({"pitch": round(pitch, 2), "roll": round(roll, 2), "grasp_dxy": [dx, dy], "grasp_dz": dz,
                        "robust": len(ok), "squeeze_m": round(float(np.mean(ok)), 4)})
    results.sort(key=lambda r: (-r["robust"], -r["squeeze_m"]))
    print(json.dumps({"candidates_passing": len(results), "best": results[:a.top]}, indent=1))


if __name__ == "__main__":
    main()
