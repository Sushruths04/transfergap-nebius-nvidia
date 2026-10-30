# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo7c1fa3bd` (file), after adopting look_again

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 88% (53/60) [78, 94] | 2.69 / 2.66 | 0 | 1.6 | 0.61 | 0.29 |
| oracle_perception | 93% (56/60) [84, 97] | 2.65 / 2.59 | 0 | 1.5 | 0.58 | 0.29 |
| oracle_calibration | 100% (60/60) [94, 100] | 2.01 / 1.99 | 0 | 1.4 | 0.53 | 0.30 |
| oracle_timing | 92% (55/60) [82, 96] | 1.98 / 1.94 | 0 | 1.3 | 0.35 | 0.35 |
| oracle_all | 100% (60/60) [94, 100] | 0.96 / 0.97 | 0 | 1.3 | 0.30 | 0.42 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +5.0 [-3.3, +13.3] | +0.05 [+0.02, +0.07] | +0.01 [-0.00, +0.02] |
| calibration | +11.7 [+3.3, +20.0] | +0.69 [+0.55, +0.84] | +0.01 [-0.00, +0.03] |
| timing | +3.3 [+0.0, +8.3] | +0.71 [+0.67, +0.75] | +0.07 [+0.04, +0.09] |

Chosen on dev: calibration -> touch_probe_calibration (argmax success budget over components with an unused fix ['calibration'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 95% (57/60) [86, 98] | 2.52 / 2.45 | 0 | 0.30 |
| full+touch_probe_calibration | 100% (60/60) [94, 100] | 2.08 / 2.08 | 0 | 0.30 |
| raw | 57% (34/60) [44, 68] | 2.87 / 2.75 | 0 | 0.26 |

Paired success gap (corrected - full): +5.0 pp, 95% CI [+0.0, +11.7], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): +0.45 cm, 95% CI [+0.34, +0.56].
Cumulative (all adopted fixes + this one, vs no fix): +43.3 pp, 95% CI [+31.7, +56.7], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
