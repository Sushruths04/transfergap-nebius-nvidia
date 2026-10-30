# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demobf3218bb` (file)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 48% (29/60) [36, 61] | 3.68 / 3.62 | 0 | 112.0 | 0.23 | -0.12 |
| oracle_perception | 80% (48/60) [68, 88] | 3.43 / 3.39 | 0 | 111.9 | 0.24 | -0.12 |
| oracle_calibration | 65% (39/60) [52, 76] | 3.16 / 3.13 | 0 | 112.3 | 0.16 | -0.12 |
| oracle_timing | 60% (36/60) [47, 71] | 2.52 / 2.45 | 0 | 95.5 | 0.18 | -0.11 |
| oracle_all | 100% (60/60) [94, 100] | 1.26 / 1.25 | 0 | 95.2 | 0.10 | -0.11 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +31.7 [+18.3, +45.0] | +0.25 [+0.17, +0.34] | -0.00 [-0.00, +0.00] |
| calibration | +16.7 [+5.0, +30.0] | +0.52 [+0.41, +0.65] | +0.00 [+0.00, +0.00] |
| timing | +11.7 [-1.7, +26.7] | +1.15 [+1.08, +1.21] | +0.00 [+0.00, +0.00] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'calibration'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 58% (35/60) [46, 70] | 3.57 / 3.47 | 0 | -0.12 |
| full+look_again | 87% (52/60) [76, 93] | 3.33 / 3.29 | 0 | -0.12 |

Paired success gap (corrected - full): +28.3 pp, 95% CI [+16.7, +40.0], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.24 cm, 95% CI [+0.17, +0.32].

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
