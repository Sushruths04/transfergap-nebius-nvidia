# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo7c1fa3bd` (file)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 68% (41/60) [56, 79] | 4.34 / 4.28 | 0 | 9.7 | 1.30 | -0.01 |
| oracle_perception | 95% (57/60) [86, 98] | 4.13 / 4.08 | 0 | 9.4 | 1.20 | -0.01 |
| oracle_calibration | 72% (43/60) [59, 81] | 3.85 / 3.84 | 0 | 9.6 | 1.27 | -0.01 |
| oracle_timing | 65% (39/60) [52, 76] | 2.84 / 2.80 | 0 | 2.1 | 0.81 | 0.10 |
| oracle_all | 100% (60/60) [94, 100] | 1.75 / 1.75 | 0 | 1.3 | 0.59 | 0.15 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +26.7 [+15.0, +38.3] | +0.21 [+0.14, +0.28] | +0.00 [+0.00, +0.01] |
| calibration | +3.3 [-8.3, +15.0] | +0.49 [+0.39, +0.61] | -0.00 [-0.01, -0.00] |
| timing | -3.3 [-8.3, +0.0] | +1.50 [+1.43, +1.56] | +0.11 [+0.09, +0.13] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'calibration'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 52% (31/60) [39, 64] | 4.26 / 4.19 | 0 | -0.01 |
| full+look_again | 92% (55/60) [82, 96] | 4.05 / 3.98 | 0 | -0.00 |

Paired success gap (corrected - full): +40.0 pp, 95% CI [+26.7, +55.0], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.21 cm, 95% CI [+0.15, +0.27].

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
