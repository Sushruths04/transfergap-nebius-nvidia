# Demo-driven gap budget (demo_budget_v1), ur10e_2f85_fixed, demo `demofbc7ecf3` (file)

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 20% (12/60) [12, 32] | 8.02 / 7.94 | 0 | 5.0 | 0.57 | 0.07 |
| oracle_perception | 38% (23/60) [27, 51] | 7.93 / 7.82 | 0 | 5.0 | 0.58 | 0.07 |
| oracle_calibration | 25% (15/60) [16, 37] | 7.82 / 7.80 | 0 | 5.0 | 0.56 | 0.07 |
| oracle_timing | 7% (4/60) [3, 16] | 4.05 / 3.90 | 0 | 4.2 | 0.13 | 0.91 |
| oracle_all | 0% (0/60) [0, 6] | 3.43 / 3.43 | 0 | 4.3 | 0.09 | 0.91 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +18.3 [+3.3, +33.3] | +0.09 [+0.05, +0.13] | +0.00 [-0.00, +0.00] |
| calibration | +5.0 [-10.0, +18.3] | +0.20 [+0.13, +0.28] | -0.00 [-0.00, +0.00] |
| timing | -13.3 [-26.7, -1.7] | +3.98 [+3.91, +4.03] | +0.83 [+0.83, +0.84] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'calibration', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
