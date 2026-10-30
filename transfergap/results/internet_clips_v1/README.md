# Internet videos instead of live (internet_clips_v1)

Three freely licensed Pexels clips (`demo_input/SOURCES.md`) run through the pipeline on the cluster: Fast SAM 3D Body pose (L40S) -> person model -> feasibility check -> physics rollouts with the frozen five-fix stack, UR5e / UR10e / KAIROS, 60 held-out seeds (1000-1059), no shoulder-width rescale (`--shoulder-width-m 0`, camera scale unknown). Event frames (grasp / release) and windows were picked by looking at contact sheets of each clip (hand-annotated, not detected). Both object-height rules are reported because the rule decides the table height under the hand (see `fsam_cluster_v1`). Simulation only; one pose estimator; these are exploratory first runs on single clips.

| clip | what happens | rule | pre-check | UR5e raw -> fixes | UR10e raw -> fixes | KAIROS raw -> fixes |
|---|---|---|---|---|---|---|
| packing box (single person, one hand carries a box) | window 195-249, grasp 212, release 233 | lowest_hand | feasible | 0 -> 51 | 0 -> 52 | 0 -> 60 |
| packing box | same | hand_at_grasp | style infeasible (carried block collides with the gripper) | 0 -> 0 | 0 -> 0 | 0 -> 0 |
| woman carrying a large box (two-handed, 8-10 cm effective object) | window 30-130, grasp 40, release 115 | lowest_hand | UR arms infeasible (collisions 4-5 cm) | 0 -> 0 | 0 -> 0 | 0 -> 34 |
| woman carrying a large box | same | hand_at_grasp | infeasible | 0 -> 0 | 0 -> 0 | 0 -> 33 |
| clothes into a storage bin (moving camera, soft garment) | window 0-110 | both | REFUSED at the demo stage: hand path 1.2 x 3.2 x 0.6 m exceeds the 1.5 m plausibility limit | not run | not run | not run |

Reading:
- The pipeline now takes an internet clip end to end and reports outcomes with reasons instead of crashing; the packing-box clip transfers to all three robots (51 to 60 of 60) once the object-height rule matches the clip, and fails completely under the other rule. The rule has to be chosen per clip.
- A two-handed carry of a box larger than the gripper opening is a poor fit for one parallel gripper: only KAIROS (12.8 cm opening) transfers it, about half the time.
- A moving camera with a soft object defeats the monocular metric scale; the plausibility gate refuses it rather than simulating nonsense, which is the intended behaviour.
- Limits: three clips, one estimator, hand-annotated events, no confidence intervals, fixes not tuned for these clips. REPORT_*.md are the pipeline reports.
