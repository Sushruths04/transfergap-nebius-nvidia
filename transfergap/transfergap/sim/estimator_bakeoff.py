"""Pose-estimator bake-off: does a newer human pose estimator make the human -> robot transfer better?

Same clips, same hand annotations (demo.clips), same demo builder (demo.gemx.load_joints_npz), same frozen fix
stacks and held-out seeds as demo_generalization_v5; ONLY the pose estimator differs (joints npz per estimator, in
the shared exporter format: demo/tools/gemx_export_joints.py, demo/tools/fsam_export_joints.py).

Metrics per estimator x demo (protocol: results/pose_estimator_bakeoff_v1/protocol.json):
  fps            median per-frame wall time of the exporter on the L40S (where recorded)
  jitter_mm      RMS second difference of the pinch point inside the clip window (lower = steadier)
  event_err      |frames| between the aperture-only segmentation (no annotation) and the annotated grasp/release
  precheck       kinematic feasibility pre-check verdict per arm (sim/feasibility.py, raw plan)
  success        held-out task success, raw plan and with the demo's v5 fix stack, both arms (n = 60 each)

    PYTHONPATH=. python -m transfergap.sim.estimator_bakeoff --protocol results/pose_estimator_bakeoff_v1/protocol.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ..demo.clips import CLIPS
from ..demo.gemx import load_joints_npz
from ..demo.schema import HumanDemo
from ..demo.segment import segment


def build(clip, joints, out):
    c = CLIPS[clip]
    d = load_joints_npz(joints, c["side"], c["window"], c["events"], {"clip": clip}, c.get("object_height", "lowest_hand"))
    d.save(out)
    return d


def jitter_mm(d):
    a = np.diff(d.pinch, 2, axis=0)
    return float(1000 * np.sqrt(np.mean(np.sum(a ** 2, axis=1))))


def event_err(d):
    meta = {k: v for k, v in d.meta.items() if k != "events"}
    try:
        s = segment(HumanDemo(d.t, d.pinch, d.aperture, d.object_xyz, d.goal_xyz, d.source, meta))
    except Exception as e:                       # aperture never closes/opens clearly: segmentation fails
        return {"grasp": None, "release": None, "error": type(e).__name__}
    ev = d.meta["events"]
    return {"grasp": abs(int(s.grasp) - ev["grasp"]), "release": abs(int(s.release) - ev["release"])}


def run(protocol_path):
    from .demo_budget import HELDOUT_SEEDS, _job, _pool, by_cond, cond_table, gap
    from . import errors_demo as E
    from .feasibility import check_arm, make_plan
    from .gap_budget import _committed
    pp = Path(protocol_path).resolve()
    if not _committed(pp):
        raise SystemExit(f"{pp} must be committed (unmodified) before the run")
    P = json.loads(pp.read_text())
    out_dir = pp.parent
    rows = []
    for est, spec in P["estimators"].items():
        fps = None
        for clip, cfg in P["demos"].items():
            joints = spec["joints"][cfg["video_key"]]
            z = np.load(joints, allow_pickle=False)
            if "wall_s" in z.files:
                fps = float(1.0 / np.median(z["wall_s"]))
            demo_path = f"runs/demos/bakeoff/{est}_{clip}.npz"
            Path(demo_path).parent.mkdir(parents=True, exist_ok=True)
            d = build(clip, joints, demo_path)
            row = {"estimator": est, "demo": clip, "jitter_mm": jitter_mm(d), "event_err": event_err(d),
                   "fps": fps if fps is not None else spec.get("fps_reported"), "robots": {}}
            plan = make_plan(demo_path)
            dspec = E.parse_demo_spec(demo_path)
            fixes = tuple(cfg["stack"])
            for robot in P["robots"]:
                pc = check_arm(plan, robot)
                jobs = [(dspec, s, "full", None, robot, (), "raw") for s in HELDOUT_SEEDS] + \
                       [(dspec, s, "full", None, robot, fixes, "stack") for s in HELDOUT_SEEDS]
                eps = _pool(_job, jobs)
                g = by_cond(eps)
                ct = cond_table(eps)
                row["robots"][robot] = {"precheck": "feasible" if pc["feasible"] else "infeasible",
                                        "precheck_reasons": pc["reasons"], "conditions": ct,
                                        "gap_stack_minus_raw": gap(g["raw"], g["stack"])}
                print(est, clip, robot, {k: (v.get("successes"), v.get("n")) if isinstance(v, dict) else v
                                         for k, v in ct.items()}, flush=True)
            rows.append(row)
    (out_dir / "results.json").write_text(json.dumps({"protocol": P["protocol"], "rows": rows}, indent=1))
    write_summary(out_dir, P, rows)


def _succ(ct, cond):
    c = ct.get(cond, {})
    k = c.get("k", c.get("successes"))
    n = c.get("n")
    return f"{k}/{n}" if k is not None else json.dumps(c)[:40]


def write_summary(out_dir, P, rows):
    L = [f"# Pose-estimator bake-off — {P['protocol']}", "", P["question"], "",
         "| demo | estimator | fps (L40S) | pinch jitter mm | event err (grasp/release frames) | robot | pre-check | "
         "raw | with stack |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        e = r["event_err"]
        ev = "fail" if e.get("grasp") is None else f"{e['grasp']}/{e['release']}"
        for robot, v in r["robots"].items():
            L.append(f"| {r['demo']} | {r['estimator']} | {r['fps'] or '-'} | {r['jitter_mm']:.1f} | {ev} | {robot} | "
                     f"{v['precheck']} | {_succ(v['conditions'], 'raw')} | {_succ(v['conditions'], 'stack')} |")
    (out_dir / "summary.md").write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", required=True)
    run(ap.parse_args().protocol)


if __name__ == "__main__":
    main()
