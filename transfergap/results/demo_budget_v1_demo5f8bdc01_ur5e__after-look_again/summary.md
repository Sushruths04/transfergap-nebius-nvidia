# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo5f8bdc01` (file), after adopting look_again

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 62% (37/60) [49, 73] | 11.73 / 11.63 | 0 | 106.9 | 1.55 | 0.02 |
| oracle_perception | 63% (38/60) [51, 74] | 11.70 / 11.66 | 0 | 107.1 | 1.55 | 0.02 |
| oracle_calibration | 97% (58/60) [89, 99] | 11.47 / 11.48 | 0 | 107.6 | 1.54 | 0.02 |
| oracle_timing | 58% (35/60) [46, 70] | 7.67 / 7.59 | 0 | 99.8 | 0.66 | 0.12 |
| oracle_all | 100% (60/60) [94, 100] | 7.35 / 7.36 | 0 | 98.6 | 0.54 | 0.12 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +1.7 [-5.0, +8.3] | +0.03 [-0.00, +0.06] | +0.00 [-0.00, +0.00] |
| calibration | +35.0 [+23.3, +48.3] | +0.26 [+0.16, +0.36] | -0.00 [-0.00, +0.00] |
| timing | -3.3 [-18.3, +11.7] | +4.06 [+4.03, +4.08] | +0.10 [+0.09, +0.10] |

Chosen on dev: calibration -> touch_probe_calibration (argmax success budget over components with an unused fix ['calibration', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 68% (41/60) [56, 79] | 11.63 / 11.54 | 0 | 0.02 |
| full+touch_probe_calibration | 95% (57/60) [86, 98] | 11.47 / 11.47 | 0 | 0.02 |
| raw | 18% (11/60) [11, 30] | 11.76 / 11.69 | 0 | 0.02 |

Paired success gap (corrected - full): +26.7 pp, 95% CI [+15.0, +38.3], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.16 cm, 95% CI [+0.08, +0.25].
Cumulative (all adopted fixes + this one, vs no fix): +76.7 pp, 95% CI [+66.7, +86.7], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
