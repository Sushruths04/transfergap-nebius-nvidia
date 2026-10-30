"""Laptop side of the real-time mode: serve a camera (or a video file, for testing) as an MJPEG stream on
127.0.0.1 so the GPU VM can read it through an SSH reverse tunnel:

    python3 live/cam_server.py --source 0 --port 8090            # webcam (only with the user present)
    python3 live/cam_server.py --source demo_input/clip.mp4       # test with a file (loops)
    ssh -i ~/.ssh/transfergap_gpu -R 8090:127.0.0.1:8090 ubuntu@<vm-ip>
    # on the VM: webcam_stream.py --source http://127.0.0.1:8090/stream.mjpg --stream-sonic ...

Uses system OpenCV (python3 -c "import cv2"). Binds to 127.0.0.1 only; nothing is exposed to the network.
"""
import argparse
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

LATEST = {"jpg": None, "n": 0}


def grab(source, width, fps, quality):
    cap = cv2.VideoCapture(int(source)) if source.isdigit() else cv2.VideoCapture(source)
    if source.isdigit():
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)      # newest frame, no driver queue
    if not cap.isOpened():
        raise SystemExit(f"cannot open source {source}")
    period, t_pub = 1.0 / fps, 0.0
    camera = source.isdigit()
    while True:
        t0 = time.time()
        ok, frame = cap.read()                       # a camera: read EVERY frame (blocks at the camera rate) so the
        if not ok:                                   # driver never queues stale frames; publish only at `fps`
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)      # file source: loop
            continue
        if camera and time.time() - t_pub < period:
            continue
        t_pub = time.time()
        if width and frame.shape[1] > width:
            frame = cv2.resize(frame, (width, int(frame.shape[0] * width / frame.shape[1])))
        LATEST["jpg"] = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])[1].tobytes()
        LATEST["n"] += 1
        if not camera:                               # a file plays at `fps`
            time.sleep(max(0.0, period - (time.time() - t0)))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith("/stream.mjpg"):
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        last = -1
        try:
            while True:
                if LATEST["n"] != last and LATEST["jpg"] is not None:
                    last = LATEST["n"]
                    jpg = LATEST["jpg"]
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " +
                                     str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
                time.sleep(0.005)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--width", type=int, default=960)
    ap.add_argument("--fps", type=float, default=25.0)
    ap.add_argument("--quality", type=int, default=80)
    a = ap.parse_args()
    threading.Thread(target=grab, args=(a.source, a.width, a.fps, a.quality), daemon=True).start()
    print(f"MJPEG on http://127.0.0.1:{a.port}/stream.mjpg (source {a.source})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
