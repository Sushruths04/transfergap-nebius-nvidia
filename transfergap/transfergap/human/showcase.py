"""Compose the integrated demo video: the person and what is measured, the G1, the robots with and without correction, and the counts.

    python -m transfergap.human.showcase --human human_overlay.mp4 --robots-dir DIR --counts repro_summary.json --out demo.mp4 [--g1 seed0_r0.mp4]

Every number on a card is read from a result file given on the command line; nothing is typed in. Videos shorter than their scene are
looped. Cards state what is NOT shown or not solved (the same list as STATUS_AND_OBJECTIVE.md), so the video does not overclaim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

W, H, FPS = 1440, 810, 25
BG, FG, ACC, OK, BAD = (24, 24, 24), (240, 240, 240), (255, 200, 0), (120, 255, 120), (110, 110, 255)


def _cv():
    import cv2
    return cv2


def card(lines, secs=4.0, title=None, colors=None):
    cv2 = _cv()
    img = np.full((H, W, 3), BG, np.uint8)
    y = 140
    if title:
        cv2.putText(img, title, (70, y), cv2.FONT_HERSHEY_SIMPLEX, 1.5, ACC, 3, cv2.LINE_AA)
        y += 80
    for i, s in enumerate(lines):
        col = (colors or {}).get(i, FG)
        cv2.putText(img, s, (70, y), cv2.FONT_HERSHEY_SIMPLEX, 0.95, col, 2, cv2.LINE_AA)
        y += 52
    return [img] * int(secs * FPS)


def read(path):
    import imageio.v2 as imageio
    r = imageio.get_reader(str(path))
    fr = [f[..., ::-1].copy() for f in r]          # BGR for cv2
    r.close()
    return fr


def fit(frame, w, h):
    cv2 = _cv()
    s = min(w / frame.shape[1], h / frame.shape[0])
    f = cv2.resize(frame, (int(frame.shape[1] * s), int(frame.shape[0] * s)))
    out = np.full((h, w, 3), BG, np.uint8)
    y0, x0 = (h - f.shape[0]) // 2, (w - f.shape[1]) // 2
    out[y0:y0 + f.shape[0], x0:x0 + f.shape[1]] = f
    return out


def caption(img, text, col=FG):
    cv2 = _cv()
    cv2.rectangle(img, (0, img.shape[0] - 34), (img.shape[1], img.shape[0]), (0, 0, 0), -1)
    cv2.putText(img, text, (8, img.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)
    return img


def loop(frames, n):
    return [frames[i % len(frames)] for i in range(n)]


def grid(tiles, cols, secs, head):
    """tiles = [(frames, caption, colour)]; returns frames of a cols-wide grid for `secs` seconds."""
    cv2 = _cv()
    rows = (len(tiles) + cols - 1) // cols
    tw, th = W // cols, (H - 60) // rows
    n = int(secs * FPS)
    cols_f = [loop(fr, n) for fr, _, _ in tiles]
    out = []
    for i in range(n):
        img = np.full((H, W, 3), BG, np.uint8)
        cv2.putText(img, head, (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.95, ACC, 2, cv2.LINE_AA)
        for k, (_, cap, col) in enumerate(tiles):
            r, c = divmod(k, cols)
            t = caption(fit(cols_f[k][i], tw, th), cap, col)
            img[60 + r * th:60 + (r + 1) * th, c * tw:(c + 1) * tw] = t
        out.append(img)
    return out


def counts_lines(summary):
    rows, colors = [], {}
    for rb, x in summary["robots"].items():
        c = {k: v["successes"] for k, v in x["conditions"].items()}
        n = next(iter(x["conditions"].values()))["n"]
        rows.append(f"{rb:14s} no correction {c['raw']:2d}/{n}   ->   fix stack {c['all_fixes']:2d}/{n}")
    return rows, colors


def build(a):
    frames = []
    frames += card(["One human demonstration, several robots.", "", "What the system measures about the person,",
                    "how each robot copies the style of the demonstration,", "and which stage fails when the copy does not work.", "",
                    "Simulation only. Every number is read from a result file."], 5, title="TransferGap")
    frames += card(["Input: the author's own video (static camera).", "RTMW3D estimates 133 keypoints per frame on the GPU:",
                    "body, both hands. From them: limb lengths, joint angles,", "pinch aperture and hand speed.", "",
                    "Monocular estimates, not ground truth."], 4, title="1. What we measure")
    hv = read(a.human)
    frames += [fit(f, W, H) for f in hv]
    rd = json.loads((Path(a.robots_dir) / "render_report.json").read_text())["rows"]
    tiles = []
    for key, v in rd.items():
        robot, cond = key.split("/")
        fr = read(v["video"])
        ok = v["success"]
        label = f"{robot} | {'no correction' if cond == 'raw' else 'with fix stack'} | seed {v['seed']} | {'placed' if ok else 'FAILED'}"
        tiles.append((fr, label, OK if ok else BAD))
    if a.g1:
        g = read(a.g1)
        frames += card(["The Unitree G1 follows the person's wrists, neck and pinch", "through the SONIC whole-body controller (legs: its own balance planner).", "",
                        "This is mimicry of the upper body.", "It is NOT yet a grasp of the object in the author's style."], 4, title="2. Humanoid")
        off = json.loads(Path(a.g1_fidelity).read_text())["offset_s"] if a.g1_fidelity else 0.0   # when the replay began in the G1 video
        n = len(g)
        # the person's video plays at its own frame rate, starting when the replay starts, then holds its last frame
        hv_sync = [hv[min(int(max(0.0, i / FPS - off) * a.human_fps), len(hv) - 1)] for i in range(n)]
        frames += grid([(hv_sync, "the person (RTMW3D overlay)", FG), (g, "G1 in MuJoCo (SONIC), same moment", FG)], 1, n / FPS, "G1 mimics the person")
        if a.g1_fidelity:
            f = json.loads(Path(a.g1_fidelity).read_text())
            nm = {"x": "forward", "y": "sideways", "z": "up"}
            lines = [f"G1 right wrist vs the person's right wrist ({f['samples']} samples, replay offset {f['offset_s']} s):", ""]
            for r in f["axes"]:
                lines.append(f"  G1 {nm[r['g1_axis']]:9s} r = {r['pearson_r']:+.2f}   range ratio {r['range_ratio_g1_over_person']:.2f}")
            lines += ["", f"mean |r| {f['mean_abs_r']:.2f}  (shuffled-time baseline, 95th percentile: {f['shuffled_baseline_mean_abs_r_p95']:.2f})",
                      "Sideways motion follows the person; forward depth hardly does:", "a single camera gives weak depth."]
            frames += card(lines, 8, title="How closely does the G1 copy the wrist?")
    frames += card(["The same demonstration copied by each arm.", "Left: no correction. Right: the correction stack",
                    "chosen by the Transfer Gap Budget.", "One seed is an illustration; the counts are on the next card."], 4, title="3. Robots")
    raws = [x for x in tiles if "no correction" in x[1]]          # top row: no correction, bottom row: with the fix stack,
    stacks = [x for x in tiles if "fix stack" in x[1]]            # one column per robot
    frames += grid(raws + stacks, max(len(raws), 1), 10, "Same demonstration, different robots (top: no correction, bottom: fix stack)")
    summ = json.loads(Path(a.counts).read_text())
    lines, colors = counts_lines(summ)
    frames += card(["Held-out seeds " + f"{summ['seeds'][0]}-{summ['seeds'][1]}" + " (paired), frozen five-correction stack:", ""] + lines +
                   ["", "One clip, one person; seeds reused from earlier development."], 7, title="Result")
    if a.agent_loop:
        lp = json.loads(Path(a.agent_loop).read_text())
        lines = ["Nemotron-3-Super picks one fix per round from a fixed menu;", "committed before the held-out trials (gain shown is held-out)."]
        for rb, rounds in lp.items():
            for r in rounds:
                if r.get("stop"):
                    lines.append(f"{rb} {r['round'] + 1}: diagnosis stops, no useful fix left")
                else:
                    g = (r.get("heldout_gap") or {}).get("delta_pp")
                    same = "rule: same" if r.get("agree") else f"rule: {r['rule']}"
                    lines.append(f"{rb} {r['round'] + 1}: {r['agent']} ({same}) {g:+.1f} pp")
        n_agree = sum(1 for rs in lp.values() for r in rs if r.get("agree"))
        n_all = sum(1 for rs in lp.values() for r in rs if not r.get("stop"))
        lines += [f"Nemotron agreed with the rule in {n_agree}/{n_all} decisions:", "it is in the loop; this run does not show it beats the rule."]
        frames += card(lines, 9, title="4. Diagnosis agent (NVIDIA Nemotron)")
    if a.critic:
        c = json.loads(Path(a.critic).read_text())
        z, f = c["zero_shot"], c["fine_tuned"]
        frames += card([f"Cosmos-Reason2-2B watches {c['n_clips']} simulator clips", "of this demo and says success or failure.", "",
                        f"zero-shot:    {100 * z['accuracy']:.1f}% right, catches {100 * z['true_negative_rate']:.0f}% of failures",
                        f"with adapter: {100 * f['accuracy']:.1f}% right, catches {100 * f['true_negative_rate']:.0f}% of failures",
                        "", "The adapter was trained earlier on other demos' clips.", "Simulator renders only; one demo, one person."], 9, title="5. Video critic (NVIDIA Cosmos)")
    frames += card(["Not solved: the G1 picking the block in the author's style (0/30 grasps),", "pose from internet clips, object detection from video,",
                    "perception and calibration errors are assumed, not measured.", "", "Next: more people, G1 closed-loop grasp, live webcam."], 6, title="Open")
    import imageio.v2 as imageio
    imageio.mimwrite(a.out, [f[..., ::-1] for f in frames], fps=FPS, macro_block_size=1)
    return {"out": a.out, "seconds": round(len(frames) / FPS, 1), "frames": len(frames)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--human", required=True)
    ap.add_argument("--robots-dir", required=True)
    ap.add_argument("--counts", required=True)
    ap.add_argument("--g1")
    ap.add_argument("--human-fps", type=float, default=21.4, help="frame rate of the person's video")
    ap.add_argument("--g1-fidelity", help="mimic_fidelity.py output json")
    ap.add_argument("--agent-loop", help="results/demo_agent_loop_*.json (Nemotron diagnosis rounds)")
    ap.add_argument("--critic", help="Cosmos critic report.json")
    ap.add_argument("--out", required=True)
    print(json.dumps(build(ap.parse_args()), indent=1))


if __name__ == "__main__":
    main()
