# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo44864be9` (file), after adopting safe_path_v2 + speed_cap_3 + speed_cap_2 + look_again

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 13% (8/60) [7, 24] | 8.29 / 8.18 | 0 | 15.3 | 0.78 | -0.10 |
| oracle_perception | 18% (11/60) [11, 30] | 8.28 / 8.19 | 0 | 15.3 | 0.78 | -0.10 |
| oracle_calibration | 0% (0/60) [0, 6] | 8.08 / 8.08 | 0 | 15.3 | 0.70 | -0.10 |
| oracle_timing | 18% (11/60) [11, 30] | 6.52 / 6.33 | 0 | 5.7 | 0.48 | -0.04 |
| oracle_all | 0% (0/60) [0, 6] | 6.17 / 6.16 | 0 | 5.8 | 0.38 | -0.05 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +5.0 [-1.7, +13.3] | +0.01 [-0.02, +0.03] | +0.00 [-0.00, +0.00] |
| calibration | -13.3 [-23.3, -5.0] | +0.21 [+0.10, +0.33] | -0.00 [-0.00, -0.00] |
| timing | +5.0 [-1.7, +11.7] | +1.77 [+1.73, +1.80] | +0.06 [+0.05, +0.07] |

Chosen on dev: timing -> speed_cap_1.5 (argmax success budget over components with an unused fix ['timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 2% (1/60) [0, 9] | 8.27 / 8.20 | 0 | -0.10 |
| full+speed_cap_1.5 | 7% (4/60) [3, 16] | 7.32 / 7.25 | 0 | -0.10 |
| full+safe_path | 2% (1/60) [0, 9] | 8.27 / 8.20 | 0 | -0.10 |
| raw | 0% (0/60) [0, 6] | 15.20 / 15.21 | 0 | -0.16 |

Paired success gap (corrected - full): +5.0 pp, 95% CI [+0.0, +10.0], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): +0.94 cm, 95% CI [+0.93, +0.95].
Nemotron agent chose `safe_path` (rule chose `speed_cap_1.5`): agent - full +0.0 pp [+0.0, +0.0]; agent - rule -5.0 pp [-10.0, +0.0].
Cumulative (all adopted fixes + this one, vs no fix): +6.7 pp, 95% CI [+1.7, +13.3], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
