# Kinematic feasibility pre-check — feasibility_precheck_v1

Thresholds (frozen): IK error > 2.0 cm or penetration > 0.5 cm on the copied reach/carry/retreat legs => style infeasible for this robot. Nominal block + 4 jitter corners, worst case. CPU only, no rollout.

**Agreement with the known simulated outcome: 24/26** (confusion label->predicted: {'feasible->feasible': 13, 'feasible->infeasible': 2, 'infeasible->feasible': 0, 'infeasible->infeasible': 11}).

| case | variant | robot | known outcome | label | pre-check | max IK err cm (reach/carry/retreat) | max penetration cm | reason |
|---|---|---|---|---|---|---|---|---|
| synthetic 0 | raw | ur5e | oracle_all 60/60 (dev) | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| person 1 notebook | raw | ur5e | oracle_all 60/60 (dev) | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| synthetic 0 | raw | ur10e | oracle_all 60/60 (dev) | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| person 1 notebook | raw | ur10e | oracle_all 60/60 (dev) | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| person 2 box | raw | ur5e | oracle_all 60/60 (dev) | feasible | infeasible ✗ | 0.0/0.0/0.0 | 4.5/0.0/4.5 | collides: reach 4.5 cm, retreat 4.5 cm (g_base, g_left_follower, g_left_pad, g_left_spring_link, g_right_coupler, g_right_follower, g_right_pad, g_right_spring_link) |
| person 2 box | raw | ur10e | oracle_all 0/60 (dev), forbidden collisions | infeasible | infeasible ✓ | 0.0/0.0/0.0 | 4.5/0.0/4.5 | collides: reach 4.5 cm, retreat 4.5 cm (g_base, g_left_follower, g_left_pad, g_left_spring_link, g_right_coupler, g_right_follower, g_right_pad, g_right_spring_link) |
| HiPHI box lift | raw | ur5e | oracle_all 1/60 (dev) | infeasible | infeasible ✓ | 77.0/0.0/0.0 | 6.8/7.4/7.2 | unreachable: reach 77.0 cm; collides: reach 6.8 cm, carry 7.4 cm, retreat 7.2 cm (carried_block, forearm_link, g_left_pad, g_right_follower, upper_arm_link) |
| HiPHI box lift | raw | ur10e | oracle_all 0/60 (dev) | infeasible | infeasible ✓ | 0.0/0.0/0.0 | 0.0/4.8/0.0 | collides: carry 4.8 cm (carried_block, g_left_pad, g_right_follower) |
| person 1 markers | raw | ur5e | 0/60 held-out with the 4-fix stack (perception, calibration and timing corrected) | infeasible | infeasible ✓ | 0.0/0.0/0.0 | 1.1/0.0/1.4 | collides: reach 1.1 cm, retreat 1.4 cm (g_right_follower, g_right_pad) |
| person 1 markers | raw | ur10e | 0/60 held-out with the 4-fix stack (perception, calibration and timing corrected) | infeasible | infeasible ✓ | 0.0/0.0/0.0 | 1.1/0.0/1.4 | collides: reach 1.1 cm, retreat 1.4 cm (g_left_pad, g_right_follower, g_right_pad) |
| person 1 orange marker | raw | ur5e | 0/60 held-out with the 4-fix stack (perception, calibration and timing corrected) | infeasible | infeasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/3.0 | collides: retreat 3.0 cm (g_left_pad, g_right_follower, g_right_pad) |
| person 1 orange marker | raw | ur10e | 0/60 held-out with the 4-fix stack (perception, calibration and timing corrected) | infeasible | infeasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/3.0 | collides: retreat 3.0 cm (g_left_pad, g_right_follower, g_right_pad) |
| person 1 notepad | raw | ur5e | 0/60 held-out with the 4-fix stack (perception, calibration and timing corrected) | infeasible | infeasible ✓ | 0.0/0.0/0.0 | 2.9/0.0/1.4 | collides: reach 2.9 cm, retreat 1.4 cm (g_left_pad, g_right_pad) |
| person 1 notepad | raw | ur10e | 0/60 held-out with the 4-fix stack (perception, calibration and timing corrected) | infeasible | infeasible ✓ | 0.0/0.0/0.0 | 2.9/0.0/1.4 | collides: reach 2.9 cm, retreat 1.4 cm (g_left_pad, g_right_pad) |
| person 1 notebook | safe_path_v2 | ur5e | 57/60 held-out with its stack | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| person 1 notebook | safe_path_v2 | ur10e | 60/60 held-out with its stack | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| person 1 markers | safe_path_v2 | ur5e | 51/60 held-out with its stack | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| person 1 markers | safe_path_v2 | ur10e | 25/60 held-out with its stack | ambiguous | feasible | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| person 1 orange marker | safe_path_v2 | ur5e | 46/60 held-out with its stack | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| person 1 orange marker | safe_path_v2 | ur10e | 58/60 held-out with its stack | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| person 1 notepad | safe_path_v2 | ur5e | 58/60 held-out with its stack | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| person 1 notepad | safe_path_v2 | ur10e | 58/60 held-out with its stack | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.0/0.0 | - |
| person 2 box | safe_path_v2 | ur5e | 60/60 held-out with its stack | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.4/0.0 | - |
| person 2 box | safe_path_v2 | ur10e | 55/60 held-out with its stack | feasible | feasible ✓ | 0.0/0.0/0.0 | 0.0/0.4/0.0 | - |
| HiPHI box lift | safe_path_v2 | ur5e | not run | prediction | infeasible | 77.0/0.0/0.0 | 6.8/7.4/7.2 | unreachable: reach 77.0 cm; collides: reach 6.8 cm, carry 7.4 cm, retreat 7.2 cm (carried_block, forearm_link, g_left_pad, g_right_follower, upper_arm_link) |
| HiPHI box lift | safe_path_v2 | ur10e | not run | prediction | infeasible | 0.0/0.0/0.0 | 0.0/4.8/0.0 | collides: carry 4.8 cm (carried_block, g_left_pad, g_right_follower) |
| person 1 notebook | raw | g1 | place 20/30 at robot pace (grasp 24/30) | feasible | infeasible ✗ | 6.3/51.2/52.0 | n/a | unreachable: reach 6.3 cm, carry 51.2 cm, retreat 52.0 cm |
| person 2 box | raw | g1 | grasp 0/30 in every condition | infeasible | infeasible ✓ | 28.7/3.8/12.1 | n/a | unreachable: reach 28.7 cm, carry 3.8 cm, retreat 12.1 cm |
| person 2 box | safe_path_v2 | g1 | grasp 0/30 at robot pace | infeasible | infeasible ✓ | 26.8/3.8/7.5 | n/a | unreachable: reach 26.8 cm, carry 3.8 cm, retreat 7.5 cm |
| person 1 notepad | raw | g1 | not run | prediction | feasible | 0.0/0.0/0.0 | n/a | - |
| HiPHI box lift | raw | g1 | not run | prediction | infeasible | 76.1/62.1/54.5 | n/a | unreachable: reach 76.1 cm, carry 62.1 cm, retreat 54.5 cm |

## Reading (written after the run; thresholds and cases unchanged)

- **All 11 infeasible cases flagged, before any rollout** (G1 person 2: unreachable, reach IK error 27–29 cm;
  HiPHI box lift: carried box driven 5–7 cm into the table, UR5e also out of reach by 77 cm; person-1 markers /
  orange marker / notepad: fingers driven 1–3 cm into the table by the copied below-grasp sweep or post-release dip).
  Every safe_path_v2 variant that worked in simulation passes (10/10 incl. the ambiguous markers/UR10e cell).
- **Miss 1 — person 2 on UR5e (false alarm, conservative):** her copied approach comes from 6.7 cm *below* the table
  top (she lifts from a stack; the object is placed at table height), so the commanded fingers go 4.5 cm into the
  table on both arms. In simulation the table simply stops the fingers and the UR5e still succeeds under oracle_all
  (60/60), while the UR10e fails (0/60). The pre-check sees the same geometric conflict on both arms and cannot say
  which one recovers physically. Finger-only contact is not always fatal.
- **Miss 2 — person 1 on G1 is not a false alarm at trial level:** the case is flagged because ONE layout (block at
  the jitter corner 0.35, −0.22) makes the frozen G1 planner's IK jump to a bad branch (49–52 cm error); 5 mm away
  the error is 0.0 cm. Seed 106 of the real G1 run (block at 0.349, −0.218) got exactly that plan and was the only
  seed with **0/3 grasps at robot pace**. See `g1_per_trial.md`: over all 180 executed G1 rollouts, plans flagged by
  the pre-check grasped **0/99**; unflagged plans at robot pace grasped 24/27 (place 20/27).
- Practical rule: run the pre-check per trial layout, not per demo; an IK failure flags a planner/layout problem, a
  path below the support surface flags a style conflict (safe_path_v2 resolves it for every person-1/2 demo on the
  arms but NOT for G1 person 2 or HiPHI, which stay infeasible — HiPHI is a prediction, never simulated with v2).
