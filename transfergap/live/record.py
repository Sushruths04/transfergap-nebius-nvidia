"""Record the live views side by side at a fixed wall-clock frame rate (each view's newest frame, sampled every
1/fps s), so streams with different rates stay in sync. Needs Pillow and ffmpeg; run where the hubs are reachable.

    python live/record.py --out live_demo.mp4 --seconds 90 \
        --views http://127.0.0.1:8092/cam.jpg http://127.0.0.1:8091/robot.jpg http://127.0.0.1:8093/g1.jpg
"""
import argparse
import io
import subprocess
import time
import urllib.request

import numpy as np
from PIL import Image


def grab(url, h):
    try:
        im = Image.open(io.BytesIO(urllib.request.urlopen(url, timeout=1).read())).convert("RGB")
        return im.resize((int(im.width * h / im.height) // 2 * 2, h))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--fps", type=float, default=15)
    ap.add_argument("--height", type=int, default=360)
    a = ap.parse_args()
    last = [None] * len(a.views)
    while any(x is None for x in last):
        last = [grab(u, a.height) or x for u, x in zip(a.views, last)]
        time.sleep(0.2)
    W = sum(x.width for x in last)
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                          f"{W}x{a.height}", "-r", str(a.fps), "-i", "-", "-c:v", "libx264", "-crf", "22",
                          "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)
    t0, n = time.time(), 0
    try:                                       # Ctrl-C / SIGINT ends the recording cleanly (valid mp4)
        while n < a.seconds * a.fps:
            last = [grab(u, a.height) or x for u, x in zip(a.views, last)]
            p.stdin.write(np.concatenate([np.asarray(x) for x in last], axis=1).tobytes())
            n += 1
            time.sleep(max(0.0, t0 + n / a.fps - time.time()))
    except KeyboardInterrupt:
        pass
    p.stdin.close()
    p.wait()
    print(f"wrote {a.out}: {n} frames, {n / a.fps:.0f} s")


if __name__ == "__main__":
    main()
