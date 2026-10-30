# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo44864be9` (file), after adopting speed_cap_3 + speed_cap_2 + safe_path + speed_cap_1.5

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 3% (2/60) [1, 11] | 5.33 / 5.19 | 0 | 4.0 | 0.48 | -0.00 |
| oracle_perception | 7% (4/60) [3, 16] | 5.01 / 4.83 | 0 | 4.2 | 0.35 | 0.01 |
| oracle_calibration | 0% (0/60) [0, 6] | 4.95 / 4.89 | 0 | 4.1 | 0.37 | -0.03 |
| oracle_timing | 3% (2/60) [1, 11] | 4.91 / 4.77 | 0 | 2.7 | 0.48 | 0.11 |
| oracle_all | 0% (0/60) [0, 6] | 4.09 / 4.07 | 0 | 2.7 | 0.31 | -0.00 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +3.3 [+0.0, +8.3] | +0.32 [+0.23, +0.43] | +0.01 [-0.00, +0.02] |
| calibration | -3.3 [-8.3, +0.0] | +0.38 [+0.25, +0.54] | -0.03 [-0.04, -0.02] |
| timing | +0.0 [+0.0, +0.0] | +0.42 [+0.39, +0.45] | +0.11 [+0.09, +0.13] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 2% (1/60) [0, 9] | 5.26 / 5.18 | 0 | -0.01 |
| full+look_again | 0% (0/60) [0, 6] | 5.02 / 4.91 | 0 | -0.01 |
| raw | 0% (0/60) [0, 6] | 10.70 / 10.70 | 0 | -0.14 |

Paired success gap (corrected - full): -1.7 pp, 95% CI [-5.0, +0.0], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): +0.24 cm, 95% CI [+0.10, +0.36].
Cumulative (all adopted fixes + this one, vs no fix): +0.0 pp, 95% CI [+0.0, +0.0], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
