# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo44864be9` (file), after adopting speed_cap_3 + speed_cap_2 + safe_path

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 2% (1/60) [0, 9] | 5.85 / 5.72 | 0 | 5.9 | 0.42 | -0.03 |
| oracle_perception | 3% (2/60) [1, 11] | 5.57 / 5.43 | 0 | 6.1 | 0.33 | -0.02 |
| oracle_calibration | 0% (0/60) [0, 6] | 5.51 / 5.46 | 0 | 6.1 | 0.36 | -0.04 |
| oracle_timing | 3% (2/60) [1, 11] | 4.91 / 4.77 | 0 | 2.7 | 0.48 | 0.11 |
| oracle_all | 0% (0/60) [0, 6] | 4.09 / 4.07 | 0 | 2.7 | 0.31 | -0.00 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +1.7 [-3.3, +8.3] | +0.27 [+0.19, +0.36] | +0.00 [-0.01, +0.02] |
| calibration | -1.7 [-5.0, +0.0] | +0.34 [+0.22, +0.48] | -0.02 [-0.03, -0.01] |
| timing | +1.7 [+0.0, +5.0] | +0.93 [+0.88, +0.98] | +0.14 [+0.11, +0.16] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 5.76 / 5.73 | 0 | -0.04 |
| full+look_again | 0% (0/60) [0, 6] | 5.54 / 5.45 | 0 | -0.03 |
| full+speed_cap_1.5 | 2% (1/60) [0, 9] | 5.26 / 5.18 | 0 | -0.01 |
| raw | 0% (0/60) [0, 6] | 10.70 / 10.70 | 0 | -0.14 |

Paired success gap (corrected - full): +0.0 pp, 95% CI [+0.0, +0.0], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): +0.22 cm, 95% CI [+0.14, +0.30].
Nemotron agent chose `speed_cap_1.5` (rule chose `look_again`): agent - full +1.7 pp [+0.0, +5.0]; agent - rule +1.7 pp [+0.0, +5.0].
Cumulative (all adopted fixes + this one, vs no fix): +0.0 pp, 95% CI [+0.0, +0.0], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
