"""Record a clip for TransferGap with a USB webcam (e.g. Logitech Brio 100), with live checks, and save a CONSTANT 30 fps file.

    python3 scripts/record_clip.py --list                         # which camera index is which (opens each one for a moment)
    python3 scripts/record_clip.py --camera 2 --out take01.mp4 [--seconds 20] [--marker-cm 12] [--width 1920 --height 1080]
    python3 scripts/record_clip.py --source some_video.mp4 --out test.mp4   # dry run on a file: no camera is opened

Preview window (press SPACE to start recording, Q to quit): shows whether the printed marker is found, the real camera frame rate and warnings.
Keep the camera on a tripod, no zoom, the upper body and the whole table in view, marker flat on the table, first 3 seconds still.
Why constant 30 fps: webcams drop their frame rate in dim light (the first clip was 21.4 fps); the pose and timing code expects a fixed rate. Frames are
resampled to 30 fps by timestamp (nearest frame) and the achieved camera fps is written next to the video (<out>.json); below 27 fps it warns: add light.
Runs locally on the laptop, light CPU, no network.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

OUT_FPS = 30.0


def resample_to_cfr(times, fps=OUT_FPS):
    """For frame timestamps (s, increasing) return the index of the frame to show at each output tick of a constant `fps` stream (nearest in time)."""
    t = np.asarray(times, float)
    t = t - t[0]
    ticks = np.arange(0.0, t[-1] + 1e-9, 1.0 / fps)
    j = np.searchsorted(t, ticks)
    j = np.clip(j, 1, len(t) - 1)
    pick = np.where(np.abs(t[j] - ticks) < np.abs(t[j - 1] - ticks), j, j - 1)
    return pick.astype(int)


def achieved_fps(times):
    t = np.asarray(times, float)
    return float((len(t) - 1) / (t[-1] - t[0])) if len(t) > 1 and t[-1] > t[0] else 0.0


def list_cameras(n=6):
    import cv2
    for i in range(n):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ok, f = cap.read()
            print(f"camera {i}: opens, frame {None if not ok else f.shape[1]}x{None if not ok else f.shape[0]}")
        cap.release()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--source", help="a video file instead of a camera (dry run)")
    ap.add_argument("--out", default="take.mp4")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--marker-cm", type=float, default=12.0)
    ap.add_argument("--no-preview", action="store_true", help="no window (for the dry run); recording starts at once")
    a = ap.parse_args()
    import cv2
    if a.list:
        list_cameras()
        return
    from transfergap.human import marker as M
    cap = cv2.VideoCapture(a.source) if a.source else cv2.VideoCapture(a.camera, cv2.CAP_V4L2)
    if not a.source:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))     # YUYV caps at a few fps in 1080p; MJPG gives 30 fps
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, a.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, a.height)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        raise SystemExit("cannot open the camera: run --list, check the cable, close other apps that use it")
    frames, times, recording = [], [], a.no_preview
    t_start = None
    fps_win = []
    while True:
        ok, f = cap.read()
        now = time.time()
        if not ok:
            break
        fps_win = (fps_win + [now])[-30:]
        cur = (len(fps_win) - 1) / (fps_win[-1] - fps_win[0]) if len(fps_win) > 5 and fps_win[-1] > fps_win[0] else 0.0
        if recording:
            frames.append(f)
            times.append(now)
            t_start = t_start or now
            if now - t_start >= a.seconds:
                break
        if not a.no_preview:
            c = M.detect(f)
            vis = f.copy()
            msg = [f"camera {cur:4.1f} fps" + ("   <- LOW: add light" if 0 < cur < 27 and not a.source else ""),
                   "marker FOUND" if c is not None else "marker NOT found (flat on the table, in view, printed at 100%)",
                   "RECORDING" if recording else "SPACE = start, Q = quit"]
            if c is not None:
                cv2.polylines(vis, [c.astype(np.int32)], True, (0, 255, 0), 3)
            for i, s in enumerate(msg):
                cv2.putText(vis, s, (20, 40 + 40 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255) if i == 2 else (255, 255, 255), 2, cv2.LINE_AA)
            cv2.imshow("TransferGap recorder", cv2.resize(vis, (960, int(960 * f.shape[0] / f.shape[1]))))
            k = cv2.waitKey(1) & 0xFF
            if k == ord("q"):
                break
            if k == ord(" ") and not recording:
                recording = True
    cap.release()
    if not a.no_preview:
        cv2.destroyAllWindows()
    if len(frames) < 10:
        raise SystemExit("nothing recorded")
    pick = resample_to_cfr(times)
    h, w = frames[0].shape[:2]
    vw = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"mp4v"), OUT_FPS, (w, h))
    for j in pick:
        vw.write(frames[j])
    vw.release()
    info = {"file": a.out, "size": [w, h], "camera_fps_achieved": round(achieved_fps(times), 2), "output_fps": OUT_FPS, "frames_out": int(len(pick)),
            "seconds": round(len(pick) / OUT_FPS, 2), "marker_cm": a.marker_cm, "dropped_or_duplicated": int(abs(len(pick) - len(frames)))}
    Path(a.out).with_suffix(".json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info, indent=1))
    if info["camera_fps_achieved"] < 27 and not a.source:
        print("WARNING: the camera delivered under 27 fps (dim light?). Add light and record again.")


if __name__ == "__main__":
    main()
