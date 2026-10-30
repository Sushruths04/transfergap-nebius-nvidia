# Style transfer with depth perception in the loop (protocol style_perception_v1)

The robot follows the retargeted human pick-and-place path (real demo recorded for a 4 cm cube, robot-nominal pace) on
5 / 6 / 7 cm cubes it never saw, with the block pose, yaw, size and the tray estimated from depth, on UR5e, UR10e and the
KAIROS arm. Protocol frozen before the held-out run (`protocol.json`; seeds 200-239, 40 seeds x 3 sizes per cell).

Result (see `heldout_scorecard.md`, `heldout_summary.md`): non-inferiority of depth beliefs vs ground-truth beliefs met on all
three robots (success gap about -1 pp; path RMSE to the human path 2.6 cm UR5e, 1.5 cm UR10e and KAIROS, identical to truth).
Absolute success is limited by the demo plan on 7 cm cubes with the 2F-85 arms (about 75% even with ground truth); that is a
property of the copied style, not of perception. `depth_hard` (all stressors, wrist look-agains) is report-only: 73-76%.
The recorded demo (`runs/demos/...`) is gitignored and not distributed.
