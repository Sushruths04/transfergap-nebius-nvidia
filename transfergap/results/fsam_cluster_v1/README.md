# Fast SAM 3D Body on the GPU cluster (2026-10-09)

Install: `docker/cluster/install_fsam_env.sh` (uv env `/ws/transfergap/envs/fsam`, torch 2.5.1+cu124, python 3.11); gated weights `facebook/sam-3d-body-dinov3` downloaded on the laptop and copied to the volume, sha256 checked against Hugging Face's published values (model.ckpt b5a2f9d3..., mhr_model.pt 352e271a...). YOLO11m-pose and MoGe weights fetched on first use. No TensorRT, no torch.compile yet: speed is the unoptimised path.
Pose export: `demo/tools/fsam_export_joints.py` (pipeline `--estimator fsam`, `TG_FSAM_PY`, `TG_FSAM_ROOT`).

| clip | frames | missed | speed (median) |
|---|---|---|---|
| author's clip (full) | 270 | 0 | 3.1 fps |
| Pexels packing-box clip (internet; RTMW3D failed it) | 479 | 11 | 3.9 fps |

## What the pipeline did with those joints (same frozen five-fix stack as before, seeds 1000-1059)

| clip / scale | UR5e raw -> stack | UR10e raw -> stack | KAIROS raw -> stack | pre-check |
|---|---|---|---|---|
| author, shoulder 0.44 m (derived) | 27 -> 59 | 30 -> 60 | 45 -> 60 | "style infeasible" (gripper-pad collisions, 0.5-2 cm) |
| author, no rescale | 28 -> 60 | 32 -> 60 | not run | same |
| (RTMW3D, same clip, for reference: `showcase_r6_shoulder044`) | 31 -> 60 | 34 -> 60 | 48 -> 60 | feasible |
| internet clip (window 195-249, events 212/233) | 0 -> 1 | 0 -> 0 | not run | "style infeasible" (the carried block and gripper collide) |
| internet clip, no rescale | 0 -> 0 | 0 -> 0 | not run | same |

## Reading (verified only)
- The pose stage now gets through the internet clip: the plausibility gate passes (hand path about 0.3 x 0.5 x 0.4 m); RTMW3D's path was 5.87 m wide and was refused.
- On the author's clip Fast SAM is not better than RTMW3D (slightly lower raw counts, same stack result), and the depth axis is noisier (path extent 0.65 m in one axis).
- With the pipeline default (`hand_at_grasp`) the robots cannot reproduce the internet clip (0/60 raw). The per-demo diagnosis loop (Nemotron through Token Factory, `../demo_agent_loop_demo44864be9.json`, five rounds per arm) found no correction worth more than +5 pp (largest +5.0 pp [0, 10.0], 95% CI touches 0). Under that rule the transfer fails for any correction; see the object-height finding below for why.
- Discrepancy with the earlier bake-off (`pose_estimator_bakeoff_v3`: Fast SAM on this clip 0/60 -> 58/60) is mostly explained by the OBJECT-HEIGHT rule, not by the pose estimator: the bake-off builds the demo with `lowest_hand` (the table is under the lowest hand point), the pipeline defaults to `hand_at_grasp`. Same Fast SAM joints, pipeline with `--object-height lowest_hand`, no rescale, frozen five-fix stack, seeds 1000-1059: UR5e 0 -> 51/60, UR10e 0 -> 52/60 (`pipe_pexels_lowesthand`, `docker/cluster/fsam_objheight.sh`). The bake-off's 58/60 used a per-demo stack, so the numbers are close but not identical. With `hand_at_grasp` the same clip stays at 0-1/60.
  Consequence: the earlier line "the robots cannot reproduce this clip" is WRONG as stated; it holds only for the pipeline's default object-height rule. Which rule is right depends on the clip (object on a desk vs lifted); it must be chosen per clip, not defaulted.
- Ruled out: the shoulder-width rescale (the no-rescale rows are the same).
