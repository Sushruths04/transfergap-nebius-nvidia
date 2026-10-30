"""Live fingertip retargeting: your hand keypoints (hands.jsonl `hands_detail`, from live/hands_pub.py) -> the Allegro robot hand, rendered
and served as MJPEG (/hand.mjpg) on --port. Kinematics only (no contact). CPU solve (~3 ms/frame) + EGL render.

    cd transfergap && MUJOCO_GL=egl PYTHONPATH=. python live/hand_live.py --model /ws/.../allegro/scene_right.xml --port 8094
"""
import argparse
import sys
import threading
import time
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hand_ik import HandIK  # noqa: E402
from hub import Hub, read_jsonl  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hands", default="http://127.0.0.1:8092/hands.jsonl")
    ap.add_argument("--model", required=True)
    ap.add_argument("--port", type=int, default=8094)
    ap.add_argument("--side", default="Right", choices=["Right", "Left"])
    ap.add_argument("--fps", type=float, default=15.0)
    ap.add_argument("--seconds", type=float, default=0)
    a = ap.parse_args()
    hub = Hub(a.port)
    ik = HandIK(a.model)
    st = {"kp": None, "n": 0, "err": {}, "t": 0.0}
    lock = threading.Lock()

    def on_msg(msg):
        hd = (msg.get("hands_detail") or {}).get(a.side)
        if not hd:
            return
        with lock:
            st["kp"], st["t"] = np.array(hd["kp"], float), time.time()

    threading.Thread(target=read_jsonl, args=(a.hands, on_msg), daemon=True).start()
    r = mujoco.Renderer(ik.m, 360, 360)
    cam = mujoco.MjvCamera()
    cam.lookat[:] = ik.org + 0.06 * ik.Rr[:, 0]          # fixed point in front of the palm (fingers move around it)
    cam.distance, cam.azimuth, cam.elevation = 0.42, 150, -40
    print(f"[hand_live] http://127.0.0.1:{a.port}/hand.mjpg  waiting for {a.hands}", flush=True)
    t0 = time.time()
    while not a.seconds or time.time() - t0 < a.seconds:
        t = time.time()
        with lock:
            kp, seen = st["kp"], st["t"]
            st["kp"] = None
        if kp is not None:
            _, e = ik.step(kp)
            st["n"] += 1
            st["err"] = e
        mujoco.mj_forward(ik.m, ik.d)
        r.update_scene(ik.d, camera=cam)
        hub.put_jpeg("hand", r.render())
        hub.put_json("hand_status", {"frames": st["n"], "scale": round(ik.scale, 3), "fingertip_err_cm": {k: round(v, 2) for k, v in st["err"].items()},
                                     "age_s": round(time.time() - seen, 2) if seen else None})
        time.sleep(max(0.0, 1.0 / a.fps - (time.time() - t)))


if __name__ == "__main__":
    main()
