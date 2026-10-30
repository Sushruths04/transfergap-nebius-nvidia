"""Minimal mp4 writer: raw RGB frames piped to the system ffmpeg (the upstream sim venv has no imageio)."""
from __future__ import annotations

import subprocess


class Mp4Writer:
    def __init__(self, path, width, height, fps=25):
        self.proc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
             "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p", "-vcodec", "libx264", "-crf", "26", str(path)],
            stdin=subprocess.PIPE)

    def write(self, frame):
        self.proc.stdin.write(frame.tobytes())

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()
