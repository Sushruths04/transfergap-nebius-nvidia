# IK comparison v1: repo damped least squares vs mink differential IK

Code: `transfergap/sim/ik_compare.py`; tests: `tests/test_ik_compare.py`; per-robot tables in `ur10e/summary.md`,
`ur5e/summary.md` (raw numbers in `summary.json`). Reproduce:
`PYTHONPATH=. python -m transfergap.sim.ik_compare --robot ur10e --out results/ik_compare_v1` (needs `mink`,
`qpsolvers`, `daqp`, `scipy`; seeds are fixed, so the numbers repeat exactly).

## What was compared

- **DLS**: the maths of `ScriptedPickPlace.ik_step` (damping 1e-3, orientation weight 0.6, clip to the controller's
  range) with the target rotation made general. A test checks that it reproduces the controller's own step to 1e-9.
  Run with 4 iterations (what the controller does per control step) and 100 iterations (converged).
- **mink**: differential IK as a QP per step (DAQP solver, damping 1e-3, configuration limits as constraints,
  frame task on the gripper pinch site), up to 200 steps, stopping at 0.2 mm / 0.1 deg.
- Both drive the same point and are judged by one independent forward-kinematics evaluator. Success =
  position <= 1 mm, orientation <= 0.5 deg, no joint-limit violation.
- Reach is the largest shoulder-to-pinch distance over 4000 random configurations (a lower bound on the true reach).
  The clip range used by the controller differs from the joint range by at most 9e-5 rad.

## Results (UR10e; UR5e is similar, see its table)

| experiment | dls_4 | dls_100 | mink |
|---|---|---|---|
| 300 reachable 6-DoF targets, start at home | 5 | 185 | **228** |
| 200 tool-down workspace targets (all reachable by a 12-restart reference), start at home | 5 | **181** | 156 |
| 100 unreachable targets: finite, in limits, error above the geometric bound | all | all | all |
| path tracking, 33 lines x 100 waypoints (sub-mm in every waypoint) | 3300/3300 | n/a | 3300/3300 |
| median solve time | 0.9 ms | 9 ms | 2 ms (1.3 ms per path step) |

UR5e: 300 full-pose 5 / 201 / **243**; tool-down 5 / 168 / **172**; path 2500/2500 for both.

## Reading

1. **Neither solver wins outright.** From the fixed home pose, a single start does not reach every target for
   either method (mink 156 to 228 of 200 to 300 on UR10e, converged DLS 181 to 185). A 12-restart reference reached
   all 200 tool-down targets, so the misses are local minima and stalls near limits, not unreachable targets.
   mink wins on full 6-DoF poses and on the UR5e; converged DLS wins on tool-down targets on the UR10e.
2. **The per-step DLS the controller uses (4 iterations) cannot jump to a far target** (5 of 300). That is by
   design: the controller moves between waypoints over seconds with warm starts, and the path experiment shows both
   methods track straight tool-down lines to under a millimetre at every waypoint (DLS 4 iterations: median
   3.6e-8 mm; mink one step: 0.025 mm; both on UR10e).
3. **IK is not what limits the arm tasks.** Tracking is already sub-millimetre with the current DLS. Replacing it
   would not change the arm results; the arm failures found earlier come from perception, calibration and timing.
4. **Where mink is the better tool:** hard joint-limit constraints inside the solve, multiple weighted tasks
   (posture, several frames), and the same formulation HOI-Retarget uses for the humanoid. That makes it the
   candidate for the G1 right arm plus waist and for new embodiments. cuRobo (collision-aware, batched) is the NVIDIA
   option and can be added as a third solver in this harness.

## Limits of this comparison

- Single start from the home pose, a fixed iteration budget per method (100 DLS, 200 mink); no tuning of either.
- "Reachable" for tool-down targets means "reached by the restart reference", which is a lower bound.
- Kinematics only: no collisions, no dynamics, no real controller tracking error (which is what limits the G1).
- cuRobo is not part of v1; it was not installed or tested here.
