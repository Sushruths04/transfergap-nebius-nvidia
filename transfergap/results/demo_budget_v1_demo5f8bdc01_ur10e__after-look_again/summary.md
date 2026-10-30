# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo5f8bdc01` (file), after adopting look_again

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 25% (15/60) [16, 37] | 8.27 / 8.15 | 0 | 113.9 | 0.54 | 0.06 |
| oracle_perception | 40% (24/60) [29, 53] | 8.22 / 8.08 | 0 | 114.0 | 0.54 | 0.06 |
| oracle_calibration | 38% (23/60) [27, 51] | 7.94 / 7.90 | 0 | 112.2 | 0.50 | 0.06 |
| oracle_timing | 17% (10/60) [9, 28] | 5.86 / 5.70 | 0 | 97.7 | 0.20 | 0.20 |
| oracle_all | 0% (0/60) [0, 6] | 5.42 / 5.42 | 0 | 96.5 | 0.16 | 0.21 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +15.0 [+3.3, +26.7] | +0.05 [+0.00, +0.10] | +0.00 [-0.00, +0.00] |
| calibration | +13.3 [-1.7, +26.7] | +0.33 [+0.22, +0.45] | +0.00 [+0.00, +0.00] |
| timing | -8.3 [-21.7, +3.3] | +2.41 [+2.38, +2.44] | +0.14 [+0.13, +0.14] |

Chosen on dev: calibration -> touch_probe_calibration (argmax success budget over components with an unused fix ['calibration', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 28% (17/60) [19, 41] | 8.20 / 8.10 | 0 | 0.06 |
| full+touch_probe_calibration | 23% (14/60) [14, 35] | 8.00 / 7.98 | 0 | 0.06 |
| raw | 7% (4/60) [3, 16] | 8.35 / 8.30 | 0 | 0.06 |

Paired success gap (corrected - full): -5.0 pp, 95% CI [-20.0, +10.0], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): +0.20 cm, 95% CI [+0.11, +0.30].
Cumulative (all adopted fixes + this one, vs no fix): +16.7 pp, 95% CI [+5.0, +28.3], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
