# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo1bc4be60` (file), after adopting speed_cap_3 + look_again + touch_probe_calibration

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 90% (54/60) [80, 95] | 7.08 / 7.10 | 0 | 7.2 | 1.97 | -0.18 |
| oracle_perception | 88% (53/60) [78, 94] | 7.06 / 7.08 | 0 | 7.2 | 1.98 | -0.18 |
| oracle_calibration | 98% (59/60) [91, 100] | 7.08 / 7.06 | 0 | 7.2 | 1.97 | -0.18 |
| oracle_timing | 97% (58/60) [89, 99] | 2.66 / 2.64 | 0 | 5.2 | 0.37 | 0.01 |
| oracle_all | 100% (60/60) [94, 100] | 2.59 / 2.59 | 0 | 5.2 | 0.37 | 0.01 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | -1.7 [-11.7, +8.3] | +0.02 [-0.00, +0.04] | -0.00 [-0.00, +0.00] |
| calibration | +8.3 [+1.7, +16.7] | +0.00 [-0.00, +0.01] | +0.00 [-0.00, +0.00] |
| timing | +6.7 [+0.0, +15.0] | +4.42 [+4.39, +4.45] | +0.19 [+0.19, +0.19] |

Chosen on dev: timing -> speed_cap_2 (argmax success budget over components with an unused fix ['timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 83% (50/60) [72, 91] | 7.10 / 7.08 | 0 | -0.18 |
| full+speed_cap_2 | 95% (57/60) [86, 98] | 4.96 / 4.95 | 0 | -0.10 |
| raw | 0% (0/60) [0, 6] | 13.94 / 13.93 | 0 | -0.21 |

Paired success gap (corrected - full): +11.7 pp, 95% CI [+5.0, +20.0], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +2.14 cm, 95% CI [+2.12, +2.15].
Cumulative (all adopted fixes + this one, vs no fix): +95.0 pp, 95% CI [+88.3, +100.0], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
