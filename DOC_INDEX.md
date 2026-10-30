# Document index (2026-10-06 night): what each file is and whether to trust it

**NEW** = written in the last day. **CURRENT** = kept up to date, trust it. **LOG** = append-only history. **HISTORICAL** = banner at the top says so; its status claims are out of date.
Scope decisions that apply everywhere: cluster only (GPU cluster, one L40S), no Nebius, no Isaac Sim, simulation only, no spending, never publish or submit without the user.

## Start here, in this order
| File | Status | Read it for |
|---|---|---|
| `STATUS_AND_OBJECTIVE.md` | **NEW, CURRENT** | the objective, a table of every stage (VERIFIED / PARTIAL / NOT DONE), counts, ranked bugs, what is needed from the user |
| `DEEP_ANALYSIS_REALISM_AND_REALTIME.md` | **NEW, CURRENT** | what in the demo is real vs assumed (the box-to-plate distance is NOT preserved), real-time control levels, UI, data to record, open scope |
| `research/GEMINI_RESEARCH_REQUESTS.md` | **NEW** | eight self-contained research prompts to hand to Gemini |
| `RECORDING_PROTOCOL.md` | **NEW** | exactly what to print, measure and record next (marker, tape numbers, takes) |
| `PIPELINE.md` | **NEW, CURRENT** | how to run each stage and the verified results (commands, limits, the metric-scale bug) |
| `HANDOFF.md` | CURRENT | the ordered to-do list, resume commands, rules that never change |
| `COORDINATION.md` | LOG (newest first) | what each agent did and when; the top entries are today's |
| `AGENTS.md` | CURRENT | rules for any coding agent (no AI attribution, cluster only, volume safety) |
| `Master Plan 2026-10-04.md` | CURRENT (sections 0d, 0c, 0b newest; the rest is the plan as of Oct 4) | architecture, NVIDIA stack, KAIROS, decisions |
| `README.md` | CURRENT | project front page |

## Evidence
| Folder | Status | Content |
|---|---|---|
| `transfergap/results/` | CURRENT, each folder frozen | 79 result folders; each has its own README or protocol. Superseded runs carry a SUPERSEDED line (`cluster_pipeline_user_v1`, `cluster_cam_user_rtmw3d_v1`) |
| `transfergap/results/OVERVIEW_human_demo.md` | CURRENT for the lane-B experiments up to 2026-10-04 | per-experiment summaries |
| `paper/SUBMISSION_CHECKLIST.md` | **NEW** | venue rules read today, what is ready, what you must do, the facts you may state and their sources, schedule to the Oct 7 AoE deadline |
| `paper/` | CURRENT | `main.tex`, review findings, the corrected abstract/conclusion draft, the external reviewers review prompt |
| `deliverables/` | untracked on purpose | videos: `TransferGap_integrated_demo_2026-10-06.mp4`, `kairos_mobile_demo_2026-10-06.mp4`, `transfergap_final_2026-10-06.mp4` (an earlier cut, now superseded by the integrated demo) |
| `research/EgoExo4D-HM analysis 2026-10-06.md` | **NEW** | analysis of the Ego-Exo4D human-meshes dataset: useful later as a source of more demonstrations |

## Historical (kept, banner added)
`Agent Handoff.md`, `Implementation Status.md`, `Execution Plan 2026-10-01.md`, `Research Synthesis 2026-09-30.md`, `Review and Next Plan 2026-09-28.md`, `TransferGap.md`, `TransferGap Research Review.md`. `KAIROS Stack Audit.md` has an update banner (KAIROS is modelled in MuJoCo, not Isaac Sim). `transfergap/docker/README.md` describes the old Nebius image and is marked historical; `transfergap/docker/UNIFIED_IMAGE.md` has a 2026-10-06 update block.

## What works today (one line each; details in `STATUS_AND_OBJECTIVE.md`)
- Video to pose on the cluster GPU (static camera only), person measurements with overlay, metric rescale from an assumed shoulder width.
- Copy of the demonstration by UR5e, UR10e, KAIROS arm and KAIROS mobile in MuJoCo, 60 seeds each, with the corrected fix stack: 60/60 (from 35, 36, 49, 49).
- G1 mimicry of the person's wrists, neck and pinch (one run, one clip, no fall; sideways wrist r = -0.95, weak forward depth).
- One image (`full-2026-10-06c`) passing 8 of 8 end-to-end stages; live webcam path at 17-21 fps with a video stand-in.

## What is not done (the scope still left)
Real scene geometry in the sim; metric scale and depth from a marker or a depth camera; live G1 on the cluster; a command UI and a polished operator console; a reliable G1 grasp; more people and clips; one-command integrated demo in the image; non-static video pose; paper rewrite (by the user). Full list with effort estimates: `DEEP_ANALYSIS_REALISM_AND_REALTIME.md` section 6.
