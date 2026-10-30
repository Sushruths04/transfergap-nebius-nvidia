# Demo-driven gap budget (demo_budget_v1), ur5e_2f85_fixed, demo `demo44864be9` (file), after adopting safe_path_v2 + speed_cap_3 + speed_cap_2

Success: Wilson 95%. Style vs the clean retargeted human path: path RMSE (cm, lower = closer to the human), approach-angle error (deg), lift-height error (cm), speed-profile correlation (1 = same profile).

## Dev seeds 0-59

| condition | success | path RMSE cm mean / median | diverged | approach ° | lift err cm | speed corr |
|---|---|---|---|---|---|---|
| full | 7% (4/60) [3, 16] | 8.45 / 8.44 | 0 | 15.2 | 0.91 | -0.10 |
| oracle_perception | 18% (11/60) [11, 30] | 8.28 / 8.19 | 0 | 15.3 | 0.78 | -0.10 |
| oracle_calibration | 0% (0/60) [0, 6] | 8.24 / 8.23 | 0 | 15.3 | 0.80 | -0.10 |
| oracle_timing | 10% (6/60) [5, 20] | 6.80 / 6.70 | 0 | 5.5 | 0.64 | -0.04 |
| oracle_all | 0% (0/60) [0, 6] | 6.17 / 6.16 | 0 | 5.8 | 0.38 | -0.05 |

| component | success recovery pp [95% CI] | path RMSE reduction cm [95% CI] | speed-corr gain [95% CI] |
|---|---|---|---|
| perception | +11.7 [+5.0, +20.0] | +0.17 [+0.12, +0.23] | +0.00 [+0.00, +0.00] |
| calibration | -6.7 [-13.3, -1.7] | +0.22 [+0.11, +0.34] | -0.00 [-0.00, +0.00] |
| timing | +3.3 [-5.0, +11.7] | +1.65 [+1.59, +1.70] | +0.06 [+0.05, +0.07] |

Chosen on dev: perception -> look_again (argmax success budget over components with an unused fix ['perception', 'timing'] on dev; ties -> pipeline order; timing fixes climb ['speed_cap_3', 'speed_cap_2', 'speed_cap_1.5']).

## Held-out seeds 1000-1059

| condition | success | path RMSE cm mean / median | diverged | speed corr |
|---|---|---|---|---|
| full | 3% (2/60) [1, 11] | 8.43 / 8.32 | 0 | -0.10 |
| full+look_again | 2% (1/60) [0, 9] | 8.27 / 8.20 | 0 | -0.10 |
| raw | 0% (0/60) [0, 6] | 15.20 / 15.21 | 0 | -0.16 |

Paired success gap (corrected - full): -1.7 pp, 95% CI [-5.0, +0.0], n=60; CI excludes zero: False.
Path RMSE change (full - corrected): +0.16 cm, 95% CI [+0.12, +0.21].
Cumulative (all adopted fixes + this one, vs no fix): +1.7 pp, 95% CI [+0.0, +5.0], n=60.

Caveats: perception and calibration magnitudes are ASSUMPTIONS (as gap_budget_v2); the hand-estimation noise is an ASSUMPTION; scripted IK controller in MuJoCo; style is measured on the tool pinch point only (no wrist orientation).
