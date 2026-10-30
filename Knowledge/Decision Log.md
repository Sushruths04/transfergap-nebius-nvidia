---
type: decision-log
updated: 2026-09-30
tags: [decisions, log, transfergap]
---

# Decision Log

Newest last. Changes to items marked "final" need the user's approval ([[Agent Handoff]] rules). Sources are notes in this vault. Index: [[Knowledge/README|Knowledge]].

| Date | Decision | Why | Source |
|---|---|---|---|
| Before Sept 27 (exact date not recorded in these notes) | Physical AI track; TransferGap is the locked project; earlier idea pitches archived | "The project remains locked for the Nebius x NVIDIA Physical AI track" | [[TransferGap]], [[Old Ideas/Home]] |
| Sept 27 | Provisioned an L40S VM in `eu-north1` (spot, `--follows-spot-price`) | Only region with L40S; $0.74/GPU-h spot vs $1.80+/h for RTX PRO 6000 | [[Implementation Status]] |
| Sept 27 | Switch to an **on-demand** L40S (`transfergap-gpu-v2`, preset `1gpu-16vcpu-64gb`) restored from a disk snapshot | Spot instance preempted mid-TensorRT build; capacity bin `1gpu-8vcpu-32gb` exhausted region-wide; preemptible spec cannot be converted; preset cannot be changed | [[Implementation Status]], [[Lessons Learned]] |
| Sept 27 | Line B arm gripper uses a pinch-distance heuristic, not a full dex_retargeting URDF pipeline | `dex_retargeting` bundled `panda_gripper.yml` uses the same thumb/index-distance pattern for any parallel gripper | [[Implementation Status]] |
| Sept 28 | Git repo scoped to `Physical AI/` only; **MIT license** | Submission needs a public repo with an OSS license and README (MIT is compliant, report 06); keep unrelated vault folders out | [[Agent Handoff]], [[06_product_hackathon]] |
| Sept 28 | Starter code fixes from the independent review (protocol-tolerance check, `validate_plan` crash, `compare` self-comparison, plan-rejection receipt); 20 tests | Review findings #3, #5 and the CLI note | [[Implementation Status]], [[Review and Next Plan 2026-09-28]] |
| Sept 28 | HiPHI pursued as a parallel track (request gated access); RHO / Graph-as-Policy not adopted as a method | HiPHI addresses the data-volume gap but is BVH, not video, and gated. RHO depends on a simulator-only success oracle | [[Implementation Status]] |
| Sept 28 | Pin upstream commits (WBC `b042411`, GEM-X `3299255`, Isaac-GR00T `51d4c89`); read primary sources verbatim before running commands | Summarizing fetch tools paraphrase; docs contradicted each other | [[Implementation Status]], [[Lessons Learned]] |
| Sept 29 | Built a local CPU-only UR5e + 2F-85 MuJoCo slice with real contact grasping (commit `cf98898`) | First real result without GPU; 510-episode sweep | [[Implementation Status]] |
| Sept 29-30 | Research closed: 13 parallel agents; **no new broad research**, only targeted checks | Execution phase starts Oct 1 | [[Research Synthesis 2026-09-30]], [[research/2026-09-29 deep research/README\|research index]] |
| Sept 30 | **Main claim = Transfer Gap Budget** (oracle-substitution decomposition per robot); second claim = diagnosis-chosen verified correction; third = Cosmos as measured critic | Ranked as most novel (C1) in report 07; closest works (H2RBench, survey) do not do per-embodiment attribution | [[Research Synthesis 2026-09-30]] §1, [[07_novelty_gaps]] |
| Sept 30 | **Cosmos 3 Nano reasoner first, Cosmos-Reason2-8B fallback** | Reason2 repo is "no longer under active development" and points to Cosmos 3; Reason2 has the simpler documented vLLM path | [[Cosmos 3]], [[Cosmos-Reason2]], [[03_nebius_infra_cosmos]] |
| Sept 30 | **Skip Managed Kubernetes**; make at least one real Serverless Job | mk8s not named in the rules, GPU scale-to-zero unconfirmed; rules name Serverless Jobs | [[Nebius Infrastructure]] |
| Sept 30 | Nemotron 3 Super is the diagnosis agent; Nano does planning | Red team named a Nemotron-in-the-loop correction the biggest lever | [[Nemotron]] |
| Sept 30 | Hosted demo URL not required for Physical AI; still build a Gradio viewer on a free HF Space | Rules page (verified by curl Sept 30) supersedes report 03; helps Design score | [[Research Synthesis 2026-09-30]] §5 |
| Sept 30 | Cuts: mk8s, mobile base, G1 autonomy / G1 GR00T fine-tune, KAIROS stack, HiPHI at scale, RHO search, WiLoR, RGB-D; decorative NVIDIA items (Parakeet, NV-Embed, Safety Guard, Ultra, NuRec, GR00T-Dreams, Cosmos Policy, Isaac port, FoundationPose) | Guarantee an honest, finished submission; avoid "logo collecting" | [[Research Synthesis 2026-09-30]] §3, §6 |
| Sept 30 | Evaluation rules frozen: at least 30 paired trials per cell; 60 dev + 60 held-out per robot; `oracle` schema field, no pooling; no-privileged-state unit test; freeze protocol in git before held-out trials | About 0.9 power for a 30% rescue with at most 5% breakage; 20 trials about 0.33 | [[Research Synthesis 2026-09-30]] §7, [[04_failure_diagnosis]] |
| Sept 30 | Arm variant: add UR10e + 2F-85 (KAIROS-matching); IK via `mink`/cuRobo | Closest public match to the KAIROS UR10 + Robotiq | [[05_embodiments_sim]] |
| Sept 30 | **User decision: GR00T is a stretch goal** (arm-only pilot, gated on at least 100 MimicGen-lite episodes) | Supersedes "never cut" in [[TransferGap]]; one clip is a demo, not a dataset | [[GR00T N1.7]], [[13_synthetic_data]] |
| Sept 30 | **User decision: submit the CoRL "Scaling H2R" 4-page workshop paper by Oct 7 AoE** | Best-fit venue; non-archival so it does not block RSS | [[Deadlines]], [[12_paper_recognition]] |
