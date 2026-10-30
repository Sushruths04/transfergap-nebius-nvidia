# Perception hard test, dev split (ur10e, seeds 0-9)

Per cell: successes over seeds, for 5 / 6 / 7 cm cubes. Failures: scorer reasons or perception_failed.

| condition | 50 mm | 60 mm | 70 mm | total | failure reasons |
|---|---|---|---|---|---|
| truth_yaw_aware | 10/10 | 10/10 | 10/10 | 30/30 | - |
| truth_yaw_blind | 10/10 | 10/10 | 5/10 | 25/30 | no_lift, not_released_and_settled_at_goal |
| depth_aligned | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_yaw | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_yaw_blind | 10/10 | 10/10 | 5/10 | 25/30 | no_lift, not_released_and_settled_at_goal |
| depth_distractors3 | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_calib_0p5deg_5mm | 10/10 | 9/10 | 5/10 | 24/30 | no_lift, not_released_and_settled_at_goal |
| depth_calib_1deg_10mm | 6/10 | 5/10 | 2/10 | 13/30 | no_lift, not_released_and_settled_at_goal |
| depth_calib_2deg_20mm | 2/10 | 1/10 | 1/10 | 4/30 | no_lift, not_released_and_settled_at_goal |
| depth_noise_10mm | 9/10 | 10/10 | 10/10 | 29/30 | perception_failed |
| depth_noise_20mm | 4/10 | 5/10 | 6/10 | 15/30 | forbidden_collision, not_released_and_settled_at_goal, perception_failed |
| depth_dropout30_fly1 | 9/10 | 9/10 | 9/10 | 27/30 | not_released_and_settled_at_goal |
| depth_arm_side | 0/10 | 0/10 | 0/10 | 0/30 | perception_failed |
| depth_arm_over | 0/10 | 0/10 | 0/10 | 0/30 | perception_failed |
| depth_arm_side_retry | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_arm_over_retry | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_calib_1deg_10mm_wrist | 10/10 | 10/10 | 6/10 | 26/30 | no_lift, not_released_and_settled_at_goal |
| depth_calib_2deg_20mm_wrist | 2/10 | 1/10 | 1/10 | 4/30 | forbidden_collision, no_lift, not_released_and_settled_at_goal |
| depth_edge_blocks | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_combined | 10/10 | 9/10 | 5/10 | 24/30 | no_lift, not_released_and_settled_at_goal |
| depth_combined_wrist | 10/10 | 10/10 | 10/10 | 30/30 | - |
