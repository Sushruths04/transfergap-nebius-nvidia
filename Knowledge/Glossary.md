---
type: glossary
updated: 2026-09-30
tags: [glossary, transfergap]
---

# Glossary

Definitions are as used in this project. Back to [[Home]] · [[Knowledge/README|Knowledge]].

## Project concepts

- **Embodiment gap** — the loss in task success when the same skill or demonstration moves to a robot with a different body. Vocabulary from the survey arXiv 2608.18433 (two axes: type of shared structure x stage where adaptation is needed). See [[Related Work]].
- **Transfer Gap Budget / gap budget** — per robot, a bar showing how much success each pipeline stage costs, measured by oracle substitution. The primary claim. See [[Research Synthesis 2026-09-30]].
- **Oracle substitution** — replace one pipeline stage at a time with simulator ground truth (perception -> true object pose; kinematics -> exact IK; contact -> oracle grasp, an upper bound only; timing -> nominal speed) and measure the success recovered. Stored in an `oracle` field of the episode schema; pooling across oracle values is forbidden.
- **Paired trials** — the same scene/seed run under two conditions (e.g. before and after a correction) so the difference is measured per pair. Required: at least 30 per decomposition cell; 60 dev + 60 held-out per robot for the correction test.
- **Wilson interval** — confidence interval for a proportion, used for success rates. Example: 8/30 gives 95% [0.14, 0.44].
- **Held-out** — trials whose object poses were not used to tune a correction; the protocol is frozen in git first.
- **Privileged state** — simulator success flags or internal state. Allowed only to label and score, never read by a policy, controller, or correction (a unit test enforces this).
- **Stage labeller** — code that assigns each failure a stage using simulator-state predicates. Stage names align with Isaac Lab-Arena: `grasp, lift, transport, place`.
- **Correction menu** — fixed set of parameterised fixes: object-relative target anchoring, tool-frame calibration, grip/timing parameters. Nemotron 3 Super picks one from the diagnosis.
- **Critic** — a model (Cosmos 3) that labels rollout outcome and failing stage; scored against simulator labels and never defines success.
- **Cliff** — observed shape of arm success versus injected error: 30/30 then a sharp drop.
- **Tiered G1 scoring** — touch, grasp, place tiers, because nobody has shown a simulated SONIC-G1 grasp (UNVERIFIED).
- **KAIROS** — the user's older Robotnik KAIROS lab robot (UR10 + Robotiq, ROS 2 Humble, Isaac Sim 4.2.0); eventual real target, cut from scope for the hackathon.
- **TransferGap product pitch** — "CI for human-to-robot transfer".

## NVIDIA and simulation terms

- **SONIC (GEAR-SONIC)** — NVIDIA GEAR whole-body tracking controller for the Unitree G1. See [[SONIC]].
- **GEM-X** — NVIDIA DAIR video-to-motion model (from GENMO). See [[GEM-X]].
- **SOMA** — the body model / 77-joint skeleton GEM-X outputs; converted to SMPL for SONIC.
- **GR00T N1.7** — NVIDIA VLA robot foundation model (3B). See [[GR00T N1.7]].
- **Cosmos 3** — NVIDIA omni world/reasoning model (Nano 16B, Super 64B). See [[Cosmos 3]]. **Cosmos-Reason2** — older reasoning VLM. See [[Cosmos-Reason2]].
- **Kimodo** — NVIDIA Toronto AI Lab motion diffusion model with end-effector constraints. See [[Kimodo-G1]].
- **cuRobo / cuRoboV2** — GPU collision-aware IK and trajectory optimization. See [[cuRoboV2]].
- **MimicGen / MimicGen-lite** — MimicGen turns a few demos into many by transforming object-centric subtask poses; "lite" is our roughly 150-line MuJoCo reimplementation. See [[13_synthetic_data]].
- **LeRobot v2.1** — dataset format GR00T at the pinned commit requires. Current `pip install lerobot` writes v3; do not use it. See [[GR00T N1.7]].
- **MuJoCo Warp** — GPU MuJoCo. See [[MuJoCo Warp]].
- **Isaac Lab-Arena / RoboLab** — NVIDIA evaluation stacks with subtask failure localization for one robot; reuse their names and cite.
- **NIM** — NVIDIA inference microservice container.
- **HiPHI** — 617.5 h optical mocap human-object dataset (arXiv 2608.16222), gated research licence, 215 GB. See [[Related Work]].
- **GMR** — General Motion Retargeting (MIT), likely BVH-to-G1 retargeter.
- **Nemotron 3 Nano / Super** — NVIDIA LLMs on Token Factory. See [[Nemotron]].

## Nebius terms

- **Token Factory** — Nebius hosted model API (OpenAI-style). **Serverless Jobs** — run-to-completion containers on Nebius GPUs; the service the hackathon rules name for simulation and evaluation. **Serverless Endpoints** — hosted containers (e.g. vLLM). See [[Nebius Infrastructure]].
- **Spot / preemptible** — cheaper VM that can be stopped with 60 s notice.
- **AoE** — Anywhere on Earth (deadline timezone). See [[Deadlines]].
