# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo5f8bdc01` (file)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 10% (6/60) [5, 20] | 8.35 / 8.22 | 0 | 113.2 | 0.54 | 0.06 |
| oracle_perception | 40% (24/60) [29, 53] | 8.22 / 8.08 | 0 | 114.0 | 0.54 | 0.06 |
| oracle_calibration | 15% (9/60) [8, 26] | 8.02 / 7.89 | 0 | 112.1 | 0.50 | 0.06 |
| oracle_timing | 8% (5/60) [4, 18] | 5.99 / 5.82 | 0 | 97.2 | 0.20 | 0.20 |
| oracle_all | 0% (0/60) [0, 6] | 5.42 / 5.42 | 0 | 96.5 | 0.16 | 0.21 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +30.0 [+16.7, +43.3] | +0.13 [-0.01, +0.26] | +0.00 [-0.00, +0.00] |
| calibration | +5.0 [-6.7, +16.7] | +0.33 [+0.22, +0.44] | +0.00 [+0.00, +0.00] |
| timing | -1.7 [-6.7, +3.3] | +2.35 [+2.32, +2.39] | +0.14 [+0.13, +0.14] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'calibration', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 7% (4/60) [3, 16] | 8.35 / 8.30 | 0 | 0.06 |
| full+look_again | 28% (17/60) [19, 41] | 8.20 / 8.10 | 0 | 0.06 |

Paired success gap (corrected - full): +21.7 pp, 95% CI [+10.0, +33.3], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.16 cm, 95% CI [+0.05, +0.27].

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
