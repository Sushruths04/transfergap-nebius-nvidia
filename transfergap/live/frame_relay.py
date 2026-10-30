"""Pod side of the cluster real-time mode. A cluster pod cannot open a connection to the laptop, so the laptop PUSHES its
camera frames (live/push_cam.py, through `kubectl port-forward`) and this relay serves them as the same MJPEG stream the
rest of the live code already reads (hands_pub.py --source http://127.0.0.1:8090/stream.mjpg).

    python3 live/frame_relay.py --port 8090          # POST /push (one JPEG per request) ; GET /stream.mjpg ; GET /status

Binds to 127.0.0.1 only. A frame older than STALE_S is not re-sent as new. /status = {"frames", "age_s"} for health checks.
"""
import argparse
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LATEST = {"jpg": None, "n": 0, "t": 0.0}
LOCK = threading.Lock()
MAX_BYTES = 4_000_000


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"             # keep-alive: one connection carries all pushed frames
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        if self.path != "/push" or not 0 < n <= MAX_BYTES:
            self.send_error(400)
            return
        body = self.rfile.read(n)
        if body[:2] != b"\xff\xd8":
            self.send_error(415)
            return
        seq = int(self.headers.get("X-Seq", 0))
        with LOCK:
            if seq and seq < LATEST.get("seq", 0):     # parallel connections can deliver out of order: keep the newest
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            LATEST.update(jpg=body, n=LATEST["n"] + 1, t=time.time(), seq=seq or LATEST.get("seq", 0))
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/status"):
            with LOCK:
                s = {"frames": LATEST["n"], "age_s": round(time.time() - LATEST["t"], 2) if LATEST["n"] else None}
            b = str(s).replace("'", '"').replace("None", "null").encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        if not self.path.startswith("/stream.mjpg"):
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Connection", "close")
        self.end_headers()
        last = -1
        try:
            while True:
                with LOCK:
                    n, jpg = LATEST["n"], LATEST["jpg"]
                if n != last and jpg is not None:
                    last = n
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " +
                                     str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
                time.sleep(0.005)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8090)
    a = ap.parse_args()
    print(f"relay on 127.0.0.1:{a.port} (POST /push, GET /stream.mjpg)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
