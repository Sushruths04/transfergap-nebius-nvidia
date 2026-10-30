# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo7c1fa3bd` (file), after adopting look_again

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 90% (54/60) [80, 95] | 4.16 / 4.11 | 0 | 9.3 | 1.19 | -0.00 |
| oracle_perception | 95% (57/60) [86, 98] | 4.13 / 4.08 | 0 | 9.4 | 1.20 | -0.01 |
| oracle_calibration | 100% (60/60) [94, 100] | 3.67 / 3.67 | 0 | 9.2 | 1.09 | -0.01 |
| oracle_timing | 90% (54/60) [80, 95] | 2.53 / 2.49 | 0 | 1.6 | 0.70 | 0.11 |
| oracle_all | 100% (60/60) [94, 100] | 1.75 / 1.75 | 0 | 1.3 | 0.59 | 0.15 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +5.0 [+0.0, +11.7] | +0.02 [+0.00, +0.05] | -0.00 [-0.00, -0.00] |
| calibration | +10.0 [+3.3, +18.3] | +0.49 [+0.39, +0.60] | -0.00 [-0.01, +0.00] |
| timing | +0.0 [-5.0, +5.0] | +1.63 [+1.57, +1.68] | +0.12 [+0.10, +0.14] |

Chosen on dev: calibration -> touch_probe_calibration (argmax success budget over components with an unused fix ['calibration'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 92% (55/60) [82, 96] | 4.05 / 3.98 | 0 | -0.00 |
| full+touch_probe_calibration | 100% (60/60) [94, 100] | 3.73 / 3.71 | 0 | -0.01 |
| raw | 52% (31/60) [39, 64] | 4.26 / 4.19 | 0 | -0.01 |

Paired success gap (corrected - full): +8.3 pp, 95% CI [+1.7, +15.0], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.32 cm, 95% CI [+0.24, +0.40].
Cumulative (all adopted fixes + this one, vs no fix): +48.3 pp, 95% CI [+35.0, +61.7], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
