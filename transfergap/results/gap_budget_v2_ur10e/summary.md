# Gap budget v2 (arm: ur10e_2f85_fixed), preliminary

Commit: `0bba41eb5a1d44e765779a142cc968b56e5ce473`. Protocol frozen at `18865d2541c785d90a4f719c9eb36e236997cd8b`. All error magnitudes are ASSUMPTIONS.

## Dev seeds 0-59: success, Wilson 95% [%]

| condition | oracle | success | failure reasons (counts) |
|---|---|---|---|
| full | none | 50% (30/60) [38, 62] | not_released_and_settled_at_goal:29, no_lift:21, forbidden_collision:1 |
| oracle_perception | perception | 73% (44/60) [61, 83] | no_lift:11, not_released_and_settled_at_goal:16 |
| oracle_retargeting | retargeting | 55% (33/60) [42, 67] | no_lift:25, not_released_and_settled_at_goal:26, forbidden_collision:1 |
| oracle_calibration | calibration | 68% (41/60) [56, 79] | not_released_and_settled_at_goal:19, no_lift:14 |
| oracle_timing | timing | 62% (37/60) [49, 73] | not_released_and_settled_at_goal:23, no_lift:19 |
| oracle_all | all | 100% (60/60) [94, 100] | - |

## Budget per component (success(oracle_k) - success(full), pp, paired bootstrap 95% CI)

| component | recovery pp | 95% CI |
|---|---|---|
| perception | +23.3 | [+10.0, +36.7] |
| retargeting | +5.0 | [-6.7, +16.7] |
| calibration | +18.3 | [+8.3, +28.3] |
| timing | +11.7 | [+5.0, +20.0] |
| oracle_all | +50.0 | [+36.7, +63.3] |

Interaction: sum of single recoveries = +58.3 pp; oracle_all recovery = +50.0 pp.

Retargeting error (ASSUMPTION, joint sigma 0.50 deg) moves the tool point at the grasp pose by median 0.70 cm, p90 1.45 cm, max 1.91 cm on this robot (kinematics only).

## Correction (chosen on dev by code: perception -> look_again)

| held-out condition (seeds 1000-1059) | success | failure reasons |
|---|---|---|
| full | 55% (33/60) [42, 67] | not_released_and_settled_at_goal:27, no_lift:23 |
| full+look_again | 77% (46/60) [65, 86] | not_released_and_settled_at_goal:13, no_lift:8, forbidden_collision:1 |

Held-out paired gap (corrected - full): +21.7 pp, 95% CI [+10.0, +33.3], n=60; CI excludes zero: True.

## Caveats

- all error magnitudes are assumptions, not measured
- scripted IK controller, not a learned policy; no human demo drives it
- grip force is nominal; contact oracle not informative
- touch probe is a noise model, probe motion and time are not simulated
- look-again and probe corrections take no execution time in the simulation
- retargeting error is a constant per-seed joint-space offset (no human wrist trajectory is retargeted); its oracle is the controller's own DLS IK, not cuRobo
- ik_resolve correction is a residual-noise model; no second IK solver is run
- UR5e and UR10e share the table layout tuned for the UR5e and identical per-seed injected errors
