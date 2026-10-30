# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demobf3218bb` (file)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 42% (25/60) [30, 54] | 2.62 / 2.54 | 0 | 110.2 | 0.12 | -0.10 |
| oracle_perception | 78% (47/60) [66, 87] | 2.22 / 2.19 | 0 | 110.2 | 0.13 | -0.10 |
| oracle_calibration | 72% (43/60) [59, 81] | 1.91 / 1.82 | 0 | 110.2 | 0.10 | -0.10 |
| oracle_timing | 47% (28/60) [35, 59] | 2.25 / 2.18 | 0 | 21.5 | 0.09 | -0.09 |
| oracle_all | 100% (60/60) [94, 100] | 0.65 / 0.65 | 0 | 18.7 | 0.06 | -0.09 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +36.7 [+25.0, +50.0] | +0.40 [+0.29, +0.52] | -0.00 [-0.00, +0.00] |
| calibration | +30.0 [+18.3, +43.3] | +0.71 [+0.56, +0.88] | +0.00 [+0.00, +0.00] |
| timing | +5.0 [-8.3, +18.3] | +0.38 [+0.34, +0.41] | +0.01 [+0.01, +0.01] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'calibration'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 50% (30/60) [38, 62] | 2.48 / 2.39 | 0 | -0.10 |
| full+look_again | 65% (39/60) [52, 76] | 2.18 / 2.00 | 0 | -0.10 |

Paired success gap (corrected - full): +15.0 pp, 95% CI [+5.0, +25.0], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.31 cm, 95% CI [+0.18, +0.44].

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
