"""Offline full-body G1 replay of a recorded person (VM): GEM-X hpe_results.pt -> SMPL v3 stream (upstream
soma_pt_to_sonic_v3.py) -> SONIC whole-body tracking -> G1 in MuJoCo, recorded by g1/sim_runner.py (third-person |
close-up mp4). Unlike the live 3-point mode, the legs follow the person too (steps, squats, turns).

    python3 ~/transfergap_g1/live/g1_replay.py --pt ~/GEM-X/outputs/demo_soma/user_take1/hpe_results.pt --fps 21.4 \
        --run-dir ~/live_runs/replay_take1
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "g1"))
from run_trials import SONIC, TRT, keys, log_has, sh, tmux_new, wait_for  # noqa: E402

GEMX = Path.home() / "GEM-X"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pt", required=True)
    ap.add_argument("--fps", type=float, required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--seconds", type=float, default=None, help="clip length (default: frames / fps)")
    ap.add_argument("--smooth", type=float, default=0.5)
    a = ap.parse_args()
    run = Path(a.run_dir).expanduser()
    logs = run / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    if a.seconds is None:
        import subprocess
        n = subprocess.check_output([str(GEMX / ".venv/bin/python"), "-c",
                                     f"import torch;p=torch.load('{a.pt}',weights_only=False);"
                                     "print(p['body_params_global']['body_pose'].shape[0])"], text=True).strip()
        a.seconds = int(n.splitlines()[-1]) / a.fps
    for s in ("g1-stream", "g1-deploy", "g1-sim"):
        sh(f"tmux kill-session -t ={s}")
    tmux_new("g1-sim", f"cd {SONIC} && MUJOCO_GL=egl .venv_sim/bin/python {ROOT}/g1/sim_runner.py --seed 0 "
                       f"--run-dir {run} --max-record-s {a.seconds + 240:.0f}", logs / "sim.log")
    time.sleep(3)
    tmux_new("g1-deploy", f"cd {SONIC}/gear_sonic_deploy && export TensorRT_ROOT={TRT} && "
                          "bash deploy.sh --input-type zmq --zmq-host localhost sim", logs / "deploy.log")
    wait_for(lambda: log_has(logs / "deploy.log", "Proceed with deployment"), 180, "deploy prompt")
    keys("g1-deploy", "y", "Enter")
    wait_for(lambda: log_has(logs / "deploy.log", "Init Done"), 240, "deploy Init Done")
    time.sleep(1)
    keys("g1-deploy", "]")
    wait_for(lambda: (run / "seed0_r0.ready").exists(), 60, "sim ready")
    go, done = run / "go", run / "done"
    go.unlink(missing_ok=True)
    done.unlink(missing_ok=True)
    tmux_new("g1-stream", f"cd {SONIC} && source {GEMX}/.venv/bin/activate && python {ROOT}/live/pt_stream.py "
                          f"--gemx-root {GEMX} --sonic-root {SONIC} --pt {a.pt} --fps {a.fps} --smooth {a.smooth} "
                          f"--go-file {go} --done-file {done}", logs / "stream.log")
    wait_for(lambda: log_has(logs / "stream.log", "holding the first pose"), 300, "stream holding first pose")
    time.sleep(3)                                     # robot settles into the person's first pose... after ENTER
    keys("g1-deploy", "Enter")
    wait_for(lambda: log_has(logs / "deploy.log", "ZMQ STREAMING MODE: ENABLED"), 20, "streaming enabled")
    time.sleep(3)                                     # let the robot align to the held first pose
    go.write_text("go\n")
    wait_for(lambda: done.exists(), a.seconds + 120, "replay finished")
    time.sleep(3)
    (run / "seed0_r0.stop").write_text("stop\n")
    wait_for(lambda: (run / "seed0_r0.episode.json").exists(), 60, "episode written")
    keys("g1-deploy", "o")
    time.sleep(1)
    for s in ("g1-stream", "g1-deploy", "g1-sim"):
        sh(f"tmux kill-session -t ={s}")
    print(f"done: {run / 'seed0_r0.mp4'}", flush=True)


if __name__ == "__main__":
    main()
