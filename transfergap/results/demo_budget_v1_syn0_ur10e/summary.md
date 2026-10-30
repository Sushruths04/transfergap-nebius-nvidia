# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `syn0` (synthetic)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 48% (29/60) [36, 61] | 5.41 / 4.78 | 1 | 8.2 | 0.78 | 0.02 |
| oracle_perception | 68% (41/60) [56, 79] | 8.15 / 4.70 | 3 | 11.4 | 1.23 | 0.02 |
| oracle_retargeting | 50% (30/60) [38, 62] | 5.47 / 4.55 | 1 | 7.1 | 0.36 | 0.40 |
| oracle_calibration | 65% (39/60) [52, 76] | 5.95 / 4.48 | 1 | 8.5 | 0.78 | 0.02 |
| oracle_timing | 57% (34/60) [44, 68] | 3.21 / 3.11 | 0 | 8.7 | 0.69 | 0.07 |
| oracle_all | 100% (60/60) [94, 100] | 1.48 / 1.48 | 0 | 0.8 | 0.04 | 0.95 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +20.0 [+6.7, +33.3] | -2.74 [-7.38, +0.64] | -0.00 [-0.02, +0.01] |
| retargeting | +1.7 [-8.3, +11.7] | -0.06 [-2.06, +1.62] | +0.38 [+0.35, +0.40] |
| calibration | +16.7 [+5.0, +28.3] | -0.54 [-3.68, +1.64] | -0.00 [-0.01, +0.01] |
| timing | +8.3 [+0.0, +16.7] | +2.20 [+1.71, +3.13] | +0.05 [+0.03, +0.07] |

Chosen on dev: perception -> look_again (argmax success budget over ['perception', 'retargeting', 'calibration', 'timing'] on dev; ties -> that order).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 42% (25/60) [30, 54] | 5.69 / 4.85 | 1 | 0.03 |
| full+look_again | 75% (45/60) [63, 84] | 5.45 / 4.62 | 1 | 0.03 |

Paired success gap (corrected - full): +33.3 pp, 95% CI [+20.0, +48.3], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.23 cm, 95% CI [+0.11, +0.36].

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; the demo is SYNTHETIC (minimum-jerk), not human data; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
