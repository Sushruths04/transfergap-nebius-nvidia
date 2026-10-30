# Perception hard test, dev split (kairos, seeds 0-9)

Per cell: successes over seeds, for 5 / 6 / 7 cm cubes. Failures: scorer reasons or perception_failed.

| condition | 50 mm | 60 mm | 70 mm | total | failure reasons |
|---|---|---|---|---|---|
| truth_yaw_aware | 10/10 | 10/10 | 10/10 | 30/30 | - |
| truth_yaw_blind | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_aligned | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_yaw | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_yaw_blind | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_distractors3 | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_calib_0p5deg_5mm | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_calib_1deg_10mm | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_calib_2deg_20mm | 3/10 | 3/10 | 4/10 | 10/30 | no_lift, not_released_and_settled_at_goal |
| depth_noise_10mm | 9/10 | 10/10 | 10/10 | 29/30 | perception_failed |
| depth_noise_20mm | 3/10 | 4/10 | 7/10 | 14/30 | not_released_and_settled_at_goal, perception_failed |
| depth_dropout30_fly1 | 9/10 | 9/10 | 9/10 | 27/30 | not_released_and_settled_at_goal |
| depth_arm_side | 1/10 | 0/10 | 0/10 | 1/30 | perception_failed |
| depth_arm_over | 1/10 | 1/10 | 0/10 | 2/30 | perception_failed |
| depth_arm_side_retry | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_arm_over_retry | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_calib_1deg_10mm_wrist | 8/10 | 7/10 | 8/10 | 23/30 | not_released_and_settled_at_goal |
| depth_calib_2deg_20mm_wrist | 1/10 | 2/10 | 1/10 | 4/30 | no_lift, not_released_and_settled_at_goal |
| depth_edge_blocks | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_combined | 10/10 | 10/10 | 10/10 | 30/30 | - |
| depth_combined_wrist | 10/10 | 10/10 | 10/10 | 30/30 | - |
