# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo44864be9` (file), after adopting safe_path_v2 + speed_cap_3

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 2% (1/60) [0, 9] | 10.03 / 9.98 | 0 | 26.7 | 1.75 | -0.12 |
| oracle_perception | 2% (1/60) [0, 9] | 9.91 / 9.83 | 0 | 26.9 | 1.64 | -0.13 |
| oracle_calibration | 5% (3/60) [2, 14] | 9.86 / 9.85 | 0 | 26.9 | 1.63 | -0.13 |
| oracle_timing | 10% (6/60) [5, 20] | 6.80 / 6.70 | 0 | 5.5 | 0.64 | -0.04 |
| oracle_all | 0% (0/60) [0, 6] | 6.17 / 6.16 | 0 | 5.8 | 0.38 | -0.05 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +0.0 [-5.0, +5.0] | +0.12 [+0.08, +0.17] | -0.00 [-0.00, -0.00] |
| calibration | +3.3 [+0.0, +8.3] | +0.17 [+0.06, +0.28] | -0.00 [-0.00, -0.00] |
| timing | +8.3 [+0.0, +16.7] | +3.23 [+3.14, +3.30] | +0.08 [+0.07, +0.09] |

Chosen on dev: timing -> speed_cap_2 (argmax success budget over components with an unused fix ['calibration', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 2% (1/60) [0, 9] | 10.02 / 9.94 | 0 | -0.12 |
| full+speed_cap_2 | 3% (2/60) [1, 11] | 8.43 / 8.32 | 0 | -0.10 |
| raw | 0% (0/60) [0, 6] | 15.20 / 15.21 | 0 | -0.16 |

Paired success gap (corrected - full): +1.7 pp, 95% CI [-3.3, +6.7], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): +1.59 cm, 95% CI [+1.57, +1.61].
Cumulative (all adopted fixes + this one, vs no fix): +3.3 pp, 95% CI [+0.0, +8.3], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
