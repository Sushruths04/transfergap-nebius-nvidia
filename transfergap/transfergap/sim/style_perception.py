"""Style transfer with depth perception in the loop, on block sizes the demo never saw (protocol style_perception_v1).

The robot follows the retargeted human pick-and-place style (real demo, clean retargeted path, robot-nominal pace: the
`oracle_all` plan of demo_budget_v1) while the block pose, yaw, size and the tray come from the depth estimator instead
of the simulator. The demo was recorded for a 4 cm cube; the robot meets 5 / 6 / 7 cm cubes.

Conditions (same seeds and scenes for every condition; success = repo scorer, style = demo_budget.episode_style against
the clean retargeted human path anchored at the true block pose, scoring side only):
  truth        ground-truth block pose + yaw (the ceiling for this plan)
  depth        depth belief, rotated blocks (yaw used), 2 mm noise
  depth_hard   depth belief + 3 distractors + 0.5 deg / 5 mm calibration error + 5 mm noise + 10 % dropouts + flying
               pixels + blocks near the workspace edge, with wrist look-again at hover and at the tray

    PYTHONPATH=. MUJOCO_GL=egl python -m transfergap.sim.style_perception dev --out results/style_perception_v1
    ... freeze --out ...  (commit protocol.json)   then   ... heldout --out ...
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from ..metrics import score_episode
from . import errors_demo as E
from . import perception_hard_eval as H
from .demo_budget import episode_style
from .gap_budget import ROOT, _committed
from .perception import Perceiver
from .perception_eval import MAX_WIDTH_M, parse_range
from .rollout import run_episode
from .scene import Scene, sample_block_xy, sample_block_yaw, sample_distractors

PROTOCOL_ID = "style_perception_v1"
ACCEPTANCE = {   # declared before the held-out run; thresholds are never changed afterwards
    "claim": "depth beliefs are not meaningfully worse than ground-truth beliefs (non-inferiority), per robot, pooled over cube sizes",
    "success_margin_pp": 10.0, "path_rmse_margin_cm": 0.5,
    "rule": "pass if (truth success - depth success) <= success_margin_pp AND (depth path RMSE - truth path RMSE) <= path_rmse_margin_cm",
    "report_only": "depth_hard (stress conditions) and the absolute success level (limited by the demo plan on 7 cm cubes with the 2F-85)"}
DEMO = "runs/demos/pexels_8135753_notebook.npz"           # the real demo used in demo_budget_v1 (gitignored, not committed)
SPLITS = {"dev": "0-9", "heldout": "200-239"}               # disjoint from every earlier seed range
SIZES = (0.025, 0.03, 0.035)                                # 5, 6, 7 cm cubes (the demo's block was 4 cm)
ROBOTS = ("ur5e", "ur10e", "kairos")
CONDS = {"truth": dict(belief="truth"),
         "depth": dict(),
         "depth_hard": dict(n_distr=3, calib_rot=0.5, calib_trans=5.0, sigma=0.005, dropout=0.10, flying=0.005,
                            jitter=0.10, wrist=True, tray_look=True)}
CODE_FILES = ["transfergap/sim/style_perception.py", "transfergap/sim/perception_hard_eval.py",
              "transfergap/sim/perception.py", "transfergap/sim/controller.py", "transfergap/sim/scene.py",
              "transfergap/sim/rollout.py"]


def one(a):
    robot, seed, half, cond = a
    c = {**H.BASE, **CONDS[cond]}
    spec = E.parse_demo_spec(DEMO)
    pert, _, ref = E.build_perturbation(spec, seed, "oracle_all")      # clean retargeted human path, no assumed errors
    bxy = sample_block_xy(seed, c["jitter"])
    yaw = sample_block_yaw(seed)
    dis = sample_distractors(seed, c["n_distr"], bxy, half)
    meas = None
    if c["belief"] == "truth":
        perceiver = H.TruthPerceiver(True)
    else:
        inner = Perceiver(MAX_WIDTH_M[robot], sigma_m=c["sigma"], calib_rot_deg=c["calib_rot"],
                          calib_trans_mm=c["calib_trans"], dropout=c["dropout"], flying=c["flying"])
        perceiver = meas = H.Measured(inner, None, True, False)
    wrist = H.WristLook(robot, c) if c["wrist"] else None
    tray = H.WristLook(robot, c, tray=True) if c["tray_look"] else None
    row = dict(robot=robot, seed=seed, half_mm=1e3 * half, cond=cond)
    try:
        ep = run_episode(seed, pert, robot=robot, block_half=half, perceiver=perceiver, block_yaw=yaw, distractors=dis,
                         block_jitter=c["jitter"], look_again=wrist, place_look=tray, condition=cond)
    except RuntimeError as e:
        return {**row, "success": False, "reasons": ["perception_failed"], "error": str(e)[:100], "style": None}
    sc = score_episode(ep)
    st = episode_style(ep, ref, Scene(seed, robot, half).goal_xyz)
    row.update(success=bool(sc["success"]), reasons=sc["failure_reasons"], style=st)
    if meas is not None and meas.err:
        row["estimate_error"] = meas.err
    return row


def _git(*a):
    return subprocess.check_output(["git", *a], cwd=ROOT, text=True).strip()


def summarize(rows, robots=ROBOTS):
    out = {}
    for robot in robots:
        for cond in CONDS:
            for half in SIZES:
                r = [x for x in rows if x["robot"] == robot and x["cond"] == cond and abs(x["half_mm"] - 1e3 * half) < 1e-6]
                if not r:
                    continue
                st = [x["style"] for x in r if x.get("style")]
                out[f"{robot}/{cond}/{2e3*half:.0f}mm"] = dict(
                    n=len(r), success=int(sum(x["success"] for x in r)),
                    failures=sorted({f for x in r for f in x["reasons"]}), n_styled=len(st),
                    path_rmse_cm=float(100 * np.mean([s["path_rmse_mean_m"] for s in st])) if st else None,
                    approach_deg=float(np.mean([s["approach_angle_deg"] for s in st])) if st else None,
                    lift_err_cm=float(100 * np.mean([s["lift_height_err_m"] for s in st])) if st else None,
                    speed_corr=float(np.mean([s["speed_profile_corr"] for s in st])) if st else None)
    return out


def write(out, rows, split):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    summ = summarize(rows)
    (out / f"{split}_results.json").write_text(json.dumps(dict(split=split, protocol=PROTOCOL_ID, demo_tag=E.parse_demo_spec(DEMO)["tag"],
                                                               summary=summ, rows=rows), indent=1))
    L = [f"# Style transfer with depth perception in the loop ({split})", "",
         "Demo `" + E.parse_demo_spec(DEMO)["tag"] + "` (4 cm cube) -> 5/6/7 cm cubes. success k/n; path RMSE cm to the clean "
         "retargeted human path (lower = closer); approach angle error deg; lift height error cm.", "",
         "| robot | condition | cube | success | path RMSE cm | approach deg | lift err cm | failures |", "|---|---|---|---|---|---|---|---|"]
    f = lambda v, d=1: "-" if v is None else f"{v:.{d}f}"
    for k, v in summ.items():
        robot, cond, size = k.split("/")
        L.append(f"| {robot} | {cond} | {size} | {v['success']}/{v['n']} | {f(v['path_rmse_cm'])} | {f(v['approach_deg'])} | "
                 f"{f(v['lift_err_cm'], 2)} | {', '.join(v['failures']) or '-'} |")
    (out / f"{split}_summary.md").write_text("\n".join(L) + "\n")


def run(split, out, seeds, workers):
    jobs = [(r, s, h, c) for r in ROBOTS for c in CONDS for h in SIZES for s in seeds]
    t0 = time.time()
    with Pool(workers) as p:
        rows = []
        for i, row in enumerate(p.imap(one, jobs, chunksize=4)):
            rows.append(row)
            if (i + 1) % 90 == 0:
                print(f"{i+1}/{len(jobs)} ({time.time()-t0:.0f}s)", flush=True)
    write(out, rows, split)


def score(out):
    proto = json.loads((out / "protocol.json").read_text())
    acc = proto["acceptance"]
    rows = json.loads((out / "heldout_results.json").read_text())["rows"]
    L = [f"# Held-out scorecard, protocol {proto['protocol']} (code commit {proto['code_commit_at_freeze'][:7]})", "",
         f"Seeds {proto['heldout_seeds']}; rule: {acc['rule']}", "",
         "| robot | truth success | depth success | gap pp | truth RMSE cm | depth RMSE cm | RMSE gap cm | verdict | depth_hard success |",
         "|---|---|---|---|---|---|---|---|---|"]
    verdicts = []
    for robot in ROBOTS:
        g = lambda cond: [x for x in rows if x["robot"] == robot and x["cond"] == cond]
        t, d, h = g("truth"), g("depth"), g("depth_hard")
        rm = lambda r: 100 * float(np.mean([x["style"]["path_rmse_mean_m"] for x in r if x.get("style")]))
        gap = 100 * (np.mean([x["success"] for x in t]) - np.mean([x["success"] for x in d]))
        rgap = rm(d) - rm(t)
        ok = gap <= acc["success_margin_pp"] and rgap <= acc["path_rmse_margin_cm"]
        verdicts.append(ok)
        L.append(f"| {robot} | {sum(x['success'] for x in t)}/{len(t)} | {sum(x['success'] for x in d)}/{len(d)} | {gap:+.1f} | "
                 f"{rm(t):.2f} | {rm(d):.2f} | {rgap:+.2f} | {'MET' if ok else 'NOT MET'} | {sum(x['success'] for x in h)}/{len(h)} |")
    L += ["", f"**Non-inferiority bar met for {sum(verdicts)} of {len(verdicts)} robots.**"]
    (out / "heldout_scorecard.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "freeze", "heldout", "score"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", default=None, help="smoke tests only (dev)")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    out = Path(a.out)
    if a.stage == "dev":
        run("dev", out, parse_range(a.seeds or SPLITS["dev"]), a.workers)
    elif a.stage == "score":
        score(out)
    elif a.stage == "freeze":
        dev = out / "dev_results.json"
        if not _committed(dev.resolve()):
            raise SystemExit("dev_results.json must be committed before freezing")
        if _git("status", "--porcelain", "--", *CODE_FILES):
            raise SystemExit("code files have uncommitted changes")
        proto = dict(protocol=PROTOCOL_ID, frozen_before_heldout=True, demo=E.parse_demo_spec(DEMO), robots=list(ROBOTS),
                     conditions=CONDS, base=H.BASE, sizes_half_m=list(SIZES), dev_seeds=SPLITS["dev"],
                     heldout_seeds=SPLITS["heldout"], plan="demo_budget_v1 oracle_all (clean retargeted human path, "
                     "robot-nominal pace)", scoring="metrics.score_episode; demo_budget.episode_style",
                     code_files=CODE_FILES, acceptance=ACCEPTANCE, code_commit_at_freeze=_git("rev-parse", "HEAD"))
        (out / "protocol.json").write_text(json.dumps(proto, indent=1))
        print("wrote protocol.json; commit it, then run heldout")
    else:
        f = (out / "protocol.json").resolve()
        if not f.exists() or not _committed(f) or not _committed((out / "dev_results.json").resolve()):
            raise SystemExit("protocol.json and dev_results.json must be committed (unmodified) before held-out")
        proto = json.loads(f.read_text())
        norm = lambda x: json.loads(json.dumps(x))
        if proto["conditions"] != norm(CONDS) or proto["sizes_half_m"] != list(SIZES) or proto["heldout_seeds"] != SPLITS["heldout"]:
            raise SystemExit("frozen protocol does not match the current constants")
        if _git("diff", proto["code_commit_at_freeze"], "--", *proto["code_files"]):
            raise SystemExit("code changed after the freeze commit")
        run("heldout", out, parse_range(SPLITS["heldout"]), a.workers)


if __name__ == "__main__":
    main()
