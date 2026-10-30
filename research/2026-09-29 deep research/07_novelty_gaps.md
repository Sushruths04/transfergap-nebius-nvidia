# 07 — Novelty gaps for TransferGap (research agent 7)

Date: 2026-09-29. Scope: where TransferGap is actually novel. This is not a general SOTA survey (that's agent 1).
Legend: **VERIFIED** means I read the arXiv abstract or HTML page, or the GitHub README, myself. **UNVERIFIED** means the claim comes from a search snippet or secondary summary only. Every source was read through a summarizing fetch tool, so exact numbers should be re-checked against the PDF before we quote them publicly.

---

## 1. Closest existing work and what each one does NOT do

| # | Work | What it does | What it does NOT do (our opening) | Status |
|---|---|---|---|---|
| 1 | **H2RBench**: *A Real-to-Sim Benchmark for Evaluating Human-to-Robot Transfer*, arXiv [2609.24778](https://arxiv.org/abs/2609.24778), submitted to CoRL 2026, Sept 21–22 2026. Authors: Xiao, Zhan, Krishna, Meng, Irshad, Zakharov, Held. Code: [github.com/xiaochy/H2RBench](https://github.com/xiaochy/H2RBench) (MIT). | Compares H2R *methods* on 4–5 tabletop tasks: Diffusion Policy, AMPLIFY, GHOST, Point-Policy, among others. Studies how each scales with human data. Sim-to-real correlation r=0.89, ρ=0.85. Built on PolaRiS / IsaacLab with Gaussian-splat scenes. | **One embodiment only**: the DROID Franka + Robotiq 2F-85. No humanoid. No one-demo-to-two-embodiments comparison. No attribution of failure to a component (perception / kinematics / contact / timing). No correction loop. It ranks methods; it does not diagnose *why* transfer fails on a given robot. | VERIFIED (abstract + README) |
| 2 | **The Embodiment Gap in Robot Foundation Models**, arXiv [2608.18433](https://arxiv.org/abs/2608.18433), Aug 2026 (Domae et al.) | A survey. Proposes an 11-item "report card" for cross-embodiment work. It includes a **4-stage failure categorization**: semantics/perception, data-interface, correspondence, execution. It also proposes an **Embodiment Adaptation Curve** (performance vs. adaptation effort). | **It is a proposal on paper, not a tool or a measurement.** Nothing is instantiated, no counterfactual measurement of each stage's share, no code. **This is our single biggest opening:** TransferGap can be the first *executable* version of this report card. | VERIFIED (abstract + HTML) |
| 3 | **Human-as-Humanoid**, arXiv [2606.32009](https://arxiv.org/abs/2606.32009), June 2026 | Converts ego-exo human video into actions for a human-aligned 60-DoF upper-body humanoid (PrimeU). Validates at the motion-recovery, action-space, and real-deployment levels. | A single target platform, so no comparison across embodiments. Staged validation, but no failure attribution. No post-hoc correction. | VERIFIED (abstract) |
| 4 | **What Matters When Cotraining Robot Manipulation Policies on Everyday Human Videos?**, arXiv [2606.06627](https://arxiv.org/abs/2606.06627), June 2026 | **The closest prior work to our "mocap vs monocular" ablation.** Compares multiview-triangulated hands against the monocular HaWoR estimator, plus calibrated noise injection. Finding: *"hand quality matters, but even with accurate hands, the inherent motion gap hinders transfer."* | **One embodiment** (AgileX Piper arm). The HTML says outright: **no explicit quantitative decomposition** of perception vs. motion. Everything is framed as a policy-training (cotraining) recipe, not a diagnostic. | VERIFIED (abstract + HTML) |
| 5 | **Demonstrate once, execute on many: Kinematic intelligence for cross-robot skill transfer**, *Science Robotics* ([doi 10.1126/scirobotics.aea1995](https://www.science.org/doi/10.1126/scirobotics.aea1995)), EPFL, ~April 2026 | One human demo turned into a globally stable dynamical system that respects each robot's joint limits and singularities. Executed on 3 different commercial arms. A search snippet says reachability similarity predicts transfer feasibility. | Kinematics only: no contact/grasp or perception attribution. Industrial arms only, no humanoid. No failure-cause decomposition. Its goal is to *make* transfer work, not to *measure* the gap. | UNVERIFIED (the paper page returned 403; content comes from [EPFL news](https://actu.epfl.ch/news/how-to-teach-the-same-skill-to-different-robots-4/) and [TechXplore](https://techxplore.com/news/2026-04-kinematic-intelligence-robots-task-safely.html) snippets) |
| 6 | **FeasibleCap**, arXiv [2603.07580](https://arxiv.org/abs/2603.07580) | Gives the demonstrator real-time feedback during capture: reachability, joint-rate limits, and collisions against a target robot. | Prevention at capture time for one target robot. It does not predict success across embodiments or attribute failures after execution. | VERIFIED (abstract) |
| 7 | **BeyondRetarget**, arXiv [2609.29850](https://arxiv.org/abs/2609.29850), Sept 2026 | Maps monocular RGB directly to humanoid motion. A search snippet says it includes an *oracle-SMPL* comparison showing the retargeting stage itself adds error. | **Motion tracking only, no objects.** The abstract does not mention the oracle ablation, and the snippet version is unverified. No manipulation success, no second embodiment. | Partially VERIFIED (abstract); oracle claim UNVERIFIED |
| 8 | **RoboMD**, arXiv [2412.02818](https://arxiv.org/abs/2412.02818), ICLR 2026 | Trains an RL agent to *find* vulnerabilities (failure-inducing conditions) of a single manipulation policy. | Searches for failure conditions. It does not attribute them to pipeline components, and nothing is human-demo or cross-embodiment. | UNVERIFIED (search snippets) |
| 9 | **ProTracer**, arXiv [2609.21369](https://arxiv.org/abs/2609.21369), Sept 2026 | Training-free VLM plus proprioception for temporal failure diagnosis and explanation. | No component attribution, no counterfactuals, no cross-embodiment, no human demos. It could serve as our *explainer* baseline. | VERIFIED (abstract) |
| 10 | **ActiveArena**, arXiv [2609.24124](https://arxiv.org/pdf/2609.24124) | Splits failed episodes into mutually exclusive states (Discovery Miss / Context Omission / Context Retained). This is the closest *style* to our decomposition. | Active perception only. Single robot. No H2R. | UNVERIFIED (snippet) |
| 11 | **Sugar**, arXiv [2605.20373](https://arxiv.org/abs/2605.20373) | Human video → G1-style humanoid loco-manipulation with autonomous recovery. | Single humanoid. No embodiment comparison, no diagnosis breakdown. | VERIFIED (abstract) |
| 12 | **SONIC**, arXiv [2511.07820](https://arxiv.org/abs/2511.07820) | Our G1 controller. 123/124 motions transfer sim→real. | Motion tracking. Makes no manipulation or H2R-gap claims. | UNVERIFIED (snippet) |

**Other signal (strong evidence that this is an open question):** the **CoRL 2026 "Scaling H2R" workshop** ([scaling-h2r-corl.github.io](https://scaling-h2r-corl.github.io/)) lists as an open research question: *"how do morphological, kinematic, and contact/force mismatches degrade transfer."* Key facts from the page:
- The call treats this as an open investigation, not a solved problem.
- **Submission deadline: Oct 7, 2026 (AoE)**, 4–8 pages, non-archival.
- **NVIDIA sponsors a Best Paper Award.**
- Workshop date: Nov 12, 2026.

VERIFIED (workshop page).

**Bottom line of the search:** I found no published work that does all three of these:
- (a) takes one human demo,
- (b) runs it on two very different embodiments (humanoid + arm),
- (c) *quantitatively decomposes* the resulting gap into pipeline components by swapping in oracles in simulation.

The pieces exist separately:
- H2RBench: a standardized H2R evaluation protocol, one robot.
- The Embodiment Gap survey: a failure-stage taxonomy on paper.
- 2606.06627: a hand-quality ablation, one robot.

**Nobody has built the counterfactual gap decomposition across embodiments.** Caveat: absence of evidence after roughly 15 targeted searches is not proof. Re-check arXiv the week before submission.

---

## 2. Five candidate novelty claims

### C1. Counterfactual gap decomposition ("TransferGap attribution") ⭐ PRIMARY
- **Claim:** For one human demonstration executed on two embodiments, TransferGap quantifies how much of each robot's success gap is due to perception, retargeting/kinematics, contact/grasp, and timing. It does this by replacing one pipeline stage at a time with a simulator oracle and measuring how much success recovers.
- **Why unclaimed:** Several near misses leave this open:
  - The Embodiment Gap survey [2608.18433] *proposes* the stage taxonomy but measures nothing.
  - 2606.06627 explicitly lacks a quantitative perception-vs-motion decomposition, on one robot.
  - H2RBench compares methods, not causes.
  - The CoRL'26 H2R workshop lists this as open.
- **Minimal 3-week experiment (1 L40S + Nebius CPU jobs):**
  - One block-to-tray task, two embodiments: G1 via SONIC, and the UR5e+2F85 fixed-base arm.
  - Pipeline: human clip → GEM-X/WiLoR → retarget → controller → simulator-state scoring. The scorer already exists in `metrics.py`.
  - Oracle swaps, one at a time:
    - (i) **perception oracle**: ground-truth human/object pose. Use HiPHI mocap or synthetic ground truth instead of monocular estimates.
    - (ii) **kinematic oracle**: IK solved directly to the object-relative target instead of mimicking the human wrist path.
    - (iii) **contact oracle**: scripted grasp at the known object pose. Report it separately as an *upper bound* and never mix it into success claims.
    - (iv) **timing oracle**: slowed or re-timed trajectory.
  - For each condition, N≥30 independent trial blocks with seeds and object-pose jitter. Metric: Δ success from each oracle, with paired bootstrap. `paired_gap` already exists.
  - Nebius Serverless Jobs / K8s run the sweep. That's a real use of the platform the rules explicitly encourage.
- **Output artifact:** a stacked-bar "gap budget" per embodiment.
- **Risk: MEDIUM.**
  - Main risk: G1 may not grasp at all. If so, its gap is dominated by "contact," which is still a valid, reportable finding.
  - Interaction effects: oracles are not additive. Report single-swap *and* all-but-one to show the interactions honestly.
  - Must avoid the RHO trap: oracles are diagnostic tools only, never part of a deployable claim.

### C2. Executable "Embodiment Report Card", the first instantiation of the 2608.18433 framework ⭐ SECONDARY (packaging/product claim)
- **Claim:** TransferGap is the first open tool that automatically produces the 11-item cross-embodiment report card and Embodiment Adaptation Curve proposed by Domae et al., from real simulator traces. It covers failure causes, calibration, interventions, and adaptation effort.
- **Why unclaimed:** The survey is a proposal only. I found no implementation (UNVERIFIED as a negative; searches returned none).
- **Minimal experiment:** Mostly engineering on top of C1:
  - Emit JSON + HTML report card per (demo, embodiment) from the episode logs and receipts that already exist.
  - Plot the adaptation curve: success vs. # corrective iterations or # synthetic demos.
  - Nemotron writes the narrative. Cosmos-Reason2 annotates video events. Neither is allowed to set labels.
- **Why pair it with C1:** It makes the research result a *product* (a "CI report for robot policy transfer"). It is easy for judges to see, and it cites a fresh (Aug 2026) peer framework, which gives credibility.
- **Risk: LOW.** Pure software, driven by data we'll already have.

### C3. Pre-execution Transfer Gap Score (predict before running the robot)
- **Claim:** Cheap features computed from the human demo plus the embodiment model predict per-embodiment success before any rollout:
  - reachability coverage of the retargeted path,
  - joint-limit and velocity margin,
  - grasp-width feasibility,
  - pose-estimation confidence,
  - retarget residual (like the 7.2 mm IK residual).
- **Why partly claimed:**
  - EPFL *Science Robotics* reportedly uses reachability similarity as a feasibility predictor (UNVERIFIED).
  - FeasibleCap checks feasibility at capture time.
  - H2RBench predicts *real* from *sim* (r=0.89), not success from pre-execution features.
  - So a multi-factor score across humanoid + arm is new-ish, but the novelty margin is thin.
- **Minimal experiment:** Needs many (demo, perturbation) pairs:
  - e.g. 20 HiPHI HOI clips × pose jitter.
  - Fit logistic regression.
  - Report AUROC with leave-one-demo-out validation.
- **Risk: MEDIUM-HIGH.** It needs many diverse demos. With one demo it's statistically meaningless, and HiPHI access approval is not guaranteed in time. Make it a stretch goal, fed by C1's data.

### C4. Mocap-vs-monocular controlled ablation across two embodiments
- **Claim:** The same HOI motion, from optical mocap (HiPHI) vs. monocular estimation of a render or recording of it, measures the perception share of the gap *per embodiment*. The prediction is that the humanoid (whole-body tracking) and the arm (wrist + gripper) differ in how sensitive they are to perception error.
- **Why partly claimed:** 2606.06627 already did triangulated-vs-monocular plus noise injection, on one arm. Our delta is the two embodiments plus a humanoid.
- **Minimal experiment:**
  - The cleanest version: take a HiPHI clip, render it (or use our own clip), and compare HiPHI ground truth vs. GEM-X-estimated poses. Alternatively, inject noise calibrated to GEM-X error, following 2606.06627's recipe.
  - Run both through both robots. This is the same machinery as C1's perception oracle.
- **Risk: MEDIUM.** It depends on HiPHI access, plus rendering or finding a video with ground truth. Noise injection is the fallback and needs no HiPHI.
- **Verdict:** Fold this into C1 as the *perception-oracle arm* rather than claiming it separately.

### C5. Diagnosis-targeted correction verified with paired trials
- **Claim:** The largest component from C1's decomposition picks *which* correction to apply, per embodiment. Examples:
  - calibrated tool-frame transform or object-relative target for the arm,
  - re-timing or grasp-pregrasp offset for G1.
- The targeted correction beats an untargeted one on held-out paired trials.
- **Why partly claimed:**
  - Correction per se is common: residual policies, RHO, and EgoRecovery [2607.19745] learns recovery from human recovery demos.
  - What's new is *diagnosis-selected* correction per embodiment from one demo.
- **Minimal experiment:**
  - 2 corrections × 2 embodiments.
  - Tune on dev seeds, evaluate on held-out seeds with `paired_gap`.
- **Risk: MEDIUM.** It depends on C1 finding a dominant, fixable component. It's a good *demo moment* (before/after), but only claim it if the paired interval excludes 0.

---

## 3. Ranking

| Rank | Claim | Novelty | Feasibility (3 wks) | Demo value | Overall |
|---|---|---|---|---|---|
| 1 | **C1 Counterfactual gap decomposition** | High | Medium | High (gap-budget bars per robot) | **Primary** |
| 2 | **C2 Executable Embodiment Report Card** | Medium-High (first implementation) | High | High (product artifact) | **Secondary** |
| 3 | C5 Diagnosis-targeted correction | Medium | Medium | Very high (before/after) | Include if C1 shows a dominant fixable factor |
| 4 | C4 Mocap vs monocular | Medium (one-robot version exists) | Medium | Medium | Merge into C1 perception oracle |
| 5 | C3 Pre-execution score | Low-Medium | Low | Medium | Stretch / future work |

## 4. Recommendation

- **Primary claim (C1):** *"From a single human demonstration, TransferGap measures a robot's transfer gap and attributes it to perception, kinematic, contact and timing causes via simulator oracle counterfactuals. We show on a humanoid (G1/SONIC) and an arm (UR5e) that the same demo fails for different reasons."*
- **Secondary claim (C2):** *"TransferGap outputs the first executable instance of the cross-embodiment report card proposed in [2608.18433]: a per-robot transfer report usable as a pre-deployment check."*
- C5 is the demo's "wow" moment, conditional on the evidence.

Concrete adjustments this implies for the plan:
1. Add an `oracle` field to the episode schema, taking one of `none|perception|kinematic|contact|timing`, and forbid pooling across oracle values. This extends tonight's `validate_protocol_consistency`.
2. The contact oracle must be reported as an upper bound only (avoids the RHO sim-oracle trap: agent 4's topic).
3. Budget ≥30 independent trial blocks per (embodiment × oracle) cell. With 2 embodiments × 5 conditions, that's ≥300 episodes. That's why the Nebius job sweep matters (agent 3's topic).
4. **Optional:** submit a 4-page version to the **CoRL 2026 Scaling H2R workshop by Oct 7 AoE**. It's non-archival, it has an NVIDIA Best Paper Award, and it matches our research question exactly. It's tight (8 days away). It only makes sense if a preliminary decomposition on the arm exists by ~Oct 5.

## 5. Things I could not verify (re-check before publicly claiming novelty)
- The EPFL *Science Robotics* paper's exact predictor and results (403 on science.org).
- Whether BeyondRetarget's oracle-SMPL ablation exists (snippet only).
- ActiveArena and RoboMD details (snippets only).
- Whether any Sept 2026 arXiv paper after ~Sept 25 overlaps. Re-run searches for "embodiment gap decomposition", "oracle counterfactual human-to-robot", and "transfer report card" before Oct 29.
