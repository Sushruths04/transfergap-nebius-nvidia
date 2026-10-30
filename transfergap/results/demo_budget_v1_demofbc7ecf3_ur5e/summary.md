# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demofbc7ecf3` (file)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 2% (1/60) [0, 9] | 13.49 / 12.69 | 0 | 24.3 | 9.87 | -0.04 |
| oracle_perception | 23% (14/60) [14, 35] | 13.63 / 12.83 | 0 | 26.1 | 10.65 | -0.04 |
| oracle_calibration | 13% (8/60) [7, 24] | 13.38 / 12.49 | 0 | 22.1 | 9.26 | -0.04 |
| oracle_timing | 8% (5/60) [4, 18] | 6.70 / 6.69 | 0 | 5.0 | 0.54 | 0.73 |
| oracle_all | 2% (1/60) [0, 9] | 6.33 / 6.30 | 0 | 5.1 | 0.54 | 0.73 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +21.7 [+10.0, +33.3] | -0.14 [-0.63, +0.36] | +0.00 [-0.00, +0.01] |
| calibration | +11.7 [+3.3, +21.7] | +0.11 [-0.32, +0.55] | +0.00 [-0.00, +0.01] |
| timing | +6.7 [+0.0, +15.0] | +6.79 [+6.46, +7.13] | +0.77 [+0.76, +0.79] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'calibration', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
