"""Stream a planned G1 joint-space motion to the SONIC deploy binary over ZMQ (protocol v1 + Dex3 hands).

Open loop: reads only the trajectory file and two signalling files (go/stop) written by the
orchestrator. It never reads simulator state. Message packing uses the upstream packer
gear_sonic.utils.teleop.zmq.zmq_planner_sender.pack_pose_message, same wire format as the GEM-X bridge.

Until the go-file exists the first frame is repeated (the robot holds the start pose); afterwards
the trajectory plays at 50 Hz, then the last frame is repeated until the stop-file exists.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import zmq

from gear_sonic.utils.teleop.zmq.zmq_planner_sender import pack_pose_message


def message(traj, k, frame_index):
    return pack_pose_message({
        "joint_pos": traj["joint_pos"][k:k + 1].astype(np.float32),
        "joint_vel": traj["joint_vel"][k:k + 1].astype(np.float32),
        "body_quat": np.array([[1.0, 0.0, 0.0, 0.0]], np.float32),     # upright pelvis, wxyz
        "frame_index": np.array([frame_index], np.int64),
        "left_hand_joints": traj["left_hand"][k:k + 1].astype(np.float32),
        "right_hand_joints": traj["right_hand"][k:k + 1].astype(np.float32),
    }, topic="pose", version=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", required=True)
    ap.add_argument("--port", type=int, default=5556)        # deploy.sh --input-type zmq subscribes here
    ap.add_argument("--go-file", required=True)
    ap.add_argument("--stop-file", required=True)
    ap.add_argument("--done-file", required=True)
    ap.add_argument("--fps", type=float, default=50.0)
    a = ap.parse_args()
    traj = dict(np.load(a.traj))
    T = len(traj["joint_pos"])
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUB)
    sock.bind(f"tcp://*:{a.port}")
    dt, fi, k = 1.0 / a.fps, 0, 0
    go, stop, done = Path(a.go_file), Path(a.stop_file), Path(a.done_file)
    t_next = time.monotonic()
    started = None
    while not stop.exists():
        if started is None and go.exists():
            started = time.time()
            print(f"[stream] go: playing {T} frames", flush=True)
        sock.send(message(traj, k, fi))
        fi += 1
        if started is not None and k < T - 1:
            k += 1
            if k == T - 1:
                done.write_text(json.dumps({"frames": T, "play_s": time.time() - started}))
                print("[stream] trajectory finished; holding last frame", flush=True)
        t_next += dt
        time.sleep(max(0.0, t_next - time.monotonic()))
    sock.close(0)
    ctx.term()


if __name__ == "__main__":
    main()
