# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo44864be9` (file)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 15.24 / 15.22 | 0 | 58.1 | 5.55 | -0.16 |
| oracle_perception | 0% (0/60) [0, 6] | 15.17 / 15.17 | 0 | 58.1 | 5.57 | -0.16 |
| oracle_calibration | 0% (0/60) [0, 6] | 15.11 / 15.10 | 0 | 58.0 | 5.55 | -0.16 |
| oracle_timing | 2% (1/60) [0, 9] | 5.63 / 5.44 | 0 | 5.5 | 0.64 | -0.06 |
| oracle_all | 0% (0/60) [0, 6] | 4.73 / 4.70 | 0 | 5.8 | 0.38 | -0.08 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +0.0 [+0.0, +0.0] | +0.07 [+0.04, +0.10] | -0.00 [-0.00, +0.00] |
| calibration | +0.0 [+0.0, +0.0] | +0.13 [+0.06, +0.19] | -0.00 [-0.00, +0.00] |
| timing | +1.7 [+0.0, +5.0] | +9.61 [+9.41, +9.78] | +0.10 [+0.09, +0.11] |

Chosen on dev: style_feasibility -> safe_path_v2 (argmax success budget over components with an unused fix ['timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 15.20 / 15.21 | 0 | -0.16 |
| full+safe_path_v2 | 0% (0/60) [0, 6] | 15.41 / 15.41 | 0 | -0.16 |

Paired success gap (corrected - full): +0.0 pp, 95% CI [+0.0, +0.0], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): -0.21 cm, 95% CI [-0.29, -0.13].

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
