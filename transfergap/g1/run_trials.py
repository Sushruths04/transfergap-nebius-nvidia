"""Run G1 contact trials on the GPU VM: for each (seed, rollout) start sim, SONIC deploy and the streamer.

Each rollout is a fresh process set (sim_runner.py, deploy.sh, stream_motion.py) in tmux sessions
g1-sim / g1-deploy / g1-stream, because the deploy binary keeps internal state and the sim has no
clean in-place reset. Keypresses follow the upstream ZMQ tutorial (docs/source/tutorials/zmq.md):
answer the deploy.sh [Y/n] prompt, ']' to start control, ENTER to enable ZMQ streaming.

    python ~/transfergap_g1/g1/run_trials.py --traj RUN/reach_nominal.npz --run-dir RUN --seeds 0-9 --rollouts 3
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
from pathlib import Path

HOME = Path.home()
SONIC = HOME / "GR00T-WholeBodyControl"
HERE = Path(__file__).resolve().parent
TRT = HOME / "TensorRT-10.13.3.9"


def sh(cmd, check=False):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)


def tmux_new(name, cmd, log):
    sh(f"tmux kill-session -t ={name}")
    full = f"{cmd} 2>&1 | tee {shlex.quote(str(log))}"
    subprocess.run(["tmux", "new-session", "-d", "-s", name, "-x", "220", "-y", "50", "bash", "-lc", full],
                   check=True)


def keys(name, *k):
    subprocess.run(["tmux", "send-keys", "-t", f"={name}:", *k], check=True)


def wait_for(pred, timeout, what):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return time.time() - t0
        time.sleep(0.5)
    raise TimeoutError(what)


def log_has(log, text):
    try:
        return text in Path(log).read_text(errors="ignore")
    except FileNotFoundError:
        return False


def kill_all():
    for s in ("g1-stream", "g1-deploy", "g1-sim"):
        sh(f"tmux kill-session -t ={s}")
    time.sleep(2)


def one_rollout(seed, rollout, traj, run, cl=None):
    tag = f"seed{seed}_r{rollout}"
    logs = {k: run / "logs" / f"{tag}.{k}.log" for k in ("sim", "deploy", "stream")}
    (run / "logs").mkdir(parents=True, exist_ok=True)
    for f in (f"{tag}.ready", f"{tag}.stop", f"{tag}.go", f"{tag}.done"):
        (run / f).unlink(missing_ok=True)
    kill_all()
    tmux_new("g1-sim", f"cd {SONIC} && MUJOCO_GL=egl .venv_sim/bin/python {HERE}/sim_runner.py "
                       f"--seed {seed} --rollout {rollout} --run-dir {run}" + (" --state-port 5601" if cl is not None else ""), logs["sim"])
    time.sleep(3)
    tmux_new("g1-deploy", f"cd {SONIC}/gear_sonic_deploy && export TensorRT_ROOT={TRT} && "
                          "bash deploy.sh --input-type zmq --zmq-host localhost sim", logs["deploy"])
    wait_for(lambda: log_has(logs["deploy"], "Proceed with deployment"), 180, "deploy prompt")
    keys("g1-deploy", "y", "Enter")
    wait_for(lambda: log_has(logs["deploy"], "Init Done"), 240, "deploy Init Done")
    time.sleep(1)
    keys("g1-deploy", "]")
    wait_for(lambda: (run / f"{tag}.ready").exists(), 60, "sim ready (band released)")
    streamer = f"stream_cl.py --state-port 5601 --log {run}/{tag}.cl.npz {cl.format(seed=seed)} " if cl is not None else "stream_motion.py "
    tmux_new("g1-stream", f"cd {SONIC} && .venv_sim/bin/python {HERE}/{streamer}--traj {traj} "
                          f"--go-file {run}/{tag}.go --stop-file {run}/{tag}.stop --done-file {run}/{tag}.done",
             logs["stream"])
    time.sleep(2)
    keys("g1-deploy", "Enter")
    wait_for(lambda: log_has(logs["deploy"], "ZMQ STREAMING MODE: ENABLED"), 10, "streaming enabled")
    time.sleep(0.5)
    (run / f"{tag}.go").write_text("go\n")
    wait_for(lambda: (run / f"{tag}.done").exists() or (run / f"{tag}.episode.json").exists(), 120,
             "trajectory done")
    time.sleep(3.0)                                      # settle time recorded after the motion ends
    (run / f"{tag}.stop").write_text("stop\n")
    wait_for(lambda: (run / f"{tag}.episode.json").exists(), 60, "episode written")
    keys("g1-deploy", "o")
    time.sleep(1)
    kill_all()


def parse_range(s):
    out = []
    for part in s.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--seeds", default="0-9")
    ap.add_argument("--rollouts", type=int, default=3)
    ap.add_argument("--closed-loop", default=None, metavar="ARGS",
                    help="use stream_cl.py (proprioceptive correction); value = extra streamer args, e.g. '--ki 1.5'")
    a = ap.parse_args()
    run = Path(a.run_dir).resolve()
    run.mkdir(parents=True, exist_ok=True)
    status = []
    for r in range(a.rollouts):                         # interleave rollouts so drift over time spreads evenly
        for s in parse_range(a.seeds):
            if (run / f"seed{s}_r{r}.episode.json").exists():
                continue
            t0 = time.time()
            try:
                one_rollout(s, r, Path(a.traj.format(seed=s)).resolve(), run, a.closed_loop)   # {seed} = per-seed plan
                ok = True
                err = None
            except Exception as e:                       # record and continue; a failed launch is not a trial
                ok, err = False, f"{type(e).__name__}: {e}"
                kill_all()
            status.append({"seed": s, "rollout": r, "ok": ok, "error": err, "wall_s": round(time.time() - t0, 1)})
            print(json.dumps(status[-1]), flush=True)
            with open(run / "status.jsonl", "a") as f:
                f.write(json.dumps(status[-1]) + "\n")
