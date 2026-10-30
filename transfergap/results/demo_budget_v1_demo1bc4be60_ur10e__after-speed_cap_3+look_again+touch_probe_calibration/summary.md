# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo1bc4be60` (file), after adopting speed_cap_3 + look_again + touch_probe_calibration

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 90% (54/60) [80, 95] | 3.95 / 3.92 | 0 | 8.6 | 0.44 | -0.09 |
| oracle_perception | 100% (60/60) [94, 100] | 3.91 / 3.91 | 0 | 8.6 | 0.45 | -0.09 |
| oracle_calibration | 92% (55/60) [82, 96] | 3.94 / 3.91 | 0 | 8.6 | 0.44 | -0.09 |
| oracle_timing | 100% (60/60) [94, 100] | 1.60 / 1.57 | 0 | 2.7 | 0.15 | 0.46 |
| oracle_all | 100% (60/60) [94, 100] | 1.48 / 1.48 | 0 | 2.7 | 0.17 | 0.47 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +10.0 [+3.3, +18.3] | +0.04 [+0.02, +0.06] | -0.00 [-0.00, +0.00] |
| calibration | +1.7 [-5.0, +8.3] | +0.01 [+0.00, +0.02] | -0.00 [-0.00, +0.00] |
| timing | +10.0 [+3.3, +18.3] | +2.35 [+2.33, +2.37] | +0.56 [+0.55, +0.56] |

Chosen on dev: timing -> speed_cap_2 (argmax success budget over components with an unused fix ['timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 85% (51/60) [74, 92] | 3.96 / 3.95 | 0 | -0.09 |
| full+speed_cap_2 | 100% (60/60) [94, 100] | 2.86 / 2.85 | 0 | 0.04 |
| raw | 0% (0/60) [0, 6] | 9.15 / 9.08 | 0 | -0.20 |

Paired success gap (corrected - full): +15.0 pp, 95% CI [+6.7, +23.3], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +1.10 cm, 95% CI [+1.09, +1.11].
Cumulative (all adopted fixes + this one, vs no fix): +100.0 pp, 95% CI [+100.0, +100.0], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
