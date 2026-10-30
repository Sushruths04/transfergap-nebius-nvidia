"""Like run_trials.py, but the reference is streamed as SONIC VR 3-point targets (stream_vr3.py, planner mode,
deploy --input-type zmq_manager) instead of joint targets. Same sim runner, same logs, same scoring.

    python run_trials_vr3.py --traj PLAN.npz --run-dir RUN --seeds 300-319 --rollouts 1 [--compliance 0.05]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from run_trials import SONIC, HERE, TRT, keys, kill_all, log_has, parse_range, tmux_new, wait_for


def one_rollout(seed, rollout, traj, run, compliance, extra_stream=""):
    tag = f"seed{seed}_r{rollout}"
    logs = {k: run / "logs" / f"{tag}.{k}.log" for k in ("sim", "deploy", "stream")}
    (run / "logs").mkdir(parents=True, exist_ok=True)
    for f in (f"{tag}.ready", f"{tag}.stop", f"{tag}.go", f"{tag}.done"):
        (run / f).unlink(missing_ok=True)
    kill_all()
    tmux_new("g1-sim", f"cd {SONIC} && MUJOCO_GL=egl .venv_sim/bin/python {HERE}/sim_runner.py "
                       f"--seed {seed} --rollout {rollout} --run-dir {run}", logs["sim"])
    time.sleep(3)
    tmux_new("g1-deploy", f"cd {SONIC}/gear_sonic_deploy && export TensorRT_ROOT={TRT} && "
                          "just run g1_deploy_onnx_ref lo policy/release/model_decoder.onnx reference/example/ "
                          "--obs-config policy/release/observation_config.yaml "
                          "--encoder-file policy/release/model_encoder.onnx "
                          "--planner-file planner/target_vel/V2/planner_sonic.onnx "
                          "--input-type zmq_manager --output-type all --zmq-host localhost --disable-crc-check "
                          f"--set-compliance {compliance}", logs["deploy"])
    wait_for(lambda: log_has(logs["deploy"], "Init Done"), 240, "deploy Init Done")
    tmux_new("g1-stream", f"cd {SONIC} && .venv_sim/bin/python {HERE}/stream_vr3.py --traj {traj} "
                          f"--go-file {run}/{tag}.go --stop-file {run}/{tag}.stop --done-file {run}/{tag}.done "
                          f"{extra_stream}", logs["stream"])
    wait_for(lambda: (run / f"{tag}.ready").exists(), 90, "sim ready (band released)")
    time.sleep(2)
    (run / f"{tag}.go").write_text("go\n")
    wait_for(lambda: (run / f"{tag}.done").exists() or (run / f"{tag}.episode.json").exists(), 120,
             "trajectory done")
    time.sleep(3.0)
    (run / f"{tag}.stop").write_text("stop\n")
    wait_for(lambda: (run / f"{tag}.episode.json").exists(), 60, "episode written")
    keys("g1-deploy", "o")
    time.sleep(1)
    kill_all()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--seeds", default="0-9")
    ap.add_argument("--rollouts", type=int, default=1)
    ap.add_argument("--compliance", default="0.05", help="VR 3-point compliance (0.01 rigid ... 0.5 compliant)")
    ap.add_argument("--stream-args", default="")
    a = ap.parse_args()
    run = Path(a.run_dir).resolve()
    run.mkdir(parents=True, exist_ok=True)
    for r in range(a.rollouts):
        for s in parse_range(a.seeds):
            if (run / f"seed{s}_r{r}.episode.json").exists():
                continue
            t0 = time.time()
            try:
                one_rollout(s, r, Path(a.traj.format(seed=s)).resolve(), run, a.compliance, a.stream_args)
                ok, err = True, None
            except Exception as e:
                ok, err = False, f"{type(e).__name__}: {e}"
                kill_all()
            row = {"seed": s, "rollout": r, "ok": ok, "error": err, "wall_s": round(time.time() - t0, 1)}
            print(json.dumps(row), flush=True)
            with open(run / "status.jsonl", "a") as f:
                f.write(json.dumps(row) + "\n")
