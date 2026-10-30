"""Build a scene twin from a clip that shows a printed marker: positions from the video, sizes from your tape.

    python -m transfergap.human.twin_from_video --video clip.mp4 --pose pose.npz --events GRASP RELEASE --marker-frame 0 \
        --marker-size-cm 12 --object-cm L W H --target-inner-cm L W --target-wall-cm H --out twin.json [--side Right] [--hfov 70]

How the numbers arise (stated, not hidden):
  * object position  = the pinch point (midpoint of thumb tip and index tip, 2D) at the GRASP frame, projected through the camera onto the plane
                       at height = half the object height (the fingers hold the object around its middle);
  * target position  = the pinch point at the RELEASE frame, projected at height = floor thickness + half the object height (the object comes to
                       rest on the floor of the target); a hand released higher above the target shifts the result along the viewing direction;
  * everything is in the TABLE FRAME of the marker (origin = marker centre), in metres, from one camera with assumed or given intrinsics;
  * the object and target SIZES are yours (tape): nothing here estimates them.
`placement` is left at the default (table midpoint to x = 0.45 m in front of the robot, no rotation): change it in the json to suit the robot.
Check the result against one tape measurement (centre-to-centre distance): it is printed next to the video-derived distance when you pass --tape-distance-cm.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import marker as M
from .analyze import SIDE, hand_idx

FLOOR_T = 0.004


def pinch_px(kp2d, frame, side="Right"):
    h = hand_idx(side)
    return (np.asarray(kp2d[frame, h["thumb_tip"]], float) + np.asarray(kp2d[frame, h["index_tip"]], float)) / 2


def build_twin(video, pose_npz, events, marker_frame, marker_size_m, obj_size_m, target_inner_m, wall_m, side="Right", hfov=70.0, K=None,
               frame_offset=0, name="twin from video + tape", tape_distance_m=None):
    det = M.detect_in_video(video, marker_frame, marker_size_m, hfov, K)
    if not det["found"]:
        raise RuntimeError(f"no marker (id 0, {M.DICT}) found in frame {marker_frame}: is it flat, in view, and printed at 100%?")
    Km, rvec, tvec = np.asarray(det["K"]), np.asarray(det["rvec"]), np.asarray(det["tvec"]).reshape(3, 1)
    z = np.load(pose_npz, allow_pickle=False)
    kp2d = np.asarray(z["kp2d"], float)
    g, r = (int(e) - frame_offset for e in events)
    zo, zt = obj_size_m[2] / 2, FLOOR_T + obj_size_m[2] / 2
    o = M.pixel_to_table(pinch_px(kp2d, g, side)[None], rvec, tvec, Km, z=zo)[0]
    t = M.pixel_to_table(pinch_px(kp2d, r, side)[None], rvec, tvec, Km, z=zt)[0]
    dist = float(np.linalg.norm(t - o))
    twin = {"schema": "transfergap.twin/v1", "name": name, "source": "marker + pose (positions) + tape (sizes)",
            "object": {"size_m": list(map(float, obj_size_m)), "xy_m": [round(float(o[0]), 4), round(float(o[1]), 4)]},
            "target": {"inner_size_m": list(map(float, target_inner_m)), "wall_height_m": float(wall_m), "xy_m": [round(float(t[0]), 4), round(float(t[1]), 4)]},
            "placement": {"yaw_deg": 0.0, "anchor_xy_m": [0.45, 0.0]}, "jitter_m": 0.01}
    check = {"video_carry_m": round(dist, 4), "marker": {k: det[k] for k in ("reprojection_px", "camera_distance_m", "marker_px_side", "intrinsics")}}
    if tape_distance_m:
        check["tape_carry_m"] = float(tape_distance_m)
        check["video_vs_tape_pct"] = round(100 * (dist - tape_distance_m) / tape_distance_m, 1)
    return twin, check


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--video", required=True)
    ap.add_argument("--pose", required=True, help="rtmw3d_export_joints.py npz (needs kp2d)")
    ap.add_argument("--events", nargs=2, type=int, required=True, metavar=("GRASP", "RELEASE"), help="frames of the video file")
    ap.add_argument("--frame-offset", type=int, default=0, help="video frame number of pose index 0 (when the pose was exported from a cut of the video)")
    ap.add_argument("--marker-frame", type=int, default=0)
    ap.add_argument("--marker-size-cm", type=float, default=12.0)
    ap.add_argument("--object-cm", type=float, nargs=3, required=True, metavar=("L", "W", "H"))
    ap.add_argument("--target-inner-cm", type=float, nargs=2, required=True, metavar=("L", "W"))
    ap.add_argument("--target-wall-cm", type=float, required=True)
    ap.add_argument("--side", default="Right")
    ap.add_argument("--hfov", type=float, default=70.0)
    ap.add_argument("--intrinsics")
    ap.add_argument("--tape-distance-cm", type=float)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    K = json.loads(Path(a.intrinsics).read_text()) if a.intrinsics else None
    twin, check = build_twin(a.video, a.pose, a.events, a.marker_frame, a.marker_size_cm / 100, [x / 100 for x in a.object_cm],
                             [x / 100 for x in a.target_inner_cm], a.target_wall_cm / 100, a.side, a.hfov, K, a.frame_offset,
                             tape_distance_m=a.tape_distance_cm / 100 if a.tape_distance_cm else None)
    Path(a.out).write_text(json.dumps(twin, indent=1))
    print(json.dumps(check, indent=1))


if __name__ == "__main__":
    main()
