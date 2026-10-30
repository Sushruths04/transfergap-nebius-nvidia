# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo5f8bdc01` (file), after adopting look_again + touch_probe_calibration

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 50% (30/60) [38, 62] | 7.96 / 7.93 | 0 | 112.8 | 0.50 | 0.06 |
| oracle_perception | 57% (34/60) [44, 68] | 7.92 / 7.91 | 0 | 112.7 | 0.50 | 0.06 |
| oracle_calibration | 38% (23/60) [27, 51] | 7.94 / 7.90 | 0 | 112.2 | 0.50 | 0.06 |
| oracle_timing | 15% (9/60) [8, 26] | 5.49 / 5.48 | 0 | 95.6 | 0.16 | 0.21 |
| oracle_all | 0% (0/60) [0, 6] | 5.42 / 5.42 | 0 | 96.5 | 0.16 | 0.21 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +6.7 [-10.0, +23.3] | +0.04 [-0.01, +0.09] | -0.00 [-0.00, +0.00] |
| calibration | -11.7 [-25.0, +3.3] | +0.02 [+0.00, +0.04] | +0.00 [-0.00, +0.00] |
| timing | -35.0 [-50.0, -18.3] | +2.47 [+2.45, +2.50] | +0.15 [+0.14, +0.15] |

Chosen on dev: style_feasibility -> safe_path (argmax success budget over components with an unused fix ['timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 23% (14/60) [14, 35] | 8.00 / 7.98 | 0 | 0.06 |
| full+safe_path | 0% (0/60) [0, 6] | 8.23 / 8.23 | 0 | 0.24 |
| full+speed_cap_3 | 23% (14/60) [14, 35] | 8.00 / 7.98 | 0 | 0.06 |
| raw | 7% (4/60) [3, 16] | 8.35 / 8.30 | 0 | 0.06 |

Paired success gap (corrected - full): -23.3 pp, 95% CI [-33.3, -13.3], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): -0.24 cm, 95% CI [-0.27, -0.20].
Nemotron agent chose `speed_cap_3` (rule chose `safe_path`): agent - full +0.0 pp [+0.0, +0.0]; agent - rule +23.3 pp [+13.3, +33.3].
Cumulative (all adopted fixes + this one, vs no fix): -6.7 pp, 95% CI [-13.3, -1.7], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
