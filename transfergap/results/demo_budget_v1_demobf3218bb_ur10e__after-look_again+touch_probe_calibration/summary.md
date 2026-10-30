# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demobf3218bb` (file), after adopting look_again + touch_probe_calibration

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 78% (47/60) [66, 87] | 1.68 / 1.53 | 0 | 107.9 | 0.22 | -0.10 |
| oracle_perception | 100% (60/60) [94, 100] | 1.47 / 1.46 | 0 | 110.1 | 0.10 | -0.10 |
| oracle_calibration | 80% (48/60) [68, 88] | 1.63 / 1.47 | 0 | 108.2 | 0.21 | -0.10 |
| oracle_timing | 63% (38/60) [51, 74] | 2.50 / 1.16 | 0 | 47.5 | 0.27 | -0.09 |
| oracle_all | 100% (60/60) [94, 100] | 0.65 / 0.65 | 0 | 18.7 | 0.06 | -0.09 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +21.7 [+11.7, +31.7] | +0.21 [+0.08, +0.38] | +0.00 [-0.00, +0.00] |
| calibration | +1.7 [-3.3, +6.7] | +0.06 [+0.02, +0.10] | +0.00 [-0.00, +0.00] |
| timing | -15.0 [-28.3, +0.0] | -0.82 [-1.34, -0.33] | +0.01 [+0.01, +0.01] |

Chosen on dev: none -> None (argmax success budget over components with an unused fix [] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
