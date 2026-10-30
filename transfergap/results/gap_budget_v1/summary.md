# Gap budget v1 (arm), preliminary

Commit: `f8dd798a564f1d1d039d9f511626818df4d60d8d`. All error magnitudes are ASSUMPTIONS.

## Dev seeds 0-59: success, Wilson 95% [%]

| condition | oracle | success | failure reasons (counts) |
|---|---|---|---|
| full | none | 57% (34/60) [44, 68] | not_released_and_settled_at_goal:26, no_lift:20 |
| oracle_perception | perception | 68% (41/60) [56, 79] | not_released_and_settled_at_goal:19, no_lift:13 |
| oracle_calibration | calibration | 68% (41/60) [56, 79] | not_released_and_settled_at_goal:19, no_lift:13 |
| oracle_timing | timing | 68% (41/60) [56, 79] | not_released_and_settled_at_goal:19, no_lift:16 |
| oracle_all | all | 100% (60/60) [94, 100] | - |

## Budget per component (success(oracle_k) - success(full), pp, paired bootstrap 95% CI)

| component | recovery pp | 95% CI |
|---|---|---|
| perception | +11.7 | [+0.0, +23.3] |
| calibration | +11.7 | [+3.3, +21.7] |
| timing | +11.7 | [+1.7, +21.7] |
| oracle_all | +43.3 | [+30.0, +55.0] |

Interaction: sum of single recoveries = +35.0 pp; oracle_all recovery = +43.3 pp.

## Correction (chosen on dev by code: perception -> look_again)

| held-out condition (seeds 1000-1059) | success | failure reasons |
|---|---|---|
| full | 53% (32/60) [41, 65] | not_released_and_settled_at_goal:28, no_lift:22 |
| full+look_again | 75% (45/60) [63, 84] | not_released_and_settled_at_goal:15, no_lift:10 |

Held-out paired gap (corrected - full): +21.7 pp, 95% CI [+10.0, +33.3], n=60; CI excludes zero: True.
