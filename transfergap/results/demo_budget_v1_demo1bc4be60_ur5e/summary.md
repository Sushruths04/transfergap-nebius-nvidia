# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo1bc4be60` (file)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 13.98 / 13.94 | 0 | 9.8 | 7.68 | -0.21 |
| oracle_perception | 0% (0/60) [0, 6] | 13.89 / 13.85 | 0 | 9.8 | 7.68 | -0.21 |
| oracle_calibration | 0% (0/60) [0, 6] | 13.86 / 13.84 | 0 | 9.8 | 7.68 | -0.21 |
| oracle_timing | 33% (20/60) [23, 46] | 3.53 / 3.39 | 0 | 5.2 | 0.37 | 0.01 |
| oracle_all | 100% (60/60) [94, 100] | 2.59 / 2.59 | 0 | 5.2 | 0.37 | 0.01 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +0.0 [+0.0, +0.0] | +0.09 [+0.05, +0.14] | -0.00 [-0.00, +0.00] |
| calibration | +0.0 [+0.0, +0.0] | +0.12 [+0.04, +0.20] | -0.00 [-0.00, +0.00] |
| timing | +33.3 [+21.7, +45.0] | +10.45 [+10.27, +10.61] | +0.22 [+0.22, +0.22] |

Chosen on dev: timing -> speed_cap_3 (argmax success budget over ['perception', 'calibration', 'timing'] on dev; ties -> that order).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 13.94 / 13.93 | 0 | -0.21 |
| full+speed_cap_3 | 17% (10/60) [9, 28] | 7.41 / 7.46 | 0 | -0.18 |

Paired success gap (corrected - full): +16.7 pp, 95% CI [+8.3, +26.7], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +6.53 cm, 95% CI [+6.46, +6.59].

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
