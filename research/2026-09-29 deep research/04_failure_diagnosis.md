# 04 — Failure detection, diagnosis, correction & evaluation rigor (TransferGap core)

Research agent 4/6. Compiled 2026-09-29. Sources fetched via web search + WebFetch (summarizing fetcher).
Legend: **VERIFIED** = read on arXiv abstract page / official repo in this session (numbers quoted from the page);
**PARTIAL** = seen only via search-result snippet or secondary summary; **UNVERIFIED** = claim from a blog or not located.
No numbers below are invented; power calculations in §4 are my own computations with stated assumptions.

---

## 1. Failure detection & reasoning — state of the art

| Work | Date / venue | What it is | Failure taxonomy | Data / bench | Reported result | Status |
|---|---|---|---|---|---|---|
| **AHA** (NVlabs) [arXiv 2410.00371](https://arxiv.org/abs/2410.00371), [code](https://github.com/NVlabs/AHA) | Oct 2024, ICLR 2025 | VLM fine-tuned for free-form failure detection + explanation; data from **FailGen** (procedurally perturbs successful sim demos) | 7 modes: `No_Grasp`, `Slip`, `Translation` offset, `Rotation` offset, `No_Rotation`, `Wrong_Action` (sequence), `Wrong_Object` | 49k+ image-query pairs, 79 RLBench tasks; eval on ManiSkill-Fail, RoboFail | Aha-13B beats GPT-4o by 12.6% avg (Aha test), 13.4% (ManiSkill-Fail); downstream: Eureka reward +22.34% success, PRoC3S TAMP +36.7% vs GPT-4o | VERIFIED (html paper) |
| **REFLECT** [arXiv 2306.15724](https://arxiv.org/abs/2306.15724) | CoRL 2023 | Hierarchical multisensory summary (RGB-D, audio, robot state) → LLM explains failure → planner corrects | Plan-vs-execution misalignment at top level; execution detail lower | RoboFail dataset | "high success" in explanation & correction planning | PARTIAL |
| **Sentinel** [arXiv 2410.04640](https://arxiv.org/abs/2410.04640), [code](https://github.com/agiachris/sentinel) | CoRL 2024 | Two detectors: statistical **temporal action consistency** (erratic failures, cheap, fast) + **VLM** for "confident but wrong" task-progress failures | Erratic vs task-progression | Diffusion policies, mobile manipulation, sim + real | Combined detects 18% more failures than either alone | PARTIAL (search snippet of paper) |
| **RACER** [arXiv 2409.14674](https://arxiv.org/abs/2409.14674) | 2024 (ICRA 2025) | Supervisor(VLM)–actor framework; augments expert demos with auto-generated failure-recovery trajectories + rich language | — | RLBench, real | Beats RVT on long-horizon, goal-change, zero-shot | PARTIAL |
| **RoboFAC** [arXiv 2505.12224](https://arxiv.org/abs/2505.12224), [code](https://github.com/mint-sjtu/robofac), [data](https://huggingface.co/datasets/MINT-SJTU/RoboFAC-dataset) | May 2025 | RoboFAC-7B for failure analysis + correction; ManiSkill-based | "systematically categorized" (names not surfaced by fetch); 8 QA types | 9,440 failure trajectories, 78,623 QA pairs, 53 scenes, sim + real | +34.1% analysis accuracy vs GPT-4o; +29.1% relative improvement as external supervisor on 4 real tasks | VERIFIED (abstract) |
| **FailSafe** [arXiv 2510.01642](https://arxiv.org/abs/2510.01642) | Oct 2025, IROS 2026 (v4 Jul 2026) | Auto failure generation paired with executable recovery actions; FailSafe-VLM (LLaVA-OneVision-7B) | not surfaced | ManiSkill; on π0-FAST, OpenVLA, OpenVLA-OFT | "up to 22.6% on average" improvement | VERIFIED (abstract) |
| **Guardian** [arXiv 2512.01946](https://arxiv.org/abs/2512.01946), [site](https://www.di.ens.fr/willow/research/guardian/) | Dec 2025 (v4 Aug 2026) | Multi-view reasoning VLM for **planning vs execution** error verification; failures by perturbing successful trajectories | **Planning errors** vs **execution errors** | GuardianFail-36k (RLBench + BridgeDataV2); eval RoboFail, RoboVQA, UR5-Fail (new) | SOTA on 3 unseen real benchmarks; raises task success in sim + real | VERIFIED (abstract) |
| **ARMOR** (self-refining VLM) [arXiv 2602.12405](https://arxiv.org/abs/2602.12405) | Feb 2026 | Iterative detection+reasoning self-refinement, self-certainty selection | — | — | "up to 30%" detection-rate gain, "up to 100%" reasoning (LLM fuzzy match) | VERIFIED (abstract) |
| **Hide-and-Seek** [arXiv 2605.30834](https://arxiv.org/abs/2605.30834) | May 2026, NeurIPS 2026 | Failure signals for VLA runtime monitoring from **trajectory-level labels only**; conformal prediction for timeliness | — | LIBERO, VLABench, real; OpenVLA, π0, π0.5 | SOTA multi-task detection (no single number in abstract) | VERIFIED (abstract) |
| **Foresight** [arXiv 2606.23085](https://arxiv.org/abs/2606.23085) | Jun 2026 | Failure detection from **action-conditioned world-model latents**, final success labels only, functional conformal prediction | — | LIBERO-Long, ManiSkill-Long, BEHAVIOR-1K, ReactorX-200, Franka | Outperforms SOTA detectors (no single number in abstract) | VERIFIED (abstract) |
| **Cosmos-Reason1** [arXiv 2503.15558](https://arxiv.org/abs/2503.15558) | Mar 2025 | Embodied reasoning ontology explicitly includes **task-completion verification** and **failure detection** across agents incl. robot arms & humanoids | 4 capabilities × 5 agent types | — | — | PARTIAL (alphaXiv summary) |
| **Cosmos-Reason2** [HF blog](https://huggingface.co/blog/nvidia/nvidia-cosmos-reason-2-brings-advanced-reasoning) | CES 2026 | 2B/8B; 256K context; timestamps, 2D/3D points, boxes, trajectories | Blog does **not** claim failure detection | — | — | VERIFIED (blog) |

Also noted (not deep-read): REBOOT precision-assembly failure/recovery dataset [arXiv 2609.22591](https://arxiv.org/html/2609.22591); LabRobFail [2607.23704](https://arxiv.org/html/2607.23704); Robometer reward models [2603.02115](https://arxiv.org/pdf/2603.02115); Cosmos 3 tech report (Jun 2026) [pdf](https://research.nvidia.com/labs/cosmos-lab/cosmos3/technical-report.pdf) — worth a check by the NVIDIA-stack agent.

**Takeaways for TransferGap**
1. The field has converged on **perturbing successful demos to synthesize labeled failures** (AHA/FailGen, Guardian, RACER, FailSafe). TransferGap can do the same *cheaply in MuJoCo*: inject known perturbations (grasp offset, tool-frame error, scale error, timing) and get ground-truth-labeled failures for free. That also gives a known-answer test for whether Cosmos/Nemotron diagnoses correctly.
2. **Two-tier detection** (Sentinel) is the right architecture: cheap numeric signals from simulator state catch most failures; the VLM is reserved for the "looks fine but is wrong" cases and for human-readable explanations.
3. **No one owns "cross-embodiment transfer failure diagnosis from a single human demo."** Existing failure work is single-robot VLA monitoring. H2RBench (below) is the nearest competitor and explicitly reports per-method failure modes but does not do automated diagnosis → correction.

## 2. Direct competitor: H2RBench (read this before pitching novelty)

**H2RBench: A Real-to-Sim Benchmark for Evaluating Human-to-Robot Transfer** — Xiao, Zhan, Krishna, Meng, Irshad, Zakharov, Held; [arXiv 2609.24778 v2, 22 Sep 2026](https://arxiv.org/html/2609.24778v2). **VERIFIED.**
- Franka Panda; Isaac Lab via PolaRiS real-to-sim; 4 tasks (pick-place, stacking, insertion, sequential); 90 rollouts × 3 seeds per config.
- Compares 4 H2R transfer methods (Phantom, Point Policy, AMPLIFY, GHOST); multi-stage success, log-odds transfer gain; sim-real Pearson r = 0.894, Spearman 0.851, MMRV 0.06.
- Per-method failure modes are **described qualitatively**: retargeting inaccuracy & visual artifacts (Phantom), latent misalignment (AMPLIFY), keypoint tracking under occlusion (Point Policy), low-level precision & imperfect 3D hand pose (GHOST). Finding: transfer gains strongest in early stages, weak near task completion (contact-rich end).
- Limitations they state: tabletop rigid only; one arm embodiment; controlled third-person video.

**Differentiation TransferGap can honestly claim:** (a) *two different embodiments* (humanoid via Sonic + fixed/wheeled arm) from the *same* demo; (b) **stage-localized automated diagnosis** with simulator-state ground truth; (c) a **targeted correction evaluated with paired trials**. H2RBench's "late-stage contact failures dominate" finding is useful prior evidence for which failure you'll see and correct.

## 3. Automated correction — options and costs

| Approach | Key refs | What it needs | Feasible in ~3 weeks on 1× L40S? |
|---|---|---|---|
| **RHO — Repositories-as-Policies** | [arXiv 2606.16458](https://arxiv.org/abs/2606.16458) (Elmaaroufi, Svegliato, Kalade, Schelle, Seshia, Zaharia; 15 Jun 2026) **VERIFIED** abstract: LIBERO-PRO **45.0%** (OpenVLA 0.0%, π0.5 12.83%); Robosuite 70.0%; RAI O3DE held-out 23.5%→44.3% | Coding agent + evolutionary search over policy repo using env reward | Partially: search cost small per blog, but needs a reward/oracle; see oracle trap below |
| **GaP — Graph-as-Policy** | [arXiv 2607.05369](https://arxiv.org/abs/2607.05369) (Chen, Xie, … Zhu, Fan, Goldberg; UC Berkeley/NVIDIA/CMU/Bosch; 6 Jul 2026) **VERIFIED** abstract; [site](https://graph-robots.github.io/gap) | Multi-agent coding harness building perception/planning/control graphs from MORSL skill library; internal sim rehearsal | Architecture idea is reusable (named nodes = failure localization); full system too big |
| kael.tech.blog RHO-on-GaP post | blog | Claims 5.27× throughput, grasps/trial 4.17→1.04, $37 search, sim-oracle caveat (→ ~2.8× without it). Blog also cites "LIBERO-PRO 64.33%" — **does not match** RHO abstract's 45.0%; possibly a different system/split | **UNVERIFIED** — treat as anecdote |
| **Residual policy on frozen VLA** | ReCoVLA [2606.09630](https://arxiv.org/abs/2606.09630) **VERIFIED**: sim 36.7%→66.7%, zero-shot sim-to-real 61.7% avg; VLaRL [2609.30868](https://arxiv.org/abs/2609.30868v1) PARTIAL; ForceRFT [2609.22840](https://arxiv.org/pdf/2609.22840) PARTIAL | RL training loop + reward; VLM picks failure mode/recovery stage | Risky: RL tuning time; but ReCoVLA's "VLM selects failure mode → targeted residual" is the conceptual template to cite |
| **VLM-as-supervisor recovery** | RACER, RoboFAC (+29.1% rel.), FailSafe (+22.6% avg) | Fine-tuned 7B VLM | Too much data work; use off-the-shelf Cosmos/Nemotron as explainer only |
| **Calibration / frame-transform correction** | Retargeting literature (e.g., [HOCALT 2606.10743](https://arxiv.org/abs/2606.10743), [WARP 2606.29940](https://arxiv.org/html/2606.29940v1) PARTIAL) | A diagnosed systematic offset (tool-frame, base yaw, scale) → fixed transform | **Yes — cheapest, deterministic, verifiable** |
| **Object-relative target re-anchoring** | Standard in retargeting; H2RBench notes late-stage precision failures | Re-express human wrist target relative to the *robot-observed* object pose instead of human-camera-frame absolute | **Yes — cheap, and directly addresses the dominant failure H2RBench reports** |
| **Grasp-offset / approach re-plan by named-node edit (GaP-style)** | GaP, RHO | Skill graph with editable parameters; LLM proposes parameter edit from diagnosis | Yes, if kept to *parameter* edits of one node |

**The sim-oracle trap (RHO/GaP blog caveat) and how to avoid it**
- The trap: the optimized policy *calls* a privileged simulator success check at run time, so the gain would not exist on hardware.
- Rules for TransferGap: (1) simulator ground truth may **label** and **score** episodes but must never be an input to the policy or correction at run time; (2) the correction may only consume observations available on the real robot (camera, joint states, gripper width/force); (3) enforce in code — the adapter's `observe()` must not expose `ground_truth()` fields; add a unit test asserting that; (4) report any privileged-information ablation separately.

## 4. Evaluation rigor — what reviewers will find credible

**Benchmarks and validity metrics**
- SimplerEnv [arXiv 2405.05941](https://arxiv.org/abs/2405.05941) — >1,500 paired sim/real evals; introduced **MMRV** + Pearson r for sim-to-real ranking validity. PARTIAL.
- RoboArena [arXiv 2506.18123](https://arxiv.org/abs/2506.18123) — double-blind **pairwise** comparison, >600 real episodes, 7 policies, DROID. PARTIAL.
- LIBERO-Plus [arXiv 2510.13626](https://arxiv.org/abs/2510.13626) — 10,030 perturbed tasks, 7 perturbation dimensions; success drops from 95% to <30% under modest perturbation → **default LIBERO splits reward memorization**. PARTIAL. LIBERO-PRO [arXiv 2510.03827](https://arxiv.org/pdf/2510.03827) similar.
- STEP [arXiv 2503.10966](https://arxiv.org/abs/2503.10966) — sequential test for comparing two policies on binary success with near-minimal trials; avoids p-hacking from "just run a few more." PARTIAL. **Directly applicable** to TransferGap's paired comparison.
- Credible-evaluation checklist distilled: fixed protocol frozen before test; held-out scenes/demos never used to choose the correction; paired design (same seed/scene/demo both arms); report all failures; interval estimates, not only point success; sim-real caveat stated. TransferGap's `metrics.py` already implements paired bootstrap + Wilson and (as of 2026-09-28) protocol-freeze checks.

**Sample size (my computation, assumptions explicit)** — two-sided α = 0.05, power 0.80:
- *Unpaired* two-proportion test: 40%→70% needs **42/arm**; 50%→70% needs **93/arm**; 50%→80% needs **39/arm**.
- *Paired* (McNemar exact, simulated 4,000 reps) where the correction fixes a fraction *fix* of trials and breaks a fraction *brk*:
  | n paired | fix .30 / brk 0 | fix .30 / brk .05 | fix .20 / brk .05 | fix .15 / brk .05 |
  |---|---|---|---|---|
  | 20 | 0.59 | 0.33 | 0.10 | 0.03 |
  | 30 | 0.93 | 0.57 | 0.23 | 0.11 |
  | 40 | 0.99 | 0.74 | 0.37 | 0.19 |
  | 60 | 1.00 | 0.91 | 0.58 | 0.31 |
- Implication: in MuJoCo, trials are cheap — target **≥60 paired trials per condition per embodiment** (e.g., 3 demos × 20 randomized object poses/seeds), plus a separate held-out block of equal size. Independence caveat: seeds under one demo are not independent evidence about *demos*; state the unit of generalization (poses) honestly, and use ≥3 distinct demos (own recordings or HiPHI HOI clips) as blocks if claiming demo-level generality.

## 5. Proposed failure taxonomy for TransferGap

Stage-indexed (matches the Nemotron skill names already validated in `adapters.py`), each with a **simulator-state ground-truth predicate** (label source) and the **observable signal** a real robot could use (correction input):

| Stage | Code | Ground-truth predicate from sim state | Real-robot-observable signal |
|---|---|---|---|
| Perception / targeting | `P1_target_offset` | Planned grasp point distance to object CoM/grasp site > τ_p | Camera: gripper–object pixel/3D offset at pre-grasp |
| Reach / kinematics | `K1_ik_unreachable`, `K2_joint_limit`, `K3_tool_frame_error` | IK residual > τ_k; joint at limit; systematic EE-pose bias across trials | Joint states, commanded vs achieved EE pose |
| Grasp | `G1_no_contact` (≈AHA No_Grasp), `G2_bad_contact` (one finger / edge) | No finger–object contact at close; contact normals/points | Gripper width after close, force/current |
| Lift / hold | `H1_slip` (≈AHA Slip) | Object z rises then drops while gripper closed | Gripper width change, camera |
| Transport | `T1_collision` | Forbidden-contact flag (already in episode schema) | Force spike, joint torque |
| Place / release | `R1_goal_miss` (≈Translation offset), `R2_unstable` | Final object pose outside tolerance / velocity not settled | Camera final pose |
| Whole-body (G1 only) | `W1_fall`, `W2_balance_step` (Sonic "walks forward" behavior documented in live_camera_teleop.md) | Base height / fall flag; base displacement > τ_w | IMU, base odometry |
| Plan | `L1_wrong_step`, `L2_wrong_object` (≈AHA Wrong_Action/Wrong_Object, Guardian "planning error") | Executed skill sequence ≠ protocol; contact with non-target object | Nemotron plan vs execution log |

**Diagnosis pipeline**
1. Rollout logs full sim state at ≥30 Hz (`states[]` schema already exists) → deterministic **labeler** assigns first failing stage + code (ground truth; no model).
2. Cheap online detector on real-observable signals (Sentinel-style consistency + thresholds) → flags stage.
3. **Cosmos-Reason2** gets the rollout MP4 + stage prompt → timestamped natural-language explanation; **Nemotron** gets structured log → proposes a correction from a whitelist (`adjust_tool_frame`, `reanchor_target_object_relative`, `adjust_grasp_offset`, `slow_transport`). Receipts saved.
4. **Score the explainers against the labeler** (accuracy per failure code, confusion matrix). This is itself a result: "how often does a VLM correctly diagnose embodiment-transfer failures" — and it is honest because the sim label is independent.
5. Validation of the labeler: inject known perturbations (FailGen-style) and check the labeler recovers the injected code ≥ ~95% before trusting it.

## 6. Candidate correction experiments (ranked)

**E1 — Object-relative target re-anchoring (recommended primary).** Feasibility: high. Impressiveness: high (addresses H2RBench's dominant late-stage precision failure).
- Baseline: retargeted wrist trajectory replayed in robot/table frame (absolute).
- Correction: express approach/grasp/place waypoints relative to the robot-perceived object and goal pose (perception from the sim camera or noisy pose estimate — *not* the oracle pose, or add calibrated noise and say so).
- Metric: pick-place success (existing scorer), plus final object error (m) and grasp-stage success; per embodiment (arm, G1).
- Design: paired, same demo × same randomized object pose × seed; object pose randomized ±5–10 cm / ±30°. **n = 60 paired per embodiment dev + 60 held-out**; power ≈0.9 if ≥30% of trials fixed with ≤5% broken (table §4).

**E2 — Diagnosed tool-frame / calibration transform correction.** Feasibility: highest (deterministic; reuses the 7.2 mm IK-residual issue already on record). Impressiveness: medium; strong as the "diagnosis → targeted fix" demo because the cause is known and measurable.
- Inject a realistic calibration error (e.g., 1–3 cm / few-degree tool or camera extrinsic error), let the pipeline diagnose `K3_tool_frame_error` from a small dev set, estimate the fixed transform from dev trials only, apply to held-out.
- Metric: success + mean EE position error at grasp; diagnosis accuracy of Cosmos/Nemotron vs injected ground truth.
- n: 30 dev (to estimate transform) + 60 held-out paired.

**E3 — GaP-style single-node parameter edit proposed by Nemotron (stretch).** Feasibility: medium. Impressiveness: high narrative ("LLM repairs the named failing skill").
- Nemotron receives the labeled failure distribution from dev trials and may edit only whitelisted parameters of one node (grasp offset, approach height, gripper close threshold, transport speed). No sim oracle at run time (§3 rules).
- Metric: held-out paired success delta; count of edit proposals rejected by validation; cost/latency receipts.
- n: 60 held-out paired; report the number of proposals tried on dev (to expose search budget, avoid selection bias).

Stop/report rule: use STEP-style sequential testing or fix n in advance; do not add trials after peeking without a sequential method.

## 7. Gaps / not verified in this pass
- RoboFAC and FailSafe explicit failure-category names (not exposed by the fetcher; check papers' tables).
- Whether Cosmos-Reason2 was evaluated on failure detection (blog silent; Cosmos-Reason1 ontology includes it). Needs a direct test on our rollouts — which §5 step 4 provides.
- Blog's 5.27×, $37, 4.17→1.04 grasps, 64.33% LIBERO-PRO — UNVERIFIED; the arXiv RHO abstract reports 45.0% on LIBERO-PRO.
- HOCALT / WARP retargeting failure frequencies not extracted.
