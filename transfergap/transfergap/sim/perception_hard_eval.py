"""Harder depth-perception test (protocol perception_hard_v1): the easy sweep (perception_eval) was 10/10 everywhere,
including with ground-truth beliefs, so it could not show whether perception is robust. Here each condition adds one
stressor, and every cell is scored against two ceilings measured in the SAME scene:

  truth_yaw_aware   ground-truth block pose AND yaw handed to the controller (what the controller can do at best)
  truth_yaw_blind   ground-truth pose, yaw ignored (isolates how much yaw alone costs)
  depth_*           belief from sim/perception.py (depth only; no ground truth)

Stressors: rotated blocks (yaw uniform in +-45 deg, used by the controller), distractor objects of other shapes,
camera calibration error (rotation + translation, uncalibrated), large depth noise, dropouts + flying pixels, the arm
hovering in the camera's view during perception, blocks near the workspace edge, and everything together.
Ground truth is read HERE only to build scenes, to pose the arm for the occlusion condition, and to measure the
estimate's error; the estimator never sees it.

    PYTHONPATH=. MUJOCO_GL=egl python -m transfergap.sim.perception_hard_eval --robot kairos --split dev --out results/perception_hard_v1
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import mujoco
import numpy as np

from .. import metrics
from .controller import ScriptedPickPlace
from .perception import Perceiver
from .perception_eval import MAX_WIDTH_M, parse_range
from .rollout import run_episode
from .gap_budget import ROOT, _committed
from .scene import BLOCK_JITTER, Scene, sample_block_xy, sample_block_yaw, sample_distractors

SPLITS = {"dev": "0-9", "heldout": "100-139"}                  # disjoint seed ranges; held-out only after a frozen protocol
SIZES = (0.025, 0.03, 0.035)                                    # block half sizes: 5, 6, 7 cm cubes (7 cm is tight in a 2F-85)
WRAP = lambda y: (y + np.pi / 4) % (np.pi / 2) - np.pi / 4

# name -> stressors. depth sigma in m; calib in deg / mm; arm = (dx, dy, height) of the tool above the block (m)
BASE = dict(yaw=True, n_distr=0, jitter=BLOCK_JITTER, sigma=0.002, calib_rot=0.0, calib_trans=0.0, dropout=0.0,
            flying=0.0, arm=None, belief="depth", use_yaw=True, wrist=False, retry=False, tray_look=False)
CONDITIONS = {
    "truth_yaw_aware": dict(belief="truth"),
    "truth_yaw_blind": dict(belief="truth", use_yaw=False),
    "depth_aligned": dict(yaw=False),                                    # the earlier easy case, new estimator
    "depth_yaw": dict(),                                                 # rotated blocks, yaw used
    "depth_yaw_blind": dict(use_yaw=False),                              # rotated blocks, yaw ignored (ablation)
    "depth_distractors3": dict(n_distr=3),
    "depth_calib_0p5deg_5mm": dict(calib_rot=0.5, calib_trans=5.0),
    "depth_calib_1deg_10mm": dict(calib_rot=1.0, calib_trans=10.0),
    "depth_calib_2deg_20mm": dict(calib_rot=2.0, calib_trans=20.0),
    "depth_noise_10mm": dict(sigma=0.010),
    "depth_noise_20mm": dict(sigma=0.020),
    "depth_dropout30_fly1": dict(dropout=0.30, flying=0.01),
    "depth_arm_side": dict(arm=(0.10, 0.0, 0.15)),
    "depth_arm_over": dict(arm=(0.0, 0.0, 0.30)),
    "depth_arm_side_retry": dict(arm=(0.10, 0.0, 0.15), retry=True),    # first look fails -> retract the arm, look again
    "depth_arm_over_retry": dict(arm=(0.0, 0.0, 0.30), retry=True),
    "depth_calib_1deg_10mm_wrist": dict(calib_rot=1.0, calib_trans=10.0, wrist=True),   # + wrist look-again at hover
    "depth_calib_2deg_20mm_wrist": dict(calib_rot=2.0, calib_trans=20.0, wrist=True),
    "depth_calib_1deg_10mm_wrist_tray": dict(calib_rot=1.0, calib_trans=10.0, wrist=True, tray_look=True),
    "depth_calib_2deg_20mm_wrist_tray": dict(calib_rot=2.0, calib_trans=20.0, wrist=True, tray_look=True),
    "depth_edge_blocks": dict(jitter=0.12),
    "depth_combined": dict(n_distr=3, calib_rot=0.5, calib_trans=5.0, sigma=0.005, dropout=0.10, flying=0.005,
                           jitter=0.10),
    "depth_combined_wrist_tray": dict(n_distr=3, calib_rot=0.5, calib_trans=5.0, sigma=0.005, dropout=0.10,
                                      flying=0.005, jitter=0.10, wrist=True, tray_look=True),
    "depth_combined_wrist": dict(n_distr=3, calib_rot=0.5, calib_trans=5.0, sigma=0.005, dropout=0.10, flying=0.005,
                                 jitter=0.10, wrist=True),
}


class WristLook:
    """Look-again from the wrist camera at hover: block pose and yaw only (the tray is out of its view). Records its
    own error against the ground truth (measurement only)."""

    def __init__(self, robot, c, tray=False):
        self.tray = tray
        self.p = Perceiver(MAX_WIDTH_M[robot], camera="wrist", sigma_m=c["sigma"], need_tray=tray, need_block=not tray,
                           min_range_m=0.2,
                           calib_rot_deg=c["calib_rot"], calib_trans_mm=c["calib_trans"], dropout=c["dropout"],
                           flying=c["flying"])
        self.err = self.failed = None

    def __call__(self, scene):
        try:
            est = self.p(scene)
        except RuntimeError:
            self.failed = True
            raise
        self.failed = False
        if self.tray:
            self.err = dict(tray_xy_mm=float(1e3 * np.hypot(*(est["info"]["tray_xy"] - scene.goal_xyz[:2]))))
        else:
            self.err = dict(xy_mm=float(1e3 * np.hypot(*(est["block_xyz"][:2] - scene.block_pos()[:2]))),
                            yaw_deg=float(abs(np.rad2deg(WRAP(est["yaw"] - scene.block_yaw)))))
        return est


class TruthPerceiver:
    """Ceiling: the controller's belief IS the ground truth (harness only)."""

    def __init__(self, use_yaw):
        self.use_yaw = use_yaw

    def __call__(self, scene):
        return {"block_xyz": scene.block_pos(), "goal_xyz": scene.goal_xyz.copy(),
                "yaw": scene.block_yaw if self.use_yaw else None,
                "width_m": 2 * scene.block_half if self.use_yaw else None}


class Measured:
    """Wraps a perceiver: optionally parks the arm in the camera's view first, then records the estimate's error
    against the ground truth (measurement only) and can drop the yaw (ablation)."""

    def __init__(self, inner, arm=None, use_yaw=True, retry=False):
        self.inner, self.arm, self.use_yaw, self.retry, self.err, self.retried = inner, arm, use_yaw, retry, None, False

    def _park_arm(self, scene):
        ctl = ScriptedPickPlace(scene)
        tgt = scene.block_pos() + np.array(self.arm)                    # scenario setup: where the arm hovers
        for _ in range(300):
            ctl.ik_step(tgt)
        scene.data.qpos[scene.arm_qadr] = ctl.q
        mujoco.mj_forward(scene.model, scene.data)

    def __call__(self, scene):
        if self.arm is not None:
            self._park_arm(scene)
        try:
            try:
                est = self.inner(scene)
            finally:
                if self.arm is not None:
                    scene.reset()
        except RuntimeError:
            if not self.retry:
                raise
            self.retried = True                         # nothing found with the arm in view: arm is home now, look again
            est = self.inner(scene)
        self.err = dict(xy_mm=float(1e3 * np.hypot(*(est["block_xyz"][:2] - scene.block_pos()[:2]))),
                        z_mm=float(1e3 * abs(est["block_xyz"][2] - scene.block_pos()[2])),
                        yaw_deg=float(abs(np.rad2deg(WRAP(est["yaw"] - scene.block_yaw)))),
                        goal_xy_mm=float(1e3 * np.hypot(*(est["goal_xyz"][:2] - scene.goal_xyz[:2]))))
        if not self.use_yaw:
            est = {**est, "yaw": None, "width_m": None}
        return est


def run_one(robot, seed, half, cond):
    c = {**BASE, **CONDITIONS[cond]}
    bxy = sample_block_xy(seed, c["jitter"])
    yaw = sample_block_yaw(seed) if c["yaw"] else 0.0
    dis = sample_distractors(seed, c["n_distr"], bxy, half)
    meas = None
    if c["belief"] == "truth":
        perceiver = TruthPerceiver(c["use_yaw"])
    else:
        inner = Perceiver(MAX_WIDTH_M[robot], sigma_m=c["sigma"], calib_rot_deg=c["calib_rot"],
                          calib_trans_mm=c["calib_trans"], dropout=c["dropout"], flying=c["flying"])
        perceiver = meas = Measured(inner, c["arm"], c["use_yaw"], c["retry"])
    wrist = WristLook(robot, c) if c["wrist"] else None
    tray_look = WristLook(robot, c, tray=True) if c["tray_look"] else None
    row = dict(seed=seed, half_mm=1e3 * half)
    try:
        ep = run_episode(seed, robot=robot, block_half=half, perceiver=perceiver, block_yaw=yaw, distractors=dis,
                         block_jitter=c["jitter"], look_again=wrist, place_look=tray_look)
    except RuntimeError as e:                                           # perception failed: counts as a failure
        return {**row, "success": False, "reasons": ["perception_failed"], "error": str(e)[:100]}
    sc = metrics.score_episode(ep)
    row.update(success=bool(sc["success"]), reasons=sc["failure_reasons"], final_error_m=sc["final_object_error_m"])
    if meas is not None and meas.err:
        row["estimate_error"] = meas.err
        row["retried"] = meas.retried
    if wrist is not None:
        row["wrist_failed"], row["wrist_error"] = wrist.failed, wrist.err
    if tray_look is not None:
        row["tray_look_failed"], row["tray_look_error"] = tray_look.failed, tray_look.err
    return row


CODE_FILES = ["transfergap/sim/perception.py", "transfergap/sim/perception_hard_eval.py", "transfergap/sim/controller.py",
              "transfergap/sim/scene.py", "transfergap/sim/rollout.py", "transfergap/sim/perception_eval.py"]
PROTOCOL_ID = "perception_hard_v1"
ACCEPTANCE = {   # declared BEFORE the held-out run; derived from dev pass C, thresholds never changed afterwards
    "metric": "pooled success over the 3 block sizes x 40 held-out seeds, per robot and condition",
    "must_pass_ge_0.90": [], "report_only": "every other condition (stress tests beyond a stated tolerance)"}


def _git(*a):
    return subprocess.check_output(["git", *a], cwd=ROOT, text=True).strip()


def freeze(out, dev_dir, must_pass):
    """Write the protocol (conditions, thresholds, seeds, acceptance bars, code commit). Commit it BEFORE held-out."""
    import inspect

    from . import perception as P
    dev = Path(dev_dir)
    for f in sorted(dev.glob("*/dev/results.json")):
        if not _committed(f.resolve()):
            raise SystemExit(f"{f} (dev results) must be committed before freezing")
    if _git("status", "--porcelain", "--", *CODE_FILES):
        raise SystemExit("code files have uncommitted changes; commit them before freezing")
    proto = dict(protocol=PROTOCOL_ID, frozen_before_heldout=True, heldout_seeds=SPLITS["heldout"], dev_seeds=SPLITS["dev"],
                 sizes_half_m=list(SIZES), conditions=CONDITIONS, base=BASE, max_width_m=MAX_WIDTH_M,
                 selection_thresholds={k: v.default for k, v in inspect.signature(P.reject_reason).parameters.items()
                                       if v.default is not inspect._empty},
                 estimator_constants=dict(TOP_BAND_M=P.TOP_BAND_M, MIN_HEIGHT_M=P.MIN_HEIGHT_M, MAX_HEIGHT_M=P.MAX_HEIGHT_M),
                 task=dict(position_tolerance_m=0.03, scorer="metrics.score_episode (block_to_tray_v1)"),
                 acceptance={**ACCEPTANCE, "must_pass_ge_0.90": must_pass}, dev_results=str(dev),
                 code_files=CODE_FILES, code_commit_at_freeze=_git("rev-parse", "HEAD"),
                 notes="Ground truth is read only to build scenes, park the arm, and measure estimate error.")
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "protocol.json").write_text(json.dumps(proto, indent=1))
    print("wrote", Path(out) / "protocol.json", "- commit it, then run --split heldout")


def check_frozen(out, conditions, sizes, seeds):
    f = (Path(out) / "protocol.json").resolve()
    if not f.exists() or not _committed(f):
        raise SystemExit("protocol.json must be committed (unmodified) before held-out trials are run")
    proto = json.loads(f.read_text())
    norm = lambda x: json.loads(json.dumps(x))                 # JSON turns tuples into lists
    if proto["conditions"] != norm(CONDITIONS) or proto["base"] != norm(BASE) or proto["sizes_half_m"] != list(SIZES) or \
            proto["heldout_seeds"] != SPLITS["heldout"] or proto["max_width_m"] != MAX_WIDTH_M:
        raise SystemExit("frozen protocol does not match the current conditions / seeds / sizes")
    if _git("diff", proto["code_commit_at_freeze"], "--", *proto["code_files"]):
        raise SystemExit("estimator / controller / scene code changed after the freeze commit")
    if seeds != parse_range(SPLITS["heldout"]) or sorted(conditions) != sorted(CONDITIONS) or list(sizes) != list(SIZES):
        raise SystemExit("held-out must run the full frozen protocol (all conditions, sizes, seeds)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--robot", default="kairos", choices=sorted(MAX_WIDTH_M))
    ap.add_argument("--split", default="dev", choices=sorted(SPLITS))
    ap.add_argument("--seeds", default=None, help="override the split's seed range, e.g. 0-3 (smoke tests)")
    ap.add_argument("--conditions", nargs="*", default=list(CONDITIONS))
    ap.add_argument("--sizes", type=float, nargs="*", default=list(SIZES))
    ap.add_argument("--calib-sweep", action="store_true",
                    help="calibration tolerance map: rotation-only and translation-only error levels, overhead only and "
                         "with wrist+tray look-again (replaces --conditions)")
    ap.add_argument("--shard", default=None, metavar="K/N",
                    help="run only conditions K, K+N, K+2N ... of the (frozen) list, writing results_shardK-N.json; "
                         "combine with --merge (cells are independent and deterministic, so sharding changes nothing)")
    ap.add_argument("--merge", action="store_true", help="combine results_shard*.json in --out/<robot>/<split> into results.json + summary.md")
    ap.add_argument("--freeze", metavar="DEV_DIR", help="write protocol.json into --out from this committed dev pass")
    ap.add_argument("--must-pass", nargs="*", default=[], help="conditions with a >= 0.90 acceptance bar (with --freeze)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.freeze:
        return freeze(a.out, a.freeze, a.must_pass)
    if a.split == "heldout":
        if a.calib_sweep or a.seeds:
            raise SystemExit("held-out cannot use --calib-sweep or --seeds")
        check_frozen(a.out, a.conditions, a.sizes, parse_range(SPLITS["heldout"]))
    if a.merge:
        return merge(a.out, a.robot, a.split)
    if a.calib_sweep:
        a.conditions = []
        for rot, tr in [(r, 0.0) for r in (0.25, 0.5, 1.0, 2.0)] + [(0.0, t) for t in (5.0, 10.0, 20.0, 40.0)]:
            for suffix, extra in (("", {}), ("_wrist_tray", dict(wrist=True, tray_look=True))):
                name = f"calib_rot{rot:g}deg_trans{tr:g}mm{suffix}"
                CONDITIONS[name] = dict(calib_rot=rot, calib_trans=tr, **extra)
                a.conditions.append(name)
    seeds = parse_range(a.seeds or SPLITS[a.split])
    shard_tag = ""
    if a.shard:
        k, n = map(int, a.shard.split("/"))
        a.conditions = a.conditions[k::n]
        shard_tag = f"_shard{k}-{n}"
    res = dict(robot=a.robot, split=a.split, seeds=seeds, sizes_half_m=a.sizes, conditions=CONDITIONS, base=BASE,
               cells={})
    t0 = time.time()
    for cond in a.conditions:
        for half in a.sizes:
            rows = [run_one(a.robot, s, half, cond) for s in seeds]
            cell = dict(n=len(rows), success=int(sum(r["success"] for r in rows)),
                        failures=sorted({x for r in rows for x in r["reasons"]}), rows=rows)
            errs = [r["estimate_error"] for r in rows if "estimate_error" in r]
            if errs:
                cell["estimate_error_median"] = {k: float(np.median([e[k] for e in errs])) for k in errs[0]}
                cell["estimate_error_max"] = {k: float(np.max([e[k] for e in errs])) for k in errs[0]}
            res["cells"][f"{cond}/half{half:g}"] = cell
            print(f"{a.robot} {a.split} {cond} {2e3*half:.0f} mm: {cell['success']}/{cell['n']} {cell['failures']} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    out = Path(a.out) / a.robot / a.split
    out.mkdir(parents=True, exist_ok=True)
    (out / f"results{shard_tag}.json").write_text(json.dumps(res, indent=1))
    if shard_tag:
        return
    write_summary(out, res, a)


def write_summary(out, res, a):
    seeds = res["seeds"]
    L = [f"# Perception hard test, {a.split} split ({a.robot}, seeds {seeds[0]}-{seeds[-1]})", "",
         "Per cell: successes over seeds, for 5 / 6 / 7 cm cubes. Failures: scorer reasons or perception_failed.", "",
         "| condition | " + " | ".join(f"{2e3*h:.0f} mm" for h in a.sizes) + " | total | failure reasons |",
         "|---|" + "---|" * (len(a.sizes) + 2)]
    for cond in a.conditions:
        cells = [res["cells"][f"{cond}/half{h:g}"] for h in a.sizes]
        reasons = sorted({x for c in cells for x in c["failures"]})
        L.append(f"| {cond} | " + " | ".join(f"{c['success']}/{c['n']}" for c in cells) +
                 f" | {sum(c['success'] for c in cells)}/{sum(c['n'] for c in cells)} | {', '.join(reasons) or '-'} |")
    (out / "summary.md").write_text("\n".join(L) + "\n")


def merge(out, robot, split):
    d = Path(out) / robot / split
    parts = sorted(d.glob("results_shard*.json"))
    if not parts:
        raise SystemExit(f"no shard files in {d}")
    res = json.loads(parts[0].read_text())
    res["cells"] = {}
    for p in parts:
        res["cells"].update(json.loads(p.read_text())["cells"])
    missing = [c for c in CONDITIONS if not all(f"{c}/half{h:g}" in res["cells"] for h in res["sizes_half_m"])]
    if missing:
        raise SystemExit(f"missing conditions after merge: {missing}")
    res["cells"] = {f"{c}/half{h:g}": res["cells"][f"{c}/half{h:g}"] for c in CONDITIONS for h in res["sizes_half_m"]}
    (d / "results.json").write_text(json.dumps(res, indent=1))
    a = argparse.Namespace(split=split, robot=robot, conditions=list(CONDITIONS), sizes=res["sizes_half_m"])
    write_summary(d, res, a)
    print("merged", len(parts), "shards ->", d / "results.json")


if __name__ == "__main__":
    main()
