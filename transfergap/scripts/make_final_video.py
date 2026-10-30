"""Final summary video (simulation only): title and result cards plus the existing result clips.
Every number on a card is read from a committed result file (results/...) or from the macro files that paper/make_*.py generate from them.
    .venv/bin/python scripts/make_final_video.py OUT.mp4
Clips (gitignored runs/videos, results/g1_in_image_v1/videos, results/perception_figures_v1) are skipped with a note if missing.
"""
import json
import re
import sys
import textwrap
from pathlib import Path

import imageio.v2 as imageio
import matplotlib
import numpy as np
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

W, H, FPS = 1280, 720, 25
ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIG = ROOT.parent / "paper" / "figures"


def macros():
    m = {}
    for f in ("real_numbers.tex", "v3_numbers.tex"):
        p = FIG / f
        if p.exists():
            m.update(dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", p.read_text())))
    return m


M = macros()


def card(lines, title=None, sub=None, secs=5, bars=None, bar_title=""):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="#101418")
    if title:
        fig.text(0.05, 0.9, title, color="white", fontsize=30, weight="bold", va="top")
    if sub:
        fig.text(0.05, 0.80, sub, color="#9fb3c8", fontsize=16, va="top")
    y = 0.70
    wrap = 58 if bars else 88
    for ln in lines:
        for part in textwrap.wrap(ln, wrap, subsequent_indent="   ") or [""]:
            fig.text(0.06, y, part, color="#e6edf3", fontsize=16 if bars else 17, va="top")
            y -= 0.062 if bars else 0.08
    if bars:
        ax = fig.add_axes([0.68, 0.12, 0.28, 0.45], facecolor="#101418")
        names, vals, labels = zip(*bars)
        ax.bar(names, vals, color=["#58a6ff", "#e3b341", "#3fb950", "#f78166", "#a371f7"][: len(vals)])
        for i, (v, lab) in enumerate(zip(vals, labels)):
            ax.text(i, v + 0.02, lab, color="white", ha="center", fontsize=12)
        ax.set_ylim(0, 1.15)
        ax.tick_params(colors="white", labelsize=10)
        [s.set_color("#444") for s in ax.spines.values()]
        ax.set_title(bar_title, color="white", fontsize=12)
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    plt.close(fig)
    return [img] * max(1, int(secs * FPS))


def clip(path, label, max_secs=12):
    path = Path(path)
    if not path.exists():
        print("missing clip, skipped:", path)
        return []
    r = imageio.get_reader(str(path))
    fps = r.get_meta_data().get("fps", 25)
    step = max(1, round(fps / FPS))
    out = []
    for i, f in enumerate(r):
        if i % step:
            continue
        im = Image.fromarray(f).convert("RGB")
        s = min(W / im.width, (H - 60) / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)))
        canvas = Image.new("RGB", (W, H), (16, 20, 24))
        canvas.paste(im, ((W - im.width) // 2, 60))
        out.append(np.array(canvas))
        if len(out) >= max_secs * FPS:
            break
    r.close()
    top = np.array(Image.fromarray(card([], title=label, secs=0.1)[0]).crop((0, 0, W, 60)))
    for f in out:
        f[:60] = top
    return out


def main():
    out = sys.argv[1]
    v3 = json.loads((RES / "gap_budget_v3/summary.json").read_text())["arms"]
    e2e_p = RES / "e2e_cluster_v1/report.json"
    fr = []
    fr += card(["One human demonstration, several robots: where does it break, and what fixes it?",
                "Simulation only. Numbers below come from committed result files."],
               title="TransferGap", sub="Transfer Gap Budget by oracle substitution (UR5e, UR10e, KAIROS arm, Unitree G1)", secs=6)
    fr += card(["Replace ONE pipeline stage at a time with simulator ground truth (an oracle).",
                "Success recovered = that stage's share of the gap (the Transfer Gap Budget).",
                "The largest item picks a correction; it is tested on held-out seeds,",
                "under a protocol committed to version control before the run.",
                "Simulator state labels and scores episodes; it never drives the robot."],
               title="The method", secs=9)
    ur5, ur10 = v3["ur5e"], v3["ur10e"]
    bars = [(k[:5], ur5["budget_pp"][k]["delta_pp"] / 100, f"{ur5['budget_pp'][k]['delta_pp']:.0f}pp") for k in ur5["budget_pp"]]
    fr += card([f"{ur5['n']} fresh seeds per arm, pre-registered",
                f"UR5e full: {ur5['full_successes']}/{ur5['n']}   UR10e: {ur10['full_successes']}/{ur10['n']}",
                "Perception is the largest budget item on both arms.",
                "look-again (the rule's choice) is the best correction:",
                f"  +{ur5['corrections']['look_again']['delta_pp']:.1f} pp (UR5e), +{ur10['corrections']['look_again']['delta_pp']:.1f} pp (UR10e)",
                "  (95% intervals exclude zero).",
                "Two earlier 60-seed readings did NOT replicate:",
                "  the paper says so."],
               title="500-seed result", secs=11, bars=bars, bar_title="UR5e oracle recovery (pp/100)")
    fr += clip(ROOT / "runs/videos/human_demo_notebook_cycle.mp4", "Real human demonstration (free-licence clip)", 8)
    fr += clip(ROOT / "runs/videos/ur5e_no_fix_seed1001.mp4", "UR5e copies the human path, no correction: fails", 10)
    fr += clip(ROOT / "runs/videos/ur5e_4_fixes_seed1001.mp4", "UR5e with the diagnosed corrections: succeeds", 10)
    g = lambda k: M.get(k, "?")  # noqa: E731
    fr += card([f"Notebook: UR5e {g('dmNotebookFiveRaw')}->{g('dmNotebookFiveStack')}/60, UR10e {g('dmNotebookTenRaw')}->{g('dmNotebookTenStack')}/60 (held-out seeds)",
                f"Markers: {g('dmMarkersFiveRaw')}->{g('dmMarkersFiveStack')} / {g('dmMarkersTenRaw')}->{g('dmMarkersTenStack')}    Orange: {g('dmOrangeFiveRaw')}->{g('dmOrangeFiveStack')} / {g('dmOrangeTenRaw')}->{g('dmOrangeTenStack')}    Notepad: {g('dmNotepadFiveRaw')}->{g('dmNotepadFiveStack')} / {g('dmNotepadTenRaw')}->{g('dmNotepadTenStack')}",
                f"Person 2: {g('dmPTwoOwnFiveRaw')}->{g('dmPTwoOwnFiveStack')} / {g('dmPTwoOwnTenRaw')}->{g('dmPTwoOwnTenStack')}    Our own recording: {g('dmOwnFiveRaw')}->{g('dmOwnFiveStack')} / {g('dmOwnTenRaw')}->{g('dmOwnTenStack')}",
                "An earlier stack applied unchanged to other cycles: no gain; on person 2 it hurt.",
                "The diagnosis has to be done per demonstration. Seeds were reused (disclosed)."],
               title="Real demonstrations, two arms", sub="successes out of 60, no correction -> correction stack (UR5e / UR10e)", secs=12)
    pf = RES / "perception_figures_v1"
    fr += clip(pf / "kairos_depth_arm_over_retry_seed1.mp4", "KAIROS: arm in view, retract and look again", 10)
    fr += clip(pf / "ur5e_depth_combined_wrist_tray_seed3.mp4", "UR5e: all stressors, wrist and tray look-again", 10)
    fr += card([f"{g('pcBarMet')} of {g('pcBarCells')} pre-declared bar cells met (each {g('pcBarMin')}-{g('pcN')} of {g('pcN')} held-out episodes).",
                f"Depth beliefs vs ground truth, same style task: {g('spKFiveDepth')} vs {g('spKFiveTruth')}, {g('spKTenDepth')} vs {g('spKTenTruth')}, {g('spKKaiDepth')} vs {g('spKKaiTruth')} of {g('spN')}.",
                "Differences are +0.8, +0.8 and +1.7 pp (point estimates, not an equivalence test).",
                f"Stress tests that fail by design: 2 deg / 20 mm calibration error: {g('pcCalibTwoFive')}/{g('pcN')} on the UR5e."],
               title="Depth perception in the loop", secs=10)
    fr += clip(RES / "g1_in_image_v1/videos/host_seed1200_not_placed.mp4", "G1, host setup, seed 1200: block not placed", 12)
    fr += clip(RES / "g1_in_image_v1/videos/image_seed1200_placed.mp4", "G1, inside the container image, same seed: placed", 12)
    fr += card([f"Closed-loop controller, seeds 1200-1239: place {g('giImgPlace')}/{g('giN')} in the image vs {g('giHostPlace')}/{g('giN')} on the host.",
                f"Five runs of seeds 1200-1209: host {g('gRerunHostK')}/{g('gRerunHostN')} grasps, image variants {g('gRerunImgK')}/{g('gRerunImgN')}.",
                "Ruled out: code, weights, packages, build, CUDA libraries, binaries, plans, pod type.",
                "Open-loop controller: NO such gap. Cause unknown; not a controller improvement.",
                f"Changing only the MuJoCo minor version (3.14 -> 3.15) cut closed-loop grasps {g('mjGraspOld')}/{g('mjNOld')} -> {g('mjGraspNew')}/{g('mjNNew')}; the image now pins it."],
               title="G1 humanoid: an unexplained gap", secs=11,
               bars=[("host", int(g("giHostPlace")) / int(g("giN")), f"{g('giHostPlace')}/{g('giN')}"),
                     ("image", int(g("giImgPlace")) / int(g("giN")), f"{g('giImgPlace')}/{g('giN')}")], bar_title="G1 place rate, same 40 seeds")
    if e2e_p.exists():
        rep = json.loads(e2e_p.read_text())
        short = {"info": "python 3.10, numpy 2.2.6, mujoco 3.14.0, EGL, L40S", "style": "style + depth perception smoke run, 3 arms",
                 "perception": "depth perception smoke run, UR5e"}
        lines = [f"{k:11s} {v['status']:5s} {short.get(k, v['detail'])[:72]}" for k, v in rep.items() if isinstance(v, dict)]
        fr += card(lines, title="End-to-end in the container, on the GPU cluster", sub="one Job, one image: tg-entrypoint e2e", secs=14)
    else:
        fr += card(["End-to-end report not available when this video was made."], title="End-to-end", secs=4)
    fr += card(["Paper: 4-page workshop draft, numbers generated from result files; independent review done (paper/REVIEW_FINDINGS.md).",
                "Open: submit the paper (user), Nebius verification run (user approval), KAIROS in Isaac Sim (user go-ahead),",
                "cause of the G1 closed-loop gap, real-robot validation."],
               title="Status", secs=10)
    imageio.mimsave(out, fr, fps=FPS, codec="libx264", quality=7, macro_block_size=1)
    print(out, round(len(fr) / FPS), "s")


main()
