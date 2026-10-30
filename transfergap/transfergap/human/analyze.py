"""What the system measures about the person: limb lengths, joint angles, hand aperture and speed, from RTMW3D keypoints.

    python -m transfergap.human.analyze --joints pose.npz --video clip.mp4 --out DIR [--side Right] [--window A B]

Input: the npz written by demo/tools/rtmw3d_export_joints.py (133 COCO-WholeBody keypoints in metres, SOMA y-up frame, plus the 2D keypoints).
Output: `human_analysis.json` (summary), `human_metrics.npz` (per-frame arrays), `human_overlay.mp4` (the video with the skeleton, a numbers
panel, three small 3D views and live curves).

Honest limits: RTMW3D is a monocular estimator. Its metric scale and its depth are estimates: limb LENGTHS are reported with their
spread over the clip (a stable length is necessary, not sufficient, for a correct one) and are not ground truth; angles are computed from
the same noisy 3D points. Nothing here is validated against motion capture.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

# COCO-WholeBody indices
L_SH, R_SH, L_EL, R_EL, L_WR, R_WR, L_HIP, R_HIP = 5, 6, 7, 8, 9, 10, 11, 12
HAND = {"Left": 91, "Right": 112}                       # wrist index of each 21-point hand block
SIDE = {"Left": dict(sh=L_SH, el=L_EL, wr=L_WR), "Right": dict(sh=R_SH, el=R_EL, wr=R_WR)}
BONES_BODY = [(5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
BONES_HAND = [(b, b + k) for b in (91, 112) for k in (1, 5, 9, 13, 17)] + \
    [(b + k, b + k + 1) for b in (91, 112) for f in (1, 5, 9, 13, 17) for k in range(f, f + 3)]


def _ang(a, b, c):
    """Angle at b (degrees) between b->a and b->c, per frame."""
    u, v = a - b, c - b
    cs = (u * v).sum(-1) / np.maximum(np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1), 1e-9)
    return np.degrees(np.arccos(np.clip(cs, -1, 1)))


REF_SHOULDER_WIDTH_M = 0.40     # ASSUMPTION: adult biacromial width; replace with the person's own measurement (--shoulder-width-m)


def metric_scale(joints, shoulder_width_m=REF_SHOULDER_WIDTH_M):
    """Scale factor that makes the median shoulder width equal `shoulder_width_m`.

    RTMW3D's 3D output is not metric (measured on the author's clip: shoulder width 1.04 m, upper arm 0.77 m, hand aperture 13.8 cm for a
    6 cm box, i.e. about 2.6x too large). One uniform factor from the body proportions fixes the size; it cannot fix the depth, which stays a
    weak monocular estimate. The shoulder width is then the reference by construction; the other limb lengths become a consistency check."""
    J = np.asarray(joints, float)
    sw = np.median(np.linalg.norm(J[:, L_SH] - J[:, R_SH], axis=1))
    return float(shoulder_width_m / max(sw, 1e-9))


def hand_idx(side):
    w = HAND[side]
    return dict(wrist=w, thumb_tip=w + 4, index_tip=w + 8, middle_mcp=w + 9, middle_tip=w + 12, pinky_mcp=w + 17)


def metrics(joints, fps, side="Right"):
    """Per-frame measurements (dict of arrays) from joints (T,133,3) in metres, any right-handed frame."""
    J = np.asarray(joints, float)
    s, h = SIDE[side], hand_idx(side)
    sh, el, wr = J[:, s["sh"]], J[:, s["el"]], J[:, s["wr"]]
    mid_sh, mid_hip = (J[:, L_SH] + J[:, R_SH]) / 2, (J[:, L_HIP] + J[:, R_HIP]) / 2
    torso = mid_sh - mid_hip
    out = {
        "upper_arm_m": np.linalg.norm(el - sh, axis=1),
        "forearm_m": np.linalg.norm(wr - el, axis=1),
        "hand_m": np.linalg.norm(J[:, h["middle_tip"]] - J[:, h["wrist"]], axis=1),
        "shoulder_width_m": np.linalg.norm(J[:, L_SH] - J[:, R_SH], axis=1),
        "torso_m": np.linalg.norm(torso, axis=1),
        "elbow_deg": _ang(sh, el, wr),
        "shoulder_deg": _ang(el, sh, sh - torso),   # arm vs the trunk line (0 = arm hanging)
        "wrist_deg": _ang(el, wr, J[:, h["middle_mcp"]]),
        "aperture_m": np.linalg.norm(J[:, h["thumb_tip"]] - J[:, h["index_tip"]], axis=1),
    }
    pin = (J[:, h["thumb_tip"]] + J[:, h["index_tip"]]) / 2
    out["pinch_xyz"] = pin
    v = np.gradient(pin, 1.0 / fps, axis=0)
    out["hand_speed_m_s"] = np.linalg.norm(v, axis=1)
    return out


def summarize(M, fps, side="Right"):
    def st(x):
        x = np.asarray(x, float)
        return {"median": round(float(np.median(x)), 4), "p10": round(float(np.percentile(x, 10)), 4),
                "p90": round(float(np.percentile(x, 90)), 4), "cv_pct": round(100 * float(np.std(x) / max(np.mean(x), 1e-9)), 1)}
    return {"side": side, "frames": int(len(M["elbow_deg"])), "fps": float(fps),
            "lengths_m": {k: st(M[k]) for k in ("upper_arm_m", "forearm_m", "hand_m", "shoulder_width_m", "torso_m")},
            "angles_deg": {k: {kk: round(float(f(M[k])), 1) for kk, f in (("min", np.min), ("median", np.median), ("max", np.max))}
                           for k in ("elbow_deg", "shoulder_deg", "wrist_deg")},
            "hand": {"aperture_m": st(M["aperture_m"]), "peak_speed_m_s": round(float(np.max(M["hand_speed_m_s"])), 3),
                     "pinch_path_extent_m": np.round(np.ptp(M["pinch_xyz"], axis=0), 3).tolist()},
            "note": "monocular estimates; lengths are stable (cv_pct) or not, never validated against ground truth"}


def _hud(img, lines, org=(10, 22), scale=0.55):
    import cv2
    w = max(len(s) for s in lines) * 11 + 14
    cv2.rectangle(img, (org[0] - 6, org[1] - 18), (org[0] - 6 + w, org[1] - 18 + 22 * len(lines) + 6), (0, 0, 0), -1)
    for i, s in enumerate(lines):
        cv2.putText(img, s, (org[0], org[1] + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)


def _mini3d(J, size, axes, side, title):
    """Small orthographic view of the upper body and both hands. axes=(horizontal, vertical, sign_h, sign_v) in the SOMA frame."""
    import cv2
    img = np.full((size, size, 3), 24, np.uint8)
    idx = [L_SH, R_SH, L_EL, R_EL, L_WR, R_WR, L_HIP, R_HIP] + list(range(91, 133))
    P = J[idx]
    c = (J[L_SH] + J[R_SH] + J[L_HIP] + J[R_HIP]) / 4
    sc = size * 0.42 / 0.75
    h, v, sh_, sv_ = axes
    pt = lambda p: (int(size / 2 + sh_ * (p[h] - c[h]) * sc), int(size / 2 - sv_ * (p[v] - c[v]) * sc))
    for a, b in BONES_BODY + BONES_HAND:
        col = (255, 200, 0) if a < 91 else ((120, 255, 120) if a >= 112 else (200, 160, 255))
        cv2.line(img, pt(J[a]), pt(J[b]), col, 2 if a < 91 else 1, cv2.LINE_AA)
    for a in (L_SH, R_SH, L_EL, R_EL, L_WR, R_WR):
        cv2.circle(img, pt(J[a]), 3, (255, 255, 255), -1)
    cv2.putText(img, title, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
    return img


def _curves(M, t, size_wh):
    import cv2
    W, H = size_wh
    img = np.full((H, W, 3), 24, np.uint8)
    T = len(M["elbow_deg"])
    for name, col, lo, hi in (("elbow_deg", (80, 160, 255), 0, 180), ("aperture_m", (120, 255, 120), 0, 0.2),
                              ("hand_speed_m_s", (255, 160, 200), 0, 3.0)):
        y = np.clip((np.asarray(M[name]) - lo) / (hi - lo), 0, 1)
        pts = np.stack([np.arange(T) / max(T - 1, 1) * (W - 10) + 5, H - 8 - y * (H - 30)], 1).astype(np.int32)
        cv2.polylines(img, [pts], False, col, 1, cv2.LINE_AA)
        cv2.putText(img, name.replace("_m_s", " m/s").replace("_deg", " deg").replace("_m", " m"), (6, 14 + 14 * ("elbow_deg", "aperture_m", "hand_speed_m_s").index(name)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1, cv2.LINE_AA)
    x = int(5 + t / max(T - 1, 1) * (W - 10))
    cv2.line(img, (x, 0), (x, H), (255, 255, 255), 1)
    return img


def overlay_video(video, z, M, summ, out, window=None, side="Right"):
    import cv2
    import imageio.v2 as imageio
    J, K2 = np.asarray(z["joints"], float), np.asarray(z["kp2d"], float)
    # joints are stored in the SOMA y-up frame: (x, y_up, z) -> back to (x, y_up, z) for the views as is
    cap = cv2.VideoCapture(str(video))
    a = int(window[0]) if window else 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, a)
    n = len(J)
    frames = []
    for t in range(n):
        ok, f = cap.read()
        if not ok:
            break
        for u, v in BONES_BODY + BONES_HAND:
            p, q = K2[t, u], K2[t, v]
            if np.isfinite(p).all() and np.isfinite(q).all():
                col = (0, 200, 255) if u < 91 else ((130, 255, 130) if u >= 112 else (255, 160, 255))
                cv2.line(f, tuple(int(c) for c in p), tuple(int(c) for c in q), col, 3 if u < 91 else 1, cv2.LINE_AA)
        h = 520
        f = cv2.resize(f, (int(f.shape[1] * h / f.shape[0]), h))
        L = summ["lengths_m"]
        _hud(f, [f"{side} arm (monocular estimate)",
                 f"upper arm {M['upper_arm_m'][t]*100:5.1f} cm  (median {L['upper_arm_m']['median']*100:.1f})",
                 f"forearm   {M['forearm_m'][t]*100:5.1f} cm  (median {L['forearm_m']['median']*100:.1f})",
                 f"hand      {M['hand_m'][t]*100:5.1f} cm",
                 f"elbow {M['elbow_deg'][t]:5.1f} deg  shoulder {M['shoulder_deg'][t]:5.1f} deg",
                 f"pinch {M['aperture_m'][t]*100:4.1f} cm   speed {M['hand_speed_m_s'][t]:.2f} m/s"])
        views = [_mini3d(J[t], 170, (0, 1, 1, 1), side, "front"), _mini3d(J[t], 170, (2, 1, 1, 1), side, "side"),
                 _mini3d(J[t], 170, (0, 2, 1, -1), side, "top")]
        panel = np.concatenate(views, axis=1)
        curves = _curves(M, t, (panel.shape[1], h - panel.shape[0]))
        right = np.concatenate([panel, curves], axis=0)
        frames.append(np.concatenate([f, right], axis=1)[..., ::-1])
    cap.release()
    imageio.mimwrite(str(out), frames, fps=float(summ["fps"]))
    return str(out)


def run(joints_npz, out, video=None, side="Right", window=None, shoulder_width_m=REF_SHOULDER_WIDTH_M):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    z = dict(np.load(joints_npz, allow_pickle=False))
    fps = float(z["fps"])
    sl = slice(window[0], window[1] + 1) if window else slice(None)
    zz = {k: (v[sl] if hasattr(v, "shape") and v.ndim and v.shape[0] == len(z["joints"]) else v) for k, v in z.items()}
    scale = metric_scale(zz["joints"], shoulder_width_m) if shoulder_width_m else 1.0
    zz["joints"] = np.asarray(zz["joints"], float) * scale
    M = metrics(zz["joints"], fps, side)
    summ = summarize(M, fps, side)
    summ["metric_scale"] = {"factor": round(scale, 4), "reference_shoulder_width_m": shoulder_width_m,
                            "note": "RTMW3D output is not metric; scaled so the median shoulder width equals the reference (ASSUMED unless measured)"}
    np.savez_compressed(out / "human_metrics.npz", **M)
    (out / "human_analysis.json").write_text(json.dumps(summ, indent=1))
    if video:
        summ["overlay"] = overlay_video(video, zz, M, summ, out / "human_overlay.mp4", window, side)
        (out / "human_analysis.json").write_text(json.dumps(summ, indent=1))
    return summ


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--joints", required=True)
    ap.add_argument("--video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--side", default="Right", choices=["Left", "Right"])
    ap.add_argument("--window", nargs=2, type=int)
    ap.add_argument("--shoulder-width-m", type=float, default=REF_SHOULDER_WIDTH_M, help="the person's shoulder width; 0 = no scaling")
    a = ap.parse_args()
    print(json.dumps(run(a.joints, a.out, a.video, a.side, a.window, a.shoulder_width_m), indent=1))


if __name__ == "__main__":
    main()
