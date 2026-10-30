# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo44864be9` (file), after adopting speed_cap_3 + speed_cap_2

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 3% (2/60) [1, 11] | 7.47 / 7.23 | 0 | 15.2 | 0.91 | -0.10 |
| oracle_perception | 2% (1/60) [0, 9] | 7.30 / 7.10 | 0 | 15.3 | 0.78 | -0.10 |
| oracle_calibration | 0% (0/60) [0, 6] | 6.87 / 6.81 | 0 | 15.3 | 0.80 | -0.10 |
| oracle_timing | 2% (1/60) [0, 9] | 5.63 / 5.44 | 0 | 5.5 | 0.64 | -0.06 |
| oracle_all | 0% (0/60) [0, 6] | 4.73 / 4.70 | 0 | 5.8 | 0.38 | -0.08 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | -1.7 [-5.0, +0.0] | +0.17 [+0.10, +0.24] | -0.00 [-0.00, +0.00] |
| calibration | -3.3 [-8.3, +0.0] | +0.60 [+0.42, +0.78] | -0.00 [-0.00, -0.00] |
| timing | -1.7 [-5.0, +0.0] | +1.84 [+1.71, +1.96] | +0.04 [+0.03, +0.05] |

Chosen on dev: style_feasibility -> safe_path_v2 (argmax success budget over components with an unused fix [] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 0% (0/60) [0, 6] | 7.25 / 7.10 | 0 | -0.10 |
| full+safe_path_v2 | 3% (2/60) [1, 11] | 8.43 / 8.32 | 0 | -0.10 |
| full+speed_cap_1.5 | 0% (0/60) [0, 6] | 6.26 / 6.15 | 0 | -0.10 |
| raw | 0% (0/60) [0, 6] | 15.20 / 15.21 | 0 | -0.16 |

Paired success gap (corrected - full): +3.3 pp, 95% CI [+0.0, +8.3], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): -1.18 cm, 95% CI [-1.35, -0.99].
Nemotron agent chose `speed_cap_1.5` (rule chose `safe_path_v2`): agent - full +0.0 pp [+0.0, +0.0]; agent - rule -3.3 pp [-8.3, +0.0].
Cumulative (all adopted fixes + this one, vs no fix): +3.3 pp, 95% CI [+0.0, +8.3], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
