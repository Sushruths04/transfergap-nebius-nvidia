---
type: related-work
updated: 2026-09-30
tags: [related-work, novelty, citations]
---

# Related Work

One line per paper. Tags are from [[01_transfer_sota]], [[11_cosmos_worldmodel]], [[10_nvidia_stack]], [[12_paper_recognition]]. Framing to keep: "we did not find prior work", not "no one has done it". Re-check arXiv for anything after Sept 25 before publishing. Back to [[Home]] · [[Knowledge/README|Knowledge]].

## Must cite and position against

| Work (ID / URL) | What it does | How TransferGap differs | Tag |
|---|---|---|---|
| **H2RBench**, arXiv 2609.24778 (2026-09-21), CMU/TRI; github.com/xiaochy/H2RBench | Real-to-sim benchmark, 4 tasks, compares 4 transfer methods on one robot; sim-vs-real correlation; no prescriptive corrections | We hold the demo fixed and vary embodiment, and add attribution plus verified correction | VERIFIED |
| **The Embodiment Gap in Robot Foundation Models**, arXiv 2608.18433 (AIST survey) | Defines the embodiment gap; two-axis map; proposes a reporting framework; no experiments | TransferGap is the empirical instrument for that framework | VERIFIED |
| **HF-WM** "Beyond Successful Robot Demonstrations", https://peiyantu.github.io/HF-WM/ | World model on human egocentric video with failure-aware post-training; policy-eval Pearson 0.983 | Single robot; no two-embodiment comparison of one demo; no stage attribution. The paper a reviewer will raise | Project page VERIFIED; arXiv id not found |
| **SONIC**, arXiv 2511.07820 (Science Robotics 2026) | G1 whole-body tracking foundation controller ([[SONIC]]) | We build on it and stress-test it on manipulation | cited in report 12 |
| **GENMO / GEM-X**, arXiv 2505.01425 (ICCV 2025) | Video-to-motion ([[GEM-X]]) | We measure its perception share of the gap | cited in report 12 |
| **GR00T N1**, arXiv 2503.14734 | VLA foundation model ([[GR00T N1.7]]) | Stretch autonomy condition | cited in report 12 |
| **Cosmos 3**, arXiv 2606.02800 | Omni reasoner + generator ([[Cosmos 3]]) | We score it as a critic against simulator labels | SNIPPET-level detail |

## Human video and transfer

| Work | What it does | Difference | Tag |
|---|---|---|---|
| Human-as-Humanoid, arXiv 2606.32009 | Human video to executable data for a 60-DoF upper-body humanoid | Single embodiment, data conversion, no gap measurement | VERIFIED |
| HumanEgo, arXiv 2605.24934 | Egocentric video to entity-level hand-object representation; claims cross-platform | A method; does not diagnose where each embodiment fails | VERIFIED |
| H2R-Bench (hyphen), arXiv 2608.13049 | Benchmarks world-model video generation of human-to-robot | Generated video, not physics; borrow "embodiment correctness", "functional contact transfer" | UNVERIFIED |
| HEX, arXiv 2604.07993 | Humanoid-aligned universal state across embodiments | Learned analogue of our shared object-relative target | VERIFIED |
| EgoScale (NVIDIA GEAR) | Human-to-robot transfer scales log-linearly | We measure where it breaks per embodiment | see [[People and Labs]] |
| EgoMimic, Phantom, EgoVLA, Being-H0.x, EgoVerse 2604.07607, HumanScale 2606.20521, others | Egocentric pretraining line | Pretraining methods; related work, not dependencies | UNVERIFIED (snippets) |
| GMR, arXiv 2510.02252 (MIT); github.com/YanjieZe/GMR | Motion retargeting incl. G1; BVH inputs | Tool for HiPHI BVH to G1; needs a joint map | VERIFIED |
| HiPHI, arXiv 2608.16222 (CoRL 2026) | 617.5 h optical mocap, 39.8% human-object interaction, 55-joint BVH, gated ModalityNet Open Research License; commercial use needs a separate licence | Optional mocap-vs-monocular ablation; never redistribute | VERIFIED |

## Failure diagnosis and evaluation

| Work | What it does | Difference | Tag |
|---|---|---|---|
| NVIDIA Isaac Lab-Arena and RoboLab (RSS 2026) | Subtask predicates (grasp, lift, transport, place), sensitivity analysis, graded score, SPARC | Single embodiment. Reuse names; cite | VERIFIED (repos, blog) |
| RHO, arXiv 2606.16458 (Seshia, Zaharia et al.) | Coding agents search over repositories-as-policies | Depends on a simulator success oracle; we forbid that. Blog numbers are not the paper's | VERIFIED |
| GaP, arXiv 2607.05369 (Jim Fan, Goldberg et al.) | Graph-as-policy harness | Skill graph as unit of diagnosis; NVIDIA-aligned | VERIFIED |
| No Free Checker survey, arXiv 2609.09250 | Verifiers for robot policies | Framing citation | UNVERIFIED contents |
| AHA, RoboFAC (per [[04_failure_diagnosis]]) | Failure reasoning | Explainers, scored against our labels | see report 04 |

## World models as evaluators

| Work | What it does | Difference | Tag |
|---|---|---|---|
| WorldGym, arXiv 2506.00613 | Video WM as simulator; r = 0.78 vs real success | Ranks policies on one robot | VERIFIED |
| WorldEval, arXiv 2505.19017 | Ranks policies in imagination | One platform | UNVERIFIED numbers |
| dWorldEval, arXiv 2604.22152 | Discrete-diffusion WM evaluator | Not cross-embodiment or human demo | abstract VERIFIED |
| FARM, arXiv 2609.11445 | Readout on frozen WM for step-wise failure scores; cross-embodiment readout transfer | Not human-demo transfer | VERIFIED |
| DreamDojo, arXiv 2602.06949 | WM on 44k h egocentric human video | Generalist simulator, not per-demo gap prediction | VERIFIED |
| DreamGen / GR00T-Dreams, arXiv 2505.12705 | Synthetic neural trajectories for GR00T | Data generation, not failure prediction; cut | VERIFIED |
| Cosmos-Surg-dVRK, arXiv 2510.16240 (NVIDIA) | Cosmos WM as policy evaluator with a V-JEPA 2 judge | Single embodiment; template for rollout plus separate judge | VERIFIED |
| Veo world simulator policy eval, arXiv 2512.10675; SC3-Eval, arXiv 2606.18610 | World-model evaluation | Cited for stretch | UNVERIFIED |
| RoboTrustBench, arXiv 2606.01600 | WMs look coherent but fail on contact and constraints | Warning for Tier 2 | VERIFIED |

## Synthetic data

MimicGen, arXiv 2310.17596 (object-centric transform; generation success 8.2 to 82.3% by task; NVIDIA Source Code License, check terms) is the basis for MimicGen-lite. DexMimicGen, SkillMimicGen and Isaac Lab Mimic are not adopted. See [[13_synthetic_data]].

## Novelty verdict (report 01, 07, 11)

No work found combining one human demo, two morphologically different robots, simulator-state labels, measured per-embodiment cause attribution and a verified correction. The CoRL Scaling H2R workshop lists this open question. Before publishing: re-check arXiv after Sept 25, read HF-WM and BeyondRetarget's oracle ablation. See [[Research Synthesis 2026-09-30]] §1 and [[Decision Log]].
