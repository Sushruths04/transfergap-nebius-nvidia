"""GPU-VM side: RTMW3D (OpenMMLab / Shanghai AI Lab, RTMW: Real-Time Multi-Person 2D and 3D Whole-body Pose
Estimation, arXiv 2407.08634; standalone package github.com/b-arac/rtmpose3d, Apache-2.0, weights rbarac/rtmpose3d)
on every frame of a video -> joints npz in the SAME format as gemx_export_joints.py / fsam_export_joints.py, so the
laptop side builds demos identically and only the pose estimator differs.

    python rtmw3d_export_joints.py --video clip.mp4 --out clip_rtmw3d_joints.npz

Per frame: integrated RTMDet person detector -> RTMW3D-L 133 COCO-WholeBody keypoints in metres, camera frame with
z up (x horizontal, y depth). The largest / nearest-to-previous person is tracked. Per-frame model (no temporal
smoothing). Points are written in the SOMA y-up convention used by the GEM-X export, and the COCO-WholeBody indices
the demo builder needs are renamed to the GEM-X joint names. Missing frames are interpolated (count recorded).
"""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np

COCO_WB = {0: "Head", 5: "LeftArm", 6: "RightArm", 9: "LeftHand", 10: "RightHand", 11: "LeftLeg", 12: "RightLeg",
           95: "LeftHandThumbEnd", 99: "LeftHandIndexEnd", 96: "LeftHandIndex1", 100: "LeftHandMiddle1",
           108: "LeftHandPinky1", 116: "RightHandThumbEnd", 120: "RightHandIndexEnd", 117: "RightHandIndex1",
           121: "RightHandMiddle1", 129: "RightHandPinky1"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="rbarac/rtmpose3d")
    ap.add_argument("--max-frames", type=int, default=0)
    a = ap.parse_args()
    from rtmpose3d import RTMPose3D
    model = RTMPose3D.from_pretrained(a.model, device="cuda:0")
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    kps, kp2, bbs, wall, prev, missing = [], [], [], [], None, 0
    while True:
        ok, bgr = cap.read()
        if not ok or (a.max_frames and len(kps) >= a.max_frames):
            break
        t0 = time.perf_counter()
        r = model(bgr, return_tensors="np")
        wall.append(time.perf_counter() - t0)
        k3, bb = np.asarray(r.get("keypoints_3d", [])), np.asarray(r.get("bboxes", []))
        if k3.size == 0:
            kps.append(np.full((133, 3), np.nan))
            kp2.append(np.full((133, 2), np.nan))
            bbs.append(np.full(4, np.nan))
            missing += 1
            continue
        cen = (bb[:, :2] + bb[:, 2:4]) / 2
        area = (bb[:, 2] - bb[:, 0]) * (bb[:, 3] - bb[:, 1])
        i = int(np.argmax(area)) if prev is None else int(np.argmin(np.linalg.norm(cen - prev, axis=1)))
        prev = cen[i]
        kps.append(k3[i])
        k2d = np.asarray(r.get("keypoints_2d", []))
        kp2.append(k2d[i][:, :2] if k2d.size else np.full((133, 2), np.nan))
        bbs.append(bb[i][:4])
    K = np.array(kps, float)
    K2, BB = np.array(kp2, float), np.array(bbs, float)
    for j in range(K.shape[1]):
        for c in range(3):
            v = K[:, j, c]
            bad = np.isnan(v)
            if bad.any() and (~bad).any():
                v[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), v[~bad])
    for arr in (K2, BB):                                  # same gap filling for the 2D keypoints and boxes
        for j in range(arr.shape[1] if arr.ndim == 3 else 1):
            cols = [arr[:, j, c] for c in range(arr.shape[2])] if arr.ndim == 3 else [arr[:, c] for c in range(arr.shape[1])]
            for v in cols:
                bad = np.isnan(v)
                if bad.any() and (~bad).any():
                    v[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), v[~bad])
    soma = np.stack([K[..., 0], K[..., 2], -K[..., 1]], -1)       # z-up camera frame -> SOMA y-up convention
    names = [COCO_WB.get(j, f"wb{j}") for j in range(K.shape[1])]
    np.savez_compressed(a.out, joints=soma.astype(np.float32), kp2d=K2.astype(np.float32), bbox=BB.astype(np.float32),
                        frame_size=np.array([int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))]), joint_names=np.array(names), fps=fps,
                        frame="soma_world_y_up", wall_s=np.array(wall),
                        meta=json.dumps({"estimator": "RTMW3D-L (rtmpose3d)", "frames_without_person": missing,
                                         "source_video": Path(a.video).name}))
    print(f"wrote {a.out}: {soma.shape}, median {1 / np.median(wall):.1f} fps, missing {missing}")


if __name__ == "__main__":
    main()
