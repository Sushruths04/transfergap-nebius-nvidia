# G1 copying person 2 (Pexels 7205253, woman, two-handed box move) — g1_style_person2_v1

- Demo: `runs/demos/pexels_7205253_woman_box_v2.npz` (object_height='hand_at_grasp'); plans
  `runs/demos/woman_v2.plan.json` and its safe_path_v2 projection; `g1/run_style_person2.sh`
  (committed before the run). Same frozen G1 grasp calibration and per-seed true target as g1_style_v1.
- Result: 0/30 grasps in every condition (touch 17/30 at her pace, 13/30 at robot pace, 13/30 with
  safe_path_v2). Wrist path RMSE 16–19 cm (person 1 on G1: 5.5 cm).
- Cause, visible BEFORE execution: the plan's IK cannot reach her path — max IK error 31 cm (align) and 28 cm
  (reach), because she walks ~0.8 m while reaching and the G1 stands in place. A kinematic-feasibility
  pre-check (IK error over the copied path) flags this without any rollout.
