# Perception hard test, heldout split (kairos, seeds 100-139)

Per cell: successes over seeds, for 5 / 6 / 7 cm cubes. Failures: scorer reasons or perception_failed.

| condition | 50 mm | 60 mm | 70 mm | total | failure reasons |
|---|---|---|---|---|---|
| truth_yaw_aware | 40/40 | 40/40 | 40/40 | 120/120 | - |
| truth_yaw_blind | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_aligned | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_yaw | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_yaw_blind | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_distractors3 | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_calib_0p5deg_5mm | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_calib_1deg_10mm | 37/40 | 36/40 | 33/40 | 106/120 | no_lift, not_released_and_settled_at_goal |
| depth_calib_2deg_20mm | 15/40 | 18/40 | 18/40 | 51/120 | no_lift, not_released_and_settled_at_goal |
| depth_noise_10mm | 33/40 | 40/40 | 40/40 | 113/120 | perception_failed |
| depth_noise_20mm | 21/40 | 29/40 | 36/40 | 86/120 | not_released_and_settled_at_goal, perception_failed |
| depth_dropout30_fly1 | 39/40 | 40/40 | 40/40 | 119/120 | not_released_and_settled_at_goal |
| depth_arm_side | 5/40 | 1/40 | 2/40 | 8/120 | perception_failed |
| depth_arm_over | 5/40 | 3/40 | 2/40 | 10/120 | perception_failed |
| depth_arm_side_retry | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_arm_over_retry | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_calib_1deg_10mm_wrist | 33/40 | 31/40 | 33/40 | 97/120 | not_released_and_settled_at_goal |
| depth_calib_2deg_20mm_wrist | 18/40 | 14/40 | 11/40 | 43/120 | no_lift, not_released_and_settled_at_goal |
| depth_calib_1deg_10mm_wrist_tray | 38/40 | 36/40 | 39/40 | 113/120 | not_released_and_settled_at_goal |
| depth_calib_2deg_20mm_wrist_tray | 26/40 | 28/40 | 26/40 | 80/120 | no_lift, not_released_and_settled_at_goal |
| depth_edge_blocks | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_combined | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_combined_wrist_tray | 40/40 | 40/40 | 40/40 | 120/120 | - |
| depth_combined_wrist | 40/40 | 40/40 | 40/40 | 120/120 | - |
