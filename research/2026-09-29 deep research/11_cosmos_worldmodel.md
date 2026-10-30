# 11 — Cosmos world model as a *pre-execution* transfer-gap predictor

Research agent 11, 2026-09-29. Question: can an NVIDIA Cosmos world model forecast where a human demo will fail on a given robot, validated against MuJoCo ground truth?

Legend: **VERIFIED** = read on the primary page (arXiv abstract / HF model card / GitHub doc) via a fetch tool (still a summarizer; full PDFs NOT read). **UNVERIFIED** = search snippet or secondary source only. No numbers below are invented; where a number is missing it says so.

---

## 1. Prior work: world models as policy evaluators

| Work | What it does | Reported agreement with ground truth | Cross-embodiment / human-demo? | Status |
|---|---|---|---|---|
| **WorldGym** (arXiv 2506.00613; https://world-model-eval.github.io/abstract; code github.com/world-model-eval/world-model-eval) | Autoregressive action-conditioned video model used as a generative simulator; initial real frame + policy actions → rollout | r = 0.78 vs real success; mean success differs by 3.3% on average; ranking across policy versions preserved. Policies: RT-1-X, Octo, OpenVLA-7B. Robots: Bridge (WidowX), Google Robot | Two robots, but evaluates **policies**, not human-demo transfer; no per-embodiment gap attribution | VERIFIED (project page) |
| **WorldEval** (arXiv 2505.19017) | World model ranks policies/checkpoints "in imagination"; also a safety detector | "Strong correlation" with real-world paired evals (no number captured) | Single platform per study; policies not human demos | UNVERIFIED numbers (abstract via search) |
| **Ctrl-World** | Controllable WM for policy eval | Reported by dWorldEval as weaker correlation / higher rank violation | — | UNVERIFIED (secondary via dWorldEval) |
| **dWorldEval** (arXiv 2604.22152) | Discrete-diffusion WM, unified vision/language/action tokens | Claims MMRV = 0.013 vs baselines up to 0.039 (from search snippet of the HTML); LIBERO, RoboTwin, real robot | Not stated as cross-embodiment or human-demo | Abstract VERIFIED; MMRV numbers UNVERIFIED (snippet) |
| **1X World Model** (https://www.1x.tech/1x-world-model.pdf) | Humanoid (NEO) action-conditioned WM for checkpoint selection | "Correlation between predicted success and true task scores"; accuracy scales with autonomous-rollout data; no coefficient captured | One embodiment (1X humanoid) | UNVERIFIED (search summary) |
| **DreamGen / GR00T-Dreams** (arXiv 2505.12705, NVIDIA) | Uses video WMs to generate synthetic "neural trajectories" for GR00T; DreamGen Bench correlates video-model quality with downstream policy success | GR00T N1 pick-place-only 0% on novel behaviors → 43.2% new behaviors / 28.5% unseen envs with DreamGen | Data generation, **not** failure prediction | VERIFIED (arXiv abstract via search) |
| **DreamDojo** (arXiv 2602.06949, Berkeley et al., CC BY 4.0) | WM pretrained on 44k h egocentric human video, post-trained on small robot data; applications include policy evaluation | No correlation number in abstract | Human video → robot, but used as a generalist simulator, not per-demo transfer-gap prediction | VERIFIED (abstract) |
| **HF-WM** "Beyond Successful Robot Demonstrations" (https://peiyantu.github.io/HF-WM/) | Action-conditioned WM trained on human egocentric video + failure-aware GRPO post-training on perturbed actions; pointflow as shared human/robot motion representation | Policy-eval Pearson r = 0.983, Spearman ρ = 0.956, MAE 2.4 pp; test-time action selection | **Closest prior work**: human video + failure prediction before execution. But single robot; no two-embodiment comparison of one demo; no stage-level attribution; arXiv id / code not found | Project page VERIFIED; arXiv id NOT found |
| **FARM** (arXiv 2609.11445, Pei et al., Sep 10 2026) | Supervised readout (≈34k params) on *frozen* WM (VLA-JEPA, not Cosmos) predictive states → step-wise failure scores | Pooled AUROC/AUPRC 85.68/88.59 (5-fold, 7 source tasks); 0.2256 ms latency | Cross-embodiment readout transfer (PIPER X, SO-101, Franka); **not** human-demo transfer | VERIFIED (abstract) |
| **Cosmos-Surg-dVRK** (arXiv 2510.16240, NVIDIA) | Cosmos WM fine-tuned on surgical robot video as an online policy evaluator; success judged by a V-JEPA 2-derived video classifier | "Strong correlation" with real dVRK outcomes; coefficient not in abstract | Single embodiment. **Useful template**: Cosmos rollout + separate learned judge | VERIFIED (abstract) |
| **RoboTrustBench** (arXiv 2606.01600, EMNLP 2026 Findings) | 7 video WMs, 1,207 pairs, 13 criteria | WMs are visually coherent but weak at constraint reasoning, counterfactuals, physical interaction | Warning, not a method | VERIFIED (abstract) |
| **MiraBench** (arXiv 2605.29360) | Action-conditioned reliability of robotic WMs | Not read | — | UNVERIFIED (title only) |

**Novelty check verdict:** Prior work establishes (a) WMs can rank *policies* on *one* embodiment with r ≈ 0.78–0.98, (b) WMs can use human video (DreamDojo, HF-WM), (c) failure signals can be read from frozen WM states and transferred across embodiments (FARM). **Not found:** using a world model to predict, *before execution*, the per-embodiment success of *the same human demonstration* retargeted to two different robots, validated against simulator ground truth, with stage-level attribution. The claim survives only in that narrow form. HF-WM is the paper a reviewer will raise; cite it and state the difference (two embodiments, same demo, stage attribution, sim-verified). Search was not exhaustive (no full PDFs; OpenReview CoRL 2026 not swept).

---

## 2. Which Cosmos checkpoints can actually be action-conditioned on our robots

### Cosmos 3 (released ~June 2026; arXiv 2606.02800; tech report research.nvidia.com/labs/cosmos-lab/cosmos3/technical-report.pdf — PDF too large to fetch, not read)
- **Cosmos3-Nano** (https://huggingface.co/nvidia/Cosmos3-Nano) — VERIFIED model card:
  - 16B params; omnimodal (text/image/video/audio/action); **action-conditioned forward dynamics** and **inverse dynamics** listed as capabilities.
  - Action trajectories 16–400 frames, **9D–57D depending on embodiment**. Listed embodiments: camera motion (9D), AV (9D), **egocentric human motion (57D)**, **single/dual Franka Panda + Robotiq (10D/20D)**, Agibot, **UR**, Google robot, WidowX 250, UMI (9D–29D each).
  - Video input max **5 frames**, 256p–720p.
  - Serving: `vllm serve nvidia/Cosmos3-Nano --omni --host 0.0.0.0 --port 8000` (vLLM-Omni), or Diffusers `DiffusionPipeline.from_pretrained("nvidia/Cosmos3-Nano", dtype=torch.bfloat16, device_map="cuda")`.
  - Hardware: Ampere/Hopper/Blackwell, **tested on H100 and GB200**; BF16 only officially. NVIDIA blog targets RTX PRO 6000 (96 GB) for Nano; FP8/NVFP4 quantization mentioned.
  - License: **OpenMDW 1.1** (commercial + non-commercial allowed).
  - **Fit for TransferGap:** UR embodiment is listed → our UR5e + 2F-85 arm is in-distribution *in embodiment* (exact UR action convention not read — tech report not fetched). **Unitree G1 humanoid is NOT listed** → no zero-shot G1 forward dynamics. The 57D egocentric human-motion channel could condition on the *human* demo itself (untested idea).
  - **L40S (48 GB) fit: UNVERIFIED.** 16B × 2 bytes ≈ 32 GB weights alone before activations/video latents; not tested on L40S by NVIDIA. Plan for an H100 (80 GB) or RTX PRO 6000 on Nebius for this component, or try FP8.
- **Cosmos3-Nano-Policy-DROID** (https://huggingface.co/nvidia/Cosmos3-Nano-Policy-DROID) — VERIFIED: a *policy* (actions from obs+language), Franka/DROID; #1 on RoboArena; server `python -m cosmos_framework.scripts.action_policy_server_robolab --port 8000` in the provided Docker. Relevant only as a possible third "method" to compare, not as a predictor.
- **Cosmos3-Super** 64B — datacenter only; out of budget.

### Cosmos-Predict2.5 (superseded by Cosmos 3; "limited maintenance")
- README (VERIFIED): checkpoints incl. `nvidia/Cosmos-Predict2.5-2B/robot/action-cond`, `.../robot/multiview-agibot`, `.../robot/policy`, plus 2B/14B base. License NVIDIA Open Model License (weights), Apache-2 (code). No VRAM/latency table in README.
- Action-conditioned post-training doc (VERIFIED, https://github.com/nvidia-cosmos/cosmos-predict2.5/blob/main/docs/post-training_video2world_action.md):
  - Dataset format = Bridge/IRASim: per-frame JSON with state `[x,y,z,roll,pitch,yaw]` + gripper (0/1); action 7D `[dx,dy,dz,droll,dpitch,dyaw,gripper_binary]` in gripper frame; paired `.mp4`.
  - Resolution 256×320, 13-frame sequences, **1 GPU** (`--nproc_per_node=1`).
  - Train: `torchrun --nproc_per_node=1 --master_port=12341 -m scripts.train --config=cosmos_predict2/_src/predict2/action/configs/action_conditioned/config.py -- experiment=ac_reason_embeddings_rectified_flow_2b_256_320 ~dataloader_train.dataloaders`
  - Infer: `python examples/action_conditioned.py -i assets/action_conditioned/basic/inference_params.json -o outputs/action_conditioned/basic --config-file cosmos_predict2/_src/predict2/action/configs/action_conditioned/config.py --checkpoint-path $CHECKPOINT_DIR/model_ema_bf16.pt --experiment ac_reason_embeddings_rectified_flow_2b_256_320`
  - **Key fit:** our UR5e arm's natural log (EE pose + gripper) maps *exactly* onto this 7D Bridge format. Post-training a 2B model on our own MuJoCo rollouts is the most tractable path. **Training time / VRAM on L40S: not documented — UNVERIFIED, must be measured.** 2B at 256×320 is the only Cosmos WM plausibly trainable on one L40S.

### Cosmos-Transfer2.5-2B (sim → photoreal)
- VERIFIED model card (https://huggingface.co/nvidia/Cosmos-Transfer2.5-2B): controls = blur, Canny edge, depth, segmentation (edge/blur auto-extracted from RGB); output 720p @ 16 fps; **requires 65.4 GB VRAM**; single-GPU generation time 285.8 s (B200), 719.4 s (H100 NVL), 870.3 s (H100 PCIe) per clip; NVIDIA Open Model License.
- **Does NOT fit an L40S (48 GB).** Needs an H100/H200-class node. ~12–15 min per clip on H100 → use for a *handful* of demo-video shots only, not dataset augmentation at scale.
- Usage pattern: Diffusers `DiffusionPipeline.from_pretrained("nvidia/Cosmos-Transfer2.5-2B")`; repo github.com/nvidia-cosmos/cosmos-transfer2.5; cookbook recipes exist (nvidia-cosmos.github.io/cosmos-cookbook). NVIDIA's SO-101 sim-to-real course has a Cosmos augmentation strategy page (docs.nvidia.com/learning/physical-ai/sim-to-real-so-101/latest/14-strategy3-cosmos.html) — UNVERIFIED content.
- Cost estimate: not computable without Nebius H100 hourly price (agent 3 only captured L40S: $1.55/h on-demand, $0.74/h spot). Formula: clips × ~0.25 h × H100 $/h.

### Cosmos Reason as judge
- Cosmos-Reason2 is in maintenance; Cosmos 3 absorbs reasoning (agent 3). Cosmos-Surg-dVRK used a **separate trained video classifier (V-JEPA 2)** as judge rather than a VLM — evidence that a learned/structured judge beats free-form VLM judging for success labels.
- For TransferGap: MuJoCo state is the ground truth for *real* sim rollouts; a judge is needed only for *WM-predicted* videos. Use Cosmos-Reason2-8B (fits L40S per agent 3: ~32 GB) or Cosmos3-Nano reasoning, and **measure the judge itself** against MuJoCo labels on real sim rollouts before trusting it on predicted videos. RoboTrustBench warns WMs look plausible while getting contact wrong (e.g. fingers touching but no stable grasp) — so the judge must be scored on grasp/lift specifically.

---

## 3. Proposed experiment (tiered so something always lands)

**Claim (narrow):** "Before running a retargeted human demo on a robot, a Cosmos world model predicts which embodiment/demo combinations will fail, and at which stage — measured against MuJoCo ground truth."

**Unit of analysis:** a *condition* = (human demo clip, embodiment ∈ {UR5e+2F-85, G1}, perturbation/correction variant). Ground truth per condition = MuJoCo success rate over its episodes, scored by `transfergap/metrics.py`.

### Tier 0 — guaranteed (days 1–4, L40S)
Cosmos-Reason2-8B (or Cosmos3-Nano reasoner if it fits) watches **real MuJoCo rollout videos** (third-person camera) and outputs {success, failed_stage}. Score against MuJoCo labels: accuracy, confusion over stages, calibration. This is not prediction, but it (a) validates the judge needed for Tier 2, (b) puts a Cosmos model in a load-bearing, *measured* role. Report honestly even if weak.

### Tier 1 — early-failure prediction from a partial rollout (week 2, L40S)
FARM-style: embed the first k frames (e.g. up to grasp onset) with a frozen Cosmos encoder / Reason embeddings; fit a tiny logistic readout to predict final MuJoCo success; evaluate AUROC on held-out conditions, including **cross-embodiment readout transfer** (train on arm, test on G1 and vice versa). Cheap, well-defined, directly comparable to FARM's reported AUROC 85.68 (different WM/tasks — cite, don't claim parity).

### Tier 2 — true pre-execution forward prediction, arm only (week 2–3, needs to be measured)
1. Log MuJoCo UR5e rollouts in Bridge 7D format (EE delta + gripper) with 256×320 video — varied demos, perturbations, successes **and** failures (failure-aware, per HF-WM's lesson that success-only data can't predict failures).
2. Post-train `Cosmos-Predict2.5-2B` action-conditioned on these (single GPU, command above). Measure wall-clock and VRAM on L40S first with a tiny run; if OOM, move to an H100 Serverless Job.
3. For held-out conditions: give the WM the initial frame + the planned action sequence (from retargeted demo, *before* execution) → predicted video → judge (Tier-0-validated) → predicted success.
4. Metric: Spearman ρ between predicted and MuJoCo success rates across conditions; mean absolute rate error; stage-agreement rate. WorldGym reported r = 0.78 and HF-WM r = 0.983 on their (different) setups — cite as context only.
- **Sample size (proposal, not a verified requirement):** ≥ 20 held-out conditions × ≥ 10 episodes each for a rank correlation to mean anything; this is a design choice to revisit with measured rollout cost. Agent 4's 60-paired-trial power figure applies to the correction experiment, not this correlation.
- **Honest limitation to state:** the WM is post-trained on the same simulator it is validated against, so Tier 2 shows the WM can *learn* embodiment-specific failure dynamics from sim, not that it transfers to real robots. Frame it as "a validated protocol for WM-based transfer prediction, with sim as the oracle a real deployment lacks."
- **Zero-shot variant (optional):** Cosmos3-Nano with UR action conditioning on MuJoCo frames, no post-training — likely poor due to sim-render domain gap; report as a baseline if an H100 is available.

### G1 fallback
No Cosmos checkpoint found with G1 action conditioning. For G1: Tier 0 and Tier 1 only (judge + early readout on real sim rollouts). Optional idea (UNTESTED): condition Cosmos3-Nano's 57D egocentric human-motion channel on the source human motion as a "what would the human outcome look like" reference — not a robot prediction; don't claim it as one.

### Guardrails (tie-in to agent 4)
- WM predictions and judge outputs are **never** inputs to the executed policy at run time during scoring runs (avoid the RHO sim-oracle trap); enforce with the unit test agent 4 proposed.
- MuJoCo labels are the only benchmark labels; Cosmos outputs are predictions evaluated *against* them.

---

## 4. Feasibility and recommendation

| Tier | NVIDIA model load-bearing | GPU | Risk | Recommendation |
|---|---|---|---|---|
| 0 Judge on sim rollouts | Cosmos-Reason2-8B / Cosmos3-Nano | L40S (Reason2-8B) | Low | **Do it** — cheap, measurable, feeds the demo's "model explains, simulator decides" moment |
| 1 Early-failure readout | Cosmos encoder embeddings | L40S | Low–medium | **Do it** as the secondary claim |
| 2 Pre-execution WM prediction (arm) | Cosmos-Predict2.5-2B action-cond, post-trained | L40S if it fits, else H100 job | **High** (training time/VRAM unmeasured; sim-render quality) | **Stretch** — start data logging early (free), attempt training only after the arm grasp baseline exists |
| Transfer2.5 photoreal demo shots | Cosmos-Transfer2.5-2B | **H100/H200 only (65.4 GB)** | Medium (cost/time) | A few hero shots for the video, clearly labeled "Cosmos-Transfer render of the sim rollout" |

Bottom line: the full "world model predicts the transfer gap" claim is novel in its narrow form but high-risk in 3 weeks; Tiers 0–1 give two defensible, measured Cosmos roles on one L40S, with Tier 2 as the headline stretch.

## Sources
- WorldGym: https://world-model-eval.github.io/abstract ; https://github.com/world-model-eval/world-model-eval
- WorldEval: https://arxiv.org/pdf/2505.19017
- dWorldEval: https://arxiv.org/abs/2604.22152 ; https://arxiv.org/html/2604.22152v1
- 1X World Model: https://www.1x.tech/1x-world-model.pdf
- DreamGen: https://arxiv.org/abs/2505.12705
- DreamDojo: https://arxiv.org/abs/2602.06949
- HF-WM: https://peiyantu.github.io/HF-WM/
- FARM: https://arxiv.org/abs/2609.11445
- Cosmos-Surg-dVRK: https://arxiv.org/abs/2510.16240
- RoboTrustBench: https://arxiv.org/abs/2606.01600
- MiraBench: https://arxiv.org/pdf/2605.29360
- Cosmos 3: https://arxiv.org/abs/2606.02800 ; https://huggingface.co/nvidia/Cosmos3-Nano ; https://huggingface.co/nvidia/Cosmos3-Nano-Policy-DROID ; https://developer.nvidia.com/blog/develop-physical-ai-reasoning-world-and-action-models-with-nvidia-cosmos-3/
- Cosmos-Predict2.5: https://github.com/nvidia-cosmos/cosmos-predict2.5/blob/main/README.md ; https://github.com/nvidia-cosmos/cosmos-predict2.5/blob/main/docs/post-training_video2world_action.md
- Cosmos-Transfer2.5: https://huggingface.co/nvidia/Cosmos-Transfer2.5-2B ; https://github.com/nvidia-cosmos/cosmos-transfer2.5
