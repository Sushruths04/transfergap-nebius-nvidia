# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demobf3218bb` (file), after adopting look_again

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 78% (47/60) [66, 87] | 3.46 / 3.39 | 0 | 112.2 | 0.23 | -0.12 |
| oracle_perception | 80% (48/60) [68, 88] | 3.43 / 3.39 | 0 | 111.9 | 0.24 | -0.12 |
| oracle_calibration | 97% (58/60) [89, 99] | 2.94 / 2.94 | 0 | 112.3 | 0.15 | -0.12 |
| oracle_timing | 73% (44/60) [61, 83] | 2.63 / 2.28 | 0 | 91.2 | 0.30 | -0.11 |
| oracle_all | 100% (60/60) [94, 100] | 1.26 / 1.25 | 0 | 95.2 | 0.10 | -0.11 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +1.7 [-5.0, +8.3] | +0.03 [+0.01, +0.06] | +0.00 [-0.00, +0.00] |
| calibration | +18.3 [+10.0, +28.3] | +0.52 [+0.42, +0.64] | +0.00 [+0.00, +0.00] |
| timing | -5.0 [-15.0, +5.0] | +0.83 [+0.55, +1.08] | +0.00 [+0.00, +0.01] |

Chosen on dev: calibration -> touch_probe_calibration (argmax success budget over components with an unused fix ['calibration'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 87% (52/60) [76, 93] | 3.33 / 3.29 | 0 | -0.12 |
| full+touch_probe_calibration | 95% (57/60) [86, 98] | 2.99 / 2.99 | 0 | -0.12 |
| raw | 58% (35/60) [46, 70] | 3.57 / 3.47 | 0 | -0.12 |

Paired success gap (corrected - full): +8.3 pp, 95% CI [-1.7, +18.3], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): +0.34 cm, 95% CI [+0.25, +0.43].
Cumulative (all adopted fixes + this one, vs no fix): +36.7 pp, 95% CI [+25.0, +48.3], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
