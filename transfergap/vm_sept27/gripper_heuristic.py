"""Parallel-gripper retargeting via pinch-distance heuristic, per the
TransferGap plan's own scoping decision (not full dex_retargeting/URDF
pipeline -- confirmed correct by checking dex_retargeting's own
panda_gripper.yml pattern, which does the same simple thing for any
1-DOF parallel gripper).

Maps WiLoR's thumb-tip (landmark 4) / index-tip (landmark 8) 3D distance
-> the Robotiq 2F-85's gripper_right_driver_joint angle (range [0, 0.8] rad
in our combined ur5e_2f85_scene.xml, confirmed via MuJoCo model inspection;
0 = fully open, 0.8 = fully closed).
"""
import numpy as np

# Typical human pinch-distance range in meters (open hand -> fully pinched).
# These are reasonable defaults; recalibrate per-user if precision matters.
PINCH_OPEN_M = 0.10   # ~10cm, relaxed open hand thumb-to-index distance
PINCH_CLOSED_M = 0.01  # ~1cm, pinched fingertips

# From the compiled MuJoCo model (gripper_right_driver_joint range).
JOINT_OPEN = 0.0
JOINT_CLOSED = 0.8


def thumb_index_distance(landmarks_3d: np.ndarray) -> float:
    """landmarks_3d: (21, 3) array, standard hand-landmark ordering
    (thumb tip = index 4, index fingertip = index 8)."""
    thumb_tip = landmarks_3d[4]
    index_tip = landmarks_3d[8]
    return float(np.linalg.norm(thumb_tip - index_tip))


def pinch_to_gripper_angle(distance_m: float) -> float:
    """Map a measured pinch distance to the driver joint angle, clamped."""
    # Normalize: 0 = open (PINCH_OPEN_M), 1 = closed (PINCH_CLOSED_M)
    t = (PINCH_OPEN_M - distance_m) / (PINCH_OPEN_M - PINCH_CLOSED_M)
    t = float(np.clip(t, 0.0, 1.0))
    return JOINT_OPEN + t * (JOINT_CLOSED - JOINT_OPEN)


if __name__ == '__main__':
    # Sanity check with synthetic landmark data at three pinch states.
    for label, dist in [('wide open (12cm)', 0.12), ('half (5.5cm)', 0.055), ('pinched (0.5cm)', 0.005)]:
        angle = pinch_to_gripper_angle(dist)
        print(f'{label}: distance={dist:.3f}m -> joint angle={angle:.3f} rad (range [0, 0.8])')
