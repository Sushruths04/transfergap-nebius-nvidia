# GR00T fine-tune on the exported dataset: what is ready, what is missing (2026-10-29)

Status: NOT started. Checked on the cluster volume today: the policy repo (Isaac-GR00T) and GR00T policy weights are NOT on `/ws/transfergap` (only `GR00T-WholeBodyControl`, used for the G1 controller, and `Cosmos-Reason2-2B`). The project notes say the author has Hugging Face access to GR00T-N1.7-3B; I did not verify it today.

Ready: `runs/dataset_v1_lerobot` (120 physics-verified episodes, UR5e/UR10e/KAIROS, 25 Hz, state + action + third/wrist camera video, LeRobot-v2.1-style layout; not yet validated with the LeRobot loader).

Missing, in order:
1. Clone the policy repo and download the 3B weights to the volume (about 10-15 GB; gated).
2. Convert the dataset to the exact layout the trainer expects (`meta/modality.json`, separate video keys for the two cameras instead of one side-by-side video, action/state field names, per-embodiment statistics) and validate it with the LeRobot loader.
3. Write an embodiment config for a 6-DoF UR arm + parallel gripper (new embodiment): action space = joint position targets + gripper; this is the part most likely to need debugging.
4. Fine-tune (LoRA or action-head only) on one L40S; then evaluate closed-loop in our MuJoCo scene on held-out seeds with the same scorer as every other result (success counts with intervals). Only that closed-loop number may be quoted; training loss is not a result.
Realistic cost: several hours of work and GPU time, with a real chance that step 3 or the evaluation harness takes longer than the time left. If attempted, run it AFTER the live session and the video are final, and report honestly if it does not finish.
