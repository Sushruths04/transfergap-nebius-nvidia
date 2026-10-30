# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo1bc4be60` (file), after adopting speed_cap_3

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 32% (19/60) [21, 44] | 4.59 / 4.47 | 0 | 8.6 | 0.45 | -0.09 |
| oracle_perception | 50% (30/60) [38, 62] | 4.30 / 4.23 | 0 | 8.6 | 0.45 | -0.09 |
| oracle_calibration | 50% (30/60) [38, 62] | 4.20 / 4.12 | 0 | 8.6 | 0.46 | -0.09 |
| oracle_timing | 35% (21/60) [24, 48] | 2.76 / 2.66 | 0 | 2.8 | 0.17 | 0.46 |
| oracle_all | 100% (60/60) [94, 100] | 1.48 / 1.48 | 0 | 2.7 | 0.17 | 0.47 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +18.3 [+8.3, +30.0] | +0.29 [+0.18, +0.42] | -0.00 [-0.00, +0.00] |
| calibration | +18.3 [+6.7, +31.7] | +0.39 [+0.29, +0.52] | +0.00 [-0.00, +0.00] |
| timing | +3.3 [-6.7, +13.3] | +1.83 [+1.76, +1.91] | +0.55 [+0.55, +0.56] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'calibration', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 25% (15/60) [16, 37] | 4.51 / 4.42 | 0 | -0.09 |
| full+look_again | 58% (35/60) [46, 70] | 4.20 / 4.13 | 0 | -0.09 |
| raw | 0% (0/60) [0, 6] | 9.15 / 9.08 | 0 | -0.20 |

Paired success gap (corrected - full): +33.3 pp, 95% CI [+16.7, +50.0], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.31 cm, 95% CI [+0.20, +0.43].
Cumulative (all adopted fixes + this one, vs no fix): +58.3 pp, 95% CI [+46.7, +70.0], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
