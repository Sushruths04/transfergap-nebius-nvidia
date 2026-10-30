# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo44864be9` (file), after adopting speed_cap_3

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 3% (2/60) [1, 11] | 9.38 / 9.48 | 0 | 26.7 | 1.75 | -0.12 |
| oracle_perception | 7% (4/60) [3, 16] | 9.26 / 9.34 | 0 | 26.9 | 1.64 | -0.13 |
| oracle_calibration | 2% (1/60) [0, 9] | 9.42 / 9.42 | 0 | 26.9 | 1.63 | -0.13 |
| oracle_timing | 2% (1/60) [0, 9] | 5.63 / 5.44 | 0 | 5.5 | 0.64 | -0.06 |
| oracle_all | 0% (0/60) [0, 6] | 4.73 / 4.70 | 0 | 5.8 | 0.38 | -0.08 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +3.3 [-5.0, +11.7] | +0.12 [+0.05, +0.18] | -0.00 [-0.00, -0.00] |
| calibration | -1.7 [-8.3, +3.3] | -0.04 [-0.16, +0.07] | -0.01 [-0.01, -0.00] |
| timing | -1.7 [-6.7, +3.3] | +3.75 [+3.58, +3.91] | +0.07 [+0.06, +0.08] |

Chosen on dev: style_feasibility -> safe_path_v2 (argmax success budget over components with an unused fix ['perception'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 2% (1/60) [0, 9] | 9.32 / 9.36 | 0 | -0.13 |
| full+safe_path_v2 | 2% (1/60) [0, 9] | 10.02 / 9.94 | 0 | -0.12 |
| full+speed_cap_2 | 0% (0/60) [0, 6] | 7.25 / 7.10 | 0 | -0.10 |
| raw | 0% (0/60) [0, 6] | 15.20 / 15.21 | 0 | -0.16 |

Paired success gap (corrected - full): +0.0 pp, 95% CI [+0.0, +0.0], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): -0.70 cm, 95% CI [-0.86, -0.53].
Nemotron agent chose `speed_cap_2` (rule chose `safe_path_v2`): agent - full -1.7 pp [-5.0, +0.0]; agent - rule -1.7 pp [-5.0, +0.0].
Cumulative (all adopted fixes + this one, vs no fix): +1.7 pp, 95% CI [+0.0, +5.0], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
