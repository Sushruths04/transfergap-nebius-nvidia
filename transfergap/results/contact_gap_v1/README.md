# Placement gap per robot (contact_gap_v1)

Computed by `scripts/contact_gap.py` from the saved episode logs of `results/showcase_r6_shoulder044` (cluster volume `showcase_out_r6/pipe/rollouts/episodes_*.jsonl`, 60 seeds per robot and condition, logs read only, copied with kubectl). Simulation only.

Metric: horizontal distance between the object's final position and the goal. This is a PLACEMENT gap, not a grasp-contact gap, so it is not the same quantity as HOI-Retarget's contact-point gap (0.5 cm) and must not be compared to it directly.

| robot | condition | median gap | p90 gap | within tolerance (3 cm, released) |
|---|---|---|---|---|
| UR5e | raw | 2.27 cm | 35.48 cm | 31/60 |
| UR5e | all fixes | 0.45 cm | 0.62 cm | 60/60 |
| UR10e | raw | 2.24 cm | 35.45 cm | 35/60 |
| UR10e | all fixes | 0.41 cm | 0.73 cm | 60/60 |
| KAIROS | raw | 1.39 cm | 32.34 cm | 48/60 |
| KAIROS | all fixes | 0.60 cm | 1.13 cm | 60/60 |

Note: UR10e raw is 35/60 by this metric but 34/60 in the showcase success count; the official success also checks collision and settle speed (one UR10e raw episode had a forbidden collision). The official counts remain those in `results/showcase_r6_shoulder044`.
A grasp-contact gap (finger position vs the object's grasp point) needs end-effector poses, which the episode logs do not contain; it would need a rerun with logging on the GPU.
