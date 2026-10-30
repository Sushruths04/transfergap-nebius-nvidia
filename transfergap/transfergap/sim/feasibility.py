"""Kinematic feasibility pre-check: can THIS robot trace the copied human path at all? (CPU only, no rollout)

Before any simulation, the retargeted human path (demo.style.robot_path, nominal block and goal) is walked point by
point with a converged inverse kinematics solve on the robot model, warm-started from the previous point (the same
tool-down objective as the controller, iterated to convergence instead of 4 steps per control tick). Per point:
  ik_err_m        |target - reached tool point|: the path leaves the robot's workspace (or joint limits)
  penetration_m   deepest overlap of a robot geom with the table or the tray at the IK pose (mj_collision), and
                  for the carry leg the carried block's bottom below the surface under it
Verdict per robot: "style infeasible for this robot" if, anywhere on the copied reach, carry or retreat leg,
  max ik_err_m > IK_ERR_MAX_M  (unreachable)    or    max penetration_m > PENETRATION_MAX_M  (collides).
Both thresholds were fixed a priori (results/feasibility_precheck_v1/protocol.json, committed before the
validation run): 2 cm = half the block, beyond which a grasp at the commanded point cannot close on it; 5 mm =
beyond MuJoCo's soft-contact overlap of a resting contact (~1 mm).

Inputs are the demo plan, the robot model and the fixed task layout (table, tray, NOMINAL block position, goal),
i.e. what a planner knows before execution. No rollout and no simulator state of a trial is read.
The G1 humanoid is checked with the frozen G1 planner (g1/plan_reach.plan_style, its own IK and calibration
args) and needs the upstream GR00T-WholeBodyControl model files (--sonic-root); IK error only for G1.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

from ..demo.schema import HumanDemo
from ..demo.style import LEGS, robot_path, safe_project, safe_project_v2, style_plan_from_demo
from .controller import R_DOWN
from .scene import BLOCK_CENTER, BLOCK_HALF, BLOCK_JITTER, TRAY_FLOOR, TRAY_XY, Scene

IK_ERR_MAX_M = 0.02
PENETRATION_MAX_M = 0.005
ALIGN_N = 20                     # samples on the straight align move (home tool point -> start of the reach)
TRAY_HALF = 0.075
# G1 grasp calibration frozen in results/g1_contact_v1 (same args as g1/run_style.sh)
G1_ARGS = {"stance_offset": (-0.075, 0.005), "grasp_dz": 0.03, "pitch_down": -0.2, "roll": -0.4}


def block_positions(jitter=True, scene=None):
    """Nominal block xy plus the four corners of the seed jitter square (worst case over the task's layouts)."""
    tw = getattr(scene, "twin", None)
    if tw is not None:                                 # the author's measured geometry (sim/twin.py)
        from . import twin as T
        c, jit, half = np.asarray(T.robot_frame(tw)["object_xy"], float), float(tw["jitter_m"]), scene.block_half
    else:
        c, jit, half = np.asarray(BLOCK_CENTER, float), BLOCK_JITTER, BLOCK_HALF
    pts = [c] + ([c + jit * np.array(s) for s in ((1, 1), (1, -1), (-1, 1), (-1, -1))] if jitter else [])
    return [np.array([x, y, half]) for x, y in pts]


class ArmIK:
    """Converged damped-least-squares IK on the arm model (objective as controller.ScriptedPickPlace.ik_step)."""

    def __init__(self, robot):
        self.s = s = Scene(seed=0, robot=robot)
        m = s.model
        self.d = mujoco.MjData(m)
        self.d.qpos[:] = s.data.qpos            # model defaults + home arm pose; the block is excluded below
        self.lo, self.hi = m.actuator_ctrlrange[:6].T
        robot_bodies = s.link_bodies | s.finger_bodies
        env = {s.table_geom} | {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n) for n in
                                ["tray_floor"] + [f"tray_wall{i}" for i in range(4)]}
        self.env = env
        self.robot_geoms = {g for g in range(m.ngeom) if m.geom_bodyid[g] in robot_bodies}

    def tool(self):
        s, d = self.s, self.d
        R = d.xmat[s.tool_body].reshape(3, 3)
        return d.xpos[s.tool_body] + R @ s.pinch_off, R

    def solve(self, target, q, iters=500, damping=1e-3, rot_w=0.6):
        s, m, d = self.s, self.s.model, self.d
        jp, jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        for _ in range(iters):
            d.qpos[s.arm_qadr] = q
            mujoco.mj_kinematics(m, d)
            mujoco.mj_comPos(m, d)
            p, R = self.tool()
            ep = target - p
            er = 0.5 * sum(np.cross(R[:, i], R_DOWN[:, i]) for i in range(3))
            if np.linalg.norm(ep) < 2e-4 and np.linalg.norm(er) < 2e-3:
                break
            mujoco.mj_jac(m, d, jp, jr, p, s.tool_body)
            J = np.vstack([jp, rot_w * jr])[:, s.arm_dof]
            dq = J.T @ np.linalg.solve(J @ J.T + damping * np.eye(6), np.r_[ep, rot_w * er])
            q = np.clip(q + dq, self.lo, self.hi)
        d.qpos[s.arm_qadr] = q
        mujoco.mj_kinematics(m, d)
        p, R = self.tool()
        tilt = float(np.degrees(np.arccos(np.clip(-R[2, 2], -1, 1))))   # tool z vs straight down
        return q, float(np.linalg.norm(target - p)), tilt

    def penetration(self):
        """Deepest robot-vs-table/tray overlap (m, >= 0) at the current pose, and which body."""
        s, m, d = self.s, self.s.model, self.d
        mujoco.mj_forward(m, d)
        worst, who = 0.0, None
        for c in d.contact[:d.ncon]:
            g1, g2 = c.geom1, c.geom2
            if (g1 in self.robot_geoms and g2 in self.env) or (g2 in self.robot_geoms and g1 in self.env):
                if -c.dist > worst:
                    rg = g1 if g1 in self.robot_geoms else g2
                    worst, who = float(-c.dist), mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[rg])
        return worst, who


def carried_block_penetration(p, scene=None):
    """Carried block (centre at the pinch point): depth of its bottom below the surface under it."""
    if scene is not None and getattr(scene, "twin", None) is not None:
        tx, ty = scene.tray_xy
        hx, hy = scene.tray_half
        in_tray = abs(p[0] - tx) < hx and abs(p[1] - ty) < hy
        return max(0.0, (scene.tray_floor if in_tray else 0.0) + scene.twin["table"]["top_z_m"] - (p[2] - scene.block_half))
    in_tray = abs(p[0] - TRAY_XY[0]) < TRAY_HALF and abs(p[1] - TRAY_XY[1]) < TRAY_HALF
    floor = TRAY_FLOOR if in_tray else 0.0
    return max(0.0, floor - (p[2] - BLOCK_HALF))


def check_arm(plan, robot, jitter=True):
    ik = ArmIK(robot)
    s = ik.s
    go, po = np.asarray(plan["grasp_offset"], float), np.asarray(plan["place_offset"], float)
    per_layout = []
    for b in block_positions(jitter, s):
        legs = robot_path(plan, b + go, s.goal_xyz + po)
        q = np.array(s.home_q, float)
        ik.d.qpos[s.arm_qadr] = q
        mujoco.mj_kinematics(s.model, ik.d)
        home = ik.tool()[0]
        start = legs["reach"][1][0]
        segs = [("align", [home + u * (start - home) for u in np.linspace(0, 1, ALIGN_N)])]
        segs += [(leg, list(legs[leg][1])) for leg in LEGS]
        out = {}
        for name, pts in segs:
            errs, pens, tilts, hits = [], [], [], set()
            for tgt in pts:
                q, err, tilt = ik.solve(np.asarray(tgt, float), q)
                pen, who = ik.penetration()
                if name == "carry":
                    pen = max(pen, carried_block_penetration(tgt, s))
                    who = who or ("carried_block" if pen > 0 else None)
                errs.append(err), pens.append(pen), tilts.append(tilt)
                if who and pen > PENETRATION_MAX_M:
                    hits.add(who)
            out[name] = {"max_ik_err_m": max(errs), "max_penetration_m": max(pens), "max_tilt_deg": max(tilts),
                         "colliding_bodies": sorted(hits), "n": len(pts),
                         "path_min_z_m": float(min(np.asarray(t)[2] for t in pts))}
        per_layout.append({"block_xyz": b.tolist(), "legs": out})
    return summarise(per_layout, robot)


def summarise(per_layout, robot):
    """Verdict from the three human-derived legs only; the robot's own align move (home -> start of the reach)
    is reported for information (the controller interpolates it softly from a non-tool-down home pose)."""
    leg_ik = {leg: max(L["legs"][leg]["max_ik_err_m"] for L in per_layout) for leg in per_layout[0]["legs"]}
    leg_pen = {leg: max(L["legs"][leg].get("max_penetration_m", 0.0) for L in per_layout) for leg in per_layout[0]["legs"]}
    worst = {"max_ik_err_m": max(leg_ik[k] for k in LEGS), "max_penetration_m": max(leg_pen[k] for k in LEGS)}
    reasons = []
    if worst["max_ik_err_m"] > IK_ERR_MAX_M:
        reasons.append("unreachable: " + ", ".join(f"{k} {100 * leg_ik[k]:.1f} cm" for k in LEGS
                                                   if leg_ik[k] > IK_ERR_MAX_M))
    if worst["max_penetration_m"] > PENETRATION_MAX_M:
        bodies = sorted({b for L in per_layout for k in LEGS for b in L["legs"][k].get("colliding_bodies", [])})
        reasons.append("collides: " + ", ".join(f"{k} {100 * leg_pen[k]:.1f} cm" for k in LEGS
                                                if leg_pen[k] > PENETRATION_MAX_M) + f" ({', '.join(bodies)})")
    return {"robot": robot, "feasible": not reasons, "verdict": "feasible" if not reasons else
            "style infeasible for this robot", "reasons": reasons, "worst": worst, "leg_max_ik_err_m": leg_ik,
            "leg_max_penetration_m": leg_pen, "layouts": per_layout}


def check_g1(plan, sonic_root, jitter=True):
    """IK error of the frozen G1 style planner over the copied path (kinematics only; no SONIC, no physics)."""
    g1_dir = Path(__file__).resolve().parents[2] / "g1"
    sys.path.insert(0, str(g1_dir))
    import plan_reach                                   # noqa: E402  (g1/ is a script folder, not a package)
    from scene import BLOCK_JITTER as G1_JITTER, BLOCK_NOMINAL_XY
    c = np.asarray(BLOCK_NOMINAL_XY, float)
    xys = [c] + ([c + G1_JITTER * np.array(s) for s in ((1, 1), (1, -1), (-1, 1), (-1, -1))] if jitter else [])
    per_layout = []
    for xy in xys:
        _, meta = plan_reach.plan_style(sonic_root, plan, 1.0, target_xy=xy, **G1_ARGS)
        e = meta["final_ik_error_m"]
        per_layout.append({"block_xy": xy.tolist(), "legs": {k: {"max_ik_err_m": float(e[k])}
                                                            for k in ("align", "reach", "carry", "retreat")}})
    return summarise(per_layout, "g1")


def make_plan(demo, variant="raw"):
    """demo: a HumanDemo .npz path or 'synthetic:<seed>'."""
    if demo.startswith("synthetic:"):
        from ..demo.synthetic import make_demo
        d = make_demo(seed=int(demo.split(":", 1)[1]))[0]
    else:
        d = HumanDemo.load(demo)
    plan = style_plan_from_demo(d)
    return {"raw": lambda p: p, "safe_path": safe_project, "safe_path_v2": safe_project_v2}[variant](plan)


def validate(protocol_path, sonic_root):
    """Run every case of a frozen protocol (must be committed unmodified) and write results.json + summary.md."""
    from .gap_budget import _committed
    pp = Path(protocol_path).resolve()
    if not _committed(pp):
        raise SystemExit(f"{pp} must be committed (unmodified) before the validation run")
    proto = json.loads(pp.read_text())
    th = proto["thresholds"]
    if th != {"IK_ERR_MAX_M": IK_ERR_MAX_M, "PENETRATION_MAX_M": PENETRATION_MAX_M}:
        raise SystemExit("module thresholds differ from the frozen protocol")
    rows, plans = [], {}
    for c in proto["cases"]:
        key = (c["demo"], c["variant"])
        plans.setdefault(key, make_plan(*key))
        res = check_g1(plans[key], sonic_root) if c["robot"] == "g1" else check_arm(plans[key], c["robot"])
        pred = "feasible" if res["feasible"] else "infeasible"
        rows.append({**c, "predicted": pred, "match": None if c["label"] not in ("feasible", "infeasible")
                     else pred == c["label"], **{k: res[k] for k in ("reasons", "worst", "leg_max_ik_err_m",
                                                                    "leg_max_penetration_m", "layouts")}})
        print(c["name"], c["robot"], c["variant"], "label", c["label"], "->", pred, res["reasons"], flush=True)
    scored = [r for r in rows if r["match"] is not None]
    conf = {f"{t}->{p}": sum(r["label"] == t and r["predicted"] == p for r in scored)
            for t in ("feasible", "infeasible") for p in ("feasible", "infeasible")}
    out = {"protocol": proto["protocol"], "n_scored": len(scored), "n_correct": sum(r["match"] for r in scored),
           "confusion": conf, "cases": rows}
    (pp.parent / "results.json").write_text(json.dumps(out, indent=1))
    cm = lambda v: f"{100 * v:.1f}"
    lines = [f"# Kinematic feasibility pre-check — {proto['protocol']}", "",
             f"Thresholds (frozen): IK error > {cm(IK_ERR_MAX_M)} cm or penetration > {cm(PENETRATION_MAX_M)} cm "
             "on the copied reach/carry/retreat legs => style infeasible for this robot. Nominal block + 4 jitter "
             "corners, worst case. CPU only, no rollout.", "",
             f"**Agreement with the known simulated outcome: {out['n_correct']}/{out['n_scored']}** "
             f"(confusion label->predicted: {conf}).", "",
             "| case | variant | robot | known outcome | label | pre-check | max IK err cm (reach/carry/retreat) "
             "| max penetration cm | reason |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ik = "/".join(cm(r["leg_max_ik_err_m"][k]) for k in LEGS)
        pen = "/".join(cm(r["leg_max_penetration_m"].get(k, 0.0)) for k in LEGS) if r["robot"] != "g1" else "n/a"
        ok = "" if r["match"] is None else (" ✓" if r["match"] else " ✗")
        lines.append(f"| {r['name']} | {r['variant']} | {r['robot']} | {r['known']} | {r['label']} | "
                     f"{r['predicted']}{ok} | {ik} | {pen} | {'; '.join(r['reasons']) or '-'} |")
    (pp.parent / "summary.md").write_text("\n".join(lines) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--demo", help="HumanDemo .npz or synthetic:<seed>")
    ap.add_argument("--protocol", help="run a frozen validation protocol (protocol.json) instead of one demo")
    ap.add_argument("--variant", default="raw", choices=["raw", "safe_path", "safe_path_v2"])
    ap.add_argument("--robots", nargs="+", default=["ur5e", "ur10e"])
    ap.add_argument("--sonic-root", default="~/GR00T-WholeBodyControl", help="needed for --robots g1")
    ap.add_argument("--no-jitter", action="store_true", help="nominal block only (default: nominal + 4 corners)")
    a = ap.parse_args()
    if a.protocol:
        validate(a.protocol, a.sonic_root)
        return
    plan = make_plan(a.demo, a.variant)
    for r in a.robots:
        res = check_g1(plan, a.sonic_root, not a.no_jitter) if r == "g1" else check_arm(plan, r, not a.no_jitter)
        print(json.dumps({k: res[k] for k in ("robot", "verdict", "reasons", "worst", "leg_max_ik_err_m",
                                              "leg_max_penetration_m")}, indent=1))


if __name__ == "__main__":
    main()


def figure(results_json, out_png):
    """Two panels: worst IK error and worst penetration per case (log scale), frozen thresholds as lines, colour =
    simulated outcome label, marker = pre-check verdict."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = [r for r in json.loads(Path(results_json).read_text())["cases"]]
    col = {"feasible": "#2a9d8f", "infeasible": "#e76f51", "ambiguous": "#9a9a9a", "prediction": "#6c757d"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 0.32 * len(rows) + 1.4), sharey=True)
    labels = [f"{r['name']} · {r['variant']} · {r['robot']}" for r in rows]
    y = np.arange(len(rows))[::-1]
    for ax, key, th, title in ((axes[0], "max_ik_err_m", IK_ERR_MAX_M, "worst IK error on the copied path"),
                               (axes[1], "max_penetration_m", PENETRATION_MAX_M, "worst table/tray penetration")):
        v = np.array([max(r["worst"][key], 1e-4) for r in rows]) * 100
        for yi, vi, r in zip(y, v, rows):
            na = r["robot"] == "g1" and key == "max_penetration_m"
            ax.scatter(0.01 if na else vi, yi, s=36, color=col[r["label"]], marker="x" if na else
                       ("o" if r["predicted"] == "feasible" else "s"), zorder=3)
        ax.axvline(th * 100, color="#333", lw=1, ls="--")
        ax.set_xscale("log")
        ax.set_xlim(0.008, 150)
        ax.set_xlabel("cm (log)")
        ax.set_title(title, fontsize=10)
        ax.grid(axis="x", alpha=0.3)
    axes[0].set_yticks(y, labels, fontsize=8)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=c, marker="o", ls="", label=f"sim outcome: {k}") for k, c in col.items()
         if k != "prediction"] + [Line2D([], [], color=col["prediction"], marker="o", ls="", label="not simulated"),
                                  Line2D([], [], color="#333", marker="s", ls="", label="pre-check: infeasible"),
                                  Line2D([], [], color="#333", marker="o", ls="", label="pre-check: feasible")]
    axes[1].legend(handles=h, fontsize=7, loc="lower right")
    fig.suptitle("Kinematic feasibility pre-check (no rollout) vs simulated outcome — dashed: frozen thresholds",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
