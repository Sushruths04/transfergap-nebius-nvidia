# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo44864be9` (file), after adopting speed_cap_3 + speed_cap_2

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 6.17 / 5.99 | 0 | 5.9 | 0.42 | -0.04 |
| oracle_perception | 0% (0/60) [0, 6] | 5.81 / 5.65 | 0 | 6.1 | 0.33 | -0.03 |
| oracle_calibration | 0% (0/60) [0, 6] | 5.65 / 5.51 | 0 | 6.1 | 0.36 | -0.05 |
| oracle_timing | 0% (0/60) [0, 6] | 5.35 / 5.08 | 0 | 2.7 | 0.48 | 0.10 |
| oracle_all | 0% (0/60) [0, 6] | 4.41 / 4.49 | 0 | 2.7 | 0.31 | 0.08 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +0.0 [+0.0, +0.0] | +0.37 [+0.25, +0.49] | +0.00 [-0.01, +0.02] |
| calibration | +0.0 [+0.0, +0.0] | +0.52 [+0.33, +0.73] | -0.02 [-0.03, -0.01] |
| timing | +0.0 [+0.0, +0.0] | +0.82 [+0.72, +0.92] | +0.14 [+0.12, +0.15] |

Chosen on dev: style_feasibility -> safe_path_v2 (argmax success budget over components with an unused fix [] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 6.04 / 5.97 | 0 | -0.05 |
| full+safe_path_v2 | 2% (1/60) [0, 9] | 6.93 / 6.81 | 0 | -0.04 |
| full+safe_path | 0% (0/60) [0, 6] | 5.76 / 5.73 | 0 | -0.04 |
| raw | 0% (0/60) [0, 6] | 10.70 / 10.70 | 0 | -0.14 |

Paired success gap (corrected - full): +1.7 pp, 95% CI [+0.0, +5.0], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): -0.89 cm, 95% CI [-1.05, -0.71].
Nemotron agent chose `safe_path` (rule chose `safe_path_v2`): agent - full +0.0 pp [+0.0, +0.0]; agent - rule -1.7 pp [-5.0, +0.0].
Cumulative (all adopted fixes + this one, vs no fix): +1.7 pp, 95% CI [+0.0, +5.0], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
