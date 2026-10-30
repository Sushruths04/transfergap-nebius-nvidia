"""IK comparison on the UR arms: the repo's damped-least-squares step vs mink differential IK (QP, joint limits).

Both solvers drive the same point (the gripper pinch site) and are judged by ONE independent evaluator
(fresh forward kinematics on the returned joints). Nothing here reads the block or any scene state.

    PYTHONPATH=. python -m transfergap.sim.ik_compare --robot ur10e --out results/ik_compare_v1

Experiments:
  full_pose    300 random reachable 6-DoF targets (FK of random joint vectors), start from the home pose
  tool_down    200 workspace positions with the tool-down orientation the controller uses; "reachable" is
               decided by a multi-restart mink reference (a lower bound on reachability, stated as such)
  unreachable  100 targets beyond the arm's reach: results must be finite, inside the limits, and the position
               error must be at least (distance from the base - reach), a bound that holds for any solver
  path         40 straight tool-down lines, 100 waypoints, 4 DLS iterations per waypoint (as the controller does)
               vs one mink step per waypoint
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import mujoco
import numpy as np

from .controller import R_DOWN
from .scene import HOME_Q, Scene

POS_TOL, ORI_TOL = 1e-3, np.deg2rad(0.5)       # success: 1 mm and 0.5 degrees
WORKSPACE = dict(x=(0.25, 0.60), y=(-0.30, 0.30), z=(0.02, 0.35))   # the table region the tasks use


def rot_angle(Ra, Rb):
    c = (np.trace(Ra.T @ Rb) - 1.0) / 2.0
    return float(np.arccos(np.clip(c, -1.0, 1.0)))


class ArmKin:
    """Kinematic view of the arm in the real scene model: pinch-site FK, limits, and both solvers."""

    def __init__(self, robot="ur10e"):
        self.scene = s = Scene(0, robot)
        self.m = m = s.model
        self.d = mujoco.MjData(m)
        self.adr, self.dof = list(s.arm_qadr), list(s.arm_dof)
        J = mujoco.mjtObj.mjOBJ_JOINT
        names = ("shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_1_joint", "wrist_2_joint",
                 "wrist_3_joint")
        jid = [mujoco.mj_name2id(m, J, n) for n in names]
        self.jlo, self.jhi = np.array([m.jnt_range[i] for i in jid]).T          # physical joint limits
        self.clo, self.chi = m.actuator_ctrlrange[:6].T                         # what the controller clips to
        self.site = s.pinch_site
        qs = m.site_quat[self.site]
        Rs = np.zeros(9)
        mujoco.mju_quat2Mat(Rs, qs)
        self.R_site_rel = Rs.reshape(3, 3)                                     # site frame in the g_base frame
        self.base = self.d.xpos[1].copy()
        self.q_home = np.array(HOME_Q, float)
        self.reach = self._reach()

    # ---- kinematics ----------------------------------------------------------------------------------
    def fk(self, q, d=None):
        d = d or self.d
        d.qpos[self.adr] = q
        mujoco.mj_kinematics(self.m, d)
        return d.site_xpos[self.site].copy(), d.site_xmat[self.site].reshape(3, 3).copy()

    def body_rot_to_site(self, R_body):
        return R_body @ self.R_site_rel

    def _reach(self):
        """Largest base-to-pinch distance over many random configurations (a lower bound on the true reach)."""
        rng = np.random.default_rng(123)
        d = mujoco.MjData(self.m)
        mujoco.mj_kinematics(self.m, d)
        base = d.xpos[self.m.body("shoulder_link").id].copy()
        best = 0.0
        for _ in range(4000):
            p, _ = self.fk(rng.uniform(self.jlo, self.jhi), d)
            best = max(best, float(np.linalg.norm(p - base)))
        self.shoulder = base
        return best

    # ---- the one evaluator -----------------------------------------------------------------------------
    def evaluate(self, q, p_t, R_t):
        q = np.asarray(q, float)
        finite = bool(np.all(np.isfinite(q)))
        if not finite:
            return dict(pos=np.inf, ori=np.inf, viol=np.inf, finite=False)
        p, R = self.fk(q)
        viol = float(max(np.max(self.jlo - q), np.max(q - self.jhi), 0.0))
        return dict(pos=float(np.linalg.norm(p - p_t)), ori=rot_angle(R, R_t), viol=viol, finite=True)

    # ---- solver A: the repo's damped least squares (math of ScriptedPickPlace.ik_step, target rotation general) ----
    def dls(self, q0, p_t, R_t_site, iters=4, damping=1e-3, rot_w=0.6):
        s, m = self.scene, self.m
        d = mujoco.MjData(m)
        R_t_body = R_t_site @ self.R_site_rel.T
        q = np.array(q0, float)
        for _ in range(iters):
            d.qpos[self.adr] = q
            mujoco.mj_kinematics(m, d)
            mujoco.mj_comPos(m, d)
            R = d.xmat[s.tool_body].reshape(3, 3)
            p = d.xpos[s.tool_body] + R @ s.pinch_off
            jp, jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
            mujoco.mj_jac(m, d, jp, jr, p, s.tool_body)
            err = np.r_[p_t - p, rot_w * 0.5 * sum(np.cross(R[:, i], R_t_body[:, i]) for i in range(3))]
            J = np.vstack([jp, rot_w * jr])[:, self.dof]
            q = np.clip(q + J.T @ np.linalg.solve(J @ J.T + damping * np.eye(6), err), self.clo, self.chi)
        return q

    # ---- solver B: mink differential IK with configuration limits ---------------------------------------
    def mink_solve(self, q0, p_t, R_t_site, iters=200, dt=0.01, damping=1e-3, solver="daqp", stop=True):
        import mink
        m = self.m
        full = np.zeros(m.nq)
        full[:] = mujoco.MjData(m).qpos                 # model default for non-arm dofs (block, gripper)
        full[self.adr] = q0
        cfg = mink.Configuration(m, full)
        task = mink.FrameTask("g_pinch", "site", position_cost=1.0, orientation_cost=1.0, lm_damping=1e-3)
        task.set_target(mink.SE3.from_rotation_and_translation(mink.SO3.from_matrix(R_t_site), p_t))
        limits = [mink.ConfigurationLimit(m)]
        used = 0
        for used in range(1, iters + 1):
            try:
                vel = mink.solve_ik(cfg, [task], dt, solver, damping, limits=limits)
            except Exception:
                break
            cfg.integrate_inplace(vel, dt)
            if stop:
                e = task.compute_error(cfg)
                if np.linalg.norm(e[:3]) < 0.2 * POS_TOL and np.linalg.norm(e[3:]) < 0.2 * ORI_TOL:
                    break
        return cfg.q[self.adr].copy(), used


def _timed(fn, *a, **k):
    t0 = time.perf_counter()
    out = fn(*a, **k)
    return out, 1e3 * (time.perf_counter() - t0)


def _ok(e):
    return e["finite"] and e["pos"] <= POS_TOL and e["ori"] <= ORI_TOL and e["viol"] <= 1e-9


def _summ(rows, ok_key="ok"):
    pos = np.array([r["pos"] for r in rows])
    ori = np.degrees([r["ori"] for r in rows])
    fin = np.isfinite(pos)
    return dict(
        n=len(rows), success=int(sum(r[ok_key] for r in rows)),
        pos_mm_median=float(np.median(pos[fin]) * 1e3) if fin.any() else None,
        pos_mm_p90=float(np.percentile(pos[fin], 90) * 1e3) if fin.any() else None,
        ori_deg_median=float(np.median(ori[fin])) if fin.any() else None,
        ori_deg_p90=float(np.percentile(ori[fin], 90)) if fin.any() else None,
        limit_violations=int(sum(r["viol"] > 1e-9 for r in rows)),
        nonfinite=int(sum(not r["finite"] for r in rows)),
        time_ms_median=float(np.median([r["ms"] for r in rows])),
    )


def _row(arm, sol_ms, p_t, R_t):
    (q, extra), ms = sol_ms
    e = arm.evaluate(q, p_t, R_t)
    e["ms"] = ms
    e["ok"] = _ok(e)
    e["iters"] = extra
    return e


def run_methods(arm, q0, p_t, R_t, dls_iters=(4, 100)):
    out = {}
    for it in dls_iters:
        out[f"dls_{it}"] = _row(arm, _timed(lambda: (arm.dls(q0, p_t, R_t, iters=it), it)), p_t, R_t)
    out["mink"] = _row(arm, _timed(arm.mink_solve, q0, p_t, R_t), p_t, R_t)
    return out


def exp_full_pose(arm, n=300, seed=0):
    rng = np.random.default_rng(seed)
    rows = {}
    for _ in range(n):
        p_t, R_t = arm.fk(rng.uniform(arm.jlo, arm.jhi))
        for k, v in run_methods(arm, arm.q_home, p_t, R_t).items():
            rows.setdefault(k, []).append(v)
    return {k: _summ(v) for k, v in rows.items()}


def _tool_down_targets(arm, n, rng):
    lo = [WORKSPACE[a][0] for a in "xyz"]
    hi = [WORKSPACE[a][1] for a in "xyz"]
    R_site = arm.body_rot_to_site(R_DOWN)
    return [(rng.uniform(lo, hi), R_site) for _ in range(n)]


def exp_tool_down(arm, n=200, restarts=12, seed=1):
    rng = np.random.default_rng(seed)
    rows, reachable = {}, []
    for p_t, R_t in _tool_down_targets(arm, n, rng):
        ref = False
        for r in range(restarts):                       # multi-restart reference: decides "reachable" (lower bound)
            q0 = arm.q_home if r == 0 else rng.uniform(arm.jlo, arm.jhi)
            q, _ = arm.mink_solve(q0, p_t, R_t, iters=150)
            if _ok(arm.evaluate(q, p_t, R_t)):
                ref = True
                break
        reachable.append(ref)
        for k, v in run_methods(arm, arm.q_home, p_t, R_t).items():
            v["reachable"] = ref
            rows.setdefault(k, []).append(v)
    return dict(n_reachable_by_restarts=int(sum(reachable)),
                all_targets={k: _summ(v) for k, v in rows.items()},
                reachable_subset={k: _summ([r for r in v if r["reachable"]]) for k, v in rows.items()
                                  if any(r["reachable"] for r in v)})


def exp_unreachable(arm, n=100, seed=2):
    rng = np.random.default_rng(seed)
    rows, bound_viol = {}, {}
    for _ in range(n):
        u = rng.normal(size=3)
        u[2] = abs(u[2])
        u /= np.linalg.norm(u)
        p_t = arm.shoulder + u * rng.uniform(1.3, 2.2) * arm.reach
        R_t = arm.body_rot_to_site(R_DOWN)
        lower = float(np.linalg.norm(p_t - arm.shoulder) - arm.reach)    # holds for any solver (reach is a lower bound)
        for k, v in run_methods(arm, arm.q_home, p_t, R_t).items():
            v["bound_ok"] = (not v["finite"]) or v["pos"] >= lower - 1e-6
            rows.setdefault(k, []).append(v)
    out = {}
    for k, v in rows.items():
        s = _summ(v)
        s["bound_violations"] = int(sum(not r["bound_ok"] for r in v))
        out[k] = s
    return out


def exp_path(arm, n_lines=40, n_wp=100, seed=3):
    rng = np.random.default_rng(seed)
    R_site = arm.body_rot_to_site(R_DOWN)
    res = {"dls_4": [], "mink_1": []}
    used = 0
    for _ in range(n_lines):
        a = rng.uniform([WORKSPACE[k][0] for k in "xyz"], [WORKSPACE[k][1] for k in "xyz"])
        L = rng.uniform(0.2, 0.4)
        u = rng.normal(size=3)
        u[2] *= 0.3
        b = a + L * u / np.linalg.norm(u)
        pts = [a + (b - a) * t for t in np.linspace(0, 1, n_wp)]
        # keep lines the converged reference can follow (so tracking error is not an unreachable-target artefact)
        q = arm.q_home.copy()
        good = True
        for p in pts:
            q, _ = arm.mink_solve(q, p, R_site, iters=60)
            if not _ok(arm.evaluate(q, p, R_site)):
                good = False
                break
        if not good:
            continue
        used += 1
        q_d = arm.mink_solve(arm.q_home, pts[0], R_site, iters=200)[0]
        q_m = q_d.copy()
        for k in res:
            res[k].append([])
        for p in pts:
            q_d, ms_d = _timed(arm.dls, q_d, p, R_site, iters=4)
            (q_m, _), ms_m = _timed(arm.mink_solve, q_m, p, R_site, iters=1, stop=False)
            ed, em = arm.evaluate(q_d, p, R_site), arm.evaluate(q_m, p, R_site)
            ed["ms"], em["ms"] = ms_d, ms_m
            res["dls_4"][-1].append(ed)
            res["mink_1"][-1].append(em)
    out = {"lines_used": used}
    for k, lines in res.items():
        flat = [r for ln in lines for r in ln]
        for r in flat:
            r["ok"] = _ok(r)
        s = _summ(flat)
        s["worst_line_max_pos_mm"] = float(max(max(r["pos"] for r in ln) for ln in lines) * 1e3) if lines else None
        out[k] = s
    return out


def to_markdown(res):
    L = [f"# IK comparison v1 ({res['robot']})", "",
         f"Success = position <= {POS_TOL*1e3:.0f} mm, orientation <= {np.degrees(ORI_TOL):.1f} deg, no joint-limit "
         "violation, judged by independent forward kinematics. Reach (max sampled shoulder-to-pinch distance): "
         f"{res['reach_m']:.3f} m. Largest difference between the controller's clip range and the joint range: "
         f"{res['clip_vs_joint_range_max_abs_diff_rad']:.2g} rad.", ""]
    def table(title, d):
        L.extend([f"## {title}", "", "| method | n | success | median mm | p90 mm | median deg | p90 deg | limit viol. | ms/solve |",
                  "|---|---|---|---|---|---|---|---|---|"])
        for k, s in d.items():
            f = lambda v: "n/a" if v is None else f"{v:.3g}"
            L.append(f"| {k} | {s['n']} | {s['success']} | {f(s['pos_mm_median'])} | {f(s['pos_mm_p90'])} | "
                     f"{f(s['ori_deg_median'])} | {f(s['ori_deg_p90'])} | {s['limit_violations']} | "
                     f"{f(s['time_ms_median'])} |")
        L.append("")
    table("Reachable 6-DoF targets (from the home pose)", res["full_pose"])
    td = res["tool_down"]
    L.append(f"Tool-down targets: {td['n_reachable_by_restarts']} of 200 reachable by the multi-restart reference.\n")
    table("Tool-down targets, all", td["all_targets"])
    table("Tool-down targets, reachable subset", td["reachable_subset"])
    table("Unreachable targets (bound violations column below)", res["unreachable"])
    L.append("Bound violations (position error below the geometric lower bound; must be 0): " +
             ", ".join(f"{k}={s['bound_violations']}" for k, s in res["unreachable"].items()) + "\n")
    L.append(f"## Path tracking ({res['path']['lines_used']} lines used)\n")
    table("Per-waypoint tracking error", {k: v for k, v in res["path"].items() if k != "lines_used"})
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--robot", default="ur10e", choices=["ur5e", "ur10e"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    arm = ArmKin(a.robot)
    q = 5 if a.quick else None
    res = dict(robot=a.robot, reach_m=arm.reach,
               clip_vs_joint_range_max_abs_diff_rad=float(max(np.max(np.abs(arm.clo - arm.jlo)),
                                                              np.max(np.abs(arm.chi - arm.jhi)))),
               full_pose=exp_full_pose(arm, n=q or 300),
               tool_down=exp_tool_down(arm, n=q or 200, restarts=3 if q else 12),
               unreachable=exp_unreachable(arm, n=q or 100),
               path=exp_path(arm, n_lines=q or 40, n_wp=20 if q else 100))
    out = Path(a.out) / a.robot
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(res, indent=1))
    (out / "summary.md").write_text(to_markdown(res))
    print(to_markdown(res))


if __name__ == "__main__":
    main()
