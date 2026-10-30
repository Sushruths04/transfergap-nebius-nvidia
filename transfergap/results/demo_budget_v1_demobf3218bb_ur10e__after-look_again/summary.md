# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demobf3218bb` (file), after adopting look_again

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 52% (31/60) [39, 64] | 2.34 / 2.23 | 0 | 109.1 | 0.20 | -0.10 |
| oracle_perception | 78% (47/60) [66, 87] | 2.22 / 2.19 | 0 | 110.2 | 0.13 | -0.10 |
| oracle_calibration | 80% (48/60) [68, 88] | 1.63 / 1.47 | 0 | 108.2 | 0.21 | -0.10 |
| oracle_timing | 52% (31/60) [39, 64] | 3.44 / 2.64 | 0 | 53.2 | 0.32 | -0.09 |
| oracle_all | 100% (60/60) [94, 100] | 0.65 / 0.65 | 0 | 18.7 | 0.06 | -0.09 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +26.7 [+16.7, +38.3] | +0.12 [+0.05, +0.19] | +0.00 [-0.00, +0.00] |
| calibration | +28.3 [+16.7, +40.0] | +0.71 [+0.54, +0.89] | +0.00 [+0.00, +0.00] |
| timing | +0.0 [-13.3, +13.3] | -1.11 [-1.70, -0.57] | +0.01 [+0.01, +0.01] |

Chosen on dev: calibration -> touch_probe_calibration (argmax success budget over components with an unused fix ['calibration'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 65% (39/60) [52, 76] | 2.18 / 2.00 | 0 | -0.10 |
| full+touch_probe_calibration | 85% (51/60) [74, 92] | 1.57 / 1.56 | 0 | -0.10 |
| raw | 50% (30/60) [38, 62] | 2.48 / 2.39 | 0 | -0.10 |

Paired success gap (corrected - full): +20.0 pp, 95% CI [+8.3, +31.7], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.61 cm, 95% CI [+0.44, +0.79].
Cumulative (all adopted fixes + this one, vs no fix): +35.0 pp, 95% CI [+23.3, +46.7], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
