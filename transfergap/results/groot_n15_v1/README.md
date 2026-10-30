# GR00T-N1.5-3B fine-tuned on our simulation data (2026-10-30)

Question: does a fine-tuned vision-language-action foundation model (NVIDIA GR00T-N1.5-3B) do the block-to-tray task, and how does it compare with our small behaviour-cloning (BC) policy (60/60 on every robot)? Every number below is closed-loop in the MuJoCo simulator, scored by the same physics scorer as every other result in this repository (success = block lifted, placed in the tray, released and settled, no forbidden collision).

**Answer (updated 14:50): it works once the action chunks are executed the right way, but it is clearly worse than the small policy.** With the first-step execution I used at first, every checkpoint scored 0-1 of 30 (runs A-C below). The gripper-to-cube measurements (section "Diagnosis") showed that the arm stopped 2-5 cm short of the cube, so I executed an action further ahead in the predicted 16-step chunk (`--look 4`). With that single evaluation-side change, the same trained model scores 25/30 (UR10e-only model, standard) and 27/30 (three-arm model on KAIROS). The three-arm model stays weak on the UR arms (5-10/30). No retraining was involved in that change.

## Setup
- Model: `nvidia/GR00T-N1.5-3B`, fine-tuned (vision tower, action head projector and diffusion model tuned; LLM frozen), batch 32, 5000 steps, one run per setting, data config `so100_dualcam` (front + wrist 224x224 camera, 6 joint positions + gripper as state, 16-step action chunks of joint targets), task text "pick up the red cube and place it in the green tray".
- Data: scripted fix-stack rollouts of one demonstration's style, physics-verified successes only, 25 Hz subsampled by 4 (`scripts/gen_groot_data.py`): 200 standard (seeds 2000-2199) + 200 mixed-size/distractor episodes (seeds 4000-4199) per robot.
- Evaluation (`scripts/eval_groot.py`): a fresh set of 30 seeds (6000-6029) per cell, temporal-ensemble execution of the action chunks like the BC evaluator; `mixed` = mixed cube sizes + distractors; `hard` = 6 cm cube + 5 distractors.

## Run A: UR10e only (400 episodes), by checkpoint, standard condition
| checkpoint (steps) | success |
|---|---|
| 1000 | 0/30 |
| 2000 | 0/30 |
| 3000 | 0/12 |
| 4000 | 0/12 (first-step execution: 0/6) |
| 5000 | 1/30 (95% CI 0.6-16.7%) |
| 5000, eval frames passed through the training video codec (h264 yuv420p crf 20) | 0/12 |
Training loss reached about 0.014 by epoch 0.5 (normalised action loss, it keeps falling); the BC policy needs far less compute and scores 60/60 on the same task.

## Run B: one model for UR5e + UR10e + KAIROS (1200 episodes), step 5000, 30 seeds per cell
| robot | standard | mixed | hard |
|---|---|---|---|
| ur10e | 0/30 | 0/30 | 2/30 |
| ur5e | 0/30 | 2/30 | 3/30 |
| kairos | 4/30 | 6/30 | 17/30 |
For comparison the BC policy `multi4` (two training seeds) scores 60/60 in every one of these cells on 60 seeds.
Failure reasons (all cells): almost always `no_lift` and `not_released_and_settled_at_goal`; a few `forbidden_collision` in mixed/hard.

## Run C: same recipe as run B, but a closer front camera (cube about 2x larger in the image), step 5000, 30 seeds per cell
Only the front camera changed (a free camera 0.95 m from the table centre instead of the usual third-person view; wrist camera, data seeds, recipe and evaluation seeds identical to run B).
| robot | standard | mixed | hard |
|---|---|---|---|
| ur10e | 0/30 | 1/30 | 4/30 |
| ur5e | 0/30 | 1/30 | 10/30 (95% CI 19-51%) |
| kairos | 3/30 | 4/30 | 9/30 (17-48%) |
Against run B: standard unchanged (0/0/3-4 of 30), UR5e and UR10e hard higher (3 -> 10 and 2 -> 4), KAIROS hard lower (17 -> 9). With 30 seeds per cell and intervals this wide, only the UR5e hard change is more than noise, and one cell moving up while another moves down does not support "the image resolution of the cube is the limit". The standard 4 cm cube stays at 0-3 of 30 for every robot even though it is now about 10 pixels wide. So the closer camera did not fix the model; the cause of the missed grasps remains unexplained (candidates not tested: too little data for a 3B model that must learn the grasp from images, 200+200 episodes per robot; the action-chunk target, which are joint positions rather than end-effector deltas; one training run and no hyper-parameter tuning).


## Diagnosis and fix (what was wrong with runs A-C)
1. Measured the offset between the gripper's pinch point and the cube at the moment the gripper command first closes (`eval_groot.py --diag`, 8 seeds each, three models): the cube was a systematic +2 cm (x), +3 to +6 cm (y), +0.8 cm (z) away in every seed, and the closest approach during the whole episode was 2-5 cm. So the arm stalled short of the cube, it did not miss randomly. (`debug_diag_*.json` are the 8-seed summaries.)
2. Hypothesis: a position-target policy that predicts "current state + a tiny step" settles at an offset fixed point. Test: execute `chunk[L]` of the latest chunk instead of the temporal ensemble of near-term targets (`--look L`). UR10e-only model, seeds 6000-6011, same model: ensemble/first-step 0/12, `--look 4` 10/12, `--look 8` 10/12; amplifying the step toward the target (`--gain 3`) 0/12 (`debug_x_*.json`).
3. `--look 4` was chosen on seeds 6000-6011. The results below use fresh seeds 6100-6129 that were never used for choosing it.
4. A look-ahead of 8 did not help the three-arm model on the UR arms (1/12 on UR10e, 2/12 on UR5e, seeds 6200-6211; `debug_sweep_*.json`).

## Run D: look-ahead execution (`--look 4`), fresh seeds 6100-6129, 30 seeds per cell
| model / robot | standard | mixed | hard (6 cm cube + 5 distractors) |
|---|---|---|---|
| UR10e-only (run A model), UR10e | 25/30 (95% CI 66-93%) | 16/30 (36-70%) | 21/30 (52-83%) |
| three-arm (run B model), KAIROS | 27/30 (74-97%) | 20/30 (49-81%) | 26/30 (70-95%) |
| three-arm, UR10e | 5/30 (7-34%) | 2/30 (2-21%) | 10/30 (19-51%) |
| three-arm, UR5e | 7/30 (12-41%) | 5/30 (7-34%) | 6/30 (10-37%) |
The small BC policy scores 60/60 in all of these cells (60 seeds). So GR00T reaches 83-90% on its best robot in the standard condition, not 100%, and the single three-arm model is much weaker on UR5e and UR10e (it saw only 0.63 epochs of its data in 5000 steps). Files: `look4_<model>_<robot>_<condition>.json`.

## Run E: three-robot model trained for another 5000 steps (lr 5e-5), look-ahead 4, fresh seeds 6100-6129, 30 per cell
| robot | standard | mixed | hard |
|---|---|---|---|
| ur10e | 0/30 | 0/30 | 9/30 |
| ur5e | 7/30 | 5/30 | 3/30 |
| kairos | 28/30 | 23/30 | 19/30 |
KAIROS improves to 28/30 on standard and 23/30 on mixed; the UR arms stay at their earlier level. Files: `runE_<robot>_<condition>.json`.

## What I checked and what I could not isolate
- Frame dumps (run A, checkpoint 3000): the arm approaches the cube, descends, closes the gripper and starts to lift, but the gripper closes **beside** the cube (the cube stays on the table), then the policy holds that pose and never retries.
- Open-loop action error against recorded demonstrations (checkpoint 2000): MSE 0.0046 (radians^2 on joints), i.e. the model fits the recorded motion roughly but not to the centimetre needed for a grasp.
- Ruled out as the cause: action-chunk indexing and gripper scale (consistent with the dataset), first-step vs ensemble execution (0/6 vs 0/12), video-codec gap (0/12).
- A hint, not a proof: the best cells are the ones with the **6 cm cube** (KAIROS hard 17/30), while the standard 4 cm cube (about 5 pixels wide at 224 px) gives 0-4/30. That fits "grasp-position precision limited by the input resolution", but the hard cell also changes the distractors and the robot, so it is not isolated. A run with a closer front camera (cube about twice as large in the image) was done to test it: see Run C below. It did not confirm the hint.

## Limits
One fine-tune per setting (no repeated training seeds), 30 evaluation seeds per cell (wide intervals), the execution setting `--look 4` was tuned on 12 other seeds (no per-model tuning beyond that), simulation only, same simulator and scene as the training data, scripted demonstrations (not human teleoperation), a single task, a single set of hyper-parameters (no tuning). These numbers are for this recipe and this evaluation setting only.

Files: `ur10e_only_*.json` (run A, per-seed results), `3arm_<robot>_<condition>.json` (run B), `close_<robot>_<condition>.json` (run C).
