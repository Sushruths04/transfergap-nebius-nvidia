# Perception hard test, heldout split (ur5e, seeds 100-139)

Per cell: successes over seeds, for 5 / 6 / 7 cm cubes. Failures: scorer reasons or perception_failed.

| condition | 50 mm | 60 mm | 70 mm | total | failure reasons |
|---|---|---|---|---|---|
| truth_yaw_aware | 40/40 | 40/40 | 40/40 | 120/120 | - |
| truth_yaw_blind | 40/40 | 34/40 | 27/40 | 101/120 | no_lift, not_released_and_settled_at_goal |
| depth_aligned | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_yaw | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_yaw_blind | 40/40 | 34/40 | 27/40 | 101/120 | no_lift, not_released_and_settled_at_goal |
| depth_distractors3 | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_calib_0p5deg_5mm | 40/40 | 33/40 | 26/40 | 99/120 | no_lift, not_released_and_settled_at_goal |
| depth_calib_1deg_10mm | 28/40 | 23/40 | 14/40 | 65/120 | no_lift, not_released_and_settled_at_goal |
| depth_calib_2deg_20mm | 7/40 | 10/40 | 8/40 | 25/120 | no_lift, not_released_and_settled_at_goal |
| depth_noise_10mm | 33/40 | 40/40 | 40/40 | 113/120 | perception_failed |
| depth_noise_20mm | 20/40 | 27/40 | 34/40 | 81/120 | forbidden_collision, not_released_and_settled_at_goal, perception_failed |
| depth_dropout30_fly1 | 39/40 | 38/40 | 38/40 | 115/120 | not_released_and_settled_at_goal |
| depth_arm_side | 3/40 | 4/40 | 9/40 | 16/120 | not_released_and_settled_at_goal, perception_failed |
| depth_arm_over | 1/40 | 0/40 | 1/40 | 2/120 | perception_failed |
| depth_arm_side_retry | 39/40 | 39/40 | 40/40 | 118/120 | not_released_and_settled_at_goal |
| depth_arm_over_retry | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_calib_1deg_10mm_wrist | 37/40 | 37/40 | 28/40 | 102/120 | forbidden_collision, no_lift, not_released_and_settled_at_goal |
| depth_calib_2deg_20mm_wrist | 14/40 | 9/40 | 4/40 | 27/120 | forbidden_collision, no_lift, not_released_and_settled_at_goal |
| depth_calib_1deg_10mm_wrist_tray | 40/40 | 40/40 | 27/40 | 107/120 | no_lift, not_released_and_settled_at_goal |
| depth_calib_2deg_20mm_wrist_tray | 27/40 | 19/40 | 8/40 | 54/120 | forbidden_collision, no_lift, not_released_and_settled_at_goal |
| depth_edge_blocks | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_combined | 40/40 | 33/40 | 28/40 | 101/120 | no_lift, not_released_and_settled_at_goal |
| depth_combined_wrist_tray | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_combined_wrist | 40/40 | 40/40 | 40/40 | 120/120 | - |
