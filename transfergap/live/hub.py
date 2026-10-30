"""Latest-wins HTTP hub for the real-time mode (stdlib only, binds 127.0.0.1; reach it through ssh -L / -R).

Channels are named; a producer calls hub.put_jpeg(name, rgb_or_jpeg) or hub.put_json(name, dict). Clients get
  /<name>.mjpg     multipart MJPEG (only the newest frame is ever sent: slow clients skip frames, never lag)
  /<name>.jsonl    one JSON object per line, newest only
  /<name>.json     the newest JSON object once (polling)
  /<name>.jpg      the newest JPEG frame once (live/record.py, screenshots)
  /cmd/<name>      increments hub.cmd[name] (e.g. a "reset" button on the viewer page)
  /                the optional index page given at construction (e.g. live/viewer.html)
JPEG encoding: OpenCV if importable, else Pillow, else a persistent ffmpeg process (the upstream sim venv may have
neither library).
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np


class _FfmpegJpeg:
    def __init__(self, w, h, quality):
        q = max(2, min(31, int(round(31 - quality * 0.29))))
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                                   f"{w}x{h}", "-i", "-", "-f", "image2pipe", "-c:v", "mjpeg", "-q:v", str(q), "-"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.buf = b""

    def encode(self, rgb):
        self.p.stdin.write(np.ascontiguousarray(rgb).tobytes())
        self.p.stdin.flush()
        while True:
            end = self.buf.find(b"\xff\xd9")
            if end >= 0:
                start = self.buf.find(b"\xff\xd8")
                jpg, self.buf = self.buf[start:end + 2], self.buf[end + 2:]
                return jpg
            self.buf += self.p.stdout.read1(1 << 16)


def make_encoder(quality=80):
    try:
        import cv2
        return lambda rgb: cv2.imencode(".jpg", np.ascontiguousarray(rgb[..., ::-1]),
                                        [cv2.IMWRITE_JPEG_QUALITY, quality])[1].tobytes()
    except ImportError:
        pass
    try:
        import io

        from PIL import Image

        def enc(rgb):
            b = io.BytesIO()
            Image.fromarray(np.ascontiguousarray(rgb)).save(b, "JPEG", quality=quality)
            return b.getvalue()
        return enc
    except ImportError:
        pass
    procs = {}

    def enc(rgb):
        h, w = rgb.shape[:2]
        if (w, h) not in procs:
            procs[(w, h)] = _FfmpegJpeg(w, h, quality)
        return procs[(w, h)].encode(rgb)
    return enc


class Hub:
    def __init__(self, port, index_html=None, quality=65, host="127.0.0.1", max_fps=10.0):
        self.data, self.seq, self.cmd, self.lock = {}, {}, {}, threading.Lock()
        self.encode = make_encoder(quality)
        self.min_dt = 1.0 / max_fps          # per-client cap: the views go through an SSH tunnel to a home connection
        self.index = Path(index_html).read_bytes() if index_html else None
        hub = self

        class H(BaseHTTPRequestHandler):
            def _head(self, ctype):
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()

            def do_GET(self):
                path = self.path.split("?")[0].lstrip("/")
                if path.startswith("cmd/"):
                    hub.cmd[path[4:]] = hub.cmd.get(path[4:], 0) + 1
                    self._head("application/json")
                    self.wfile.write(b'{"ok": true}')
                    return
                if path == "cmds.json":
                    self._head("application/json")
                    self.wfile.write(json.dumps(hub.cmd).encode())
                    return
                if path == "" and hub.index is not None:
                    self._head("text/html")
                    self.wfile.write(hub.index)
                    return
                name, _, kind = path.rpartition(".")
                if name not in hub.data and kind != "json":
                    self.send_error(404)
                    return
                try:
                    if kind == "jpg":                       # newest frame once (recorder, screenshots)
                        self._head("image/jpeg")
                        self.wfile.write(hub.data[name])
                    elif kind == "json":
                        self._head("application/json")
                        self.wfile.write(json.dumps(hub.data.get(name, {})).encode())
                    elif kind == "mjpg":
                        self._head("multipart/x-mixed-replace; boundary=frame")
                        for jpg in hub.follow(name):
                            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " +
                                             str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
                    elif kind == "jsonl":
                        self._head("application/x-ndjson")
                        for obj in hub.follow(name):
                            self.wfile.write(json.dumps(obj).encode() + b"\n")
                            self.wfile.flush()
                    else:
                        self.send_error(404)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *a):
                pass

        self.server = ThreadingHTTPServer((host, port), H)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def put_json(self, name, obj):
        with self.lock:
            self.data[name] = obj
            self.seq[name] = self.seq.get(name, 0) + 1

    def put_jpeg(self, name, frame):
        jpg = frame if isinstance(frame, (bytes, bytearray)) else self.encode(frame)
        self.put_json(name, jpg)

    def follow(self, name, poll_s=0.003):
        last, t_last = -1, 0.0
        while True:
            s = self.seq.get(name, 0)
            if s != last and name in self.data and time.time() - t_last >= self.min_dt:
                last, t_last = s, time.time()
                yield self.data[name]
            else:
                time.sleep(poll_s)


def read_jsonl(url, on_obj, retry_s=1.0):
    """Client side: follow a /<name>.jsonl stream forever (reconnects), calling on_obj(dict) per line."""
    import urllib.request
    while True:
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                for line in r:
                    if line.strip():
                        on_obj(json.loads(line))
        except Exception as e:                     # tunnel not up yet / producer restarted
            on_obj({"_error": repr(e)})
            time.sleep(retry_s)
