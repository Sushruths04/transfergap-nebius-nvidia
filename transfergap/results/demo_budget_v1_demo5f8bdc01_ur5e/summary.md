# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo5f8bdc01` (file)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 38% (23/60) [27, 51] | 11.78 / 11.70 | 0 | 107.0 | 1.55 | 0.02 |
| oracle_perception | 63% (38/60) [51, 74] | 11.70 / 11.66 | 0 | 107.1 | 1.55 | 0.02 |
| oracle_calibration | 48% (29/60) [36, 61] | 11.53 / 11.48 | 0 | 107.7 | 1.54 | 0.02 |
| oracle_timing | 23% (14/60) [14, 35] | 7.77 / 7.70 | 0 | 99.4 | 0.61 | 0.12 |
| oracle_all | 100% (60/60) [94, 100] | 7.35 / 7.36 | 0 | 98.6 | 0.54 | 0.12 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +25.0 [+13.3, +36.7] | +0.08 [-0.04, +0.20] | -0.00 [-0.00, +0.00] |
| calibration | +10.0 [-1.7, +21.7] | +0.25 [+0.15, +0.35] | +0.00 [-0.00, +0.00] |
| timing | -15.0 [-28.3, -1.7] | +4.01 [+3.99, +4.04] | +0.09 [+0.09, +0.10] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'calibration', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 18% (11/60) [11, 30] | 11.76 / 11.69 | 0 | 0.02 |
| full+look_again | 68% (41/60) [56, 79] | 11.63 / 11.54 | 0 | 0.02 |

Paired success gap (corrected - full): +50.0 pp, 95% CI [+36.7, +63.3], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.13 cm, 95% CI [+0.02, +0.23].

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
