# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo5f8bdc01` (file), after adopting look_again + touch_probe_calibration

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 97% (58/60) [89, 99] | 11.47 / 11.46 | 0 | 108.0 | 1.58 | 0.02 |
| oracle_perception | 100% (60/60) [94, 100] | 11.45 / 11.45 | 0 | 107.8 | 1.58 | 0.02 |
| oracle_calibration | 97% (58/60) [89, 99] | 11.47 / 11.48 | 0 | 107.6 | 1.54 | 0.02 |
| oracle_timing | 77% (46/60) [65, 86] | 7.41 / 7.37 | 0 | 98.4 | 0.55 | 0.12 |
| oracle_all | 100% (60/60) [94, 100] | 7.35 / 7.36 | 0 | 98.6 | 0.54 | 0.12 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +3.3 [+0.0, +8.3] | +0.01 [-0.02, +0.05] | -0.00 [-0.00, +0.00] |
| calibration | +0.0 [-6.7, +6.7] | -0.00 [-0.02, +0.02] | -0.00 [-0.00, -0.00] |
| timing | -20.0 [-31.7, -8.3] | +4.06 [+4.04, +4.08] | +0.10 [+0.10, +0.10] |

Chosen on dev: timing -> speed_cap_3 (argmax success budget over components with an unused fix ['timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 95% (57/60) [86, 98] | 11.47 / 11.47 | 0 | 0.02 |
| full+speed_cap_3 | 95% (57/60) [86, 98] | 11.47 / 11.47 | 0 | 0.02 |
| full+safe_path | 0% (0/60) [0, 6] | 11.66 / 11.65 | 0 | 0.08 |
| raw | 18% (11/60) [11, 30] | 11.76 / 11.69 | 0 | 0.02 |

Paired success gap (corrected - full): +0.0 pp, 95% CI [+0.0, +0.0], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): +0.00 cm, 95% CI [+0.00, +0.00].
Nemotron agent chose `safe_path` (rule chose `speed_cap_3`): agent - full -95.0 pp [-100.0, -90.0]; agent - rule -95.0 pp [-100.0, -90.0].
Cumulative (all adopted fixes + this one, vs no fix): +76.7 pp, 95% CI [+66.7, +86.7], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
