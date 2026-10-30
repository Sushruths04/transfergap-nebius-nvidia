# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo1bc4be60` (file), after adopting speed_cap_3 + look_again

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 48% (29/60) [36, 61] | 7.31 / 7.32 | 0 | 7.2 | 1.98 | -0.18 |
| oracle_perception | 48% (29/60) [36, 61] | 7.29 / 7.32 | 0 | 7.2 | 1.99 | -0.18 |
| oracle_calibration | 98% (59/60) [91, 100] | 7.08 / 7.06 | 0 | 7.2 | 1.97 | -0.18 |
| oracle_timing | 58% (35/60) [46, 70] | 3.18 / 3.07 | 0 | 5.2 | 0.40 | 0.01 |
| oracle_all | 100% (60/60) [94, 100] | 2.59 / 2.59 | 0 | 5.2 | 0.37 | 0.01 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +0.0 [-6.7, +6.7] | +0.03 [+0.00, +0.05] | -0.00 [-0.00, +0.00] |
| calibration | +50.0 [+38.3, +61.7] | +0.24 [+0.17, +0.31] | -0.00 [-0.00, +0.00] |
| timing | +10.0 [+3.3, +18.3] | +4.13 [+4.04, +4.21] | +0.19 [+0.19, +0.19] |

Chosen on dev: calibration -> touch_probe_calibration (argmax success budget over components with an unused fix ['calibration', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 58% (35/60) [46, 70] | 7.23 / 7.19 | 0 | -0.18 |
| full+touch_probe_calibration | 83% (50/60) [72, 91] | 7.10 / 7.08 | 0 | -0.18 |
| raw | 0% (0/60) [0, 6] | 13.94 / 13.93 | 0 | -0.21 |

Paired success gap (corrected - full): +25.0 pp, 95% CI [+8.3, +41.7], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.14 cm, 95% CI [+0.09, +0.19].
Cumulative (all adopted fixes + this one, vs no fix): +83.3 pp, 95% CI [+73.3, +91.7], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
