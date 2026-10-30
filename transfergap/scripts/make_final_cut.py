"""Assemble the silent ~90 s final cut from committed/verified clips and result files (CPU, one process). Captions only; voice-over is added by the author.

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

    def put(self, im):
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


def card(out, lines, secs, sub=None):
    im = canvas()
    items = []
    for i, l in enumerate(lines):
        sc, th = (1.25, 3) if i == 0 else (0.85, 2)
        for k, r in enumerate(wrap(l, sc, th)):
            items.append((r, sc, th, (118, 185, 0) if i == 0 else (235, 235, 235), 62 if (i == 0 and k == 0) or (i > 0 and k == 0 and items) else 38))
    y = 150 if len(items) >= 5 else 220
    for n, (r, sc, th, col, _) in enumerate(items):
        if n:
            y += items[n][4] if items[n][4] != 62 else 56
        text(im, r, (70, y), sc, col, th)
    if sub:
        rows = [r for l in sub for r in wrap(l, 0.65, 1)]
        for i, r in enumerate(rows):
            text(im, r, (70, H - 30 - 30 * (len(rows) - 1 - i)), 0.65, (180, 180, 180), 1)
    for _ in range(int(secs * FPS)):
        out.put(im)


def single(out, vid, cap, start=0, end=None, label=None):
    for f in frames(vid, start, end):
        im = canvas()
        im[40:H - 140, :] = fit(f, W, H - 180)
        if label:
            text(im, label, (24, 28), 0.7, (118, 185, 0))
        caption(im, cap)
        out.put(im)


def pair(out, lv, ll, rv, rl, cap, start=0, end=None):
    A, B = frames(lv, start, end), frames(rv, start, end)
    for i in range(min(len(A), len(B))):
        im = canvas()
        for k, (f, l, c) in enumerate(((A[i], ll, (110, 110, 240)), (B[i], rl, (118, 185, 0)))):
            x = 0 if k == 0 else W // 2
            im[70:70 + 480, x:x + W // 2] = fit(f, W // 2, 480)
            text(im, l, (x + 20, 50), 0.75, c)
        caption(im, cap)
        out.put(im)


def still(out, img_path, cap, secs):
    f = cv2.imread(str(img_path))
    im = canvas()
    im[20:H - 120, :] = fit(f, W, H - 140)
    caption(im, cap)
    for _ in range(int(secs * FPS)):
        out.put(im)


def main(path):
    out = Out(path)
    hq, sm = UI / "media" / "hq", UI / "media" / "scale"
    card(out, ["TransferGap", "One demonstration. Several robots.", "When the copy fails, we say which stage failed."], 4,
         ["Simulation only. Every number on screen comes from a committed result file."])
    single(out, UI / "media" / "human_overlay.mp4",
           ["You: pose, limb lengths, elbow angle and pinch measured from one clip.", f"Monocular estimate; shoulder width {TG['shoulder_width_m']} m is derived, not measured.", "Background replaced for the video; all measurements come from the original clip."], label="1. Measure the person")
    for r, name in (("ur5e", "UR5e"), ("ur10e", "UR10e"), ("kairos_mobile", "KAIROS mobile")):
        k = "kairos" if r == "kairos_mobile" else r
        d = TG["robots"][k]
        pair(out, hq / f"{r}_raw_seed1001.mp4", "raw copy", hq / f"{r}_stack_seed1001.mp4", "with fixes",
             [f"{name}: held-out success {d['raw']['k']}/{d['raw']['n']} -> {d['fix']['k']}/{d['fix']['n']} on 60 seeds (this clip: one seed, an illustration)."])
    for cm in (3, 5, 7):
        x = SC["ur10e"][f"{cm}.0cm"]
        pair(out, sm / f"ur10e_{cm}cm_raw_seed1000.mp4", f"raw copy, {cm} cm cube", sm / f"ur10e_{cm}cm_stack_seed1000.mp4", "with fixes",
             [f"UR10e, {cm} cm cube (never tuned for it): {x['raw']}/{x['n']} -> {x['fix']}/{x['n']} on 60 seeds. Exploratory."])
    single(out, ROOT / "results" / "g1_in_image_v1" / "videos" / "image_seed1200_placed.mp4",
           ["Unitree G1, closed-loop pick and place in the container image (generic block, not the author's style).",
            "Image runs pooled: 52/72 places (CI 61-81%). Long-lived pod: 11/40, same seeds, cause unknown."], start=4, end=16, label="Humanoid")
    single(out, ROOT / "results" / "hand_retarget_v1" / "hand_retarget.mp4",
           ["Fingers: your 21 hand keypoints drive a dexterous robot hand (Allegro) by fingertip IK. Kinematic only.",
            "Fingertip error 0.5-1.6 cm (thumb 4.1 cm), partly noise in the monocular keypoints."], label="Fingers")
    card(out, ["One demonstration becomes data", "120 physics-verified episodes, UR5e + UR10e + KAIROS, with camera video.",
               "A Cosmos-Reason2 critic agrees on all 120 and rejects 40 of 49 failures (96% accuracy).",
               "Apple-shaped 7 cm object: UR10e 1 -> 52 of 60, KAIROS 40 -> 60 (UR5e 0 -> 28: gripper limit)."], 8,
         ["Training DATA from one demonstration, simulated video only; no policy has been trained on it yet."])
    pm = UI / "media" / "policy_multi"
    if (pm / "ur10e_seed6000_success.mp4").exists():
        for r, name in (("ur5e", "UR5e"), ("ur10e", "UR10e"), ("kairos", "KAIROS")):
            single(out, pm / f"{r}_seed6000_success.mp4",
                   [f"One learned policy for all three robots (no scripted controller): {name}, a fresh seed. Images + joint positions -> actions.",
                    "Trained on 900 verified episodes of one demonstration's style: 120/120 per robot on 120 fresh seeds (needs smoothed execution)."],
                   label="One policy, three robots")
        card(out, ["The first policy broke when the world changed", "Trained only on the default 4 cm cube and an empty table:",
                   "6 cm cube: UR5e 0, UR10e 4, KAIROS 0 of 60.  Three distractor objects: 13, 1, 5 of 60.",
                   "Fix: train on varied cube sizes (3-7 cm) and clutter. Then 60/60 on every condition tried, including 5 distractors",
                   "and a 2.5 cm cube it never saw (KAIROS 58/60 at 7 cm + 5 distractors)."], 11,
             ["Simulation only, one training run, data are scripted rollouts of one demonstration's style; not a policy learned from the video itself."])
    card(out, ["One policy, four robots", "UR5e, UR10e, KAIROS arm, and the KAIROS arm on its mobile base (parked). No robot id.",
               "60/60 in all 12 cells: standard, mixed sizes + clutter, and 6 cm cube + 5 distractors.",
               "Two training runs: 60/60 in all 24 cells on 60 held-out seeds; on 60 new seeds 22 of 24 cells at 60/60, two at 59/60.", "The scripted controller on the same seeds: 56-60 of 60."], 9,
         ["Simulation only; 60 held-out seeds per cell; the mobile base stays parked (arm only, no navigation)."])
    card(out, ["NVIDIA GR00T-N1.5 (3B): it works, but not as well", "Fine-tuned on our simulation episodes (400 per robot):",
               "At first 0 to 1 of 30: the arm stopped 2-5 cm short of the cube. Executing the plan 4 steps ahead fixed it, no retraining.",
               "Now: UR10e 25/30, KAIROS 27/30 on fresh seeds (standard). The UR5e / UR10e arms of the 3-robot model: 5-10/30.",
               "The small policy gets 60/60 in the same cells."], 9,
         ["One fine-tune per setting, 30 seeds per cell; simulation only; execution setting chosen on 12 other seeds."])
    card(out, ["NVIDIA open models, called through Nebius", "Nemotron-3-Super on Nebius Token Factory reads the failure statistics and picks the next fix: UR5e 31 -> 60 of 60, UR10e 34 -> 60 (held-out seeds).",
               "Cosmos-Reason2 critic (LoRA): 96% accuracy on 240 simulated clips, rejects 40 of 49 failures.",
               "GR00T-N1.5 (3B) fine-tuned on our data: UR10e 25/30, KAIROS 27/30. SONIC drives the Unitree G1 humanoid."], 11,
         ["Nemotron calls go to the Nebius Token Factory API (saved receipts in results/). Simulation and training ran on a university GPU cluster."])
    still(out, ROOT.parent / "paper" / "figures" / "gap_budget_v3.png",
          ["Which stage costs most? Paired oracle substitution, 500 fresh seeds per arm.", "Perception is the largest budget item, look-again the best correction. Error sizes are assumed."], 7)
    card(out, ["What this is not", "Simulation only; one clip, one person.", "Humanoid copies your arms, but not yet your grasp style (0/30).", "Perception and calibration error sizes are assumed.", "Live webcam path measured with a recorded clip, not yet a real webcam."], 9)
    out.close()
    print("frames", out.n, "seconds", round(out.n / FPS, 1))


if __name__ == "__main__":
    main(sys.argv[1])
