# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demo7c1fa3bd` (file)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 68% (41/60) [56, 79] | 2.99 / 2.95 | 0 | 1.9 | 0.68 | 0.27 |
| oracle_perception | 93% (56/60) [84, 97] | 2.65 / 2.59 | 0 | 1.5 | 0.58 | 0.29 |
| oracle_calibration | 78% (47/60) [66, 87] | 2.35 / 2.26 | 0 | 1.5 | 0.62 | 0.28 |
| oracle_timing | 67% (40/60) [54, 77] | 2.36 / 2.37 | 0 | 1.9 | 0.44 | 0.33 |
| oracle_all | 100% (60/60) [94, 100] | 0.96 / 0.97 | 0 | 1.3 | 0.30 | 0.42 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +25.0 [+11.7, +38.3] | +0.34 [+0.24, +0.45] | +0.03 [+0.01, +0.05] |
| calibration | +10.0 [+0.0, +20.0] | +0.64 [+0.51, +0.80] | +0.01 [-0.01, +0.03] |
| timing | -1.7 [-5.0, +0.0] | +0.62 [+0.58, +0.66] | +0.06 [+0.03, +0.09] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'calibration'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 57% (34/60) [44, 68] | 2.87 / 2.75 | 0 | 0.26 |
| full+look_again | 95% (57/60) [86, 98] | 2.52 / 2.45 | 0 | 0.30 |

Paired success gap (corrected - full): +38.3 pp, 95% CI [+25.0, +51.7], n=60; CI excludes zero: True.
Path RMSE change (full - corrected): +0.35 cm, 95% CI [+0.25, +0.45].

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
