"""The G1 mimics a recorded person: RTMW3D joints (demo/tools/rtmw3d_export_joints.py) -> hands channel (live/hands_pub.py --replay) ->
"virtual VR headset" (live/g1_vr3pt.py: wrists and neck, right hand closes on a pinch) -> GEAR-SONIC whole-body policy -> G1 in MuJoCo,
recorded by g1/sim_runner.py. Same chain as the live webcam mode, fed from a file; runs inside the image (see g1/image_g1_mimic.sh).

    python3 live/g1_mimic_run.py --joints pose.npz --run-dir OUT [--fps 21.4]

Output: OUT/seed0_r0.mp4 (third-person | close-up), OUT/seed0_r0.episode.json, OUT/logs/*.
Honest limits: a monocular estimate drives the wrists and neck only (the legs are the policy's own balance planner); with the legs hidden or
the person's pose far from the robot's zero pose the robot may fall (seen on an earlier stock video); whether it falls on a given clip is reported, not assumed.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "g1"))
from run_trials import SONIC, TRT, keys, log_has, sh, tmux_new, wait_for  # noqa: E402

SESS = ("g1m-hands", "g1m-bridge", "g1m-deploy", "g1m-sim")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--joints", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--fps", type=float, default=None, help="replay rate (default: the npz fps)")
    ap.add_argument("--settle-s", type=float, default=6.0, help="seconds the robot balances before the replay starts")
    a = ap.parse_args()
    import numpy as np
    z = np.load(a.joints, allow_pickle=False)
    dur = len(z["joints"]) / float(a.fps or z["fps"])
    run = Path(a.run_dir).expanduser()
    logs = run / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    for s in SESS:
        sh(f"tmux kill-session -t ={s}")
    # the planner input (zmq_manager) must flow before control starts: bridge first, then sim + deploy
    tmux_new("g1m-bridge", f"cd {SONIC} && timeout {int(dur + 400)} .venv_sim/bin/python {ROOT}/live/g1_vr3pt.py "
                           f"--hands http://127.0.0.1:8092/hands.jsonl --auto-calib", logs / "bridge.log")
    tmux_new("g1m-sim", f"cd {SONIC} && MUJOCO_GL=egl .venv_sim/bin/python {ROOT}/g1/sim_runner.py --seed 0 "
                        f"--run-dir {run} --max-record-s {dur + a.settle_s + 240:.0f}", logs / "sim.log")
    time.sleep(3)
    tmux_new("g1m-deploy", f"cd {SONIC}/gear_sonic_deploy && export TensorRT_ROOT={TRT} && "
                           "bash deploy.sh --input-type zmq_manager --zmq-host localhost sim", logs / "deploy.log")
    wait_for(lambda: log_has(logs / "deploy.log", "Proceed with deployment"), 180, "deploy prompt")
    keys("g1m-deploy", "y", "Enter")
    wait_for(lambda: log_has(logs / "deploy.log", "Init Done"), 240, "deploy Init Done")
    time.sleep(1)
    keys("g1m-deploy", "]")
    wait_for(lambda: (run / "seed0_r0.ready").exists(), 60, "sim ready (band released)")
    time.sleep(a.settle_s)                                   # the robot stands under its own planner first
    fps = f"--replay-fps {a.fps}" if a.fps else ""
    tmux_new("g1m-hands", f"cd {ROOT} && {SONIC}/.venv_sim/bin/python live/hands_pub.py --replay {a.joints} --replay-once "
                          f"--port 8092 {fps}", logs / "hands.log")
    t_end = time.time() + dur + 30
    while time.time() < t_end and not sh("tmux has-session -t =g1m-hands").returncode:
        time.sleep(1)
    time.sleep(3)
    fell = sh("tmux has-session -t =g1m-sim").returncode != 0      # sim_runner ended on its own = a fall or a failure
    (run / "seed0_r0.stop").write_text("stop\n")
    try:
        wait_for(lambda: (run / "seed0_r0.episode.json").exists(), 90, "episode written")
    except Exception as e:
        print(f"[g1_mimic] {e}", flush=True)
    keys("g1m-deploy", "o")
    time.sleep(1)
    for s in SESS:
        sh(f"tmux kill-session -t ={s}")
    print(f"done: {run / 'seed0_r0.mp4'} (sim ended early / possible fall: {fell})", flush=True)


if __name__ == "__main__":
    main()
