"""Presentation clip with a clean background: keep the person (segmentation mask) and the table with its objects (fixed polygon, the camera is static), replace everything else with a plain studio backdrop.
Measurements and pose estimates always come from the ORIGINAL clip; this is only for the video. Usage:
    python3 scripts/clean_background.py IN.mp4 OUT.mp4 [--weights yolo11n-seg.pt] [--preview N]
"""
import argparse
import subprocess
import sys

import cv2
import imageio_ffmpeg
import numpy as np

TABLE = np.array([[362, 553], [804, 556], [842, 720], [310, 720]], np.int32)      # table top in the 1280x720 frame (static camera)


def backdrop(h, w):
    y = np.linspace(0, 1, h)[:, None, None]
    top, bot = np.array([205, 200, 196], float), np.array([150, 146, 142], float)     # BGR light warm grey, darker toward the floor
    bg = (top * (1 - y) + bot * y) * np.ones((1, w, 1))
    horizon = int(h * 0.5)
    bg[horizon:] *= 0.93
    return bg.astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--weights", default="yolo11n-seg.pt")
    ap.add_argument("--preview", type=int, default=None, help="write this frame index as PNG next to the output and stop")
    a = ap.parse_args()
    from ultralytics import YOLO
    model = YOLO(a.weights)
    cap = cv2.VideoCapture(a.src)
    fps, w, h = cap.get(cv2.CAP_PROP_FPS), int(cap.get(3)), int(cap.get(4))
    bg = backdrop(h, w)
    tab = np.zeros((h, w), np.uint8)
    cv2.fillPoly(tab, [TABLE], 255)
    out = None if a.preview is not None else subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                                                    "-pix_fmt", "yuv420p", "-vcodec", "libx264", "-crf", "20", a.dst], stdin=subprocess.PIPE)
    prev, i = np.zeros((h, w), np.float32), 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        if a.preview is not None and i != a.preview:
            i += 1
            continue
        r = model.predict(im, classes=[0], verbose=False, retina_masks=True, imgsz=640)[0]
        m = np.zeros((h, w), np.float32)
        if r.masks is not None:
            for k in range(len(r.masks.data)):
                mk = cv2.resize(r.masks.data[k].cpu().numpy(), (w, h), interpolation=cv2.INTER_LINEAR)
                if (mk > 0.5).sum() > 8000 and np.abs(np.nonzero(mk > 0.5)[1].mean() - w / 2) < w * 0.3:     # the person in the middle, not the child on the right
                    m = np.maximum(m, mk)
        m = cv2.erode((m > 0.5).astype(np.float32), np.ones((5, 5), np.uint8))
        m = cv2.GaussianBlur(m, (0, 0), 2)
        m = 0.7 * m + 0.3 * prev if i else m                                                    # light temporal smoothing against flicker
        prev = m
        hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
        red = (((hsv[..., 0] < 9) | (hsv[..., 0] > 168)) & (hsv[..., 1] > 150) & (hsv[..., 2] > 110)).astype(np.float32)      # saturated red/orange of the slide behind the arm (skin is far less saturated)
        blue = ((hsv[..., 0] > 88) & (hsv[..., 0] < 132) & (hsv[..., 1] > 95) & (hsv[..., 2] > 70)).astype(np.float32)           # blue cloth of the pile behind the person
        orange = ((hsv[..., 0] >= 9) & (hsv[..., 0] < 24) & (hsv[..., 1] > 175) & (hsv[..., 2] > 140)).astype(np.float32)        # saturated orange cloth (skin is less saturated)
        red = np.maximum(red, np.maximum(blue, orange))
        red = cv2.dilate(red, np.ones((7, 7), np.uint8))
        red[tab > 0] = 0
        m = m * (1 - red)
        alpha = np.maximum(m, (tab > 0).astype(np.float32))[..., None]
        comp = (im * alpha + bg * (1 - alpha)).astype(np.uint8)
        if a.preview is not None:
            cv2.imwrite(a.dst, comp)
            return
        out.stdin.write(np.ascontiguousarray(comp).tobytes())
        i += 1
    if out:
        out.stdin.close()
        out.wait()
    print("frames", i)


if __name__ == "__main__":
    main()
