"""Record the person locally at full quality (no network): countdown + live preview window, then N seconds of video.

    python3 live/record_cam.py --source 4 --seconds 45 --out runs/videos/user_take1.mp4
"""
import argparse
import time

import cv2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=int, default=4)
    ap.add_argument("--seconds", type=float, default=45)
    ap.add_argument("--countdown", type=float, default=10)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1280x720")
    a = ap.parse_args()
    w, h = map(int, a.size.split("x"))
    cap = cv2.VideoCapture(a.source)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS, 30)
    w, h = int(cap.get(3)), int(cap.get(4))
    out = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (w, h))
    cv2.namedWindow("recording", cv2.WINDOW_NORMAL)
    t0, n = time.time(), 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        el = time.time() - t0
        vis = f.copy()
        if el < a.countdown:
            msg = f"get in position: {a.countdown - el:.0f}"
        else:
            out.write(f)
            n += 1
            msg = f"REC {el - a.countdown:4.1f} / {a.seconds:.0f} s"
            if el - a.countdown >= a.seconds:
                break
        cv2.putText(vis, msg, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 4)
        cv2.imshow("recording", vis)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    out.release()
    cap.release()
    cv2.destroyAllWindows()
    print(f"wrote {a.out}: {n} frames ({w}x{h}), {n / max(a.seconds, 1e-6):.1f} fps")


if __name__ == "__main__":
    main()
