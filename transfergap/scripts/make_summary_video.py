"""Summary video of the 2026-10-05 session: title/result cards (matplotlib) + existing result clips + the in-image G1 rollout.
Every number on a card is copied from a committed result file or the cluster log noted in COORDINATION.md; nothing is invented.
    .venv/bin/python scripts/make_summary_video.py OUT.mp4 [g1_clip.mp4 ...]
"""
import sys
from pathlib import Path
import numpy as np
import imageio.v2 as imageio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

W, H, FPS = 1280, 720, 25
ROOT = Path(__file__).resolve().parents[1]


def card(lines, title=None, sub=None, secs=5, bars=None):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="#101418")
    if title:
        fig.text(0.05, 0.9, title, color="white", fontsize=30, weight="bold", va="top")
    if sub:
        fig.text(0.05, 0.80, sub, color="#9fb3c8", fontsize=16, va="top")
    y = 0.70
    for ln in lines:
        fig.text(0.06, y, ln, color="#e6edf3", fontsize=18, va="top"); y -= 0.085
    if bars:
        ax = fig.add_axes([0.58, 0.12, 0.36, 0.5], facecolor="#101418")
        names, vals, ns = zip(*bars)
        ax.bar(names, vals, color=["#3fb950", "#d29922"])
        for i, (v, n) in enumerate(zip(vals, ns)):
            ax.text(i, v + 0.02, f"{v:.0%} (n={n})", color="white", ha="center", fontsize=14)
        ax.set_ylim(0, 1.1); ax.tick_params(colors="white"); [s.set_color("#444") for s in ax.spines.values()]
        ax.set_title("grasp rate, hand in good position", color="white", fontsize=13)
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    plt.close(fig)
    return [img] * int(secs * FPS)


def clip(path, label, max_secs=14):
    r = imageio.get_reader(str(path)); fps = r.get_meta_data().get("fps", 25); step = max(1, round(fps / FPS))
    out = []
    for i, f in enumerate(r):
        if i % step:
            continue
        im = Image.fromarray(f).convert("RGB"); s = min(W / im.width, (H - 60) / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)))
        canvas = Image.new("RGB", (W, H), (16, 20, 24)); canvas.paste(im, ((W - im.width) // 2, 60))
        out.append(np.array(canvas))
        if len(out) >= max_secs * FPS:
            break
    r.close()
    lab = card([], title=label, secs=0.1)[0]
    top = np.array(Image.fromarray(lab).crop((0, 0, W, 60)))
    for f in out:
        f[:60] = top
    return out


def main():
    out, g1 = sys.argv[1], sys.argv[2:]
    fr = []
    fr += card(["Overnight run, 2026-10-05 (simulation only)", "What was built, tested and what is still open"], title="TransferGap", sub="robot copies a human's picking style; G1 + UR5e + UR10e + KAIROS", secs=4)
    fr += card(["Full G1 image built on the GPU cluster (kaniko, about 16 min, 13 GB)",
                "Pushed to a private GitHub registry after the GPU cluster GitLab registry broke (503)",
                ("40 G1 seeds run INSIDE the image: place 31/40 (host, same seeds: 11/40)" if g1 else "G1 run inside the image: NOT shown here"),
                "Pelvis-drift replication on 80 fresh seeds: criterion met, narrowly",
                "Gap NOT explained: fresh pod, engines, CPU, code, files all ruled out",
                "Image and repository history checked for author names"], title="Achieved", secs=8)
    for spec in g1:                       # "label::path"
        lab, path = spec.split("::", 1)
        fr += clip(path, lab, 16)
    fr += card(["In the frozen window (40 of 80 fresh rollouts):", "drift < 6.25 cm: 16/19 grasp", "drift >= 6.25 cm: 11/21 grasp",
                "difference 0.32 (bar 0.25), one-sided p = 0.034 (bar 0.05)", "association only; not shown to be causal"],
               title="Pelvis drift vs grasp", secs=8, bars=[("low drift", 16 / 19, 19), ("high drift", 11 / 21, 21)])
    pf = ROOT / "results/perception_figures_v1"
    for f, lab in [("kairos_depth_arm_over_retry_seed1.mp4", "KAIROS: arm in view, retract and look again"),
                   ("ur5e_depth_combined_wrist_tray_seed3.mp4", "UR5e: all stressors, wrist and tray look-again")]:
        if (pf / f).exists():
            fr += clip(pf / f, lab, 12)
    fr += card(["Perception hard test, held-out: all 30 pre-declared bar cells met",
                "Style transfer with depth perception: matches ground truth on all 3 arms",
                "Not done: registry digests on GitLab, Nebius run (waits for your approval),",
                "causal test of pelvis drift, wrist-orientation analysis"], title="Results and open items", secs=9)
    imageio.mimsave(out, fr, fps=FPS, codec="libx264", quality=7, macro_block_size=1)
    print(out, len(fr) / FPS, "s")

main()
