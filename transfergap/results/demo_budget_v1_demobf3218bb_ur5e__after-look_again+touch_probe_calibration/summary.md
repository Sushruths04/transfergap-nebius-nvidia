# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demobf3218bb` (file), after adopting look_again + touch_probe_calibration

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 98% (59/60) [91, 100] | 2.96 / 2.96 | 0 | 112.3 | 0.16 | -0.12 |
| oracle_perception | 100% (60/60) [94, 100] | 2.94 / 2.93 | 0 | 112.3 | 0.16 | -0.12 |
| oracle_calibration | 97% (58/60) [89, 99] | 2.94 / 2.94 | 0 | 112.3 | 0.15 | -0.12 |
| oracle_timing | 88% (53/60) [78, 94] | 1.80 / 1.45 | 0 | 91.2 | 0.22 | -0.11 |
| oracle_all | 100% (60/60) [94, 100] | 1.26 / 1.25 | 0 | 95.2 | 0.10 | -0.11 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +1.7 [+0.0, +5.0] | +0.03 [-0.00, +0.05] | +0.00 [-0.00, +0.00] |
| calibration | -1.7 [-6.7, +3.3] | +0.03 [+0.02, +0.04] | +0.00 [+0.00, +0.00] |
| timing | -10.0 [-18.3, -3.3] | +1.16 [+0.90, +1.38] | +0.01 [+0.00, +0.01] |

Chosen on dev: none -> None (argmax success budget over components with an unused fix [] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
