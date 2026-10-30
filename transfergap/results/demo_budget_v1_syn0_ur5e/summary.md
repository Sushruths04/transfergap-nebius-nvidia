# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `syn0` (synthetic)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 50% (30/60) [38, 62] | 7.32 / 7.18 | 0 | 7.5 | 0.56 | -0.10 |
| oracle_perception | 75% (45/60) [63, 84] | 7.19 / 7.12 | 0 | 7.6 | 0.51 | -0.10 |
| oracle_retargeting | 57% (34/60) [44, 68] | 7.18 / 7.11 | 0 | 6.5 | 0.57 | -0.09 |
| oracle_calibration | 67% (40/60) [54, 77] | 7.06 / 6.98 | 0 | 7.5 | 0.49 | -0.10 |
| oracle_timing | 58% (35/60) [46, 70] | 4.05 / 3.86 | 0 | 7.7 | 0.55 | 0.02 |
| oracle_all | 100% (60/60) [94, 100] | 2.69 / 2.69 | 0 | 2.7 | 0.07 | 0.85 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +25.0 [+10.0, +40.0] | +0.12 [+0.03, +0.22] | +0.00 [-0.00, +0.00] |
| retargeting | +6.7 [+1.7, +13.3] | +0.14 [+0.10, +0.17] | +0.01 [+0.01, +0.01] |
| calibration | +16.7 [+5.0, +28.3] | +0.26 [+0.17, +0.35] | -0.00 [-0.00, +0.00] |
| timing | +8.3 [+1.7, +15.0] | +3.27 [+3.20, +3.33] | +0.12 [+0.11, +0.13] |

Chosen on dev: perception -> look_again (argmax success budget over ['perception', 'retargeting', 'calibration', 'timing'] on dev; ties -> that order).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 48% (29/60) [36, 61] | 7.26 / 7.17 | 0 | -0.10 |
| full+look_again | 78% (47/60) [66, 87] | 7.12 / 7.04 | 0 | -0.10 |

Paired success gap (corrected - full): +30.0 pp, 95% CI [+16.7, +45.0], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.14 cm, 95% CI [+0.03, +0.25].

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; the demo is SYNTHETIC (minimum-jerk), not human data; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
