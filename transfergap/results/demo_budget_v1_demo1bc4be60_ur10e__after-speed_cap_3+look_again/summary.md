# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo1bc4be60` (file), after adopting speed_cap_3 + look_again

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 45% (27/60) [33, 58] | 4.35 / 4.29 | 0 | 8.6 | 0.44 | -0.09 |
| oracle_perception | 50% (30/60) [38, 62] | 4.30 / 4.23 | 0 | 8.6 | 0.45 | -0.09 |
| oracle_calibration | 92% (55/60) [82, 96] | 3.94 / 3.91 | 0 | 8.6 | 0.44 | -0.09 |
| oracle_timing | 50% (30/60) [38, 62] | 2.32 / 2.25 | 0 | 2.7 | 0.17 | 0.46 |
| oracle_all | 100% (60/60) [94, 100] | 1.48 / 1.48 | 0 | 2.7 | 0.17 | 0.47 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +5.0 [+0.0, +11.7] | +0.05 [+0.02, +0.07] | -0.00 [-0.00, +0.00] |
| calibration | +46.7 [+33.3, +60.0] | +0.40 [+0.31, +0.52] | -0.00 [-0.00, -0.00] |
| timing | +5.0 [-5.0, +15.0] | +2.03 [+1.95, +2.10] | +0.55 [+0.55, +0.55] |

Chosen on dev: calibration -> touch_probe_calibration (argmax success budget over components with an unused fix ['calibration', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 58% (35/60) [46, 70] | 4.20 / 4.13 | 0 | -0.09 |
| full+touch_probe_calibration | 85% (51/60) [74, 92] | 3.96 / 3.95 | 0 | -0.09 |
| raw | 0% (0/60) [0, 6] | 9.15 / 9.08 | 0 | -0.20 |

Paired success gap (corrected - full): +26.7 pp, 95% CI [+11.7, +41.7], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.24 cm, 95% CI [+0.17, +0.32].
Cumulative (all adopted fixes + this one, vs no fix): +85.0 pp, 95% CI [+76.7, +93.3], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
