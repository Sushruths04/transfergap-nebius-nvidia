"""v7: hackathon pitch cut (< 3 min), PIL typography + OpenCV clips, silent.

    python3 scripts/make_final_cut_v7.py OUT.mp4
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
    wd = int(tw(s, 26, "M", 2) + 56)
    box(im, 64, 20, wd, 40, 10, CARD, BORDER, 1, False, a)
    cv2.circle  # no-op reference for linters
    d = ImageDraw.Draw(im)
    d.ellipse([78, 34, 90, 46], fill=lerp(BLUE, PAGE, a))
    T(im, s, 102, 49, 26, "M", INK, sp=2, a=a, bg=CARD)


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
    im = Image.fromarray(BASE.copy())
    T(im, 'Results shown in simulation', 1216, 704, 26, 'R', MUT, 'r')
    return im


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
    T(im, ttl, 88, y + 44 + dy, 30, "B", INK, a=p, bg=CARD)
    P(im, cap, 88, y + 84 + dy, 26, "R", SEC, maxw, 31, p, CARD)


def clips(out, vids, labs, ch, ttl, chips, cap, secs, speed=1.0, start=0, cnt=None):
    out.start()
    n = int(secs * FPS)
    fr = [pick(frames(v, start), n, speed) for v in vids]
    for k in range(n):
        im = newim()
        chapter_chip(im, ch)
        if cnt:
            cwd = int(tw(cnt, 26, "M") + 40)
            box(im, 1216 - cwd, 20, cwd, 40, 10, CARD, BLUE, 2, False)
            T(im, cnt, 1216 - cwd / 2, 49, 26, "M", BLUE, "m", bg=CARD)
        if len(vids) == 1:
            put_clip(im, fr[0][k], 64, 92, 1152, 410)
        else:
            for j in range(2):
                x, y, w, h = put_clip(im, fr[j][k], 64 + j * 588, 92, 564, 410)
                chip(im, x + 14, y + 14, labs[j][0], CARD, 24, "M", 14, 36, labs[j][1], None, bg=CARD) if False else None
                lab, col = labs[j]
                cw = int(tw(lab.upper(), 26, "M", 1.5) + 44)
                box(im, x + 14, y + 14, cw, 38, 10, CARD, BORDER, 1, False)
                ImageDraw.Draw(im).ellipse([x + 26, y + 27, x + 38, y + 39], fill=col)
                T(im, lab.upper(), x + 46, y + 41, 26, "M", INK, sp=1.5, bg=CARD)
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


def draw_person_np(im, cx, cy, sc, col):
    arr = np.array(im)
    person(arr, cx, cy, col, sc)
    im.paste(Image.fromarray(arr))


def hook(im, t, k):
    a = eo((t - 1.0) / 1.0)
    P(im, "Every robot starts with one person showing how.", 64, 150, 56, "B", INK, 1100, 68, a)
    pa = eo((t - 0.3) / 0.8)
    arr = np.array(im)
    for q in range(2):
        ph = ((t - 0.8 + q * 1.1) % 2.2) / 2.2
        if t > 0.8:
            cv2.circle(arr, (640, 470), int(14 + 70 * ph), lerp(GREYC, PAGE, 1 - 0.8 * (1 - ph)), 2, cv2.LINE_AA)
    person(arr, 640, 478, lerp(INK, PAGE, pa), 0.32)
    im.paste(Image.fromarray(arr))
    ca = eo((t - 3.0) / 0.8)
    T(im, "1", 64, 650, 120, "B", BLUE, a=ca)
    T(im, "demonstration", 64 + tw("1", 120, "B") + 24, 650, 44, "M", SEC, a=ca)


WHY = [("Robots are leaving the factory", "Arms, mobile manipulators, humanoids.", BLUE),
       ("Foundation models for robots are here", "NVIDIA GR00T, Cosmos, Nemotron.", BLUE),
       ("The bottleneck", "Teaching every new robot takes expert time.", ORANGE)]


def why(im, t, k):
    chapter_chip(im, "2 Why now")
    T(im, "Why now", 64, 128, 56, "B", INK)
    for i, (h1, h2, col) in enumerate(WHY):
        a = eo((t - 1.2 - 5.0 * i) / 0.8)
        if a <= 0:
            continue
        y = 168 + i * 150
        dx = int((1 - a) * 90)
        box(im, 64 + dx, y, 1152, 128, 16, CARD, BORDER, 1, True, a)
        ImageDraw.Draw(im).rounded_rectangle([64 + dx + 28, y + 28, 64 + dx + 36, y + 100], 4, fill=lerp(col, CARD, a))
        T(im, h1, 64 + dx + 64, y + 54, 36, "B", INK, a=a, bg=CARD)
        T(im, h2, 64 + dx + 64, y + 98, 28, "R", SEC, a=a, bg=CARD)
    T(im, "Can one demonstration teach many robots?", 64, 650, 36, "B", BLUE, a=eo((t - 17.5) / 0.8))


def dots(im, y0, filled, col_on, n_hollow_col=GREYC, fillprog=None):
    for i in range(60):
        x, y = 100 + (i % 30) * 36, y0 + (i // 30) * 48
        on = i < filled
        if on:
            box(im, x - 12, y - 12, 24, 24, 12, col_on, None, 0, False)
        else:
            box(im, x - 12, y - 12, 24, 24, 12, PAGE, n_hollow_col, 2, False)


def gap(im, t, k):
    chapter_chip(im, "3 The gap")
    P(im, "A human demo copied onto a robot works about half the time: 31 of 60 on the UR5e.", 64, 130, 36, "B", INK, 1152, 46, eo((t - 0.6) / 0.8))
    T(im, "Nobody knows why.", 64, 270, 40, "B", ORANGE, a=eo((t - 5.0) / 0.8))
    if t < 8.5:
        n = int(31 * eo((t - 1.5) / 3.0))
        dots(im, 420, n, ORANGE)
        T(im, f"{n} of 60", 64, 600, 64, "B", ORANGE)
    else:
        u = eo((t - 9.5) / 3.0)
        n = 31 + int(29 * u)
        dots(im, 420, n, GREEN if n > 31 else ORANGE)
        for i in range(31):
            pass
        T(im, f"{n} of 60", 64, 600, 64, "B", GREEN if n > 31 else ORANGE)
    T(im, "TransferGap finds the failing stage and fixes it.", 64, 340, 40, "B", BLUE, a=eo((t - 8.8) / 0.8))


PIPE = [("Human video", "One demonstration"),
        ("Measure the person", "Pose, limb lengths"),
        ("Copy to robots", "UR5e, UR10e, KAIROS, G1"),
        ("Fails? Diagnose", "Perception, retargeting, calibration, timing"),
        ("Pick the fix", "Nemotron-3-Super via Nebius Token Factory API"),
        ("Verified fix", f"UR5e: {N['ur5e_raw']} -> {N['fixed']} of {N['of']}"),
        ("Train one policy", "One network, all robots"),
        ("Fine-tune GR00T", "NVIDIA N1.5, 3B model")]


def prects():
    bw, bh = 264, 262
    return [(64 + (c if r == 0 else 3 - c) * (bw + 32), 84 + r * (bh + 32), bw, bh) for i in range(8) for r, c in [divmod(i, 4)]]


def pipeline(im, t, k):
    chapter_chip(im, "4 How it works")
    R = [(x, y + 0, w, h) for x, y, w, h in prects()]
    R = [(x, y + 0, w, h) for x, y, w, h in R]
    cur = min(7, int((t - 0.5) / 1.2)) if t < 10.2 else min(7, int((t - 10.2) / 0.6))
    for i, (x, y, w, h) in enumerate(R):
        y += 0
        a = eo((t - 0.5 - 1.2 * i) / 0.6)
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
        dy = int((1 - a) * 12)
        box(im, x, y, w, h, 16, CARD, BLUE if hi else BORDER, 3 if hi else 1, True, a, dy)
        ImageDraw.Draw(im).ellipse([x + 20, y + 18 + dy, x + 56, y + 54 + dy], fill=lerp(BLUE if hi else INK, CARD, a))
        T(im, str(i + 1), x + 38, y + 45 + dy, 26, "B", (255, 255, 255), "m", a=a, bg=BLUE if hi else INK)
        yy = P(im, PIPE[i][0], x + 20, y + 90 + dy, 26, "B", INK, w - 36, 31, a, CARD)
        P(im, PIPE[i][1], x + 20, yy + 4, 26, "R", SEC, w - 36, 31, a, CARD)


def cube_anim(im, t, k):
    chapter_chip(im, "5 Scale up")
    cwd = int(tw("1 demonstration  ·  bigger objects", 26, "M") + 40)
    box(im, 1216 - cwd, 20, cwd, 40, 10, CARD, BLUE, 2, False)
    T(im, "1 demonstration  ·  bigger objects", 1216 - cwd / 2, 49, 26, "M", BLUE, "m", bg=CARD)
    T(im, "Then we make the object bigger", 64, 128, 56, "B", INK)
    g = eo(t / 2.5)
    s = int(30 + 190 * g)
    cx, cy = 340, 460
    box(im, cx - s // 2, cy + 110 - s, s, s, 10, (255, 232, 222), ORANGE, 3, True)
    T(im, "7 cm cube", cx, 600, 32, "B", INK, "m")
    c = eo((t - 1.0) / 2.5)
    T(im, "UR10e, held-out seeds", 700, 290, 30, "R", SEC)
    T(im, f"{int(N['cube7_raw'] + (N['cube7_fix'] - N['cube7_raw']) * c)}", 700, 440, 150, "B", GREEN if c > 0.05 else ORANGE)
    T(im, f"of {N['of']}", 700 + tw(f"{N['cube7_fix']}", 150, "B") + 28, 440, 56, "M", SEC)
    T(im, f"raw copy {N['cube7_raw']}  ->  with fixes {N['cube7_fix']}", 700, 520, 34, "B", INK, a=eo((t - 2.8) / 0.6))


ROWS = ["UR5e", "UR10e", "KAIROS arm", "KAIROS mobile"]
COLS = ["standard", "mixed", "hard"]


def grid(im, t, k):
    chapter_chip(im, "6 One brain")
    T(im, "One learned policy drives four robots", 64, 128, 52, "B", INK)
    tx, ty, tw_, hh, rh = 64, 160, 1152, 56, 66
    box(im, tx, ty, tw_, hh + rh * 4, 16)
    c0 = 330
    cwid = (tw_ - c0) / 3
    T(im, "ROBOT", tx + 32, ty + 38, 26, "M", MUT, sp=2, bg=CARD)
    for j, c in enumerate(COLS):
        T(im, c.upper(), tx + c0 + cwid * (j + .5), ty + 38, 26, "M", MUT, "m", sp=2, bg=CARD)
    d = ImageDraw.Draw(im)
    d.line([tx + 1, ty + hh, tx + tw_ - 2, ty + hh], fill=BORDER, width=1)
    lit = 0
    for i, rn in enumerate(ROWS):
        y = ty + hh + i * rh
        if i:
            d.line([tx + 24, y, tx + tw_ - 24, y], fill=GRID, width=1)
        T(im, rn, tx + 32, y + rh // 2 + 10, 30, "M", INK, bg=CARD)
        for j in range(3):
            n = i * 3 + j
            a = (t - 0.6 - 0.35 * n) / 0.3
            if a <= 0:
                continue
            lit += a >= 1
            sc = 0.5 + 0.5 * eo(a) if a < 1 else 1.0
            cx, cy = tx + c0 + cwid * (j + .5), y + rh / 2
            w2, h2 = int(156 * sc), int(44 * sc)
            box(im, cx - w2 / 2, cy - h2 / 2, w2, h2, 10, GREEN, None, 0, False)
            T(im, f"{N['of']}/{N['of']}", cx, cy + int(10 * sc), max(10, int(28 * sc)), "B", (255, 255, 255), "m", bg=GREEN)
    by = ty + hh + rh * 4 + 56
    T(im, f"{lit} of 12 cells at {N['of']}/{N['of']}", 64, by, 36, "B", GREEN)
    s = f"Two training runs; {N['grid_cells_full']} of {N['grid_cells_total']} cells {N['of']}/{N['of']} on {N['grid_seeds']} brand-new seeds."
    T(im, s, 64, by + 46, 28, "R", INK, a=eo((t - 5.5) / 0.8))


MODELS = [("N", "Nemotron-3-Super", "Picks the fix.", "Nebius Token Factory API"),
          ("C", "Cosmos-Reason2 critic", f"{N['cosmos_acc']}% accuracy on {N['cosmos_clips']} simulated clips.", None),
          ("G", "GR00T-N1.5 (3B)", f"Fine-tuned: {N['gr_kairos']}/{N['gr_of']} on KAIROS, {N['gr_ur10e']}/{N['gr_of']} on UR10e.", None),
          ("S", "SONIC", "Whole-body control of the Unitree G1 humanoid.", None)]


def models(im, t, k):
    chapter_chip(im, "7 The stack")
    T(im, "NVIDIA models and Nebius", 64, 128, 56, "B", INK)
    for i, (ic, ti, body, pill) in enumerate(MODELS):
        a = eo((t - 0.6 - 1.5 * i) / 0.7)
        if a <= 0:
            continue
        x, y = 64 + (i % 2) * 592, 160 + (i // 2) * 232
        dy = int((1 - a) * 12)
        box(im, x, y, 560, 212, 16, CARD, BLUE if pill else BORDER, 3 if pill else 1, True, a, dy)
        ImageDraw.Draw(im).ellipse([x + 28, y + 28 + dy, x + 92, y + 92 + dy], fill=lerp((226, 237, 250), CARD, a))
        T(im, ic, x + 60, y + 72 + dy, 32, "B", BLUE, "m", a=a, bg=(226, 237, 250))
        T(im, ti, x + 112, y + 58 + dy, 30, "B", INK, a=a, bg=CARD)
        yy = y + 104 + dy
        if pill:
            wd = int(tw(pill, 26, "M") + 32)
            box(im, x + 112, yy - 28, wd, 40, 10, BLUE, None, 0, False, a)
            T(im, pill, x + 112 + wd / 2, yy, 26, "M", (255, 255, 255), "m", a=a, bg=BLUE)
            yy += 48
        P(im, body, x + 112, yy + 4, 26, "R", SEC, 420, 31, a, CARD)
    T(im, "Nemotron called through the Nebius Token Factory API.", 64, 654, 28, "R", SEC, a=eo((t - 7.0) / 0.8))


def gr00t(im, t, k):
    chapter_chip(im, "7 The stack")
    T(im, "GR00T-N1.5, fine-tuned", 64, 128, 56, "B", INK)
    T(im, "From 0 to 27/30 in one debugging session", 64, 172, 32, "R", SEC)
    x0, wmax = 300, 860
    d = ImageDraw.Draw(im)
    for v in (0, N["gr_of"]):
        x = x0 + int(wmax * v / N["gr_of"])
        d.line([x, 260, x, 470], fill=GRID if v else BORDER, width=2)
        T(im, str(v), x, 508, 26, "R", MUT, "m")
    for i, (nm, v) in enumerate((("KAIROS", N["gr_kairos"]), ("UR10e", N["gr_ur10e"]))):
        a = eo((t - 0.8 - 1.0 * i) / 3.0)
        y = 290 + i * 100
        T(im, nm, 64, y + 44, 32, "M", INK)
        wbar = max(4, int(wmax * v / N["gr_of"] * a))
        d.rounded_rectangle([x0, y, x0 + wbar, y + 64], 4, fill=VIOLET)
        d.rectangle([x0, y, x0 + 4, y + 64], fill=VIOLET)
        T(im, f"{int(v * a)}/{N['gr_of']}", x0 + wbar - 16 if wbar > 170 else x0 + wbar + 16, y + 44, 34, "B", (255, 255, 255) if wbar > 170 else INK, "r" if wbar > 170 else "l", bg=VIOLET if wbar > 170 else PAGE)
    T(im, "Fresh seeds; no retraining after the fix.", 64, 600, 28, "R", SEC, a=eo((t - 5.0) / 0.8))


def icon_np(arr, kind, cx, cy, col):
    if kind == "arm":
        arm(arr, cx, cy + 34, 0.4, -0.6, col)
    elif kind == "mobile":
        cv2.rectangle(arr, (cx - 34, cy + 22), (cx + 34, cy + 36), col, -1, cv2.LINE_AA)
        for wx in (-22, 22):
            cv2.circle(arr, (cx + wx, cy + 40), 7, col, -1, cv2.LINE_AA)
        cv2.line(arr, (cx, cy + 22), (cx + 12, cy - 12), col, 7, cv2.LINE_AA)
        cv2.line(arr, (cx + 12, cy - 12), (cx + 34, cy - 24), col, 7, cv2.LINE_AA)
    elif kind == "human":
        cv2.circle(arr, (cx, cy - 30), 11, col, -1, cv2.LINE_AA)
        cv2.line(arr, (cx, cy - 18), (cx, cy + 14), col, 8, cv2.LINE_AA)
        cv2.line(arr, (cx - 22, cy - 10), (cx + 22, cy - 10), col, 6, cv2.LINE_AA)
        cv2.line(arr, (cx, cy + 14), (cx - 12, cy + 42), col, 7, cv2.LINE_AA)
        cv2.line(arr, (cx, cy + 14), (cx + 12, cy + 42), col, 7, cv2.LINE_AA)
    else:
        cv2.ellipse(arr, (cx, cy + 16), (22, 18), 0, 0, 360, col, -1, cv2.LINE_AA)
        for fx, h in ((-18, 30), (-6, 40), (6, 40), (18, 30)):
            cv2.line(arr, (cx + fx, cy + 8), (cx + fx, cy + 8 - h), col, 6, cv2.LINE_AA)
        cv2.line(arr, (cx - 22, cy + 18), (cx - 40, cy + 2), col, 6, cv2.LINE_AA)


def vision(im, t, k):
    chapter_chip(im, "8 Vision")
    T(im, "From one demonstration to every robot", 64, 128, 52, "B", INK)
    cx, cy, R = 640, 372, 160
    e = eo(t / 2.5)
    nodes = [(0, "arm", "UR arms"), (90, "mobile", "KAIROS"), (180, "human", "G1 humanoid"), (270, "hand", "Robot hand")]
    arr = np.array(im)
    ph = 0.5 + 0.5 * np.sin(t * 2.2)
    for a_ in range(45, 360, 90):
        x = int(cx + R * e * np.cos(np.radians(a_)))
        y = int(cy + R * e * np.sin(np.radians(a_)))
        for q in range(0, 360, 30):
            cv2.ellipse(arr, (x, y), (40, 40), 0, q, q + 14, lerp(GREYC, PAGE, 0.3 + 0.5 * ph), 2, cv2.LINE_AA)
    for a_, kind, nm in nodes:
        x = int(cx + R * e * np.cos(np.radians(a_)))
        y = int(cy + R * e * np.sin(np.radians(a_)))
        cv2.line(arr, (cx, cy), (x, y), GREYC, 2, cv2.LINE_AA)
    im.paste(Image.fromarray(arr))
    for a_, kind, nm in nodes:
        x = int(cx + R * e * np.cos(np.radians(a_)))
        y = int(cy + R * e * np.sin(np.radians(a_)))
        box(im, x - 48, y - 48, 96, 96, 48, CARD, BLUE, 2, True)
    box(im, cx - 48, cy - 48, 96, 96, 48, CARD, INK, 2, True)
    arr = np.array(im)
    person(arr, cx, cy + 12, INK, 0.5)
    for a_, kind, nm in nodes:
        x = int(cx + R * e * np.cos(np.radians(a_)))
        y = int(cy + R * e * np.sin(np.radians(a_)))
        icon_np(arr, kind, x, y, BLUE)
    im.paste(Image.fromarray(arr))
    for a_, kind, nm in nodes:
        x = int(cx + R * e * np.cos(np.radians(a_)))
        y = int(cy + R * e * np.sin(np.radians(a_)))
        if a_ == 0:
            T(im, nm, x + 62, y + 10, 28, "M", SEC, a=e)
        elif a_ == 180:
            T(im, nm, x - 62, y + 10, 28, "M", SEC, "r", a=e)
        elif a_ == 90:
            T(im, nm, x + 62, y + 10, 28, "M", SEC, a=e)
        else:
            T(im, nm, x + 62, y + 10, 28, "M", SEC, a=e)
    P(im, "Robots plug in as simulation models: 4 today, built to scale to more.", 64, 656, 28, "R", INK, 1000, 34, eo((t - 3.5) / 0.8))


def final(im, t, k):
    T(im, "TransferGap", 64, 112, 64, "B", INK)
    figs = [(f"{N['ur5e_raw']} -> {N['fixed']}", f"UR5e, of {N['of']} held-out seeds", ORANGE),
            (f"{N['of']}/{N['of']}", "One policy, 12 of 12 cells", GREEN),
            (f"{N['gr_kairos']}/{N['gr_of']}", "GR00T-N1.5 on KAIROS", VIOLET)]
    for i, (big, lab, col) in enumerate(figs):
        a = eo((t - 0.5 - 0.7 * i) / 0.7)
        x, dy = 64 + i * 400, int((1 - eo((t - 0.5 - 0.7 * i) / 0.7)) * 12)
        box(im, x, 160, 352, 220, 16, CARD, BORDER, 1, True, a, dy)
        ImageDraw.Draw(im).rectangle([x + 28, 190 + dy, x + 76, 194 + dy], fill=lerp(col, CARD, a))
        T(im, big, x + 28, 280 + dy, 64, "B", INK, a=a, bg=CARD)
        P(im, lab, x + 28, 330 + dy, 26, "R", SEC, 300, 31, a, CARD)
    T(im, "github.com/Sushruths04/transfergap-nebius-nvidia", 64, 470, 34, "M", BLUE, a=eo((t - 3.0) / 0.8))
    T(im, "Built on NVIDIA open models and Nebius Token Factory", 64, 530, 30, "R", SEC, a=eo((t - 3.8) / 0.8))


def main(path):
    out = Out(path)
    hq, sm = UI / "media" / "hq", UI / "media" / "scale"
    marks = []

    def mark(s):
        marks.append((out.n / FPS, s))
    mark("Hook: one person, one demonstration"); run(out, 12, hook)
    mark("Why now"); run(out, 23, why)
    mark("The gap"); run(out, 15, gap)
    mark("How it works")
    run(out, 15, pipeline)
    clips(out, [UI / "media" / "human_overlay.mp4"], None, "4 How it works", "Pose and limb lengths from one clip", [("1 clip", BLUE)],
          "Background replaced for the video; measurements come from the original clip.", 10, 0.8, cnt="1 demonstration")
    mark("Scale up: from 1 robot to 4")
    for i, (r, name) in enumerate((("ur5e", "UR5e"), ("ur10e", "UR10e"), ("kairos_mobile", "KAIROS"))):
        k_ = {"ur5e": "ur5e", "ur10e": "ur10e", "kairos_mobile": "kairos"}[r]
        d = TG["robots"][k_]
        clips(out, [hq / f"{r}_raw_seed1001.mp4", hq / f"{r}_stack_seed1001.mp4"], [("raw copy", ORANGE), ("with fixes", GREEN)], "5 Scale up",
              f"{name}: raw copy vs diagnosed fix", [(f"{d['raw']['k']}/{d['raw']['n']}", ORANGE), (f"{d['fix']['k']}/{d['fix']['n']}", GREEN)],
              "Held-out success over 60 seeds; this clip shows one seed.", 5, 1.7,
              cnt="1 demonstration  ·  " + ("1 robot" if i == 0 else f"{i + 1} robots"))
    clips(out, [ROOT / "results" / "g1_in_image_v1" / "videos" / "image_seed1200_placed.mp4"], None, "5 Scale up", "The Unitree G1 humanoid places blocks",
          [(f"{N['g1_ok']} of {N['g1_n']}", GREEN)], "Closed-loop pick and place, pooled over runs.", 8, 1.0, 4, cnt="1 demonstration  ·  4 robots")
    clips(out, [ROOT / "results" / "hand_retarget_v1" / "hand_retarget.mp4"], None, "5 Scale up", "Fingers drive a robot hand",
          [("21 keypoints", BLUE)], "Hand keypoints become fingertip targets for a dexterous hand.", 6, 2.1, cnt="1 demonstration  ·  plus a hand")
    run(out, 4, cube_anim)
    clips(out, [sm / "ur10e_7cm_raw_seed1000.mp4", sm / "ur10e_7cm_stack_seed1000.mp4"], [("raw copy", ORANGE), ("with fixes", GREEN)], "5 Scale up",
          "UR10e, 7 cm cube", [(f"{N['cube7_raw']}/{N['of']}", ORANGE), (f"{N['cube7_fix']}/{N['of']}", GREEN)],
          "A bigger object the fixes were never tuned for.", 6, 1.4, cnt="1 demonstration  ·  bigger objects")
    mark("One brain: one policy, four robots")
    pm = UI / "media" / "policy_multi"
    for r, name in (("ur5e", "UR5e"), ("ur10e", "UR10e"), ("kairos", "KAIROS")):
        clips(out, [pm / f"{r}_seed6000_success.mp4"], None, "6 One brain", f"The same policy drives the {name}",
              [(f"{N['of']}/{N['of']}", GREEN)], "Images and joint positions in, actions out.", 3, 2.85, cnt="one policy  ·  four robots")
    run(out, 11, grid)
    mark("NVIDIA + Nebius stack"); run(out, 9, models); run(out, 8, gr00t)
    mark("Vision"); run(out, 8, vision)
    mark("Close"); run(out, 8, final)
    out.close()
    print("frames", out.n, "seconds", round(out.n / FPS, 1))
    for m in marks:
        print(f"{int(m[0] // 60)}:{int(m[0] % 60):02d}  {m[1]}")


if __name__ == "__main__":
    main(sys.argv[1])
