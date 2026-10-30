"""Transfer Gap Budget, arm half.

  python -m transfergap.sim.gap_budget dev [--protocol v1|v2] [--robot ur5e|ur10e]
        dev seeds 0-59 x all conditions, pick correction, write protocol.json + dev_results.json
  (commit the results dir: protocol.json, and for v2 also dev_results.json)
  python -m transfergap.sim.gap_budget heldout [--protocol ...] [--robot ...]
        seeds 1000-1059 x {full, corrected}; refuses unless the protocol (and v2 dev results) are committed
  python -m transfergap.sim.gap_budget sweep     # success vs error magnitude, random directions, n=30/level
  python -m transfergap.sim.gap_budget videos    # one failure/oracle-success pair
  python -m transfergap.sim.gap_budget figures

Protocols:
  v1  errors.py, UR5e only, results/gap_budget_v1/ (frozen; default, unchanged behaviour)
  v2  errors_v2.py (adds the retargeting/kinematics stage, per-component RNG streams), any robot,
      results/gap_budget_v2_<robot>/
"""
from __future__ import annotations

import argparse
import importlib
import json
import multiprocessing as mp
import os
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..metrics import paired_gap, score_episode, summarize, wilson_interval
from .rollout import run_episode
from .scene import DEFAULT_ROBOT, ROBOTS

ROOT = Path(__file__).resolve().parents[2]            # transfergap/ (project dir)
DEV_SEEDS = list(range(0, 60))
HELDOUT_SEEDS = list(range(1000, 1060))
SWEEP_SEEDS = list(range(2000, 2030))                  # n=30 per level, disjoint from dev and held-out
SWEEP_LEVELS = {"target_offset_m": [0.0, 0.01, 0.02, 0.03, 0.04, 0.05],
                "tcp_offset_m": [0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06]}
ERROR_MODULES = {"v1": "errors", "v2": "errors_v2"}


@dataclass(frozen=True)
class Cfg:
    protocol: str = "v1"
    robot: str = DEFAULT_ROBOT

    def __post_init__(self):
        if self.protocol not in ERROR_MODULES:
            raise ValueError(f"unknown protocol {self.protocol!r}")
        if self.robot not in ROBOTS:
            raise ValueError(f"unknown robot {self.robot!r}")
        if self.protocol == "v1" and self.robot != "ur5e":
            raise ValueError("gap_budget_v1 is frozen for the UR5e; use --protocol v2 for other robots")

    @property
    def errors(self):
        return importlib.import_module(f".{ERROR_MODULES[self.protocol]}", __package__)

    @property
    def name(self):
        return "gap_budget_v1" if self.protocol == "v1" else f"gap_budget_{self.protocol}_{self.robot}"

    @property
    def res(self):
        return ROOT / "results" / self.name

    @property
    def runs(self):
        return ROOT / "runs" / ("gap_budget" if self.protocol == "v1" else self.name)

    @property
    def protocol_path(self):
        return self.res / "protocol.json"

    @property
    def singles(self):
        return tuple(f"oracle_{c}" for c in self.errors.COMPONENTS)


def _job(a):
    seed, cond, corr, protocol, robot = a
    pert, oracle = Cfg(protocol, robot).errors.build_perturbation(seed, cond, corr)
    tag = cond if corr is None else f"{cond}+{corr}"
    return run_episode(seed, pert, label=tag, oracle=oracle, condition=tag, robot=robot)


def _sweep_job(a):
    seed, kw, val, robot = a
    return run_episode(seed, {kw: val}, label=f"{kw}={val}", oracle="none", condition=f"{kw}={val}", robot=robot)


def _pool(fn, jobs):
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    with mp.get_context("spawn").Pool(min(20, mp.cpu_count() or 2)) as pool:
        return pool.map(fn, jobs, chunksize=2)


def git_hash():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def write_jsonl(path, eps):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in eps))


def by_cond(eps):
    d = {}
    for e in eps:
        d.setdefault(e["condition"], []).append(e)
    return d


def cond_table(eps):
    """Per-condition success (Wilson CI) and failure-reason counts."""
    out = {}
    summarize(eps)   # validates every episode and refuses cross-oracle pooling
    for cond, rows in by_cond(eps).items():
        res = [score_episode(e) for e in rows]
        n, k = len(res), sum(r["success"] for r in res)
        reasons = Counter(x for r in res for x in r["failure_reasons"])
        out[cond] = {"oracle": rows[0].get("oracle"), "n": n, "successes": k, "success_rate": k / n,
                     "wilson_95": wilson_interval(k, n), "failure_reasons": dict(reasons)}
    return out


def gap(a, b):
    """b minus a, paired by seed (metrics.paired_gap)."""
    g = paired_gap(a, b)
    return {"delta_pp": g["success_gap_b_minus_a_pp"], "ci95_pp": g["paired_bootstrap_95_pp"], "n": g["paired_trials"]}


def budget(groups, singles):
    full = groups["full"]
    b = {c.replace("oracle_", ""): gap(full, groups[c]) for c in singles}
    allg = gap(full, groups["oracle_all"])
    interaction = {"sum_of_single_recoveries_pp": sum(v["delta_pp"] for v in b.values()),
                   "oracle_all_recovery_pp": allg["delta_pp"], "oracle_all": allg}
    interaction["sum_minus_all_pp"] = interaction["sum_of_single_recoveries_pp"] - allg["delta_pp"]
    return b, interaction


def choose_component(b, components):
    """Largest single-oracle budget; ties broken by `components` order. Deterministic, logged."""
    order = {c: i for i, c in enumerate(components)}
    return max(b, key=lambda c: (round(b[c]["delta_pp"], 9), -order[c]))


def md_table(rows, head):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(r) + " |" for r in rows])


def fmt_ci(t):
    return f"{100*t['success_rate']:.0f}% ({t['successes']}/{t['n']}) [{100*t['wilson_95'][0]:.0f}, {100*t['wilson_95'][1]:.0f}]"


def retarget_tool_error(cfg, seeds):
    """Descriptive kinematics only (no rollout, no success): how far the v2 retargeting joint error moves the
    tool point at the nominal grasp pose of each seed. Uses ground-truth block pose because it is analysis code,
    not a controller."""
    import mujoco
    from .controller import ScriptedPickPlace
    from .scene import Scene
    out = []
    for s in seeds:
        scene = Scene(s, cfg.robot)
        ctl = ScriptedPickPlace(scene)
        for _ in range(200):
            ctl.ik_step(ctl.belief)
        d = mujoco.MjData(scene.model)
        d.qpos[scene.arm_qadr] = ctl.q
        p0 = ctl.tool_point(d).copy()
        d.qpos[scene.arm_qadr] = np.clip(ctl.q + cfg.errors.sample_errors(s)["retarget_q_err"], ctl.lo, ctl.hi)
        out.append(float(np.linalg.norm(ctl.tool_point(d) - p0)))
    a = np.array(out)
    return {"n": len(a), "median_m": float(np.median(a)), "p90_m": float(np.quantile(a, 0.9)), "max_m": float(a.max()),
            "note": "tool-point displacement at the nominal grasp pose caused by the injected joint-space retargeting error"}


def env_info():
    import mujoco
    commit = (ROOT / "transfergap" / "sim" / "assets" / "MENAGERIE_COMMIT")
    return {"mujoco": mujoco.__version__, "menagerie_commit": commit.read_text().strip() if commit.exists() else None}


def stage_dev(cfg):
    E = cfg.errors
    eps = _pool(_job, [(s, c, None, cfg.protocol, cfg.robot) for s in DEV_SEEDS for c in E.CONDITIONS])
    write_jsonl(cfg.runs / "dev.jsonl", eps)
    groups = by_cond(eps)
    table = cond_table(eps)
    b, inter = budget(groups, cfg.singles)
    comp = choose_component(b, E.COMPONENTS)
    corr = E.CORRECTIONS[comp]
    comps = ", ".join(E.COMPONENTS)
    res = {"seeds": [DEV_SEEDS[0], DEV_SEEDS[-1]], "conditions": table, "budget": b, "interaction": inter,
           "chosen_component": comp, "chosen_correction": corr,
           "choice_rule": f"argmax over {{{comps}}} of success(oracle_k)-success(full) on dev; ties -> {comps} order"}
    if cfg.protocol != "v1":
        res["robot"] = cfg.robot
        res["retarget_tool_error_descriptive"] = retarget_tool_error(cfg, DEV_SEEDS)
    cfg.res.mkdir(parents=True, exist_ok=True)
    (cfg.res / "dev_results.json").write_text(json.dumps(res, indent=1))
    protocol = {"protocol": "gap_budget_v1" if cfg.protocol == "v1" else E.PROTOCOL_NAME,
                "frozen_before_heldout": True, "chosen_component": comp,
                "chosen_correction": corr, "dev_budget_pp": {k: v["delta_pp"] for k, v in b.items()},
                "dev_seeds": [DEV_SEEDS[0], DEV_SEEDS[-1]], "heldout_seeds": [HELDOUT_SEEDS[0], HELDOUT_SEEDS[-1]],
                "heldout_conditions": ["full", f"full+{corr}"], "constants": E.constants(),
                "scoring": "metrics.score_episode, task block_to_tray_v1", "code_commit_at_freeze": git_hash()}
    if cfg.protocol != "v1":
        protocol.update({"robot": cfg.robot, "robot_label": ROBOTS[cfg.robot][2], "components": list(E.COMPONENTS),
                         "conditions": E.CONDITIONS, "corrections": E.CORRECTIONS, "env": env_info(),
                         "retargeting_oracle": "exact IK: the controller's own DLS IK on the robot model, no joint offset"})
    cfg.protocol_path.write_text(json.dumps(protocol, indent=1))
    print(cfg.name, json.dumps({k: table[k]["success_rate"] for k in table}))
    print("budget pp:", {k: round(v["delta_pp"], 1) for k, v in b.items()}, "chosen:", comp, "->", corr)


def _committed(path):
    rel = str(path.relative_to(ROOT))
    if subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=ROOT, capture_output=True).returncode:
        return False
    return not subprocess.check_output(["git", "status", "--porcelain", "--", rel], cwd=ROOT, text=True).strip()


def stage_heldout(cfg):
    must = [cfg.protocol_path] + ([] if cfg.protocol == "v1" else [cfg.res / "dev_results.json"])
    for p in must:
        if not p.exists() or not _committed(p):
            raise SystemExit(f"{p.name} must be committed (unmodified) before held-out trials are run")
    proto = json.loads(cfg.protocol_path.read_text())
    E = cfg.errors
    if proto["constants"] != json.loads(json.dumps(E.constants())):
        raise SystemExit("error-model constants differ from the frozen protocol")
    if cfg.protocol != "v1" and proto.get("robot") != cfg.robot:
        raise SystemExit("frozen protocol is for a different robot")
    assert not set(DEV_SEEDS) & set(HELDOUT_SEEDS)
    corr = proto["chosen_correction"]
    eps = _pool(_job, [(s, "full", c, cfg.protocol, cfg.robot) for s in HELDOUT_SEEDS for c in (None, corr)])
    write_jsonl(cfg.runs / "heldout.jsonl", eps)
    groups = by_cond(eps)
    g = gap(groups["full"], groups[f"full+{corr}"])
    res = {"seeds": [HELDOUT_SEEDS[0], HELDOUT_SEEDS[-1]], "correction": corr, "conditions": cond_table(eps),
           "paired_gap_corrected_minus_full": g, "ci_excludes_zero": g["ci95_pp"][0] > 0 or g["ci95_pp"][1] < 0}
    (cfg.res / "heldout_results.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    write_summary(cfg)


def load(path):
    return [json.loads(l) for l in path.read_text().splitlines()]


def write_summary(cfg):
    E, RES = cfg.errors, cfg.res
    dev, held = json.loads((RES / "dev_results.json").read_text()), json.loads((RES / "heldout_results.json").read_text())
    proto = json.loads(cfg.protocol_path.read_text())
    caveats = ["all error magnitudes are assumptions, not measured",
               "scripted IK controller, not a learned policy; no human demo drives it",
               "grip force is nominal; contact oracle not informative",
               "touch probe is a noise model, probe motion and time are not simulated",
               "look-again and probe corrections take no execution time in the simulation"]
    if cfg.protocol != "v1":
        caveats += ["retargeting error is a constant per-seed joint-space offset (no human wrist trajectory is retargeted); "
                    "its oracle is the controller's own DLS IK, not cuRobo",
                    "ik_resolve correction is a residual-noise model; no second IK solver is run",
                    "UR5e and UR10e share the table layout tuned for the UR5e and identical per-seed injected errors"]
    summ = {"git_commit": git_hash(), "protocol_commit_hint": proto["code_commit_at_freeze"], "constants": proto["constants"],
            "dev": dev, "heldout": held, "caveats": caveats}
    if cfg.protocol != "v1":
        summ.update({"protocol": proto["protocol"], "robot": cfg.robot, "env": proto.get("env")})
    (RES / "summary.json").write_text(json.dumps(summ, indent=1))
    rows = [[c, dev["conditions"][c]["oracle"], fmt_ci(dev["conditions"][c]),
             ", ".join(f"{k}:{v}" for k, v in dev["conditions"][c]["failure_reasons"].items()) or "-"]
            for c in E.CONDITIONS]
    title = "# Gap budget v1 (arm), preliminary" if cfg.protocol == "v1" else \
        f"# Gap budget {cfg.protocol} (arm: {ROBOTS[cfg.robot][2]}), preliminary"
    md = [title, "", f"Commit: `{git_hash()}`. Protocol frozen at `{proto['code_commit_at_freeze']}`. "
          "All error magnitudes are ASSUMPTIONS.", "",
          "## Dev seeds 0-59: success, Wilson 95% [%]", "",
          md_table(rows, ["condition", "oracle", "success", "failure reasons (counts)"]), "",
          "## Budget per component (success(oracle_k) - success(full), pp, paired bootstrap 95% CI)", ""]
    rows = [[k, f"{v['delta_pp']:+.1f}", f"[{v['ci95_pp'][0]:+.1f}, {v['ci95_pp'][1]:+.1f}]"] for k, v in dev["budget"].items()]
    it = dev["interaction"]
    rows.append(["oracle_all", f"{it['oracle_all_recovery_pp']:+.1f}", f"[{it['oracle_all']['ci95_pp'][0]:+.1f}, {it['oracle_all']['ci95_pp'][1]:+.1f}]"])
    md += [md_table(rows, ["component", "recovery pp", "95% CI"]), "",
           f"Interaction: sum of single recoveries = {it['sum_of_single_recoveries_pp']:+.1f} pp; oracle_all recovery = {it['oracle_all_recovery_pp']:+.1f} pp.", ""]
    if "retarget_tool_error_descriptive" in dev:
        r = dev["retarget_tool_error_descriptive"]
        md += [f"Retargeting error (ASSUMPTION, joint sigma {np.rad2deg(proto['constants']['RETARGET_JOINT_SIGMA_RAD']):.2f} deg) "
               f"moves the tool point at the grasp pose by median {100*r['median_m']:.2f} cm, p90 {100*r['p90_m']:.2f} cm, "
               f"max {100*r['max_m']:.2f} cm on this robot (kinematics only).", ""]
    md += [f"## Correction (chosen on dev by code: {dev['chosen_component']} -> {dev['chosen_correction']})", ""]
    hc, g = held["conditions"], held["paired_gap_corrected_minus_full"]
    rows = [[c, fmt_ci(t), ", ".join(f"{k}:{v}" for k, v in t["failure_reasons"].items()) or "-"] for c, t in hc.items()]
    md += [md_table(rows, ["held-out condition (seeds 1000-1059)", "success", "failure reasons"]), "",
           f"Held-out paired gap (corrected - full): {g['delta_pp']:+.1f} pp, 95% CI [{g['ci95_pp'][0]:+.1f}, {g['ci95_pp'][1]:+.1f}], n={g['n']}; "
           f"CI excludes zero: {held['ci_excludes_zero']}.", ""]
    if cfg.protocol != "v1":
        md += ["## Caveats", ""] + [f"- {c}" for c in caveats] + [""]
    (RES / "summary.md").write_text("\n".join(md))


def stage_sweep(cfg):
    jobs = [(s, kw, v, cfg.robot) for kw, lv in SWEEP_LEVELS.items() for v in lv for s in SWEEP_SEEDS]
    eps = _pool(_sweep_job, jobs)
    write_jsonl(cfg.runs / "sweep_random_dir.jsonl", eps)
    out = {}
    for e in eps:
        kw, v = list(e["perturbation"].items())[0]
        out.setdefault(kw, {}).setdefault(v, []).append(score_episode(e)["success"])
    curves = {kw: [{"level_m": v, "n": len(r), "successes": sum(r), "wilson_95": wilson_interval(sum(r), len(r))}
                   for v, r in sorted(d.items())] for kw, d in out.items()}
    cfg.res.mkdir(parents=True, exist_ok=True)
    (cfg.res / "sweep_random_dir.json").write_text(json.dumps(curves, indent=1))
    for kw, c in curves.items():
        print(kw, [(x["level_m"], x["successes"]) for x in c])


def stage_videos(cfg):
    eps = load(cfg.runs / "dev.jsonl")
    g = by_cond(eps)
    ok = {e["seed"] for e in g["oracle_perception"] if score_episode(e)["success"]}
    cands = [e["seed"] for e in g["full"] if not score_episode(e)["success"] and e["seed"] in ok]
    if not cands:
        raise SystemExit("no seed where full fails and oracle_perception succeeds")
    seed = cands[0]
    vd = cfg.runs / "videos"
    vd.mkdir(parents=True, exist_ok=True)
    for c in ("full", "oracle_perception"):
        pert, oracle = cfg.errors.build_perturbation(seed, c)
        ep = run_episode(seed, pert, video_path=str(vd / f"seed{seed}_{c}.mp4"), label=c, oracle=oracle, condition=c,
                         robot=cfg.robot)
        print(c, "success" if score_episode(ep)["success"] else "FAIL", ep["video"], score_episode(ep)["failure_reasons"])


def stage_figures(cfg):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    BLUE, ORANGE, GREY = "#0072B2", "#E69F00", "#666666"          # Okabe-Ito
    RES = cfg.res
    fd = RES / "figs"
    fd.mkdir(parents=True, exist_ok=True)
    dev = json.loads((RES / "dev_results.json").read_text())

    def save(fig, name):
        for ext in ("png", "pdf"):
            fig.savefig(fd / f"{name}.{ext}", dpi=200, bbox_inches="tight")
        plt.close(fig)

    # (a) gap budget bars
    names = list(cfg.errors.COMPONENTS)
    k = len(names)
    v = [dev["budget"][n]["delta_pp"] for n in names] + [dev["interaction"]["oracle_all_recovery_pp"]]
    ci = [dev["budget"][n]["ci95_pp"] for n in names] + [dev["interaction"]["oracle_all"]["ci95_pp"]]
    err = [[x - c[0] for x, c in zip(v, ci)], [c[1] - x for x, c in zip(v, ci)]]
    fig, ax = plt.subplots(figsize=(1.4 * (k + 1) + 1, 3.6))
    ax.bar(range(k + 1), v, yerr=err, capsize=4, color=[BLUE] * k + [GREY])
    ax.set_xticks(range(k + 1), names + ["all"])
    ax.set_ylabel("success recovered vs full (pp)")
    ax.set_title(f"Transfer gap budget, {ROBOTS[cfg.robot][2]}, dev seeds 0-59 (n=60 paired)\n"
                 f"full-condition success {100*dev['conditions']['full']['success_rate']:.0f}%", fontsize=10)
    ax.axhline(0, color="k", lw=0.8)
    save(fig, "a_gap_budget")

    # (b) sweeps
    sw_path = RES / "sweep_random_dir.json"
    if sw_path.exists():
        sw = json.loads(sw_path.read_text())
        fig, axs = plt.subplots(1, 2, figsize=(8, 3.4), sharey=True)
        for ax, (kw, title, col) in zip(axs, [("target_offset_m", "Perception error (xy, random direction)", BLUE),
                                              ("tcp_offset_m", "Tool calibration error (random 3D direction)", ORANGE)]):
            c = sw[kw]
            x = [100 * p["level_m"] for p in c]
            y = [p["successes"] / p["n"] for p in c]
            ax.errorbar(x, y, yerr=[[a - p["wilson_95"][0] for a, p in zip(y, c)], [p["wilson_95"][1] - a for a, p in zip(y, c)]],
                        marker="o", color=col, capsize=3)
            ax.set_xlabel("error magnitude (cm)")
            ax.set_title(title, fontsize=10)
            ax.set_ylim(-0.03, 1.05)
        axs[0].set_ylabel("success rate (n=30/level, Wilson 95%)")
        save(fig, "b_success_vs_error")

    # (c) before / after
    held = json.loads((RES / "heldout_results.json").read_text())
    hc = held["conditions"]
    corr = held["correction"]
    keys = ["full", f"full+{corr}"]
    y = [hc[k]["success_rate"] for k in keys]
    lo = [hc[k]["wilson_95"][0] for k in keys]
    hi = [hc[k]["wilson_95"][1] for k in keys]
    g = held["paired_gap_corrected_minus_full"]
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    ax.bar(range(2), y, yerr=[[a - b for a, b in zip(y, lo)], [b - a for a, b in zip(y, hi)]], capsize=4, color=[GREY, BLUE])
    ax.set_xticks(range(2), ["full (uncorrected)", f"corrected:\n{corr}"])
    ax.set_ylabel("success rate (Wilson 95%)")
    ax.set_ylim(0, 1.05)
    ax.set_title(f"Held-out seeds 1000-1059\npaired gap {g['delta_pp']:+.1f} pp, 95% CI [{g['ci95_pp'][0]:+.1f}, {g['ci95_pp'][1]:+.1f}]", fontsize=10)
    save(fig, "c_correction_before_after")
    print("figures in", fd)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["dev", "heldout", "sweep", "videos", "figures", "summary"])
    ap.add_argument("--protocol", default="v1", choices=sorted(ERROR_MODULES))
    ap.add_argument("--robot", default=DEFAULT_ROBOT, choices=sorted(ROBOTS))
    a = ap.parse_args()
    cfg = Cfg(a.protocol, a.robot)
    {"dev": stage_dev, "heldout": stage_heldout, "sweep": stage_sweep, "videos": stage_videos,
     "figures": stage_figures, "summary": write_summary}[a.stage](cfg)


if __name__ == "__main__":
    main()
