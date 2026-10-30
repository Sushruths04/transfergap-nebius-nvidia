# 10 — Maximum load-bearing NVIDIA stack for TransferGap

Research agent 10, 2026-09-29. Web sources were fetched via a summarizing tool, so every item is marked **VERIFIED** (read on the primary page/model card/repo) or **UNVERIFIED** (third-party, snippet, or inferred). All integration-hour figures are **my estimates** based on the codebase state recorded in `Implementation Status.md`.

Compute envelope: 1× L40S 48 GB VM, plus Nebius Serverless Jobs/Endpoints, plus Token Factory. **Key price fact from agent 3's file:** on nebius.com/prices, H100 costs $3.85/h on-demand and $0.79/h spot (H100 and H200). That spot price makes the 80 GB-class models below affordable as short, preemptible Serverless Jobs.

---

## 1. Inventory

### 1.1 Cosmos family

| Model | Exact ID | License / commercial | VRAM / hardware | Serving | Role in TransferGap | Effort | Judge value | NVIDIA-recognition value |
|---|---|---|---|---|---|---|---|---|
| **Cosmos 3 Nano** (reasoner, i.e. VLM mode) | `nvidia/Cosmos3-Nano` (16B total = 8B reasoner + 8B generator) | OpenMDW 1.1; "ready for commercial and non-commercial use". VERIFIED (HF card) | ~34 GB for inference according to Spheron's calculator (UNVERIFIED). The card lists only Ampere/Hopper/Blackwell and BF16 only (VERIFIED). L40S is Ada, not listed; it probably works through vLLM, but that is UNVERIFIED | `vllm serve nvidia/Cosmos3-Nano --hf-overrides '{"architectures": ["Cosmos3ReasonerForConditionalGeneration"]}' --tensor-parallel-size 1 --mm-encoder-tp-mode data --async-scheduling --allowed-local-media-path / --media-io-kwargs '{"video": {"num_frames": -1}}'` (VERIFIED, recipes.vllm.ai). Recipe baseline is 1× H200; `--enable-layerwise-offload` exists for small GPUs. The Reasoner NIM exists, but the NIM support matrix does not list L40S | **Video critic and event extractor.** (a) Segments the human demo into timed skill steps. (b) Explains each robot rollout failure. (c) Its explanations are scored against simulator labels, so it never defines benchmark success | 6–10 h | High: the newest Cosmos, shown doing real work | High: few people have used Cosmos 3 on robot failure attribution yet |
| Cosmos 3 video-input caveat | — | — | The card states "Video: 5 frames max" (VERIFIED on card). The vLLM reasoner recipe sets `num_frames: -1` (VERIFIED). It is **UNVERIFIED which limit applies to reasoner video understanding**, so test with a real 10 s rollout on day 1 | — | Decides whether Cosmos 3 can be the critic or whether we fall back to Reason2 | 1 h test | — | — |
| **Cosmos 3 generator: forward dynamics** (action-conditioned video) | `nvidia/Cosmos3-Nano`, `--omni` mode | Same as above | NIM Cosmos3-Generator nano needs **≥79 GiB per device** (VERIFIED, NIM 3.0.0 support matrix). **Will not fit the L40S**, so it needs an H100/H200 Serverless Job (spot $0.79/h) | `vllm serve nvidia/Cosmos3-Nano --omni --init-timeout 1800` (VERIFIED). Actions go in `extra_params["action"]` as `[chunk, raw_action_dim]` with `num_frames = chunk+1`; `domain_name`, `raw_action_dim` and `action_mode` are set in `extra_params` (UNVERIFIED, search snippet of the Cosmos repo docs) | **World-model preview of a proposed correction** on the UR arm, before running it in simulation. The model card lists **UR (10D)** among supported forward-dynamics embodiments (VERIFIED). We then measure agreement between the world model's predicted outcome and the MuJoCo ground truth | 16–24 h, high risk | High "wow" factor, but only credible if the measured agreement is reported honestly | **Very high**: world models as policy evaluators is an active NVIDIA research thread (Cosmos-Surg-dVRK, arXiv 2510.16240, VERIFIED abstract; Cosmos Policy) |
| **Cosmos-Reason2-8B** (fallback critic) | `nvidia/Cosmos-Reason2-8B` (also 2B and 32B) | VERIFIED in agent 3 file | 32 GB, fits the L40S. The repo says it is no longer actively developed and points to Cosmos 3 (VERIFIED, agent 3) | vLLM, documented in agent 3 file | Fallback critic if Cosmos 3 fails on the L40S or the frame limit bites | 3–4 h | Medium | Medium |
| **Cosmos-Reason2-2B (inside GR00T)** | Backbone of `nvidia/GR00T-N1.7-3B` | — | — | — | "GR00T-N1.7 VLM backbone is now Cosmos-Reason2-2B" (VERIFIED, GR00T-N1.7-3B card). Any GR00T fine-tune therefore **also uses Cosmos** — say so in the writeup | 0 h | Medium (narrative) | Medium |
| **Cosmos-Transfer2.5-2B** | `nvidia/Cosmos-Transfer2.5-2B` | NVIDIA Open Model License, commercial OK, derivatives allowed (VERIFIED) | **65.4 GB minimum**, BF16, Ampere/Hopper/Blackwell. About 12 min per clip on H100 PCIe. Outputs 720p/16 fps (VERIFIED). NIM wants ≥80 GB | github.com/nvidia-cosmos/cosmos-transfer2.5, as an H100/H200 spot Serverless Job | **Only load-bearing as an ablation:** re-render MuJoCo rollouts photoreal (depth + segmentation control), then check whether the Cosmos critic's diagnosis accuracy holds on photoreal video versus raw sim renders. That is a visual sim-to-real test of the diagnoser. If it is used only for pretty demo footage it is **decorative** | 8–12 h | Medium–high (visuals) | Medium |
| Cosmos-Predict2.5 / **Cosmos Policy** | `nvidia/Cosmos-Predict2.5-2B`; code `nvlabs/cosmos-policy` (Jan 29, 2026; LIBERO 98.5%, RoboCasa 67.1% @ 50 demos) (VERIFIED, HF blog) | NVIDIA Open Model License (UNVERIFIED for Cosmos Policy specifically) | NIM wants ≥80 GB (VERIFIED) | — | Would be a *third* policy family to fine-tune. **Cut**: duplicates GR00T and doubles training risk | — | — | — |
| **GR00T-Dreams / DreamGen** | github.com/NVIDIA/GR00T-Dreams (Apache-2.0, active; VERIFIED) | Apache-2.0 | Requires world-model fine-tune + IDM. Pretrained IDMs exist only for Franka, GR1, SO-100 and RoboCasa; UR and G1 would need a custom IDM (VERIFIED) | — | Multiplying demos via generated video. **Cut**: our data comes from MuJoCo, which already gives physically labeled actions more cheaply | — | — | — |

### 1.2 Robot policies, motion and control

| Model/tool | ID | License | VRAM | Role | Effort | Judges | Recognition |
|---|---|---|---|---|---|---|---|
| **GEAR-SONIC** | `nvidia/GEAR-SONIC` + NVlabs/GR00T-WholeBodyControl | NVIDIA Open Model License, commercial with attribution (VERIFIED, HF card via search) | Already running on the L40S with TensorRT 10.13 | **Core.** G1 whole-body tracking of the human motion stream; already proven on Sept 27 | 0 h (done) | High | High |
| **GEM-X + SOMA** | NVlabs/GEM-X (Apache-2.0 code, VERIFIED in tutorial); SOMA body model | Code Apache-2.0; checkpoint license UNVERIFIED | Already running | **Core.** RGB human demo → 77-joint SOMA → SMPL → SONIC | 0 h (done) | High | High |
| **Kimodo** (motion diffusion) | `nvidia/Kimodo-G1-RP-v1` / `-SEED-v1`, `nvidia/Kimodo-SOMA-RP-v1.1`; code nv-tlabs/kimodo | Code Apache-2.0. **Kimodo-G1-RP-v1: NVIDIA Open Model License, commercial OK** (VERIFIED). SMPLX-RP is R&D-only (VERIFIED) | ~17 GB, or <3 GB with `TEXT_ENCODER_DEVICE=cpu` (VERIFIED) | **Core; this is new.** Generates G1-feasible motion under **end-effector position constraints** (hands/feet), full-body keyframes and 2D root paths. Outputs MuJoCo qpos CSV for G1 and interoperates with GEAR-SONIC and GMR (VERIFIED). Two load-bearing uses: (1) **G1 correction operator**: re-generate the human-demo motion with a hand-position constraint at the *perceived object position*, i.e. the object-relative correction agent 4 ranked #1, implemented natively for the G1; (2) **controlled augmentation**: N constraint-perturbed variants of the one demo, giving the paired-trial pool / GR00T data | 8–14 h | High | **High**: NVIDIA Toronto AI Lab model released March 2026; novel use as a correction operator |
| **GR00T N1.7** | `nvidia/GR00T-N1.7-3B` | NVIDIA Open Model License (VERIFIED) | Fine-tune: ≥40 GB, 1× L40-class supported for demo datasets (VERIFIED, Isaac-GR00T hardware doc read last night) | **Autonomy condition.** Short NEW_EMBODIMENT fine-tune for the UR5e arm on sim-collected episodes (agent 2's runbook); UNITREE_G1_SONIC only if time allows. Report it as a pilot | 20–40 h, high risk | **Very high**: it's the flagship robot model | **Very high** |
| **cuRoboV2** | NVlabs/curobo; arXiv 2603.05493 (Sundaralingam, Murali, Birchfield, 2026) | **Apache-2.0**, commercial (VERIFIED via search result/README) | GPU, small | **Core; replaces our hand-rolled Pinocchio IK.** (1) Collision-aware IK and trajectory optimization for the UR5e: a batch solve over the human wrist trajectory. (2) **Pre-execution "kinematic feasibility" score per embodiment** (the % of demo poses reachable collision-free); cuRoboV2 advertises high-DoF and humanoid whole-body support (VERIFIED abstract/README). This becomes a cheap *predictor* feature for the transfer gap. (3) Arm correction operator: re-solve with an object-relative target offset | 8–12 h | High | High |
| **TensorRT 10.13** | — | NVIDIA SDK license | — | Already required by SONIC deploy. Also usable for GR00T inference speed-up (hardware doc: 1.5–3.3× over eager) | 0 h / 4 h | Low–medium | Medium |
| FoundationPose / FoundationStereo | NVlabs/FoundationPose | **NVIDIA Source Code License** (non-commercial research; VERIFIED via search) | Needs **RGB-D** + a CAD mesh or reference images | Would track the object's 6D trajectory in the human demo, making targets object-relative from real video. **Conditional:** only load-bearing if the human demo is recorded with depth (RGB-D camera or phone LiDAR). With a monocular RGB clip it can't run. Otherwise cut; in sim, object pose comes from ground truth | 10–16 h | Medium | Medium |

### 1.3 Nemotron family (Token Factory)

| Model | ID | Availability | Role | Effort | Judges | Recognition |
|---|---|---|---|---|---|---|
| **Nemotron 3 Nano** | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | On our Token Factory catalog, and a smoke call succeeded Sept 27 (VERIFIED in project log) | **Core.** Planner: goal → validated skill graph (already in `adapters.py`). Also the cheap narrative writer for the report viewer | 0–2 h | Medium | Medium |
| **Nemotron 3 Super** | `nvidia/nemotron-3-super-120b-a12b` (120B/12B active, up to 1M context) | On our catalog (VERIFIED, project log + nebius.com blog) | **Core; this is the load-bearing agent.** It reads simulator failure logs (per-stage predicates), cuRobo feasibility and the Cosmos critic output, then emits a **structured correction proposal** (JSON: `{target_stage, operator: kimodo_constraint \| curobo_offset \| timing_scale, params}`). That proposal is executed and verified with paired trials. The red team (agent 9) named this the single biggest lever | 8–12 h | **Very high** | High |
| Nemotron 3 Nano Omni | `nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16` (video+audio+image, 30B-A3B MoE, released Apr 28 2026, NVIDIA Nemotron Open Model License, FP8/NVFP4) (VERIFIED, NVIDIA tech blog) | **Not on our Sept 27 Token Factory catalog**; self-host needs FP8 (~30 GB, UNVERIFIED) | **Optional second, independent video critic**, scored against the same simulator labels. It turns "does the VLM explain the failure correctly?" into a measured inter-critic comparison (Cosmos 3 vs Nemotron Omni) rather than one opinion. Load-bearing only if actually scored | 6–8 h | Medium | Medium |
| Nemotron 3 Ultra | `nvidia/Nemotron-3-Ultra-550b-a55b` | On catalog | Adds cost, no distinct role. **Cut** | — | — | — |
| Nemotron 3.5 Lightning | `nvidia/Nemotron-3_5-Lightning` | On catalog | Possible latency-critical replacement for Nano in the live demo; not needed | — | — | — |
| Nemotron Safety Guard | (23 categories, 9 languages; UNVERIFIED ID) | — | Could guard free-text task input in the web app. **Decorative → cut** | — | — | — |

### 1.4 Simulation and infrastructure

| Tool | Facts | Role | Effort |
|---|---|---|---|
| **MuJoCo Warp** (google-deepmind/mujoco_warp, NVIDIA co-developed) | GPU MuJoCo on NVIDIA hardware (VERIFIED, repo title) | **Core for statistics.** Batch-simulate hundreds or thousands of **arm** episodes (cuRobo trajectories on our UR5e+2F-85 MJCF) on the L40S or a Serverless Job. That makes the ~60 paired trials per condition agent 4 computed cheap. The **G1/SONIC loop stays on CPU MuJoCo with the real-time C++ deploy**, so G1 trial counts stay small; state that honestly | 10–16 h |
| **Newton 1.0** (newton-physics/newton; GTC 2026; NVIDIA + DeepMind + Disney, Linux Foundation; MuJoCo Warp as primary backend) (VERIFIED, search result + repo) | License Apache-2.0 (UNVERIFIED) | Using MuJoCo Warp directly is simpler. Newton adds USD/Isaac Lab interop we don't need now. **Mention as the upgrade path, don't adopt** | — |
| Isaac Sim / Isaac Lab / **Isaac Lab-Arena** | Arena alpha v0.2.x on Isaac Lab 2.3; GR00T client-server; **subtask predicates grasp/lift/transport/place + sensitivity analysis** (VERIFIED, isaac-sim/IsaacLab-Arena). **RoboLab** (NVlabs, RSS 2026): graded scores, SPARC smoothness, failure-event logging; features being productized into Arena (VERIFIED, NVIDIA tech blog, Jul 11 2026) | **Don't port; align vocabulary.** Name our per-stage predicates exactly like Arena's (`grasp, lift, transport, place`), add RoboLab's **graded score + SPARC** to `metrics.py`, and keep a GR00T client-server contract compatible with Arena's. That signals fluency in NVIDIA's own evaluation stack at ~4 h cost. **Novelty caution:** Arena already does per-subtask failure localization and sensitivity analysis *for one embodiment*. TransferGap's claim must stay "same human demo → two embodiments → attributed gap → verified correction" | 4 h |
| Omniverse NuRec / 3DGUT | GA at GTC 2026; Gaussian-splat reconstruction, Isaac Sim integration (VERIFIED, NVIDIA/radiancefields) | Reconstructing the user's real lab as a sim scene is attractive for the KAIROS future, but out of scope. **Cut** | — |
| NIM | Cosmos3 Reasoner NIM available; Generator NIM ≥79 GiB; L40S **not** in the Cosmos NIM support matrix (VERIFIED) | Use vLLM on the L40S; NIM only on H100/H200 jobs if convenient | — |
| **Nebius Token Factory / Serverless Jobs / Endpoints** | Agent 3 | Nemotron calls; MuJoCo-Warp/SONIC sweeps as Jobs; Cosmos generator on spot H100/H200 | — |

### 1.5 Explicitly decorative → cut

Parakeet ASR (voice task input), NV-Embed (no retrieval need), Nemotron Safety Guard, Nemotron Ultra, NuRec, GR00T-Dreams/DreamGen, Cosmos Policy / Predict2.5, and an Isaac Sim/Lab port. Adding any of these would read as "logo collecting" to a technical judge.

---

## 2. Proposed final NVIDIA stack (maximum, every piece load-bearing)

```
Human RGB demo ──► GEM-X + SOMA ─────────────► SMPL stream ──► GEAR-SONIC (TensorRT) ──► G1 in MuJoCo
      │                                                              ▲
      │                                    Kimodo-G1 (EE-constraint re-generation) ─┘  ← G1 correction operator
      ├─► Cosmos 3 Reasoner: timed skill-step segmentation of the human demo
      ├─► Nemotron 3 Nano: goal → validated skill graph (reach/grasp/lift/transport/place/release)
      └─► wrist/object targets ─► cuRoboV2 (batch IK/trajopt, collision-aware) ─► UR5e+2F-85 in MuJoCo(-Warp)
                                        │                                         ▲
                                        └── pre-execution feasibility score        └ cuRobo offset re-solve ← arm correction operator
Rollouts ──► simulator stage predicates (ground truth, Arena-style names; RoboLab graded score + SPARC)
         ──► Cosmos 3 Reasoner critic (fallback Cosmos-Reason2-8B); optional 2nd critic Nemotron 3 Nano Omni
         ──► Nemotron 3 Super diagnosis agent → JSON correction {stage, operator, params}
         ──► apply via Kimodo / cuRobo ──► paired re-run (Nebius Serverless Jobs) ──► report viewer
Stretch A: GR00T N1.7-3B NEW_EMBODIMENT pilot on sim-collected arm episodes (backbone = Cosmos-Reason2-2B) = "autonomy" condition
Stretch B: Cosmos 3 forward dynamics (UR 10D) previews the correction before sim; world-model vs sim agreement reported
Stretch C: Cosmos-Transfer2.5 photoreal re-render → critic-accuracy ablation
```

The core covers 9 NVIDIA components: GEM-X, SOMA, SONIC, TensorRT, Kimodo, cuRoboV2, Cosmos 3 Reasoner, Nemotron 3 Nano, Nemotron 3 Super; plus MuJoCo Warp as an NVIDIA-co-developed simulator. The stretch goals add GR00T N1.7 (with Cosmos-Reason2-2B), Cosmos 3 generator and Cosmos-Transfer2.5. Every component either produces data the benchmark consumes, or produces an output that is **scored** against simulator ground truth.

**Hard rule, from agents 1/4:** no model (and no correction operator) may read simulator success oracles at run time. Simulator state only labels and scores.

**Suggested priority if time is short:** Nemotron Super correction loop > Kimodo + cuRobo operators > Cosmos 3 critic > GR00T pilot > Cosmos forward-dynamics preview > Transfer2.5 ablation.

**Day-1 verification tests (cheap, before committing):**
1. Does Cosmos 3 Nano reasoner load on the L40S under vLLM, and does it accept a 10 s rollout (the 5-frame question)?
2. Does `GET /v1/models` on Token Factory list any Cosmos or Nemotron Omni model?
3. Does Kimodo-G1 CSV output play through SONIC in our MuJoCo loop, or only through its own `mujoco_load`? The README says it interoperates with GEAR-SONIC for "interactive tracking" (VERIFIED wording), but the exact interface is UNVERIFIED.
4. Can cuRoboV2 load the UR5e URDF, and does its FK agree with the menagerie MJCF over multiple configurations? This closes review finding #2 (the 7.2 mm residual).

---

## 3. NVIDIA recognition levers

- **Upstream contribution (cheap, concrete):** open a PR/issue on NVlabs/GR00T-WholeBodyControl for the doc inconsistency we already found. `gear_sonic/examples/live_camera_teleop/README.md` passes `--zmq-port/--zmq-topic` to `deploy.sh`, which the tutorial says are swallowed as the positional mode argument. This is a real, verifiable fix to a GEAR repo.
- **Release artifacts in NVIDIA-native formats:** a LeRobot v2.1 dataset of paired two-embodiment rollouts with stage labels on HF, with a model-card-style README crediting SONIC/GEM-X/Kimodo/Cosmos; the TransferGap scorer aligned with Isaac Lab-Arena/RoboLab metric names.
- **Paper:** position against H2RBench (agent 1), Isaac Lab-Arena/RoboLab (single-embodiment subtask diagnosis), and Cosmos-Surg-dVRK / "Evaluating Gemini Robotics Policies in a Veo World Simulator" (arXiv 2512.10675) / SC3-Eval (arXiv 2606.18610) for the world-model-as-evaluator stretch. The survey "No Free Checker: A Survey of Verifiers for Robot Policies" (arXiv 2609.09250) is a directly relevant citation for the verifier framing. All four exist as search results (UNVERIFIED contents).
- **NVIDIA Research internships:** GEAR, the Seattle Robotics Lab and the Learning & Perception group are listed as intern hosts in the NVIDIA 2026 PhD robotics internship posting (VERIFIED as a search result, builtin.com). Kimodo comes from the Toronto AI Lab and cuRobo from SRL; building on both gives natural people to credit and contact.
- **NVIDIA Graduate Fellowship:** PhD students only (≥1 year completed), up to $60k, with a mandatory internship. The last seen deadline was Sept 15, 2025 for the 2026–27 cycle (VERIFIED, NVIDIA blog), so the next cycle is presumably ~Sept 2026–2027 (**UNVERIFIED**; check research.nvidia.com/graduate-fellowships).
- **NVIDIA Inception:** relevant only if TransferGap becomes a startup (free program; details not researched here).
- **GTC 2027 poster / NVIDIA Technical Blog guest content:** no current call found (**UNVERIFIED**; check in November).

---

## Sources
- https://huggingface.co/nvidia/Cosmos3-Nano
- https://huggingface.co/blog/nvidia/cosmos-3-for-physical-ai
- https://developer.nvidia.com/blog/develop-physical-ai-reasoning-world-and-action-models-with-nvidia-cosmos-3/
- https://recipes.vllm.ai/nvidia/Cosmos3-Nano
- https://docs.nvidia.com/nim/cosmos/3.0.0/support-matrix.html
- https://www.spheron.network/tools/gpu-recommender/nvidia/Cosmos3-Nano/ (third-party VRAM)
- https://huggingface.co/nvidia/Cosmos-Transfer2.5-2B
- https://huggingface.co/blog/nvidia/cosmos-policy-for-robot-control
- https://arxiv.org/abs/2510.16240 (Cosmos-Surg-dVRK)
- https://arxiv.org/pdf/2512.10675 (Veo world-simulator policy eval)
- https://arxiv.org/pdf/2606.18610 (SC3-Eval), https://arxiv.org/pdf/2609.09250 (No Free Checker survey)
- https://github.com/NVIDIA/GR00T-Dreams
- https://huggingface.co/nvidia/GR00T-N1.7-3B
- https://huggingface.co/nvidia/GEAR-SONIC
- https://github.com/nv-tlabs/kimodo, https://huggingface.co/nvidia/Kimodo-G1-RP-v1
- https://github.com/NVlabs/curobo, https://arxiv.org/abs/2603.05493
- https://github.com/NVlabs/FoundationPose
- https://developer.nvidia.com/blog/nvidia-nemotron-3-nano-omni-powers-multimodal-agent-reasoning-in-a-single-efficient-open-model/
- https://nebius.com/blog/posts/nemotron3-super-now-available (via agent 3)
- https://github.com/newton-physics/newton, https://github.com/google-deepmind/mujoco_warp
- https://github.com/isaac-sim/IsaacLab-Arena, https://github.com/NVLabs/RoboLab, https://developer.nvidia.com/blog/how-to-evaluate-general-purpose-robot-policies-for-real-world-deployment/
- https://developer.nvidia.com/omniverse/nurec
- https://research.nvidia.com/graduate-fellowships, https://blogs.nvidia.com/blog/applications-open-graduate-fellowship-awards-2025/, https://builtin.com/job/nvidia-2026-internships-phd-robotics-research/7018738
