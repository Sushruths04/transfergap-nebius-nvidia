# Fingertip retargeting to a dexterous hand (hand_retarget_v1)

Code: `live/hand_retarget.py`. Input: the 21 right-hand keypoints per frame of the author's clip (`joints_scaled.npz` of `results/showcase_r6_shoulder044`, 270 frames). Robot hand: Wonik Allegro (MuJoCo Menagerie, 16 joints, 4 fingers). Kinematics only: no contact, no object, palm fixed in space, pinky not mapped. Method: palm frame from wrist and finger bases, fingertip targets scaled by the robot/human finger-length ratio (0.877), one rotation chosen from the 24 axis-aligned rotations by the smallest fingertip error on every 6th frame (best 2.32 cm average; the identity rotation gave 5.58 cm), then per-finger damped least-squares IK with joint limits. The idea (fingertip alignment) follows UniDex / dex-retargeting as seen in search summaries; this implementation is written from scratch and is not compared with theirs.

Fingertip tracking error in the robot's scale (cm), median / 90th percentile over the clip:
| finger | median | p90 |
|---|---|---|
| thumb | 4.1 | 6.26 |
| index | 1.56 | 3.73 |
| middle | 1.6 | 2.49 |
| ring | 0.47 | 4.95 |

Limits: the human keypoints are monocular estimates from a distant camera (finger segment lengths vary by 20-30% frame to frame), so the error includes input noise; the thumb is the weakest because the Allegro thumb kinematics differ most from a human thumb; the axis alignment is fitted on this clip (a one-off calibration, not validated on other people). Video: `hand_retarget.mp4` (left: your hand skeleton, right: the Allegro hand).
