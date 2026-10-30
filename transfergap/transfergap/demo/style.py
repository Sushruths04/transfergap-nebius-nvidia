"""Style-preserving retargeting: carry the human's hand PATH (not just its endpoints) over to the robot, and score
how much of that style the robot kept.

Retargeting (no simulator state; the demo is the only input)
  The demo is cut at grasp and release into three legs: reach (ends at the grasp), carry (grasp -> release) and
  retreat (starts at the release). Each leg is stored object-relative in the robot table frame (after a yaw
  alignment), resampled to N_LEG samples with its own time stamps, so the human's speed profile within a leg is
  kept:
    reach    points relative to the human grasp point          -> anchored at (perceived block + grasp_offset)
    carry    points relative to the grasp point, plus the human carry vector; at run time the xy part is mapped
             by the similarity (yaw + scale) that takes the human carry vector onto the robot's
             (grasp target -> release target) vector; heights are kept in metres (lift height is style)
    retreat  points relative to the human release point         -> anchored at (goal + place_offset)
Style metrics (scoring side; may use logged simulator tool positions, never fed back to the controller)
  path_rmse_m           RMS distance between the robot tool path and the retargeted human path, per leg, after
                        resampling both on normalised leg time
  approach_angle_deg    angle between the human and robot approach directions over the last APPROACH_M of reach
  lift_height_err_m     |robot peak lift above grasp - human peak lift above grasp|
  speed_profile_corr    Pearson correlation of normalised speed profiles over the whole demo-driven motion
"""
from __future__ import annotations

import numpy as np

from .retarget import plan_from_demo, yaw_matrix
from .segment import segment

N_LEG = 40
APPROACH_M = 0.05
LEGS = ("reach", "carry", "retreat")


def _resample(t, x, n):
    t = np.asarray(t, float)
    u = (t - t[0]) / max(t[-1] - t[0], 1e-9)
    s = np.linspace(0.0, 1.0, n)
    return s * (t[-1] - t[0]), np.stack([np.interp(s, u, x[:, i]) for i in range(x.shape[1])], axis=1)


def style_plan_from_demo(demo, align_yaw=0.0):
    """plan_from_demo(...) plus a "style" block with the three object-relative legs."""
    align_yaw = float(demo.meta.get("align_yaw_rad", align_yaw))     # set by pipeline --scene (camera/table alignment from the measured twin)
    plan = plan_from_demo(demo, align_yaw)
    seg = segment(demo)
    R = yaw_matrix(align_yaw)
    p = demo.pinch @ R.T
    g, r = p[seg.grasp], p[seg.release]
    legs = {}
    for name, a, b, anchor in (("reach", seg.reach_start, seg.grasp, g), ("carry", seg.grasp, seg.release, g),
                               ("retreat", seg.release, seg.end, r)):
        b = max(b, a + 1)
        ts, xs = _resample(demo.t[a:b + 1], p[a:b + 1] - anchor, N_LEG)
        legs[name] = {"t_s": ts.tolist(), "rel": xs.tolist()}
    plan["style"] = {"legs": legs, "human_carry_vec": (r - g).tolist(), "n_leg": N_LEG}
    return plan


def safe_project(plan):
    """Style-safety projection: copy of `plan` whose reach, carry and retreat legs never go below the height at
    which the robot contacts the object (reach/carry: grasp height; retreat: release height). Everything else in
    the human path is kept. Motivation (2026-10-02): copied human motions that sweep under a flat object or follow
    the object down into a container drive the robot into the table/tray even when every pipeline stage is
    perfect. Style is still scored against the UNprojected human path, so the projection's style cost is measured."""
    import copy
    p = copy.deepcopy(plan)
    for leg in LEGS:
        rel = np.array(p["style"]["legs"][leg]["rel"])
        rel[:, 2] = np.maximum(rel[:, 2], 0.0)
        p["style"]["legs"][leg]["rel"] = rel.tolist()
    p["safe_projected"] = True
    return p


RETREAT_LIFT_M = 0.05      # safe_project_v2: clear height reached early in the retreat
RETREAT_LIFT_FRAC = 0.2    # ... within this fraction of the retreat leg


def safe_project_v2(plan):
    """safe_project plus a lift-first retreat: after the release the copied path first rises to RETREAT_LIFT_M
    above the release point (within the first RETREAT_LIFT_FRAC of the leg) before following the human's motion,
    so open fingers never sweep sideways at object height. Added 2026-10-02 after safe_project (v1) clamped a
    person's down-and-sideways retreat at block height and the open fingers dragged the block out of the tray."""
    p = safe_project(plan)
    rel = np.array(p["style"]["legs"]["retreat"]["rel"])
    s = np.linspace(0.0, 1.0, len(rel))
    rel[:, 2] = np.maximum(rel[:, 2], RETREAT_LIFT_M * np.minimum(1.0, s / RETREAT_LIFT_FRAC))
    p["style"]["legs"]["retreat"]["rel"] = rel.tolist()
    p["safe_projected"] = "v2"
    return p


APPROACH_FRAC = 0.4        # approach_from_above: last fraction of the reach leg that is replaced
APPROACH_HEIGHT_M = 0.08   # ... by a move to this height above the grasp point, then a vertical descent


def approach_from_above(plan):
    """safe_project_v2 plus a top-down final approach: the human reach is kept for its first (1 - APPROACH_FRAC);
    the rest goes to APPROACH_HEIGHT_M above the grasp point and then straight down onto it. Carry and retreat stay
    the human's. Added 2026-10-02 after the G1 failed to grasp (0/30, also with safe_path_v2) when copying a person
    who slid the hand in sideways at table level: the Dex3 grasp calibration needs a top-down final approach."""
    p = safe_project_v2(plan)
    rel = np.array(p["style"]["legs"]["reach"]["rel"])
    n = len(rel)
    k = int(round((1 - APPROACH_FRAC) * (n - 1)))
    start, above = rel[k].copy(), np.array([0.0, 0.0, APPROACH_HEIGHT_M])
    m = n - 1 - k
    for j in range(1, m + 1):
        u = j / m
        rel[k + j] = start + (above - start) * min(1.0, 2 * u) if u <= 0.5 else above * (1 - (2 * u - 1))
    p["style"]["legs"]["reach"]["rel"] = rel.tolist()
    p["safe_projected"] = "approach_from_above"
    return p


def carry_map(human_vec, robot_vec):
    """3x3 map for carry-leg offsets: xy similarity taking human_vec[:2] onto robot_vec[:2], z unchanged."""
    h, q = np.asarray(human_vec[:2], float), np.asarray(robot_vec[:2], float)
    nh, nq = np.linalg.norm(h), np.linalg.norm(q)
    M = np.eye(3)
    if nh > 1e-6 and nq > 1e-6:
        ang = np.arctan2(q[1], q[0]) - np.arctan2(h[1], h[0])
        M[:2, :2] = (nq / nh) * yaw_matrix(ang)[:2, :2]
    return M


def robot_path(plan, grasp_target, release_target):
    """Retargeted human path in robot world coordinates: {leg: (t_s array, xyz array)}. The carry leg is warped so
    it starts at grasp_target and ends exactly at release_target."""
    st = plan["style"]
    grasp_target, release_target = np.asarray(grasp_target, float), np.asarray(release_target, float)
    out = {}
    L = st["legs"]
    out["reach"] = (np.array(L["reach"]["t_s"]), grasp_target + np.array(L["reach"]["rel"]))
    hv = np.array(st["human_carry_vec"])
    rv = release_target - grasp_target
    rel = np.array(L["carry"]["rel"]) @ carry_map(hv, rv).T
    s = np.linspace(0.0, 1.0, len(rel))[:, None]
    end_err = rv - rel[-1]                 # z residual (and numerical xy residual), spread linearly over the leg
    out["carry"] = (np.array(L["carry"]["t_s"]), grasp_target + rel + s * end_err)
    out["retreat"] = (np.array(L["retreat"]["t_s"]), release_target + np.array(L["retreat"]["rel"]))
    return out


# ---------------------------------------------------------------- scoring side

def _leg_resample(xyz, n=N_LEG):
    xyz = np.asarray(xyz, float)
    if len(xyz) < 2:
        return np.repeat(xyz[:1], n, axis=0)
    return _resample(np.arange(len(xyz), dtype=float), xyz, n)[1]


def _speed_profile(xyz, t):
    v = np.linalg.norm(np.gradient(np.asarray(xyz, float), np.asarray(t, float), axis=0), axis=1)
    return _resample(np.asarray(t, float), v[:, None], 3 * N_LEG)[1][:, 0]


def style_metrics(reference, robot):
    """reference / robot: {leg: (t_s, xyz)} in the same world frame. Robot legs are cut from the logged tool path
    by the controller's own leg labels. Returns the four style metrics (see module doc)."""
    rmse = {}
    for leg in LEGS:
        a, b = _leg_resample(reference[leg][1]), _leg_resample(robot[leg][1])
        rmse[leg] = float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))

    def approach_dir(xyz):
        xyz = np.asarray(xyz, float)
        end = xyz[-1]
        d = np.linalg.norm(xyz - end, axis=1)
        idx = np.flatnonzero(d >= APPROACH_M)
        start = xyz[idx[-1]] if idx.size else xyz[0]
        v = end - start
        return v / max(np.linalg.norm(v), 1e-9)

    cosang = float(np.clip(approach_dir(reference["reach"][1]) @ approach_dir(robot["reach"][1]), -1, 1))
    lift = lambda c: float(np.max(np.asarray(c, float)[:, 2]) - np.asarray(c, float)[0, 2])

    def whole(path):
        ts, xs, off = [], [], 0.0
        for leg in LEGS:
            t, x = np.asarray(path[leg][0], float), np.asarray(path[leg][1], float)
            ts.append(t - t[0] + off)
            xs.append(x)
            off = ts[-1][-1] + 1e-3
        return np.concatenate(ts), np.concatenate(xs)

    sa, sb = _speed_profile(*whole(reference)[::-1]), _speed_profile(*whole(robot)[::-1])
    corr = float(np.corrcoef(sa, sb)[0, 1]) if sa.std() > 1e-9 and sb.std() > 1e-9 else 0.0
    return {"path_rmse_m": rmse, "path_rmse_mean_m": float(np.mean(list(rmse.values()))),
            "approach_angle_deg": float(np.degrees(np.arccos(cosang))),
            "lift_height_err_m": abs(lift(robot["carry"][1]) - lift(reference["carry"][1])),
            "speed_profile_corr": corr}
