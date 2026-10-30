"""v5 self-explanatory animated cut (< 3 min). Assemble the silent final cut from committed/verified clips and result files (CPU, one process). Captions only; voice-over is added by the author.

    python scripts/make_final_cut.py OUT.mp4
Numbers on screen come from ui_demo/data.js, ui_demo/scale_data.js (built from committed results) and the G1 result READMEs; nothing is typed in that is not in a result file.
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui_demo"
W, H, FPS = 1280, 720, 25
# ---- all on-screen numbers live here (edit this dict only) ----
N = dict(
    ur5e_raw=31, ur10e_raw=34, kairos_raw=48, fixed=60, of=60,
    cube7_raw=0, cube7_fix=56,
    grid_cells_full=22, grid_cells_total=24, grid_cells_59=2, grid_seeds=60,
    cosmos_acc=96, cosmos_clips=240, cosmos_reject=40, cosmos_fail=49,
    gr_before="0-1", gr_ur10e=25, gr_kairos=27, gr_multi="5-10", gr_of=30, gr_ahead=4,
    g1_ok=52, g1_n=72, g1_style_ok=0, g1_style_n=30,
    shoulder_m=0.44,
)
BG = (17, 12, 9)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def load_js(p):
    s = Path(p).read_text()
    return json.loads(s[s.index("{"):s.rindex("}") + 1])


TG = load_js(UI / "data.js")
SC = load_js(UI / "scale_data.js")


def text(img, s, org, scale=0.8, col=(235, 235, 235), th=2):
    cv2.putText(img, s, org, FONT, scale, col, th, cv2.LINE_AA)


def canvas():
    return np.full((H, W, 3), BG, np.uint8)


def caption(img, lines):
    """Bottom caption bar; long lines wrap to the frame width (smaller font if there would be more than three rows)."""
    sc = 0.72
    rows = [r for l in lines for r in wrap(l, sc, 2, W - 48)]
    if len(rows) > 3:
        sc = 0.58
        rows = [r for l in lines for r in wrap(l, sc, 2, W - 48)]
    step = int(46 * sc)
    cv2.rectangle(img, (0, H - 28 - step * len(rows)), (W, H), (30, 22, 16), -1)
    for i, r in enumerate(rows):
        text(img, r, (24, H - 14 - step * (len(rows) - 1 - i)), sc)


def frames(path, start=0.0, end=None):
    c = cv2.VideoCapture(str(path))
    fps = c.get(cv2.CAP_PROP_FPS) or 25
    n = int(c.get(cv2.CAP_PROP_FRAME_COUNT))
    a, b = int(start * fps), int(end * fps) if end else n
    c.set(cv2.CAP_PROP_POS_FRAMES, a)
    out = []
    for i in range(a, min(b, n)):
        ok, im = c.read()
        if not ok:
            break
        out.append(im)
    return out


def fit(im, w, h):
    s = min(w / im.shape[1], h / im.shape[0])
    r = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)))
    o = np.zeros((h, w, 3), np.uint8)
    o[:] = (6, 8, 12)
    y, x = (h - r.shape[0]) // 2, (w - r.shape[1]) // 2
    o[y:y + r.shape[0], x:x + r.shape[1]] = r
    return o


class Out:
    def __init__(self, path):
        self.p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                                   "-r", str(FPS), "-i", "-", "-pix_fmt", "yuv420p", "-vcodec", "libx264", "-crf", "22", str(path)], stdin=subprocess.PIPE)
        self.n = 0
        self.k = 99

    def start(self):
        self.k = 0

    def put(self, im):
        if self.k < 8:
            a = (self.k + 1) / 8
            im = cv2.addWeighted(im, a, canvas(), 1 - a, 0)
            self.k += 1
        self.p.stdin.write(np.ascontiguousarray(im).tobytes())
        self.n += 1

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def wrap(s, scale, th, maxw=W - 140):
    """Split one text line into rows that fit the frame width."""
    rows, cur = [], ""
    for w in s.split(" "):
        t = (cur + " " + w).strip()
        if cur and cv2.getTextSize(t, FONT, scale, th)[0][0] > maxw:
            rows.append(cur)
            cur = w
        else:
            cur = t
    return rows + [cur]


GREEN, WHITE, GREY, RED, BLUE = (118, 185, 0), (235, 235, 235), (170, 170, 170), (90, 90, 240), (230, 170, 80)
PANEL = (40, 30, 22)


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def tsize(s, sc, th=2):
    return cv2.getTextSize(s, FONT, sc, th)[0]


def blend(im, fn, a):
    if a >= 0.999:
        fn(im)
    elif a > 0.01:
        tmp = im.copy()
        fn(tmp)
        im[:] = cv2.addWeighted(tmp, a, im, 1 - a, 0)


def para(im, s, x, y, maxw, sc=0.7, col=WHITE, th=1, step=None):
    """Wrapped paragraph; returns y after last row."""
    step = step or int(40 * sc)
    for r in wrap(s, sc, th, maxw):
        text(im, r, (x, y), sc, col, th)
        y += step
    return y


def chap(im, s):
    cv2.rectangle(im, (0, 0), (tsize(s, 0.9)[0] + 40, 42), (30, 22, 16), -1)
    text(im, s, (16, 31), 0.9, GREEN)


def lower_third(im, k, title, num, y):
    """Slide-in title bar (k = frames since segment start)."""
    p = ease(k / 12)
    if p <= 0:
        return
    w = 640
    rows = wrap(title, 0.8, 1, w - 40)
    h = 22 + 32 * len(rows) + 42
    x = int(-w + (w + 0) * p)
    cv2.rectangle(im, (x, y), (x + w, y + h), (30, 22, 16), -1)
    cv2.rectangle(im, (x, y), (x + 8, y + h), GREEN, -1)
    for i, r in enumerate(rows):
        text(im, r, (x + 24, y + 30 + 32 * i), 0.8, WHITE, 1)
    text(im, num, (x + 24, y + h - 12), 0.85, GREEN, 2)


def pick(fr, n, speed):
    """Resample a frame list to n output frames at given speed (>=1 skips frames; holds last)."""
    return [fr[min(len(fr) - 1, int(i * speed))] for i in range(n)]


def single(out, vid, cap, ch, lt, secs, speed=1.0, start=0):
    out.start()
    fr = pick(frames(vid, start), int(secs * FPS), speed)
    for k, f in enumerate(fr):
        im = canvas()
        im[40:H - 140, :] = fit(f, W, H - 180)
        chap(im, ch)
        caption(im, cap)
        lower_third(im, k, lt[0], lt[1], 470 - 32 * (len(wrap(lt[0], 0.8, 1, 600)) - 1))
        out.put(im)


def pair(out, lv, ll, rv, rl, cap, ch, lt, secs, speed=1.0):
    out.start()
    n = int(secs * FPS)
    A, B = pick(frames(lv), n, speed), pick(frames(rv), n, speed)
    for k in range(n):
        im = canvas()
        for j, (f, l, c) in enumerate(((A[k], ll, RED), (B[k], rl, GREEN))):
            x = 0 if j == 0 else W // 2
            im[70:70 + 480, x:x + W // 2] = fit(f, W // 2, 480)
            text(im, l, (x + 20, 60), 0.75, c)
        chap(im, ch)
        caption(im, cap)
        lower_third(im, k, lt[0], lt[1], 440 - 32 * (len(wrap(lt[0], 0.8, 1, 600)) - 1))
        out.put(im)


def run(out, secs, draw):
    out.start()
    for k in range(int(secs * FPS)):
        im = canvas()
        draw(im, k / FPS, k)
        out.put(im)


def intro(im, t, k):
    a = ease(t / 1.2)
    sc = 2.6 + 0.4 * (1 - a)
    s = "TransferGap"
    w = tsize(s, sc, 5)[0]
    blend(im, lambda i: text(i, s, ((W - w) // 2, 200), sc, GREEN, 5), a)
    cv2.line(im, (W // 2 - int(300 * ease((t - 1) / 1.2)), 225), (W // 2 + int(300 * ease((t - 1) / 1.2)), 225), GREEN, 3)
    tag = ["One human demonstration -> many robots.", "When the copy fails, we say which stage failed."]
    for i, l in enumerate(tag):
        w = tsize(l, 0.95, 2)[0]
        blend(im, lambda ii, l=l, w=w, i=i: text(ii, l, ((W - w) // 2, 290 + 44 * i), 0.95, WHITE, 2), ease((t - 1.6 - 0.8 * i) / 0.8))
    # human -> robots motif
    cx, cy = 200, 520
    blend(im, lambda i: (cv2.circle(i, (cx, cy - 30), 22, WHITE, 3), cv2.line(i, (cx, cy - 8), (cx, cy + 40), WHITE, 3),
                         cv2.line(i, (cx - 30, cy + 5), (cx + 30, cy + 5), WHITE, 3), text(i, "1 person", (cx - 50, cy + 80), 0.8, GREY, 1)), ease((t - 3.4) / 0.6))
    for j, nm in enumerate(["UR5e", "UR10e", "KAIROS", "G1"]):
        ty = 440 + j * 62
        p = ease((t - 4.0 - 0.45 * j) / 0.8)
        x2 = int(cx + 60 + (W - 420 - cx - 60) * p)
        cv2.line(im, (cx + 60, cy), (x2, ty), GREEN, 2)
        if p >= 1:
            cv2.rectangle(im, (W - 420, ty - 24), (W - 200, ty + 24), PANEL, -1)
            cv2.rectangle(im, (W - 420, ty - 24), (W - 200, ty + 24), GREEN, 2)
            text(im, nm, (W - 400, ty + 9), 0.75, WHITE, 2)
    blend(im, lambda i: text(i, "Simulation only.", (W - 180, 520), 0.8, GREY, 1), ease((t - 6.5) / 0.6))


PIPE = [("Human video", "one short clip"),
        ("Measure the person", "pose, limb lengths"),
        ("Copy to robots", "UR5e, UR10e, KAIROS, G1"),
        ("Fails? Diagnose", "perception, retargeting, calibration, timing"),
        ("Pick the fix", "Nemotron-3-Super, Nebius Token Factory"),
        ("Verified fix", f"UR5e {N['ur5e_raw']} -> {N['fixed']} of {N['of']}"),
        ("Train one policy", "one network, all robots"),
        ("Fine-tune GR00T", "NVIDIA N1.5, 3B")]


def pipe_rects():
    bw, bh, gap = 290, 255, 30
    r = []
    for i in range(8):
        row, c = divmod(i, 4)
        c = c if row == 0 else 3 - c
        r.append((15 + c * (bw + gap), 70 + row * (bh + 40), bw, bh))
    return r


def pipeline(im, t, k):
    text(im, "How it works", (24, 52), 1.0, GREEN, 2)
    R = pipe_rects()
    for i, (x, y, w, h) in enumerate(R):
        a = ease((t - 0.4 - 1.0 * i) / 0.6)
        if i and a > 0:
            px, py, pw, ph = R[i - 1]
            p0 = (px + pw // 2, py + ph // 2)
            p1 = (x + w // 2, y + h // 2)
            if abs(p0[1] - p1[1]) < 5:
                d = 1 if p1[0] > p0[0] else -1
                a0, a1 = (px + pw if d > 0 else px), (x if d > 0 else x + w)
                e = int(a0 + (a1 - a0) * a)
                cv2.arrowedLine(im, (a0, p0[1]), (e, p0[1]), GREY, 3, tipLength=0.35 if a > 0.9 else 0.01)
            else:
                e = int(py + ph + (y - py - ph) * a)
                cv2.arrowedLine(im, (p0[0], py + ph), (p0[0], e), GREY, 3, tipLength=0.3 if a > 0.9 else 0.01)

        def draw(i2, i=i, x=x, y=y, w=w, h=h):
            cv2.rectangle(i2, (x, y), (x + w, y + h), PANEL, -1)
            cv2.rectangle(i2, (x, y), (x + w, y + h), (110, 110, 110), 2)
            text(i2, str(i + 1), (x + 12, y + 30), 0.85, GREY, 2)
            yy = y + 66
            for r in wrap(PIPE[i][0], 0.95, 2, w - 24):
                text(i2, r, (x + 14, yy), 0.95, GREEN if i not in (3,) else (80, 160, 255), 2)
                yy += 38
            para(i2, PIPE[i][1], x + 14, yy + 8, w - 24, 0.85, WHITE, 1, 34)
        blend(im, draw, a)
    if t > 8.6:
        u = (t - 8.6) / 5.0 * 7
        i = min(6, int(u))
        f = ease(u - i)
        a, b = R[i], R[i + 1]
        x, y, w, h = [int(a[j] + (b[j] - a[j]) * f) for j in range(4)]
        cv2.rectangle(im, (x - 4, y - 4), (x + w + 4, y + h + 4), (60, 230, 255) if k % 8 < 4 else GREEN, 4)
    text(im, "All results: simulation, held-out random seeds.", (24, H - 18), 0.8, GREY, 1)


ROWS = ["UR5e", "UR10e", "KAIROS arm", "KAIROS mobile"]
COLS = ["standard", "mixed", "hard"]


def grid(im, t, k):
    chap(im, "4 Learn one policy")
    text(im, "One policy, four robots (no robot id)", (24, 76), 0.9, WHITE, 2)
    x0, y0, cw, rh = 280, 160, 300, 80
    for j, c in enumerate(COLS):
        text(im, c, (x0 + j * cw + 90, y0 - 14), 0.95, GREEN, 2)
    lit = 0
    for i, rn in enumerate(ROWS):
        text(im, rn, (24, y0 + i * rh + 50), 0.9, WHITE, 2)
        for j in range(3):
            n = i * 3 + j
            a = ease((t - 0.8 - 0.4 * n) / 0.4)
            lit += a >= 1
            x, y = x0 + j * cw, y0 + i * rh
            cv2.rectangle(im, (x + 6, y + 6), (x + cw - 6, y + rh - 6), PANEL, -1)
            if a > 0:
                def d(i2, x=x, y=y):
                    cv2.rectangle(i2, (x + 6, y + 6), (x + cw - 6, y + rh - 6), (40, 110, 0), -1)
                    cv2.rectangle(i2, (x + 6, y + 6), (x + cw - 6, y + rh - 6), GREEN, 3)
                    text(i2, f"{N['of']}/{N['of']}", (x + 90, y + 52), 1.1, WHITE, 2)
                blend(im, d, a)
    text(im, f"{lit} / 12 cells at {N['of']}/{N['of']}", (24, 510), 0.95, GREEN, 2)
    blend(im, lambda i2: para(i2, f"Two training runs: {N['grid_cells_full']} of {N['grid_cells_total']} cells {N['of']}/{N['of']} and two 59/{N['of']} on {N['grid_seeds']} brand-new seeds.", 24, 565, W - 48, 0.85, WHITE, 2, 34), ease((t - 6.8) / 0.8))
    blend(im, lambda i2: text(i2, "Mobile base parked (arm only). Simulation.", (24, H - 18), 0.8, GREY, 1), ease((t - 7.6) / 0.8))


def bars(im, t, k):
    chap(im, "5 GR00T")
    text(im, f"GR00T-N1.5 (3B): successes out of {N['gr_of']} fresh seeds", (24, 80), 0.9, WHITE, 2)
    px0, px1, py0, py1 = 110, 1230, 125, 425
    cv2.line(im, (px0, py1), (px1, py1), GREY, 2)
    cv2.line(im, (px0, py0), (px0, py1), GREY, 2)
    yv = lambda v: int(py1 - (py1 - py0) * v / N["gr_of"])
    for v in (0, 10, 20, 30):
        text(im, str(v), (px0 - 50, yv(v) + 8), 0.85, GREY, 2)
    bw, gp = 170, 90
    data = [("before: first-step execution", 1, 0, f"{N['gr_before']}/{N['gr_of']}", RED),
            (f"after: {N['gr_ahead']} steps ahead, UR10e", N["gr_ur10e"], 0, f"{N['gr_ur10e']}/{N['gr_of']}", GREEN),
            (f"after: {N['gr_ahead']} steps ahead, KAIROS", N["gr_kairos"], 0, f"{N['gr_kairos']}/{N['gr_of']}", GREEN),
            ("3-robot model, UR5e / UR10e", 10, 5, f"{N['gr_multi']}/{N['gr_of']}", BLUE)]
    for i, (lab, v, lo, vl, col) in enumerate(data):
        x = px0 + 40 + i * (bw + gp)
        a = ease((t - 0.8 - 1.4 * i) / 1.2)
        top = yv(v * a)
        cv2.rectangle(im, (x, top), (x + bw, py1), col, -1)
        if lo:
            cv2.rectangle(im, (x, yv(lo * a)), (x + bw, py1), (170, 120, 40), -1)
        if a >= 1:
            text(im, vl, (x + 20, top + 40), 1.0, (10, 10, 10), 2) if v >= 20 else text(im, vl, (x + 20, top - 10), 1.0, WHITE, 2)
        blend(im, lambda i2, lab=lab, x=x: para(i2, lab, x - 25, py1 + 30, bw + 60, 0.8, WHITE, 1, 30), ease((t - 1.0 - 1.4 * i) / 0.6))
    a = ease((t - 6.5) / 0.8)
    yl = yv(N["gr_of"])
    def dl(i2):
        for x in range(px0, int(px0 + (px1 - px0) * a), 16):
            cv2.line(i2, (x, yl), (x + 8, yl), (60, 230, 255), 3)
        text(i2, f"small policy: {N['of']}/{N['of']}", (px1 - 380, yl - 10), 0.9, (60, 230, 255), 2)
    dl(im)
    blend(im, lambda i2: caption(i2, ["The arm stopped 2-5 cm short of the cube; executing the plan 4 steps ahead fixed it, no retraining."]), ease((t - 8.0) / 0.8))


MODELS = [("N", "Nemotron-3-Super", "via Nebius Token Factory API: diagnosis"),
          ("C", "Cosmos-Reason2 critic", f"{N['cosmos_acc']}% accuracy on {N['cosmos_clips']} simulated clips"),
          ("G", "GR00T-N1.5 (3B)", "fine-tuned policy"),
          ("S", "SONIC", "whole-body control of the Unitree G1")]


def models(im, t, k):
    text(im, "NVIDIA models and Nebius", (24, 56), 1.0, GREEN, 2)
    for i, (ic, ti, body) in enumerate(MODELS):
        a = ease((t - 0.6 - 1.6 * i) / 0.7)
        x, y = 24 + (i % 2) * 626, 80 + (i // 2) * 270

        def d(i2, x=x, y=y, ic=ic, ti=ti, body=body, a=a):
            ox = int((1 - a) * 40)
            x += ox
            cv2.rectangle(i2, (x, y), (x + 600, y + 250), PANEL, -1)
            cv2.rectangle(i2, (x, y), (x + 600, y + 250), GREEN, 2)
            cv2.rectangle(i2, (x + 15, y + 20), (x + 100, y + 105), GREEN, -1)
            text(i2, ic, (x + 35, y + 85), 1.9, (10, 10, 10), 4)
            text(i2, ti, (x + 120, y + 55), 0.95, GREEN, 2)
            para(i2, body, x + 120, y + 105, 465, 0.85, WHITE, 1, 36)
        blend(im, d, a)
    blend(im, lambda i2: text(i2, "Nemotron is called through the Nebius Token Factory API.", (24, H - 18), 0.8, GREY, 1), ease((t - 7.5) / 0.8))


LIMITS = ["Simulation only.", "One demonstration, one task.", "Policies trained on scripted rollouts.", "Mobile base parked.",
          f"Shoulder width assumed {N['shoulder_m']} m.", "GR00T worse than the small policy."]


def limits(im, t, k):
    chap(im, "6 Limits")
    text(im, "What this is not", (70, 110), 1.2, GREEN, 3)
    for i, l in enumerate(LIMITS):
        a = ease((t - 0.5 - 0.9 * i) / 0.5)
        blend(im, lambda i2, l=l, i=i, a=a: (cv2.circle(i2, (80 + int((1 - a) * -30), 190 + i * 62 - 8), 8, GREEN, -1),
                                             text(i2, l, (110 + int((1 - a) * -30), 190 + i * 62), 0.95, WHITE, 2)), a)


def outro(im, t, k):
    s = "TransferGap"
    w = tsize(s, 2.4, 5)[0]
    text(im, s, ((W - w) // 2, 180), 2.4, GREEN, 5)
    L = [f"Raw copy {N['ur5e_raw']}/{N['of']} -> {N['fixed']}/{N['of']} with diagnosed fixes (UR5e).",
         f"One small policy: {N['of']}/{N['of']} on four robots. GR00T-N1.5: {N['gr_ur10e']}-{N['gr_kairos']}/{N['gr_of']}.",
         "Nemotron-3-Super via Nebius Token Factory picks the fix."]
    for i, l in enumerate(L):
        blend(im, lambda i2, l=l, i=i: para(i2, l, 70, 300 + i * 90, W - 140, 0.9, WHITE, 2), ease((t - 0.8 - 0.9 * i) / 0.7))


def main(path):
    out = Out(path)
    hq, sm = UI / "media" / "hq", UI / "media" / "scale"
    marks = []

    def mark(s):
        marks.append((round(out.n / FPS, 1), s))
    mark("Intro"); run(out, 8, intro)
    mark("How it works (pipeline)"); run(out, 14, pipeline)
    mark("1 Measure"); single(out, UI / "media" / "human_overlay.mp4",
           ["Background replaced for the video; measurements come from the original clip.", f"Monocular estimate; shoulder width {N['shoulder_m']} m is assumed."],
           "1 Measure", ("Pose, limb lengths, elbow angle, pinch from one clip", "1 clip"), 9, 0.8)
    single(out, ROOT / "results" / "hand_retarget_v1" / "hand_retarget.mp4",
           ["Fingers: 21 hand keypoints drive a dexterous robot hand by fingertip IK. Kinematic only."],
           "1 Measure", ("Fingers copied to a robot hand", "21 keypoints"), 8, 1.6)
    mark("2 Copy: humanoid"); single(out, ROOT / "results" / "g1_in_image_v1" / "videos" / "image_seed1200_placed.mp4",
           [f"Unitree G1 closed-loop pick and place with a generic block; copying the author's grasp style: {N['g1_style_ok']}/{N['g1_style_n']}."],
           "2 Copy", ("Humanoid G1 places a block", f"{N['g1_ok']}/{N['g1_n']} pooled"), 12, 1.0, start=4)
    mark("3 Diagnose + fix: robots")
    ks = {"ur5e": "ur5e", "ur10e": "ur10e", "kairos_mobile": "kairos"}
    for r, name in (("ur5e", "UR5e"), ("ur10e", "UR10e"), ("kairos_mobile", "KAIROS mobile")):
        d = TG["robots"][ks[r]]
        pair(out, hq / f"{r}_raw_seed1001.mp4", "raw copy", hq / f"{r}_stack_seed1001.mp4", "with fixes",
             [f"{name}: held-out success {d['raw']['k']}/{d['raw']['n']} -> {d['fix']['k']}/{d['fix']['n']} (this clip: one seed, an illustration)."],
             "3 Diagnose + fix", (f"{name}: raw copy vs diagnosed fixes", f"{d['raw']['k']} -> {d['fix']['k']} of {d['fix']['n']}"), 8.5)
    mark("3 Diagnose + fix: object size")
    for cm in (3, 5, 7):
        big = cm == 7
        cap = [f"UR10e, {cm} cm cube (never tuned for it): {N['cube7_raw']}/{N['of']} -> {N['cube7_fix']}/{N['of']} on held-out seeds. Exploratory."] if big else [f"UR10e, {cm} cm cube (never tuned for it): raw copy vs diagnosed fixes. Exploratory."]
        pair(out, sm / f"ur10e_{cm}cm_raw_seed1000.mp4", f"raw, {cm} cm cube", sm / f"ur10e_{cm}cm_stack_seed1000.mp4", "with fixes", cap,
             "3 Diagnose + fix", (f"Bigger object: {cm} cm cube", f"{N['cube7_raw']} -> {N['cube7_fix']} of {N['of']}" if big else "same fixes"), 6, 1.4)
    mark("4 Learn one policy")
    pm = UI / "media" / "policy_multi"
    for r, name in (("ur5e", "UR5e"), ("ur10e", "UR10e"), ("kairos", "KAIROS")):
        single(out, pm / f"{r}_seed6000_success.mp4",
               [f"One learned policy for all robots (no scripted controller): {name}, a fresh seed. Images + joint positions -> actions."],
               "4 Learn one policy", (f"Same policy, {name}", f"{N['of']}/{N['of']} per cell"), 5, 1.7)
    run(out, 10, grid)
    mark("5 GR00T"); run(out, 12, bars)
    mark("NVIDIA models and Nebius"); run(out, 10, models)
    mark("6 Limits"); run(out, 7, limits)
    mark("Summary"); run(out, 6, outro)
    out.close()
    print("frames", out.n, "seconds", round(out.n / FPS, 1))
    for m in marks:
        print(f"{int(m[0]//60)}:{int(m[0]%60):02d}  {m[1]}")


if __name__ == "__main__":
    main(sys.argv[1])
