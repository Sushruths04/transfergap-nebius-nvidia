# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo1bc4be60` (file)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 9.10 / 9.02 | 0 | 9.7 | 2.09 | -0.20 |
| oracle_perception | 0% (0/60) [0, 6] | 8.92 / 8.92 | 0 | 9.7 | 2.09 | -0.20 |
| oracle_calibration | 0% (0/60) [0, 6] | 8.87 / 8.80 | 0 | 9.7 | 2.08 | -0.20 |
| oracle_timing | 35% (21/60) [24, 48] | 2.76 / 2.66 | 0 | 2.8 | 0.17 | 0.46 |
| oracle_all | 100% (60/60) [94, 100] | 1.48 / 1.48 | 0 | 2.7 | 0.17 | 0.47 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +0.0 [+0.0, +0.0] | +0.18 [+0.08, +0.28] | -0.00 [-0.00, +0.00] |
| calibration | +0.0 [+0.0, +0.0] | +0.23 [+0.14, +0.32] | -0.00 [-0.00, -0.00] |
| timing | +35.0 [+23.3, +46.7] | +6.34 [+6.19, +6.47] | +0.66 [+0.66, +0.66] |

Chosen on dev: timing -> speed_cap_3 (argmax success budget over ['perception', 'calibration', 'timing'] on dev; ties -> that order).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 9.15 / 9.08 | 0 | -0.20 |
| full+speed_cap_3 | 25% (15/60) [16, 37] | 4.51 / 4.42 | 0 | -0.09 |

Paired success gap (corrected - full): +25.0 pp, 95% CI [+15.0, +36.7], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +4.63 cm, 95% CI [+4.55, +4.71].

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
