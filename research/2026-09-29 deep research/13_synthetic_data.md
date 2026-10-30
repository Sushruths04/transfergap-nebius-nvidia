# 13 — Synthetic data: one human demo → many episodes (research agent 13)

Scope: NVIDIA synthetic-data pipelines (DreamGen/GR00T-Dreams, MimicGen family, Isaac Lab Mimic / GR00T-Mimic, Cosmos Transfer) and whether TransferGap can multiply one demo into 100+ valid LeRobot episodes per embodiment on one L40S. VERIFIED = primary page read via fetch (summarizing tool, not full PDF read); UNVERIFIED = search snippet/secondary.

## 1. Pipelines compared

| Pipeline | Input | Robots | Needs Isaac Sim? | Compute | License | Fit for us |
|---|---|---|---|---|---|---|
| **MimicGen** (NVlabs/mimicgen) | ~10 source demos + object poses + subtask segmentation | robosuite (MuJoCo) arms | **No** — robosuite/MuJoCo | CPU-feasible sim replay | NVIDIA Source Code License (code), CC-BY 4.0 (data) — check non-commercial terms | **Algorithm is the best fit**; reimplement against our own MuJoCo scene |
| **DexMimicGen** (NVlabs/dexmimicgen) | ~60 demos across 9 tasks → 20k+ | bimanual dexterous (humanoid-like) in robosuite | No (robosuite) | modest | not confirmed | Reference for G1 two-hand case only |
| **SkillMimicGen** (CoRL 2024) | few demos + skill segmentation, motion planning for transit | arms | robosuite | modest | not confirmed | Idea: replace MimicGen's naive linear interpolation with motion planning |
| **Isaac Lab Mimic / GR00T-Mimic** | teleop demos (HDF5), `annotate_demos.py --auto` | Franka stack, GR-1 pick-place, **Unitree G1 locomanip** | **Yes** (Isaac Lab, Isaac Sim 6.1) | e.g. GR-1 ~18–40 min data gen on RTX 6000 Ada | Apache/BSD (Isaac Lab) | Strong NVIDIA-branding value, but moves us off MuJoCo — cost/risk too high for Oct 30 |
| **DreamGen / GR00T-Dreams** | image + language prompt; world model fine-tuned on robot data; IDM trained on robot data | GR1, Franka, SO-100, RoboCasa | No | **Very heavy**: RoboCasa 240k samples = 54 h on 1500 L40s | Apache-2.0 | Not feasible for generation at scale; tiny-scale demo only |
| **Cosmos Transfer 2.5** | sim video + control maps (depth/edge/seg/blur) | any (video-level) | No (any sim video) | 2B model; GPU-heavy per clip | NVIDIA Open Model License | **Use for photoreal visual augmentation / demo video**, not action generation |

### Key verified facts
- Isaac Lab Mimic commands: `record_demos.py`, `annotate_demos.py --auto`, `generate_dataset.py --num_envs 10 --generation_num_trials 1000 --headless`; output HDF5, convertible to LeRobot for GR00T N1.5. Reported data-gen success: Franka stack ~50%, GR-1 pick-place 65–80%, G1 locomanip 65–82%. VERIFIED — https://isaac-sim.github.io/IsaacLab/main/source/overview/imitation-learning/teleop_imitation.html
- MimicGen commands: `prepare_src_dataset.py --env_interface ... --env_interface_type robosuite`, `generate_core_configs.py`, `generate_dataset.py --config ... --auto-remove-exp`. VERIFIED — https://mimicgen.github.io/docs/tutorials/getting_started.html
- MimicGen algorithm: object-centric subtasks; transform source EEF target poses by T_new = T_obj_new · (T_obj_src)⁻¹ · T_eef_src; naive linear interpolation to segment start (not collision-aware); delta-pose controller; keep only successful rollouts; generation success 8.2%–82.3% by task. Assumes quasi-static rigid objects, known object poses at subtask start, one reference object per subtask. VERIFIED — https://arxiv.org/html/2310.17596 ; 50K demos / 18 tasks from ~200 human demos (abstract) https://arxiv.org/abs/2310.17596
- DreamGen: world model primarily WAN2.1 LoRA (also Hunyuan, CogVideoX, Cosmos tested); needs substantial robot data to fine-tune (GR1: 2,884 trajectories; SO-100: 10–13 videos/task); IDM = diffusion transformer + SigLIP-2, flow matching. Gains: GR1 37%→46.4%, SO-100 21%→45.5%; novel behaviors 43.2% vs 11.2%. Compute: 54 h on 1500 L40s for 240k RoboCasa samples. VERIFIED — https://arxiv.org/html/2505.12705 ; repo https://github.com/NVIDIA/GR00T-Dreams (Apache-2.0, uses Cosmos-Predict2; IDM command `torchrun scripts/idm_training.py --dataset-path <path> --embodiment_tag gr1`). VERIFIED.
- Cosmos Transfer 2.5: built on Predict 2.5, controls = edge/blur/segmentation/depth; `robot-multiview-control` 2B checkpoint; cookbook recipe for sim→real augmentation. UNVERIFIED details (snippets) — https://github.com/nvidia-cosmos/cosmos-transfer2.5 , https://nvidia-cosmos.github.io/cosmos-cookbook/recipes/inference/transfer2_5/inference-carla-sdg-augmentation/inference.html , SO-101 sim-to-real course: https://docs.nvidia.com/learning/physical-ai/sim-to-real-so-101/latest/14-strategy3-cosmos.html
- Newer, relevant, UNVERIFIED (snippet only): HumanoidMimicGen (arXiv 2605.27724, loco-manipulation via whole-body planning); OmniRetarget (arXiv 2509.26633, interaction-preserving humanoid data generation). Worth a read if G1 manipulation is pursued.

## 2. Recommended: MuJoCo-native "MimicGen-lite" for our block-to-tray task

No Isaac Sim needed. Reimplement the MimicGen transform (it's ~150 lines) in our own scene — robosuite env interfaces don't fit our MjSpec-built UR5e+2F-85 scene.

**Source demo:** one successful episode from the human clip → WiLoR hand pose → object-relative EEF targets + pinch-distance gripper (already built, `ur5e_ik.py`, `gripper_heuristic.py`), executed and scored successful in sim. Also usable: a scripted IK demo as a second, clean source (label it separately — it is not human-derived).

**Segmentation (2 subtasks, simulator-state auto-detected):**
1. `grasp_block`: start → gripper closes and block contact detected (contact pair in `data.contact`, block z rises).
2. `place_in_tray`: → gripper opens with block inside tray bounds.

**Generation loop (per episode i):**
1. Sample new block pose (x,y within table region, yaw ∈ [−π, π]) and tray pose; optionally randomize block size ±20%, friction, mass, lighting/texture (for visual policy), camera jitter.
2. For subtask k with reference object O: transform each source EEF target pose: `T_new = T_O_new @ inv(T_O_src) @ T_eef_src`.
3. Interpolate from current EEF pose to first transformed pose (linear in position, slerp in orientation; N≈20 steps). Upgrade over MimicGen: reject/replan if interpolation path collides (SkillMimicGen idea) — simple check via MuJoCo collision on sampled waypoints.
4. Solve IK per target (Pinocchio DLS, existing), check joint limits/singularity; execute with the same controller used at eval.
5. Replay source gripper command per step.
6. Score with `transfergap.metrics.score_episode` (lift + released/settled at goal, no forbidden collision). **Keep only successes**; log the failure rate itself as a metric (generation success is informative about embodiment difficulty).
7. Record observations (ego/third-person camera RGB, joint state), actions, task prompt → LeRobot v2.1 writer.

**Per-embodiment:**
- UR5e+2F-85: straightforward (delta/absolute EEF actions + 1-D gripper).
- G1: much harder — SONIC's GEM-X path streams wrists/fingers as zeros (flagged by agent 9), and G1 whole-body manipulation needs its own data path (Isaac Lab Mimic's G1 locomanip task exists but is Isaac-only). Recommendation: generate at scale only for the arm; for G1, generate motion-tracking variants (e.g. target-offset perturbations of the reference motion) and score tracking error, not grasp success, unless G1 grasping is proven first.

**Expected yield:** MimicGen reports 8–82% generation success; for a simple 2-subtask pick-place with a parallel gripper, expect the high end, but plan for ~30–50% until measured. 100 valid episodes → budget ~300 attempts. Each attempt is a few seconds of CPU MuJoCo — parallelize as a Nebius Serverless Job array (CPU is enough; GPU only for rendering if EGL).

**Estimated effort:** 1.5–2.5 days to build and validate, given scene/IK/gripper code already exists on the VM (must be recovered first).

## 3. Experiment this enables — is it novel?

**Data-scaling curve per embodiment: GR00T fine-tuned on 1 / 10 / 100 synthetic variants of ONE human demo, evaluated on a frozen held-out pose distribution, per embodiment.** Report: success vs N, and the *transfer gap* (human-demo replay success vs learned-policy success) vs N.

- Novelty assessment: data-scaling curves are well-studied (MimicGen, DreamGen, DexMimicGen all report them), so the curve alone is **not novel**. What may be interesting: (a) generation *yield* per embodiment as a cheap, pre-training predictor of embodiment difficulty (fraction of transformed human segments that are kinematically/physically executable on robot X) — this links directly to TransferGap's "measure where transfer fails" thesis; (b) decomposing why generated variants fail (IK infeasible / collision in interpolation / grasp slip / place miss) as a per-embodiment failure histogram derived from one demo. I found no paper that uses MimicGen-style generation yield as a transferability diagnostic across embodiments (not exhaustive; UNVERIFIED as a novelty claim — agent 7 should cross-check).
- Recommended framing: "one human demo → per-embodiment executable-variant yield + failure histogram (diagnostic), and → 100-episode dataset enabling a GR00T fine-tune pilot (secondary)."

## 4. NVIDIA-model usage angle (for recognition)

- **MimicGen algorithm** (NVIDIA Research) — cite it; our implementation is a MuJoCo port.
- **GR00T N1.7** — fine-tuned on the generated LeRobot data (single L40S "demo dataset" tier, per Isaac-GR00T hardware doc).
- **Cosmos Transfer 2.5** — optional: turn a few MuJoCo renders into photoreal clips for (a) the demo video and (b) a small visual-robustness ablation (policy trained on raw sim vs Cosmos-augmented frames). Keep small; per-clip generation is GPU-heavy. Label outputs "Built on NVIDIA Cosmos" (license notice).
- **DreamGen/GR00T-Dreams** — do NOT attempt generation at scale (compute far beyond budget). At most mention as related work, or run the DreamGen Bench-style IF/PA scoring idea on our own videos using Cosmos Reason.

## 5. Pitfalls

1. **Physically invalid trajectories:** MimicGen interpolation is geometry-unaware → collisions; transforms can exceed reach/joint limits. Mitigate: IK feasibility + collision check before execution; success filtering on simulator state only.
2. **Success filter bias:** kept episodes over-represent easy poses; report the generation yield and pose coverage, and evaluate on a held-out pose distribution sampled independently.
3. **Train/eval leakage:** do not evaluate on poses/seeds used for generation; freeze held-out seeds and the protocol (tolerances) before generating. The existing `validate_protocol_consistency` guard helps for tolerance drift, not for seed leakage — add a seed-set disjointness check.
4. **Sim oracle leakage into the policy:** generation may use simulator object poses (MimicGen assumes known object poses); the *trained policy* must not receive privileged state at eval time — observation keys should be camera + proprioception only.
5. **IDM quality (DreamGen):** pseudo-actions from video are noisy, need robot training data we don't have — reason to avoid DreamGen here.
6. **One-demo diversity ceiling:** 100 variants of one demo are 100 re-posings of one strategy, not 100 demonstrations; say so explicitly; don't claim broad generalization.
7. **License:** MimicGen code under NVIDIA Source Code License — reimplementing the published algorithm is safer than vendoring its code into an MIT repo; cite the paper.

## Sources
- https://github.com/NVIDIA/GR00T-Dreams
- https://arxiv.org/abs/2505.12705 , https://arxiv.org/html/2505.12705
- https://github.com/NVlabs/mimicgen , https://mimicgen.github.io/docs/tutorials/getting_started.html
- https://arxiv.org/abs/2310.17596 , https://arxiv.org/html/2310.17596
- https://isaac-sim.github.io/IsaacLab/main/source/overview/imitation-learning/teleop_imitation.html
- https://nvidia-cosmos.github.io/cosmos-cookbook/recipes/inference/transfer1/gr00t-mimic/inference.html
- https://github.com/nvidia-cosmos/cosmos-transfer2.5
- https://nvidia-cosmos.github.io/cosmos-cookbook/recipes/inference/transfer2_5/inference-carla-sdg-augmentation/inference.html
- https://docs.nvidia.com/learning/physical-ai/sim-to-real-so-101/latest/14-strategy3-cosmos.html
- https://github.com/NVlabs/dexmimicgen/ , https://arxiv.org/abs/2410.24185
- https://arxiv.org/pdf/2605.27724 (HumanoidMimicGen, UNVERIFIED) , https://arxiv.org/pdf/2509.26633 (OmniRetarget, UNVERIFIED)
