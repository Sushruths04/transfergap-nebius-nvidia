"""GPU-VM side: Fast SAM 3D Body (ECCV 2026, github.com/yangtiming/Fast-SAM-3D-Body, MIT; SAM 3D Body weights under
the SAM License, gated) on every frame of a video -> joints npz in the SAME format as gemx_export_joints.py, so the
laptop side (transfergap.demo.gemx.load_joints_npz + demo.clips annotations) builds demos identically and only the
pose estimator differs. Run from the Fast-SAM-3D-Body root in its environment:

    python /path/to/fsam_export_joints.py --video clip.mp4 --out clip_fsam_joints.npz [--max-frames N]

Per frame: estimator.process_one_image (YOLO-pose person detection, MoGe FOV, 3DB body + hand decoders) ->
the tracked person's 70 MHR keypoints in camera coordinates (pred_keypoints_3d + pred_cam_t). Single-image method:
no temporal model, so the camera frame is the only frame; the world "up" is estimated once per clip as the mean
mid-hip -> neck direction (person upright on average; ASSUMPTION, recorded in meta), and points are written in the
SOMA y-up convention the GEM-X export uses. Joint names are mapped onto the GEM-X names the demo builder reads.
Frames without a detection are linearly interpolated (count recorded). Wall time per frame is recorded.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

NAME_MAP = {  # MHR70 name -> GEM-X/SOMA joint name used downstream
    "right-thumb-tip": "RightHandThumbEnd", "right-index-tip": "RightHandIndexEnd",
    "left-thumb-tip": "LeftHandThumbEnd", "left-index-tip": "LeftHandIndexEnd",
    "right-wrist": "RightHand", "left-wrist": "LeftHand", "right-shoulder": "RightArm", "left-shoulder": "LeftArm",
    "right-hip": "RightLeg", "left-hip": "LeftLeg", "neck": "Chest", "nose": "Head",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--image-size", type=int, default=512)
    ap.add_argument("--yolo", default="checkpoints/yolo/yolo11m-pose.pt")
    a = ap.parse_args()
    sys.path.insert(0, ".")
    from mocap.core.setup_estimator import build_default_estimator
    from sam_3d_body.metadata.mhr70 import mhr_names
    est = build_default_estimator(image_size=a.image_size, yolo_model_path=a.yolo)
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    kps, wall, prev_c, n_missing = [], [], None, 0
    while True:
        ok, bgr = cap.read()
        if not ok or (a.max_frames and len(kps) >= a.max_frames):
            break
        t0 = time.perf_counter()
        outs = est.process_one_image(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), cam_int=None, hand_box_source="yolo_pose")
        wall.append(time.perf_counter() - t0)
        if not outs:
            kps.append(np.full((70, 3), np.nan))
            n_missing += 1
            continue
        cen = [np.r_[(o["bbox"][0] + o["bbox"][2]) / 2, (o["bbox"][1] + o["bbox"][3]) / 2] for o in outs]
        area = [(o["bbox"][2] - o["bbox"][0]) * (o["bbox"][3] - o["bbox"][1]) for o in outs]
        i = int(np.argmax(area)) if prev_c is None else int(np.argmin([np.linalg.norm(c - prev_c) for c in cen]))
        prev_c = cen[i]
        o = outs[i]
        kps.append(np.asarray(o["pred_keypoints_3d"], float)[:70] + np.asarray(o["pred_cam_t"], float))
        print(f"\r[fsam] frame {len(kps)} {1 / wall[-1]:5.1f} fps", end="", flush=True)
    K = np.array(kps)                                        # (T, 70, 3) camera frame: x right, y down, z forward
    for j in range(K.shape[1]):                              # fill missed frames
        for c in range(3):
            v = K[:, j, c]
            bad = np.isnan(v)
            if bad.any() and (~bad).any():
                v[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), v[~bad])
    idx = {n: i for i, n in enumerate(mhr_names)}
    mid_hip = 0.5 * (K[:, idx["left-hip"]] + K[:, idx["right-hip"]])
    up = np.nanmean(K[:, idx["neck"]] - mid_hip, axis=0)
    up /= np.linalg.norm(up)
    x = np.array([1.0, 0.0, 0.0]) - up[0] * up               # camera x, orthogonal to up
    x /= np.linalg.norm(x)
    y = np.cross(up, x)                                      # z-up world: (x, y, up), right-handed
    W = K @ np.stack([x, y, up], 1)                          # (T, 70, 3) world z-up
    soma = np.stack([W[..., 0], W[..., 2], -W[..., 1]], -1)  # SOMA y-up convention (inverse of soma_to_demo_frame)
    names = [NAME_MAP.get(n, n) for n in mhr_names]
    np.savez_compressed(a.out, joints=soma.astype(np.float32), joint_names=np.array(names), fps=fps,
                        frame="soma_world_y_up", wall_s=np.array(wall),
                        meta=json.dumps({"estimator": "Fast SAM 3D Body (sam-3d-body-dinov3)", "image_size": a.image_size,
                                         "up_from": "mean mid-hip->neck direction (camera frame)",
                                         "frames_without_person": n_missing, "source_video": Path(a.video).name}))
    print(f"\nwrote {a.out}: {soma.shape}, median {1 / np.median(wall):.1f} fps, missing {n_missing}")


if __name__ == "__main__":
    main()
