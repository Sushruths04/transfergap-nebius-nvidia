"""One command from a human video to robot results: pose -> demo -> feasibility -> corrected rollouts -> report.

    python -m transfergap.pipeline --video clip.mp4 --out runs/pipe1 --robots ur5e ur10e kairos \
        [--window 60 206 --events 102 166] [--side Right] [--joints clip_joints.npz]

Stages (each writes its status into <out>/pipeline_report.json; a failed stage stops the later ones but is reported):
  perceive     video -> per-frame joints (RTMW3D in its own interpreter, $TG_POSE_PY; skipped with --joints)
  demo         joints -> HumanDemo (grasp/release from --events, else the aperture segmenter) + plausibility checks
  feasibility  can each robot trace the copied path at all (CPU, no rollout)
  rollouts     held-out seeds, no correction vs the frozen fix stack, per robot (sim.demo_repro)
  report       <out>/REPORT.md

Honest limits: RTMW3D is only trusted for a static camera with the person in view (it fails on internet clips, see
results/pose_estimator_bakeoff_v3); the plausibility check flags such output instead of simulating it. Perception and
calibration errors in the rollouts are the assumed ones of sim.errors_demo (see the paper).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
POSE_TOOL = HERE / "demo" / "tools" / "rtmw3d_export_joints.py"
FSAM_TOOL = HERE / "demo" / "tools" / "fsam_export_joints.py"
DEFAULT_FIXES = "speed_cap_3,look_again,touch_probe_calibration,speed_cap_2,safe_path_v2"
MAX_EXTENT_M = 1.5       # a pick-and-place hand path wider than this is a failed pose estimate, not a task
MAX_MEDIAN_APERTURE_M = 0.30


def plausibility(demo):
    """Reasons a HumanDemo cannot be a real single-hand pick-and-place (empty list = plausible)."""
    why = []
    p, ap = np.asarray(demo.pinch, float), np.asarray(demo.aperture, float)
    if not np.isfinite(p).all() or not np.isfinite(ap).all():
        why.append("non-finite pinch/aperture")
        return why
    ext = p.max(0) - p.min(0)
    if (ext > MAX_EXTENT_M).any():
        why.append(f"hand path extent {np.round(ext, 2).tolist()} m exceeds {MAX_EXTENT_M} m (pose estimate is not metric or failed)")
    if np.median(ap) > MAX_MEDIAN_APERTURE_M:
        why.append(f"median finger aperture {np.median(ap):.2f} m exceeds {MAX_MEDIAN_APERTURE_M} m")
    return why


def stage_perceive(a, out, rep):
    if a.joints:
        return Path(a.joints)
    joints = out / "joints.npz"
    t0 = time.time()
    if getattr(a, "estimator", "rtmw3d") == "fsam":
        # Fast SAM 3D Body: needs its own interpreter and its repository root as the working directory (checkpoints/, mocap/)
        py, root = a.pose_python or os.environ.get("TG_FSAM_PY"), os.environ.get("TG_FSAM_ROOT")
        if not py or not root:
            raise RuntimeError("--estimator fsam needs TG_FSAM_PY (or --pose-python) and TG_FSAM_ROOT (the Fast-SAM-3D-Body checkout)")
        r = subprocess.run([py, str(FSAM_TOOL), "--video", str(Path(a.video).resolve()), "--out", str(joints.resolve())], capture_output=True, text=True, cwd=root)
        name = "Fast SAM 3D Body"
    else:
        py = a.pose_python or os.environ.get("TG_POSE_PY")
        if not py:
            raise RuntimeError("no pose interpreter: pass --pose-python or set TG_POSE_PY (or give --joints)")
        r = subprocess.run([py, str(POSE_TOOL), "--video", a.video, "--out", str(joints)], capture_output=True, text=True)
        name = "RTMW3D-L"
    if r.returncode or not joints.exists():
        raise RuntimeError("pose export failed: " + (r.stderr or r.stdout)[-400:])
    rep["detail"] = {"estimator": name, "wall_s": round(time.time() - t0, 1),
                     "log_tail": [ln for ln in r.stdout.replace("\r", "\n").splitlines() if "wrote" in ln][-1:]}
    return joints


def stage_demo(a, out, rep, joints):
    from .demo import gemx
    from .human.analyze import metric_scale
    scale = 1.0
    if a.shoulder_width_m:                 # RTMW3D coordinates are not metric (about 2.6x too large on the author's clip): rescale
        z = dict(np.load(joints, allow_pickle=False))
        scale = metric_scale(z["joints"], a.shoulder_width_m)
        z["joints"] = (np.asarray(z["joints"], float) * scale).astype(np.float32)
        joints = out / "joints_scaled.npz"
        np.savez_compressed(joints, **z)
    window = tuple(a.window) if a.window else None
    events = {"grasp": a.events[0], "release": a.events[1]} if a.events else None
    d = gemx.load_joints_npz(str(joints), side=a.side, window=window, events=events,
                             object_height=a.object_height)
    extra = {}
    if getattr(a, "scene", None):          # the measured twin: real distance sets the scale, the real carry direction sets the alignment
        from .sim import twin as T
        tw = T.load(a.scene)
        os.environ["TG_TWIN"] = str(Path(a.scene).resolve())          # inherited by the rollout subprocesses
        hv = np.asarray(d.goal_xyz, float)[:2] - np.asarray(d.object_xyz, float)[:2]
        tv = T.carry_vector(tw)
        lh, lt = float(np.linalg.norm(hv)), float(np.linalg.norm(tv))
        f = lt / max(lh, 1e-9)
        extra = {"scene": tw["name"], "scene_sha": tw["sha256"], "human_carry_m": round(lh, 3), "scene_carry_m": round(lt, 3),
                 "carry_scale_factor": round(f, 3)}
        if a.scale_from == "scene":        # replace the assumed body scale by the measured object-to-target distance
            z = dict(np.load(joints, allow_pickle=False))
            z["joints"] = (np.asarray(z["joints"], float) * f).astype(np.float32)
            scale *= f
            joints = out / "joints_scaled.npz"
            np.savez_compressed(joints, **z)
            d = gemx.load_joints_npz(str(joints), side=a.side, window=window, events=events, object_height=a.object_height)
            hv = np.asarray(d.goal_xyz, float)[:2] - np.asarray(d.object_xyz, float)[:2]
        yaw = float(np.arctan2(tv[1], tv[0]) - np.arctan2(hv[1], hv[0]))
        d.meta["align_yaw_rad"] = yaw                                    # style_plan_from_demo applies it
        extra.update({"scale_from": a.scale_from, "align_yaw_deg": round(float(np.degrees(yaw)), 1),
                      "twin_problems": {r: T.validate(tw, r) for r in a.robots}})
        if not 0.67 <= f <= 1.5 and a.scale_from != "scene":
            extra["warning"] = (f"the body-scale demo has a carry of {lh:.2f} m but the scene says {lt:.2f} m (factor {f:.2f}): "
                                "the shoulder-width scale or the measured distance is off; use --scale-from scene or re-measure")
    why = plausibility(d)
    path = out / "demo.npz"
    d.save(str(path))
    rep["detail"] = {"metric_scale": round(scale, 4), "shoulder_width_ref_m": a.shoulder_width_m or None, "frames": int(len(d.t)), "events": "given" if events else "auto (aperture segmenter)",
                     "pinch_extent_m": np.round(np.ptp(d.pinch, axis=0), 3).tolist(), "plausibility": why or "ok", **extra}
    if why:
        raise RuntimeError("demo is not plausible: " + "; ".join(why))
    return path


def stage_feasibility(a, out, rep, demo_path):
    from .sim import feasibility
    plan = feasibility.make_plan(str(demo_path), "raw")
    res = {}
    for r in a.robots:
        x = feasibility.check_arm(plan, r, True)
        res[r] = {k: x[k] for k in ("verdict", "reasons", "worst")}
    rep["detail"] = res
    (out / "feasibility.json").write_text(json.dumps(res, indent=1, default=float))


def stage_rollouts(a, out, rep, demo_path):
    d = out / "rollouts"
    cmd = [sys.executable, "-m", "transfergap.sim.demo_repro", "--demo", str(demo_path), "--fixes", a.fixes,
           "--robots", ",".join(a.robots), "--out", str(d)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("rollouts failed: " + r.stderr[-400:])
    s = json.loads((d / "repro_summary.json").read_text())
    rep["detail"] = {rb: {c: f"{v['successes']}/{v['n']}" for c, v in x["conditions"].items()}
                     for rb, x in s["robots"].items()}


def write_report(out, rep):
    L = ["# Pipeline report", "", f"input: `{rep['input']}`", ""]
    L += ["| stage | status | detail |", "|---|---|---|"]
    for k, v in rep["stages"].items():
        L.append(f"| {k} | {v['status']} | {json.dumps(v.get('detail', v.get('error', '')), default=str)[:300]} |")
    (out / "REPORT.md").write_text("\n".join(L) + "\n")


def run(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep = {"input": a.video or a.joints, "robots": a.robots, "fixes": a.fixes, "stages": {}}
    ctx = {}
    plan = [("perceive", lambda r: stage_perceive(a, out, r)),
            ("demo", lambda r: stage_demo(a, out, r, ctx["joints"])),
            ("feasibility", lambda r: stage_feasibility(a, out, r, ctx["demo"])),
            ("rollouts", lambda r: stage_rollouts(a, out, r, ctx["demo"]))]
    failed = False
    for name, fn in plan:
        r = {"status": "skipped (earlier stage failed)"} if failed else {}
        if not failed:
            t0 = time.time()
            try:
                v = fn(r)
                if name == "perceive":
                    ctx["joints"] = v
                if name == "demo":
                    ctx["demo"] = v
                r["status"] = "ok"
            except Exception as e:  # report, do not crash: a robust pipeline says which stage broke
                r["status"], r["error"] = "FAILED", str(e)[:600]
                failed = True
            r["seconds"] = round(time.time() - t0, 1)
        rep["stages"][name] = r
    rep["ok"] = not failed
    (out / "pipeline_report.json").write_text(json.dumps(rep, indent=1, default=str))
    write_report(out, rep)
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--video")
    ap.add_argument("--joints", help="skip pose estimation: a joints npz from an exporter")
    ap.add_argument("--out", required=True)
    ap.add_argument("--robots", nargs="+", default=["ur5e", "ur10e", "kairos"])
    ap.add_argument("--side", default="Right", choices=["Right", "Left", "both"])
    ap.add_argument("--window", nargs=2, type=int)
    ap.add_argument("--events", nargs=2, type=int, help="grasp and release frame, in clip (window) frames")
    ap.add_argument("--object-height", default="hand_at_grasp", choices=["lowest_hand", "hand_at_grasp"])
    ap.add_argument("--fixes", default=DEFAULT_FIXES)
    ap.add_argument("--estimator", default="rtmw3d", choices=["rtmw3d", "fsam"], help="pose estimator (fsam = Fast SAM 3D Body: TG_FSAM_PY, TG_FSAM_ROOT)")
    ap.add_argument("--pose-python")
    ap.add_argument("--scene", help="measured scene twin json (sim/twin.py): the robots then do YOUR task geometry, not the fixed sim layout")
    ap.add_argument("--scale-from", default="shoulder", choices=["shoulder", "scene"],
                    help="shoulder: scale the pose from --shoulder-width-m; scene: scale it so the hand's carry equals the measured object-to-target distance")
    ap.add_argument("--shoulder-width-m", type=float, default=0.40,
                    help="the person's shoulder width in metres (default 0.40 is an ASSUMED adult value: measure yours); 0 = do not rescale")
    a = ap.parse_args(argv)
    if not (a.video or a.joints):
        ap.error("give --video or --joints")
    rep = run(a)
    print(json.dumps({k: v["status"] for k, v in rep["stages"].items()}))
    sys.exit(0 if rep["ok"] else 1)


if __name__ == "__main__":
    main()
