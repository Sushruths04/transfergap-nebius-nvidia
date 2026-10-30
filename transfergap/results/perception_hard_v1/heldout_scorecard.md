# Held-out scorecard, protocol perception_hard_v1 (frozen at code commit 04793f0)

Held-out seeds 100-139 (40 seeds x 3 cube sizes = 120 episodes per cell), pooled; Wilson 95% interval; dev rate (seeds 0-9) for comparison. `*` = acceptance bar (>= 0.90 pooled, declared before the run).

| condition | ur5e | ur10e | kairos |
|---|---|---|---|
| *truth_yaw_aware | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) |
| truth_yaw_blind | 101/120 [0.77, 0.90] (dev 0.80) | 107/120 [0.82, 0.94] (dev 0.83) | 120/120 [0.97, 1.00] (dev 1.00) |
| *depth_aligned | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) |
| *depth_yaw | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) |
| depth_yaw_blind | 101/120 [0.77, 0.90] (dev 0.80) | 104/120 [0.79, 0.92] (dev 0.83) | 120/120 [0.97, 1.00] (dev 1.00) |
| *depth_distractors3 | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) |
| depth_calib_0p5deg_5mm | 99/120 [0.75, 0.88] (dev 0.80) | 100/120 [0.76, 0.89] (dev 0.80) | 120/120 [0.97, 1.00] (dev 1.00) |
| depth_calib_1deg_10mm | 65/120 [0.45, 0.63] (dev 0.43) | 65/120 [0.45, 0.63] (dev 0.43) | 106/120 [0.81, 0.93] (dev 0.90) |
| depth_calib_2deg_20mm | 25/120 [0.15, 0.29] (dev 0.13) | 25/120 [0.15, 0.29] (dev 0.13) | 51/120 [0.34, 0.51] (dev 0.23) |
| *depth_noise_10mm | 113/120 [0.88, 0.97] (dev 0.97) | 113/120 [0.88, 0.97] (dev 0.97) | 113/120 [0.88, 0.97] (dev 0.97) |
| depth_noise_20mm | 81/120 [0.59, 0.75] (dev 0.53) | 82/120 [0.60, 0.76] (dev 0.50) | 86/120 [0.63, 0.79] (dev 0.47) |
| depth_dropout30_fly1 | 115/120 [0.91, 0.98] (dev 0.90) | 115/120 [0.91, 0.98] (dev 0.90) | 119/120 [0.95, 1.00] (dev 0.90) |
| depth_arm_side | 16/120 [0.08, 0.21] (dev 0.27) | 0/120 [0.00, 0.03] (dev 0.00) | 8/120 [0.03, 0.13] (dev 0.03) |
| depth_arm_over | 2/120 [0.00, 0.06] (dev 0.00) | 0/120 [0.00, 0.03] (dev 0.00) | 10/120 [0.05, 0.15] (dev 0.07) |
| *depth_arm_side_retry | 118/120 [0.94, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) |
| *depth_arm_over_retry | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) |
| depth_calib_1deg_10mm_wrist | 102/120 [0.78, 0.90] (dev 0.83) | 101/120 [0.77, 0.90] (dev 0.87) | 97/120 [0.73, 0.87] (dev 0.77) |
| depth_calib_2deg_20mm_wrist | 27/120 [0.16, 0.31] (dev 0.10) | 26/120 [0.15, 0.30] (dev 0.13) | 43/120 [0.28, 0.45] (dev 0.10) |
| depth_calib_1deg_10mm_wrist_tray | 107/120 [0.82, 0.94] (dev 0.90) | 108/120 [0.83, 0.94] (dev 0.87) | 113/120 [0.88, 0.97] (dev 0.90) |
| depth_calib_2deg_20mm_wrist_tray | 54/120 [0.36, 0.54] (dev 0.40) | 59/120 [0.40, 0.58] (dev 0.40) | 80/120 [0.58, 0.74] (dev 0.67) |
| *depth_edge_blocks | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) |
| depth_combined | 101/120 [0.77, 0.90] (dev 0.80) | 100/120 [0.76, 0.89] (dev 0.80) | 120/120 [0.97, 1.00] (dev 1.00) |
| *depth_combined_wrist_tray | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) |
| *depth_combined_wrist | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) | 120/120 [0.97, 1.00] (dev 1.00) |

**Acceptance: 30 of 30 bar cells met.** None failed.

Report-only conditions are stress tests beyond a stated tolerance (camera calibration error, 20 mm depth noise, arm in view without a retry); their rates are results, not pass/fail.
