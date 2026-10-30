# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo44864be9` (file), after adopting safe_path_v2

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 15.46 / 15.44 | 0 | 58.1 | 5.53 | -0.16 |
| oracle_perception | 0% (0/60) [0, 6] | 15.39 / 15.39 | 0 | 58.1 | 5.55 | -0.16 |
| oracle_calibration | 0% (0/60) [0, 6] | 15.33 / 15.31 | 0 | 58.0 | 5.54 | -0.16 |
| oracle_timing | 10% (6/60) [5, 20] | 6.80 / 6.70 | 0 | 5.5 | 0.64 | -0.04 |
| oracle_all | 0% (0/60) [0, 6] | 6.17 / 6.16 | 0 | 5.8 | 0.38 | -0.05 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +0.0 [+0.0, +0.0] | +0.06 [+0.04, +0.09] | -0.00 [-0.00, +0.00] |
| calibration | +0.0 [+0.0, +0.0] | +0.13 [+0.04, +0.22] | +0.00 [-0.00, +0.00] |
| timing | +10.0 [+3.3, +18.3] | +8.66 [+8.54, +8.76] | +0.12 [+0.11, +0.13] |

Chosen on dev: timing -> speed_cap_3 (argmax success budget over components with an unused fix ['timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 15.41 / 15.41 | 0 | -0.16 |
| full+speed_cap_3 | 2% (1/60) [0, 9] | 10.02 / 9.94 | 0 | -0.12 |
| raw | 0% (0/60) [0, 6] | 15.20 / 15.21 | 0 | -0.16 |

Paired success gap (corrected - full): +1.7 pp, 95% CI [+0.0, +5.0], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): +5.39 cm, 95% CI [+5.34, +5.43].
Cumulative (all adopted fixes + this one, vs no fix): +1.7 pp, 95% CI [+0.0, +5.0], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
