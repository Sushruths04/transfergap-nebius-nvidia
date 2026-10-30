# Style fidelity: how closely the robot reproduces the person's motion (style_fidelity_v1)

Computed from the per-episode `style` field of the saved showcase logs (`results/showcase_r6_shoulder044`, 60 held-out seeds per robot and condition, medians). Metrics are those of `sim/errors_demo.episode_style`: RMSE between the robot tool path and the person's hand path after the pipeline's alignment, approach angle, lift-height error, and the correlation of the speed profiles. Simulation only; offline replay of one clip, not the live loop.

| robot | condition | path RMSE (cm) | approach angle (deg) | lift-height error (cm) | speed-profile corr |
|---|---|---|---|---|---|
| ur5e | raw | 4.19 | 9.4 | 1.13 | -0.01 |
| ur5e | all_fixes | 4.8 | 9.1 | 1.09 | 0.03 |
| ur10e | raw | 2.75 | 1.4 | 0.54 | 0.29 |
| ur10e | all_fixes | 3.23 | 1.5 | 0.53 | 0.43 |
| kairos | raw | 2.77 | 1.4 | 0.71 | 0.26 |
| kairos | all_fixes | 3.23 | 1.5 | 0.73 | 0.36 |

Reading: succeeding at the task is not the same as acting like the person. The fixes raise success (31->60 on UR5e) but do not improve path fidelity (the speed caps and safe-path fixes deviate slightly from the human path: RMSE rises by about 0.5 cm). Median path error is 2.8-4.8 cm, so the robot reproduces the shape of the motion but not to the centimetre. Wrist rotation and finger shape are not part of these metrics because they are not copied.

## Caveat found on re-reading the controller (2026-10-29, later)
The arm controller already follows each retargeted human leg (reach, carry, retreat) at the person's own leg timing, stretched by `timing_scale` (`sim/controller.py`: "follow a retargeted human leg at the human's own timing"); the speed-cap fixes change the absolute pace, not the shape. The person's speed trace comes from monocular pose at about 21 fps and is noisy, so a low speed-profile correlation is partly a property of the metric (noise in the reference), not only of the robot. This metric has not been validated against a smoothed or motion-capture reference. Treat "speed correlation <= 0.43" as "not shown to match", not as "proven to differ". The path RMSE (2.8-4.8 cm) and approach-angle numbers are less noise-sensitive.
