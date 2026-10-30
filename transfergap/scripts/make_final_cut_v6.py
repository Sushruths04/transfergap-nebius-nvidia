"""v6: light editorial cut (< 3 min), PIL typography + OpenCV clips, silent.

    python3 scripts/make_final_cut_v6.py OUT.mp4
All on-screen numbers live in the dict N below (the rest comes from ui_demo/data.js and scale_data.js).
"""
import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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

PAGE, CARD, BORDER = (252, 252, 251), (255, 255, 255), (230, 229, 225)
INK, SEC, MUT, GRID = (11, 11, 11), (82, 81, 78), (138, 137, 133), (236, 235, 231)
BLUE, ORANGE, GREEN, VIOLET, GREYC = (42, 120, 214), (235, 104, 52), (27, 175, 122), (98, 80, 214), (184, 183, 178)
FD = "/usr/share/fonts/truetype/ubuntu/Ubuntu-"
FILES = {"R": FD + "R.ttf", "M": FD + "M.ttf", "B": FD + "B.ttf"}


def load_js(p):
    s = Path(p).read_text()
    return json.loads(s[s.index("{"):s.rindex("}") + 1])


TG = load_js(UI / "data.js")
SC = load_js(UI / "scale_data.js")


# ---------------------------------------------------------------- helpers
def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def eo(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def lerp(c, d, a):
    return tuple(int(c[i] * a + d[i] * (1 - a)) for i in range(3))


@lru_cache(None)
def font(size, w="R"):
    return ImageFont.truetype(FILES[w], size)


def tw(s, size, w="R", sp=0):
    return font(size, w).getlength(s) + sp * len(s)


def T(im, s, x, y, size=26, w="R", col=INK, al="l", sp=0, a=1.0, bg=PAGE):
    """Text with baseline at y; al l/m/r; sp = letter spacing; a = fade toward bg."""
    d = ImageDraw.Draw(im)
    c = lerp(col, bg, a)
    f = font(size, w)
    wd = tw(s, size, w, sp)
    x0 = x if al == "l" else x - wd / 2 if al == "m" else x - wd
    if sp:
        for ch in s:
            d.text((x0, y), ch, font=f, fill=c, anchor="ls")
            x0 += f.getlength(ch) + sp
    else:
        d.text((x0, y), s, font=f, fill=c, anchor="ls")
    return wd


def wrap(s, size, maxw, w="R"):
    rows, cur = [], ""
    for wd in s.split(" "):
        t = (cur + " " + wd).strip()
        if cur and tw(t, size, w) > maxw:
            rows.append(cur)
            cur = wd
        else:
            cur = t
    return rows + [cur]


def P(im, s, x, y, size, w, col, maxw, lh=None, a=1.0, bg=PAGE, al="l"):
    lh = lh or int(size * 1.3)
    for r in wrap(s, size, maxw, w):
        T(im, r, x, y, size, w, col, al, a=a, bg=bg)
        y += lh
    return y


@lru_cache(None)
def sprite(w, h, r, fill, outline, ow, shadow):
    pad = 28 if shadow else 2
    S = 3
    big = Image.new("RGBA", ((w + 2 * pad) * S, (h + 2 * pad) * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    box = [pad * S, pad * S, (pad + w) * S - 1, (pad + h) * S - 1]
    if outline:
        d.rounded_rectangle(box, r * S, fill=outline + (255,))
        box = [box[0] + ow * S, box[1] + ow * S, box[2] - ow * S, box[3] - ow * S]
    d.rounded_rectangle(box, max(1, (r - ow) * S), fill=fill + (255,))
    shape = big.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS)
    if shadow:
        sh = Image.new("L", shape.size, 0)
        ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 5, pad + w, pad + h + 5], r, fill=22)
        sh = sh.filter(ImageFilter.GaussianBlur(7))
        black = Image.new("RGBA", shape.size, (0, 0, 0, 0))
        black.putalpha(sh)
        shape = Image.alpha_composite(black, shape)
    return shape.convert("RGB"), shape.getchannel("A"), pad


def box(im, x, y, w, h, r=16, fill=CARD, outline=BORDER, ow=1, shadow=True, a=1.0, dy=0):
    rgb, al, pad = sprite(int(w), int(h), r, fill, outline, ow, shadow)
    if a < 0.999:
        al = al.point(lambda v: int(v * a))
    im.paste(rgb, (int(x - pad), int(y - pad + dy)), al)


def chip(im, x, y, label, col, size=28, w="B", padx=18, h=44, fill=None, tcol=None, a=1.0, sc=1.0, al="l", bg=CARD):
    """Rounded chip; returns its width. fill=None -> solid col with white text."""
    wd = int(tw(label, size, w) + 2 * padx)
    if al == "r":
        x = x - wd
    if sc != 1.0:
        cx, cy = x + wd / 2, y + h / 2
        wd2, h2 = int(wd * sc), int(h * sc)
        box(im, cx - wd2 / 2, cy - h2 / 2, wd2, h2, 10, fill or col, None, 0, False)
        T(im, label, cx, cy + int(size * sc * 0.35), max(8, int(size * sc)), w, tcol or (255, 255, 255), "m", bg=col)
        return wd
    box(im, x, y, wd, h, 10, fill or col, None, 0, False, a)
    T(im, label, x + wd / 2, y + h / 2 + int(size * 0.35), size, w, tcol or (255, 255, 255), "m", a=a, bg=fill or col)
    return wd


def chapter_chip(im, label, a=1.0):
    n, name = label.split(" ", 1)
    s = f"{n}   {name.upper()}"
    wd = int(tw(s, 24, "M", 2) + 56)
    box(im, 64, 20, wd, 40, 10, CARD, BORDER, 1, False, a)
    cv2.circle  # no-op reference for linters
    d = ImageDraw.Draw(im)
    d.ellipse([78, 34, 90, 46], fill=lerp(BLUE, PAGE, a))
    T(im, s, 102, 48, 24, "M", INK, sp=2, a=a, bg=CARD)


def title(im, s, sub=None, a=1.0):
    T(im, s, 64, 128, 56, "B", INK, a=a)
    if sub:
        T(im, sub, 64, 168, 28, "R", SEC, a=a)


def arrow(im, x0, y0, x1, y1, col=MUT, w=2, a=1.0, head=9):
    d = ImageDraw.Draw(im)
    c = lerp(col, PAGE, a)
    d.line([x0, y0, x1, y1], fill=c, width=w)
    v = np.array([x1 - x0, y1 - y0], float)
    n = np.linalg.norm(v)
    if n < head * 2:
        return
    v /= n
    p = np.array([-v[1], v[0]])
    tip = np.array([x1, y1], float)
    d.polygon([tuple(tip), tuple(tip - v * head + p * head * .55), tuple(tip - v * head - p * head * .55)], fill=c)


def dotted(im, x0, x1, y, col=GREYC, a=1.0):
    d = ImageDraw.Draw(im)
    x = x0
    while x < x0 + (x1 - x0) * a:
        d.line([x, y, x + 6, y], fill=col, width=2)
        x += 14


def hgrid_base():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    v = 1 - 0.018 * np.clip(r - 0.6, 0, 1)
    return (np.array(PAGE, float)[None, None, :] * v[..., None]).astype(np.uint8)


BASE = hgrid_base()


def newim():
    return Image.fromarray(BASE.copy())


def frames(path, start=0.0, end=None):
    c = cv2.VideoCapture(str(path))
    fps = c.get(cv2.CAP_PROP_FPS) or 25
    nn = int(c.get(cv2.CAP_PROP_FRAME_COUNT))
    a, b = int(start * fps), int(end * fps) if end else nn
    c.set(cv2.CAP_PROP_POS_FRAMES, a)
    out = []
    for i in range(a, min(b, nn)):
        ok, im = c.read()
        if not ok:
            break
        out.append(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
    return out


def pick(fr, n, speed):
    return [fr[min(len(fr) - 1, int(i * speed))] for i in range(n)]


class Out:
    def __init__(self, path):
        self.p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                   "-r", str(FPS), "-i", "-", "-pix_fmt", "yuv420p", "-vcodec", "libx264", "-crf", "18", str(path)], stdin=subprocess.PIPE)
        self.n, self.k, self.last = 0, 99, None

    def start(self):
        self.k = 0

    def put(self, im):
        a = np.asarray(im, np.uint8)
        if self.k < 10 and self.last is not None:
            t = ease((self.k + 1) / 10)
            a = (a * t + self.last * (1 - t)).astype(np.uint8)
        self.k += 1
        self.last = a
        self.p.stdin.write(np.ascontiguousarray(a).tobytes())
        self.n += 1

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def run(out, secs, draw):
    out.start()
    for k in range(int(secs * FPS)):
        im = newim()
        draw(im, k / FPS, k)
        out.put(im)


# ---------------------------------------------------------------- clip scenes
@lru_cache(None)
def rmask(w, h, r):
    m = Image.new("L", (w * 3, h * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 3 - 1, h * 3 - 1], r * 3, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def put_clip(im, arr, x0, y0, mw, mh):
    h0, w0 = arr.shape[:2]
    s = min(mw / w0, mh / h0)
    w, h = int(w0 * s), int(h0 * s)
    x, y = x0 + (mw - w) // 2, y0 + (mh - h) // 2
    box(im, x, y, w, h, 16, CARD, BORDER, 1, True)
    im.paste(Image.fromarray(cv2.resize(arr, (w - 2, h - 2), interpolation=cv2.INTER_AREA)), (x + 1, y + 1), rmask(w - 2, h - 2, 15))
    return x, y, w, h


def lower_third(im, k, ttl, chips, cap):
    p = eo((k - 5) / 10)
    if p <= 0:
        return
    y = 520
    dy = int((1 - p) * 12)
    box(im, 64, y, 1152, 136, 16, CARD, BORDER, 1, True, p, dy)
    # chips right aligned
    x = 1216 - 24
    cw = 0
    for lab, col in reversed(chips):
        wd = int(tw(lab, 28, "B") + 36)
        if cw:
            x -= 36
        x -= wd
        cw += wd
        chip(im, x, y + 46 + dy, lab, col, a=p)
        # arrow between chips
    if len(chips) == 2:
        ax = x + int(tw(chips[0][0], 28, "B") + 36) + 8
        arrow(im, ax, y + 68 + dy, ax + 20, y + 68 + dy, MUT, 2, p, 8)
    maxw = 1152 - 48 - (cw + 36 * (len(chips) - 1)) - 24
    T(im, ttl, 88, y + 44 + dy, 28, "B", INK, a=p, bg=CARD)
    P(im, cap, 88, y + 80 + dy, 24, "R", SEC, maxw, 29, p, CARD)


def clips(out, vids, labs, ch, ttl, chips, cap, secs, speed=1.0, start=0):
    out.start()
    n = int(secs * FPS)
    fr = [pick(frames(v, start), n, speed) for v in vids]
    for k in range(n):
        im = newim()
        chapter_chip(im, ch)
        if len(vids) == 1:
            put_clip(im, fr[0][k], 64, 92, 1152, 410)
        else:
            for j in range(2):
                x, y, w, h = put_clip(im, fr[j][k], 64 + j * 588, 92, 564, 410)
                chip(im, x + 14, y + 14, labs[j][0], CARD, 24, "M", 14, 36, labs[j][1], None, bg=CARD) if False else None
                lab, col = labs[j]
                cw = int(tw(lab.upper(), 24, "M", 1.5) + 44)
                box(im, x + 14, y + 14, cw, 38, 10, CARD, BORDER, 1, False)
                ImageDraw.Draw(im).ellipse([x + 26, y + 27, x + 38, y + 39], fill=col)
                T(im, lab.upper(), x + 46, y + 40, 24, "M", INK, sp=1.5, bg=CARD)
        lower_third(im, k, ttl, chips, cap)
        out.put(im)


# ---------------------------------------------------------------- animated scenes
def person(a, cx, cy, col, sc=1.0):
    cv2.circle(a, (cx, int(cy - 52 * sc)), int(17 * sc), col, -1, cv2.LINE_AA)
    cv2.ellipse(a, (cx, int(cy + 5 * sc)), (int(26 * sc), int(40 * sc)), 0, 180, 360, col, -1, cv2.LINE_AA)
    cv2.rectangle(a, (cx - int(26 * sc), int(cy + 4 * sc)), (cx + int(26 * sc), int(cy + 38 * sc)), col, -1, cv2.LINE_AA)


def arm(a, bx, by, ang1, ang2, col, sc=1.0):
    cv2.rectangle(a, (bx - 28, by - 8), (bx + 28, by), col, -1, cv2.LINE_AA)
    j1 = (int(bx + 0 * sc), by - 8)
    e1 = (int(bx + 70 * np.sin(ang1)), int(by - 8 - 70 * np.cos(ang1)))
    e2 = (int(e1[0] + 62 * np.sin(ang2)), int(e1[1] - 62 * np.cos(ang2)))
    cv2.line(a, j1, e1, col, 9, cv2.LINE_AA)
    cv2.line(a, e1, e2, col, 9, cv2.LINE_AA)
    for p_ in (j1, e1):
        cv2.circle(a, p_, 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(a, p_, 9, col, 2, cv2.LINE_AA)
    cv2.line(a, e2, (e2[0] - 10, e2[1] + 16), col, 4, cv2.LINE_AA)
    cv2.line(a, e2, (e2[0] + 10, e2[1] + 16), col, 4, cv2.LINE_AA)


def intro(im, t, k):
    a1 = eo(t / 1.0)
    T(im, "TransferGap", 64, 200 + int((1 - a1) * 14), 112, "B", INK, a=a1)
    bw = int(210 * eo((t - 1.0) / 0.9))
    ImageDraw.Draw(im).rectangle([66, 226, 66 + bw, 231], fill=BLUE)
    for i, l in enumerate(["One human demonstration -> many robots.", "When the copy fails, we say which stage failed."]):
        T(im, l, 64, 292 + 46 * i, 32, "R", SEC, a=eo((t - 1.6 - 0.8 * i) / 0.8))
    arr = np.array(im)
    pa = eo((t - 3.2) / 0.6)
    if pa > 0:
        person(arr, 200, 560, lerp(INK, PAGE, pa))
    bus_y = 626
    prog = eo((t - 3.8) / 1.2)
    x_end = int(200 + (1180 - 200) * prog)
    if prog > 0:
        cv2.line(arr, (200, 612), (200, bus_y), MUT, 2, cv2.LINE_AA)
        cv2.line(arr, (200, bus_y), (x_end, bus_y), MUT, 2, cv2.LINE_AA)
    poses = [(0.35, -0.5), (-0.3, 0.7), (0.15, 0.9)]
    for j, nm in enumerate(["UR5e", "UR10e", "KAIROS"]):
        bx = 560 + j * 270
        s = eo((t - 4.4 - 0.5 * j) / 0.6)
        if x_end >= bx and s > 0:
            cv2.line(arr, (bx, bus_y), (bx, int(bus_y - 28 * s)), MUT, 2, cv2.LINE_AA)
        if s > 0.99:
            sw = 0.25 * np.sin((t - 5) * 1.6 + j)
            arm(arr, bx, 598, poses[j][0] + sw * 0.3, poses[j][1] + sw, BLUE)
    im.paste(Image.fromarray(arr))
    T(im, "Human", 200, 676, 24, "M", MUT, "m", a=pa)
    for j, nm in enumerate(["UR5e", "UR10e", "KAIROS"]):
        T(im, nm, 560 + j * 270, 676, 24, "M", MUT, "m", a=eo((t - 5.0 - 0.5 * j) / 0.5))
    T(im, "Simulation only.", 1216, 292 + 46, 24, "R", MUT, "r", a=eo((t - 6.6) / 0.6))


PIPE = [("Human video", "One short clip"),
        ("Measure the person", "Pose, limb lengths"),
        ("Copy to robots", "UR5e, UR10e, KAIROS, G1"),
        ("Fails? Diagnose", "Perception, retargeting, calibration, timing"),
        ("Nemotron picks the fix", "Nemotron-3-Super, Nebius Token Factory"),
        ("Verified fix", f"UR5e success {N['ur5e_raw']} -> {N['fixed']} of {N['of']}"),
        ("Train one policy", "One network, all robots"),
        ("Fine-tune GR00T-N1.5", "NVIDIA 3B robot model")]


def prects():
    bw, bh = 264, 236
    out = []
    for i in range(8):
        row, c = divmod(i, 4)
        c = c if row == 0 else 3 - c
        out.append((64 + c * (bw + 32), 128 + row * (bh + 40), bw, bh))
    return out


def pipeline(im, t, k):
    T(im, "How it works", 64, 84, 56, "B", INK)
    R = prects()
    cur = min(7, int((t - 0.4) / 1.0)) if t < 8.6 else min(7, int((t - 8.6) / 0.68))
    for i, (x, y, w, h) in enumerate(R):
        a = eo((t - 0.4 - 1.0 * i) / 0.6)
        if i and a > 0:
            px, py, pw, ph = R[i - 1]
            if py == y:
                d = 1 if x > px else -1
                x0 = px + pw + 4 if d > 0 else px - 4
                x1 = x - 4 if d > 0 else x + w + 4
                arrow(im, x0, y + h // 2, int(x0 + (x1 - x0) * a), y + h // 2, MUT, 2, 1, 9 if a > .9 else 1)
            else:
                cx = px + pw // 2
                y0, y1 = py + ph + 3, y - 3
                arrow(im, cx, y0, cx, int(y0 + (y1 - y0) * a), MUT, 2, 1, 9 if a > .9 else 1)
        if a <= 0:
            continue
        hi = i == cur
        box(im, x, y, w, h, 16, CARD, BLUE if hi else BORDER, 3 if hi else 1, True, a, int((1 - a) * 12))
        dy = int((1 - a) * 12)
        d = ImageDraw.Draw(im)
        d.ellipse([x + 20, y + 18 + dy, x + 56, y + 54 + dy], fill=lerp(BLUE if hi else INK, CARD, a))
        T(im, str(i + 1), x + 38, y + 44 + dy, 24, "B", (255, 255, 255), "m", a=a, bg=BLUE if hi else INK)
        yy = y + 90 + dy
        yy = P(im, PIPE[i][0], x + 20, yy, 26, "B", INK, w - 36, 31, a, CARD)
        P(im, PIPE[i][1], x + 20, yy + 4, 24, "R", SEC, w - 36, 29, a, CARD)
    T(im, "All results: simulation, held-out random seeds.", 64, 692, 24, "R", MUT)


ROWS = ["UR5e", "UR10e", "KAIROS arm", "KAIROS mobile"]
COLS = ["standard", "mixed", "hard"]


def grid(im, t, k):
    chapter_chip(im, "4 Learn one policy")
    title(im, "One policy, four robots", "No robot id is given to the network.")
    tx, ty, tw_, hh, rh = 64, 188, 1152, 56, 66
    box(im, tx, ty, tw_, hh + rh * 4, 16)
    c0 = 330
    cwid = (tw_ - c0) / 3
    T(im, "ROBOT", tx + 32, ty + 37, 24, "M", MUT, sp=2, bg=CARD)
    for j, c in enumerate(COLS):
        T(im, c.upper(), tx + c0 + cwid * (j + .5), ty + 37, 24, "M", MUT, "m", sp=2, bg=CARD)
    d = ImageDraw.Draw(im)
    d.line([tx + 1, ty + hh, tx + tw_ - 2, ty + hh], fill=BORDER, width=1)
    lit = 0
    for i, rn in enumerate(ROWS):
        y = ty + hh + i * rh
        if i:
            d.line([tx + 24, y, tx + tw_ - 24, y], fill=GRID, width=1)
        T(im, rn, tx + 32, y + rh // 2 + 10, 28, "M", INK, bg=CARD)
        for j in range(3):
            n = i * 3 + j
            a = (t - 0.8 - 0.42 * n) / 0.35
            if a <= 0:
                continue
            lit += a >= 1
            chip(im, tx + c0 + cwid * (j + .5) - 78, y + 11, f"{N['of']}/{N['of']}", GREEN, 28, "B", 0, 44, sc=0.5 + 0.5 * eo(a) if a < 1 else 1.0) if False else None
            sc = 0.5 + 0.5 * eo(a) if a < 1 else 1.0
            chip(im, int(tx + c0 + cwid * (j + .5) - 78), y + 11, f"{N['of']}/{N['of']}", GREEN, 28, "B", 0, 44, sc=sc) if False else None
            wd = 156
            cx, cy = tx + c0 + cwid * (j + .5), y + rh / 2
            w2, h2 = int(wd * sc), int(44 * sc)
            box(im, cx - w2 / 2, cy - h2 / 2, w2, h2, 10, GREEN, None, 0, False)
            T(im, f"{N['of']}/{N['of']}", cx, cy + int(10 * sc), max(10, int(28 * sc)), "B", (255, 255, 255), "m", bg=GREEN)
    by = ty + hh + rh * 4 + 54
    T(im, f"{lit} of 12 cells at {N['of']}/{N['of']}", 64, by, 32, "B", GREEN)
    s = f"Two training runs: {N['grid_cells_full']} of {N['grid_cells_total']} cells {N['of']}/{N['of']} and two {N['of'] - 1}/{N['of']} on {N['grid_seeds']} brand-new seeds."
    T(im, s, 64, by + 44, 26, "R", INK, a=eo((t - 6.8) / 0.8))
    T(im, "Mobile base parked (arm only). Simulation.", 64, 692, 24, "R", MUT, a=eo((t - 7.6) / 0.8))


def bars(im, t, k):
    chapter_chip(im, "5 GR00T")
    title(im, "GR00T-N1.5 (3B)", f"Successes out of {N['gr_of']} fresh seeds")
    x0, x1, ytop, ybot = 120, 1216, 232, 452
    u = (ybot - ytop) / N["gr_of"]
    d = ImageDraw.Draw(im)
    for v in (0, 10, 20):
        y = int(ybot - u * v)
        d.line([x0, y, x1, y], fill=GRID if v else BORDER, width=1 if v else 2)
        T(im, str(v), x0 - 14, y + 8, 24, "R", MUT, "r")
    T(im, str(N["gr_of"]), x0 - 14, ytop + 8, 24, "R", MUT, "r")
    ra = eo((t - 6.4) / 0.8)
    dotted(im, x0, x1, ytop, GREYC, ra)
    T(im, f"small policy: {N['of']}/{N['of']}", x1, ytop - 12, 26, "B", SEC, "r", a=ra)
    slot = (x1 - x0) / 4
    data = [("before: first-step execution", 1, 0, f"{N['gr_before']}/{N['gr_of']}", ORANGE, False),
            (f"after: {N['gr_ahead']} steps ahead, UR10e", N["gr_ur10e"], 0, f"{N['gr_ur10e']}/{N['gr_of']}", VIOLET, True),
            (f"after: {N['gr_ahead']} steps ahead, KAIROS", N["gr_kairos"], 0, f"{N['gr_kairos']}/{N['gr_of']}", VIOLET, True),
            ("3-robot model, UR5e / UR10e", 10, 5, f"{N['gr_multi']}/{N['gr_of']}", (201, 195, 240), False)]
    for i, (lab, v, lo, vl, col, inside) in enumerate(data):
        cx = x0 + slot * (i + .5)
        a = eo((t - 0.8 - 1.2 * i) / 1.1)
        bx = int(cx - 75)
        hgt = max(4, int(u * v * a))
        r = 4
        d.rounded_rectangle([bx, ybot - hgt, bx + 150, ybot + r], r, fill=col)
        d.rectangle([bx, ybot - 1, bx + 150, ybot + 3], fill=PAGE)
        d.line([bx - 6, ybot, bx + 156, ybot], fill=BORDER, width=2)
        if lo:
            d.rounded_rectangle([bx, ybot - int(u * lo * a), bx + 150, ybot + r], r, fill=VIOLET)
            d.rectangle([bx, ybot - 1, bx + 150, ybot + 3], fill=PAGE)
            d.line([bx - 6, ybot, bx + 156, ybot], fill=BORDER, width=2)
        if a >= 1:
            if inside:
                T(im, vl, cx, ybot - hgt + 42, 32, "B", (255, 255, 255), "m", bg=col)
            else:
                T(im, vl, cx, ybot - hgt - 14, 28, "B", ORANGE if i == 0 else INK, "m")
        P(im, lab, cx, ybot + 36, 24, "R", SEC, 240, 28, eo((t - 1.0 - 1.2 * i) / 0.6), PAGE, "m")
    aa = eo((t - 4.8) / 0.6)
    if aa > 0:
        T(im, f"execute {N['gr_ahead']} steps ahead", x0 + 20, 330, 26, "M", VIOLET, a=aa)
        arrow(im, x0 + 20, 346, int(x0 + 20 + (x0 + slot * 1.5 - 75 - 14 - x0 - 20) * aa), 346, VIOLET, 3, 1, 11 if aa > .9 else 1)
    P(im, "The arm stopped 2-5 cm short of the cube; executing the plan 4 steps ahead fixed it, no retraining.", 64, 590, 28, "R", INK, 1152, 36, eo((t - 8.0) / 0.8))


MODELS = [("N", "Nemotron-3-Super", "Reads failure statistics, diagnoses, picks the fix.", "Nebius Token Factory API"),
          ("C", "Cosmos-Reason2 critic", f"{N['cosmos_acc']}% accuracy on {N['cosmos_clips']} simulated clips.", None),
          ("G", "GR00T-N1.5 (3B)", "Fine-tuned policy.", None),
          ("S", "SONIC", "Whole-body control of the Unitree G1.", None)]


def models(im, t, k):
    T(im, "NVIDIA models and Nebius", 64, 120, 56, "B", INK)
    for i, (ic, ti, body, pill) in enumerate(MODELS):
        a = eo((t - 0.6 - 1.5 * i) / 0.7)
        if a <= 0:
            continue
        x, y = 64 + (i % 2) * 592, 168 + (i // 2) * 232
        dy = int((1 - a) * 12)
        box(im, x, y, 560, 208, 16, CARD, BLUE if pill else BORDER, 3 if pill else 1, True, a, dy)
        d = ImageDraw.Draw(im)
        d.ellipse([x + 28, y + 28 + dy, x + 92, y + 92 + dy], fill=lerp((226, 237, 250), CARD, a))
        T(im, ic, x + 60, y + 72 + dy, 32, "B", BLUE, "m", a=a, bg=(226, 237, 250))
        T(im, ti, x + 112, y + 58 + dy, 30, "B", INK, a=a, bg=CARD)
        yy = y + 100 + dy
        if pill:
            wd = int(tw(pill, 24, "M") + 32)
            box(im, x + 112, yy - 26, wd, 38, 10, BLUE, None, 0, False, a)
            T(im, pill, x + 112 + wd / 2, yy, 24, "M", (255, 255, 255), "m", a=a, bg=BLUE)
            yy += 44
        P(im, body, x + 112, yy + 4, 26, "R", SEC, 420, 31, a, CARD)
    T(im, "Nemotron is called through the Nebius Token Factory API.", 64, 664, 26, "R", SEC, a=eo((t - 7.5) / 0.8))


LIMITS = ["Simulation only.", "One demonstration, one task.", "Policies trained on scripted rollouts.", "Mobile base parked.",
          f"Shoulder width assumed {N['shoulder_m']} m.", "GR00T worse than the small policy."]


def limits(im, t, k):
    chapter_chip(im, "6 Limits")
    title(im, "What this is not")
    d = ImageDraw.Draw(im)
    for i, l in enumerate(LIMITS):
        a = eo((t - 0.5 - 0.8 * i) / 0.5)
        y = 220 + i * 70
        c = lerp(MUT, PAGE, a)
        d.ellipse([70, y - 20, 106, y + 16], outline=c, width=2)
        d.line([80, y - 2, 96, y - 2], fill=c, width=2)
        T(im, l, 128 + int((1 - a) * 12), y + 10, 34, "R", INK, a=a)
        d.line([64, y + 34, 700, y + 34], fill=lerp(GRID, PAGE, a), width=1)


def outro(im, t, k):
    T(im, "TransferGap", 64, 130, 64, "B", INK)
    figs = [(f"{N['ur5e_raw']} -> {N['fixed']}", f"UR5e raw copy to diagnosed fixes, of {N['of']} held-out seeds", ORANGE),
            (f"{N['of']}/{N['of']}", "One small policy, four robots, all 12 cells", GREEN),
            (f"{N['gr_ur10e']}-{N['gr_kairos']}/{N['gr_of']}", "GR00T-N1.5 fine-tuned, standard cells", VIOLET)]
    for i, (big, lab, col) in enumerate(figs):
        a = eo((t - 0.6 - 0.8 * i) / 0.7)
        x = 64 + i * 400
        box(im, x, 190, 352, 300, 16, CARD, BORDER, 1, True, a, int((1 - a) * 12))
        dy = int((1 - a) * 12)
        ImageDraw.Draw(im).rectangle([x + 28, 222 + dy, x + 76, 226 + dy], fill=lerp(col, CARD, a))
        T(im, big, x + 28, 320 + dy, 64, "B", INK, a=a, bg=CARD)
        P(im, lab, x + 28, 372 + dy, 26, "R", SEC, 300, 32, a, CARD)
    T(im, "Nemotron is called through the Nebius Token Factory API. Simulation only.", 64, 600, 26, "R", SEC, a=eo((t - 3.4) / 0.8))


def main(path):
    out = Out(path)
    hq, sm = UI / "media" / "hq", UI / "media" / "scale"
    marks = []

    def mark(s):
        marks.append((out.n / FPS, s))
    mark("Intro"); run(out, 8, intro)
    mark("How it works (pipeline)"); run(out, 14, pipeline)
    mark("1 Measure")
    clips(out, [UI / "media" / "human_overlay.mp4"], None, "1 Measure", "Pose and limb lengths from one clip", [("1 clip", BLUE)],
          "Background replaced for the video; measurements come from the original clip.", 9, 0.8)
    clips(out, [ROOT / "results" / "hand_retarget_v1" / "hand_retarget.mp4"], None, "1 Measure", "Fingers copied to a robot hand", [("21 keypoints", BLUE)],
          "21 hand keypoints drive a dexterous robot hand by fingertip IK. Kinematic only.", 8, 1.6)
    mark("2 Copy: humanoid")
    clips(out, [ROOT / "results" / "g1_in_image_v1" / "videos" / "image_seed1200_placed.mp4"], None, "2 Copy", "Humanoid G1 places a block",
          [(f"{N['g1_ok']}/{N['g1_n']} pooled", GREEN)],
          f"Closed-loop pick and place with a generic block. Copying the author's grasp style: {N['g1_style_ok']}/{N['g1_style_n']}.", 12, 1.0, 4)
    mark("3 Diagnose + fix: robots")
    ks = {"ur5e": "ur5e", "ur10e": "ur10e", "kairos_mobile": "kairos"}
    for r, name in (("ur5e", "UR5e"), ("ur10e", "UR10e"), ("kairos_mobile", "KAIROS mobile")):
        d = TG["robots"][ks[r]]
        clips(out, [hq / f"{r}_raw_seed1001.mp4", hq / f"{r}_stack_seed1001.mp4"], [("raw copy", ORANGE), ("with fixes", GREEN)], "3 Diagnose + fix",
              f"{name}: raw copy vs diagnosed fixes", [(f"{d['raw']['k']}/{d['raw']['n']}", ORANGE), (f"{d['fix']['k']}/{d['fix']['n']}", GREEN)],
              "Held-out success over 60 seeds. This clip shows one seed, an illustration.", 8.5)
    mark("3 Diagnose + fix: object size")
    for cm in (3, 5, 7):
        big = cm == 7
        clips(out, [sm / f"ur10e_{cm}cm_raw_seed1000.mp4", sm / f"ur10e_{cm}cm_stack_seed1000.mp4"], [(f"raw, {cm} cm", ORANGE), ("with fixes", GREEN)], "3 Diagnose + fix",
              f"UR10e, bigger object: {cm} cm cube",
              [(f"{N['cube7_raw']}/{N['of']}", ORANGE), (f"{N['cube7_fix']}/{N['of']}", GREEN)] if big else [("same fixes", BLUE)],
              "Never tuned for this size. Exploratory." if not big else "Never tuned for this size; held-out seeds. Exploratory.", 6, 1.4)
    mark("4 Learn one policy")
    pm = UI / "media" / "policy_multi"
    for r, name in (("ur5e", "UR5e"), ("ur10e", "UR10e"), ("kairos", "KAIROS")):
        clips(out, [pm / f"{r}_seed6000_success.mp4"], None, "4 Learn one policy", f"One learned policy, {name}", [(f"{N['of']}/{N['of']} per cell", GREEN)],
              "No scripted controller: a fresh seed, images and joint positions in, actions out.", 5, 1.7)
    run(out, 10, grid)
    mark("5 GR00T"); run(out, 12, bars)
    mark("NVIDIA models and Nebius"); run(out, 10, models)
    mark("6 Limits"); run(out, 7, limits)
    mark("Summary"); run(out, 6, outro)
    out.close()
    print("frames", out.n, "seconds", round(out.n / FPS, 1))
    for m in marks:
        print(f"{int(m[0] // 60)}:{int(m[0] % 60):02d}  {m[1]}")


if __name__ == "__main__":
    main(sys.argv[1])
