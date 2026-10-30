"""Real-time session orchestrator, GPU VM side. Starts, in tmux sessions:
  live-sim     G1 GEAR-SONIC MuJoCo sim (g1/sim_runner.py) serving its view as MJPEG on :8093
  live-deploy  SONIC deploy (zmq input) — keypresses as in g1/run_trials.py
  live-hands   GEM-X live on the laptop camera (live/hands_pub.py, also streams SMPL v3 to SONIC) on :8092
  live-arm     UR arm following the right hand (live/arm_live.py) on :8091 (viewer page at /)
Expects the laptop webcam on 127.0.0.1:8090 through `ssh -R` (live/run_live_laptop.sh does that).

    python3 ~/transfergap_g1/live/run_live_vm.py [--no-g1] [--robot ur5e] [--minutes 30]
    python3 ~/transfergap_g1/live/run_live_vm.py --stop
Layout on the VM (synced by run_live_laptop.sh): ~/transfergap_g1/{g1,live,transfergap}; GEM-X at ~/GEM-X.
UNVERIFIED until the first live session (written 2026-10-02 from the verified G1 trial and GEM-X live commands).
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
INPUT = "zmq"
AUTO = ""
SESSIONS = ("live-orch", "live-rec", "live-arm", "live-g1bridge", "live-hands", "live-deploy", "live-sim")


def stop(keep_orch=False):
    sh("tmux send-keys -t =live-rec: C-c")           # finish the session video
    sh("tmux send-keys -t =live-arm: C-c")           # arm_live saves the session (joints + robot) on Ctrl-C
    sh("tmux send-keys -t =live-deploy: o")
    for _ in range(20):
        time.sleep(0.5)
        if sh("tmux has-session -t =live-arm").returncode:
            break
    for s in SESSIONS[1:] if keep_orch else SESSIONS:
        sh(f"tmux kill-session -t ={s}")
    sh("pkill -INT -f 'live/arm_live.py'")           # orphans outside tmux (e.g. after a lost tmux server)
    for _ in range(30):                              # let it finish writing the session files
        time.sleep(0.5)
        if sh("pgrep -f 'live/arm_live.py'").returncode:
            break
    pats = ("live/arm_live.py", "live/hands_pub.py", "live/g1_vr3pt.py", "g1/sim_runner.py", "g1_deploy_onnx_ref")
    for pat in pats:
        sh(f"pkill -f '{pat}'")
    time.sleep(2)
    for pat in pats:                                 # DDS threads can outlive SIGTERM; stale sims/deploys on the
        sh(f"pkill -9 -f '{pat}'")                   # same DDS domain make the robot fall instantly
    time.sleep(1)
    left = sh("pgrep -af 'sim_runner.py|deploy_onnx|g1_vr3pt|hands_pub|arm_live'").stdout.strip()
    if left:
        print(f"[stop] still running:\n{left}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-g1", action="store_true", help="arm only (no SONIC; GEM-X + arm listener)")
    ap.add_argument("--robot", default="ur5e")
    ap.add_argument("--grip", default="aperture")
    ap.add_argument("--minutes", type=float, default=30, help="hard stop for every process")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--supervise", action="store_true", help="stay running and restart the G1 after a fall")
    ap.add_argument("--g1-mode", default="vr3pt", choices=["vr3pt", "smpl"],
                    help="vr3pt: planner legs + upper body from wrists/neck (live/g1_vr3pt.py); smpl: full-body SMPL v3")
    ap.add_argument("--replay", default=None, help="joints .npz replayed instead of the camera (testing)")
    ap.add_argument("--estimator", default="gemx", choices=["gemx", "rtmw3d"],
                    help="rtmw3d: ~27 fps, needs a static full-body camera; vr3pt G1 mode only")
    a = ap.parse_args()
    if a.stop:
        stop()
        return
    run = Path.home() / "live_runs" / time.strftime("%Y%m%d_%H%M%S")
    logs = run / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    stop(keep_orch=True)
    secs = int(a.minutes * 60)
    global INPUT, AUTO
    INPUT = "zmq_manager" if a.g1_mode == "vr3pt" else "zmq"
    AUTO = " --auto-calib" if a.replay else ""        # replays have nobody to press the calibration button
    if not a.no_g1 and a.g1_mode == "vr3pt":            # planner input must flow before control starts
        tmux_new("live-g1bridge", f"cd {SONIC} && timeout {secs} .venv_sim/bin/python {ROOT}/live/g1_vr3pt.py "
                                  f"--hands http://127.0.0.1:8092/hands.jsonl{AUTO}", logs / "g1bridge.log")
    if not a.no_g1:
        start_g1(run, logs, secs)
    sonic = f"--stream-sonic --sonic-root {SONIC}" if (not a.no_g1 and a.g1_mode == "smpl") else ""
    if a.replay:
        tmux_new("live-hands", f"cd {ROOT} && timeout {secs} {SONIC}/.venv_sim/bin/python live/hands_pub.py "
                               f"--replay {a.replay} --port 8092", logs / "hands.log")
    elif a.estimator == "rtmw3d":
        tmux_new("live-hands", f"cd ~/rtmpose3d && source .venv/bin/activate && timeout {secs} python "
                               f"{ROOT}/live/hands_pub.py --estimator rtmw3d "
                               f"--source http://127.0.0.1:8090/stream.mjpg --port 8092", logs / "hands.log")
    else:
        tmux_new("live-hands", f"cd {GEMX} && source .venv/bin/activate && timeout {secs} python {ROOT}/live/hands_pub.py "
                               f"--gemx-root {GEMX} --upstream {SONIC}/gear_sonic/examples/live_camera_teleop "
                               f"--source http://127.0.0.1:8090/stream.mjpg --port 8092 {sonic}", logs / "hands.log")
    tmux_new("live-arm", f"cd {ROOT} && MUJOCO_GL=egl PYTHONPATH=. timeout -s INT {secs} {SONIC}/.venv_sim/bin/python "
                         f"live/arm_live.py --robot {a.robot} --grip {a.grip} --port 8091 --out {run}"
                         + (" --auto-calib" if a.replay else ""), logs / "arm.log")
    if not a.no_g1 and a.g1_mode == "smpl":
        wait_for(lambda: log_has(logs / "hands.log", "poses"), 300, "first live pose")
        enable_stream(logs)
    views = " ".join(f"http://127.0.0.1:{p}" for p in ("8092/cam.jpg", "8091/robot.jpg") +
                     (() if a.no_g1 else ("8093/g1.jpg",)))
    tmux_new("live-rec", f"cd {run} && sleep 20 && {SONIC}/.venv_sim/bin/python {ROOT}/live/record.py "
                         f"--out session_video.mp4 --seconds {secs} --views {views}", logs / "rec.log")
    print(f"live session up; logs in {logs}; viewer: http://127.0.0.1:8091/ (via ssh -L); stop with --stop",
          flush=True)
    if a.no_g1 or not a.supervise:
        return
    t_end, n = time.time() + secs, 0                 # G1 supervisor: a fall ends sim_runner -> restart sim + deploy
    while time.time() < t_end:
        time.sleep(2)
        if sh("tmux has-session -t =live-sim").returncode:
            n += 1
            print(f"[supervisor] G1 sim ended (fall or stop) -> restart #{n}", flush=True)
            sh("tmux kill-session -t =live-deploy")
            time.sleep(2)
            sub = run / f"g1_restart{n}"
            (sub / "logs").mkdir(parents=True, exist_ok=True)
            try:
                if INPUT != "zmq":                   # fresh bridge first: idle planner input, then re-calibration
                    tmux_new("live-g1bridge", f"cd {SONIC} && timeout {int(t_end - time.time())} .venv_sim/bin/python "
                                              f"{ROOT}/live/g1_vr3pt.py --hands http://127.0.0.1:8092/hands.jsonl{AUTO}",
                             sub / "logs" / "g1bridge.log")
                start_g1(sub, sub / "logs", int(t_end - time.time()))
                if INPUT == "zmq":
                    enable_stream(sub / "logs")
            except Exception as e:                   # keep supervising; arm + camera stay live meanwhile
                print(f"[supervisor] restart failed: {e}", flush=True)


def enable_stream(logs):
    time.sleep(2)
    keys("live-deploy", "Enter")
    wait_for(lambda: log_has(logs / "deploy.log", "ZMQ STREAMING MODE: ENABLED"), 10, "streaming enabled")


def start_g1(run, logs, secs):
    if True:  # noqa: SIM108
        tmux_new("live-sim", f"cd {SONIC} && MUJOCO_GL=egl timeout {secs} .venv_sim/bin/python {ROOT}/g1/sim_runner.py "
                             f"--seed 0 --run-dir {run} --no-video --mjpeg-port 8093 --max-record-s {secs}",
                 logs / "sim.log")
        time.sleep(3)
        tmux_new("live-deploy", f"cd {SONIC}/gear_sonic_deploy && export TensorRT_ROOT={TRT} && "
                                f"bash deploy.sh --input-type {INPUT} --zmq-host localhost sim", logs / "deploy.log")
        wait_for(lambda: log_has(logs / "deploy.log", "Proceed with deployment"), 180, "deploy prompt")
        keys("live-deploy", "y", "Enter")
        wait_for(lambda: log_has(logs / "deploy.log", "Init Done"), 240, "deploy Init Done")
        time.sleep(1)
        keys("live-deploy", "]")
        wait_for(lambda: (run / "seed0_r0.ready").exists(), 60, "sim ready (band released)")


if __name__ == "__main__":
    main()
