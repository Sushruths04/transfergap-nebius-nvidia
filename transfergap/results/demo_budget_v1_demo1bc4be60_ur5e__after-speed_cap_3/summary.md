# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo1bc4be60` (file), after adopting speed_cap_3

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 25% (15/60) [16, 37] | 7.46 / 7.42 | 0 | 7.2 | 2.01 | -0.18 |
| oracle_perception | 48% (29/60) [36, 61] | 7.29 / 7.32 | 0 | 7.2 | 1.99 | -0.18 |
| oracle_calibration | 33% (20/60) [23, 46] | 7.22 / 7.20 | 0 | 7.2 | 2.03 | -0.18 |
| oracle_timing | 33% (20/60) [23, 46] | 3.53 / 3.39 | 0 | 5.2 | 0.37 | 0.01 |
| oracle_all | 100% (60/60) [94, 100] | 2.59 / 2.59 | 0 | 5.2 | 0.37 | 0.01 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +23.3 [+11.7, +35.0] | +0.17 [+0.10, +0.25] | -0.00 [-0.00, +0.00] |
| calibration | +8.3 [-6.7, +23.3] | +0.24 [+0.17, +0.33] | -0.00 [-0.00, -0.00] |
| timing | +8.3 [-3.3, +20.0] | +3.93 [+3.82, +4.03] | +0.19 [+0.19, +0.19] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'calibration', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 17% (10/60) [9, 28] | 7.41 / 7.46 | 0 | -0.18 |
| full+look_again | 58% (35/60) [46, 70] | 7.23 / 7.19 | 0 | -0.18 |
| raw | 0% (0/60) [0, 6] | 13.94 / 13.93 | 0 | -0.21 |

Paired success gap (corrected - full): +41.7 pp, 95% CI [+28.3, +55.0], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.18 cm, 95% CI [+0.10, +0.26].
Cumulative (all adopted fixes + this one, vs no fix): +58.3 pp, 95% CI [+45.0, +70.0], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
