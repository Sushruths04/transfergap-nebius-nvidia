"""Laptop side of the cluster real-time mode: read a webcam (or a video file) and POST JPEG frames to the relay in the pod.

    kubectl port-forward -n isaac-sim deploy/tg-dev 8095:8090 &      # relay port in the pod -> laptop
    python3 live/push_cam.py --source 0 --url http://127.0.0.1:8095/push
    python3 live/push_cam.py --source clip.mp4 --loop                  # test with a file (no webcam needed)

Only the frames you choose to send leave the laptop, and only to the port-forwarded relay. Ctrl-C stops it.
A dropped connection is retried; frames are never queued (a late frame is worse than a skipped one).
"""
import argparse
import time
import http.client
import queue
import threading
import urllib.parse

import cv2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0")
    ap.add_argument("--url", default="http://127.0.0.1:8095/push")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--fps", type=float, default=15.0)
    ap.add_argument("--quality", type=int, default=70)
    ap.add_argument("--loop", action="store_true", help="file source: restart at the end")
    ap.add_argument("--workers", type=int, default=4, help="parallel connections")
    ap.add_argument("--seconds", type=float, default=0, help="stop after N s (0 = until Ctrl-C)")
    a = ap.parse_args()
    cam = a.source.isdigit()
    cap = cv2.VideoCapture(int(a.source) if cam else a.source)
    if cam:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        raise SystemExit(f"cannot open source {a.source}")
    u = urllib.parse.urlparse(a.url)
    q, stats = queue.Queue(maxsize=a.workers), {"sent": 0, "fails": 0}

    def worker():                       # each worker has its own persistent connection: a round trip through the
        conn = None                     # port-forward is ~100 ms, so several in flight keep the frame rate up
        while True:
            seq, jpg = q.get()
            try:
                if conn is None:
                    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=5)
                conn.request("POST", u.path, body=jpg, headers={"Content-Type": "image/jpeg", "X-Seq": str(seq)})
                conn.getresponse().read()
                stats["sent"] += 1
            except Exception as e:      # port-forward dropped: reconnect, never queue stale frames
                stats["fails"] += 1
                conn = None
                if stats["fails"] % 20 == 1:
                    print(f"push failed ({e}); retrying", flush=True)
                time.sleep(0.5)

    for _ in range(a.workers):
        threading.Thread(target=worker, daemon=True).start()
    seq = 0
    period, t_end, t_last = 1.0 / a.fps, (time.time() + a.seconds if a.seconds else None), 0.0
    while t_end is None or time.time() < t_end:
        t0 = time.time()
        ok, f = cap.read()
        if not ok:
            if a.loop and not cam:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            break
        if cam and t0 - t_last < period:      # read every camera frame so the driver never queues, send at --fps
            continue
        t_last = t0
        if a.width and f.shape[1] > a.width:
            f = cv2.resize(f, (a.width, int(f.shape[0] * a.width / f.shape[1])))
        jpg = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, a.quality])[1].tobytes()
        seq += 1
        try:
            q.put_nowait((seq, jpg))
        except queue.Full:               # all workers busy: drop this frame (a late frame is worse than a skipped one)
            pass
        if not cam:
            time.sleep(max(0.0, period - (time.time() - t0)))
    print(f"sent {stats['sent']} frames, {stats['fails']} failures")


if __name__ == "__main__":
    main()
