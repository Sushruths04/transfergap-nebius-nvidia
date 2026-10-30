---
type: index
updated: 2026-09-30
tags: [knowledge, moc, transfergap]
---

# Knowledge — map of content

Atomic notes distilled only from the Sept 29-30 research reports, [[Research Synthesis 2026-09-30]] and [[Implementation Status]]. Nothing here is new research. VERIFIED / UNVERIFIED tags are copied from the reports: VERIFIED means the primary page was fetched (via a summarizing tool), not that a full PDF was read. Where a note disagrees with the synthesis, the synthesis wins.

Back to [[Home]] · [[Agent Handoff]] · [[research/2026-09-29 deep research/README|research index]]

## Project memory
- [[Decision Log]] — every decision so far, dated, with why and source.
- [[Deadlines]] — hackathon, workshop, GTC, RSS, with verification status.
- [[Lessons Learned]] — practical gotchas already hit.
- [[Ideas Backlog]] — stretch ideas, not committed.
- [[Glossary]] — terms and acronyms.

## Context
- [[Related Work]] — papers and how TransferGap differs.
- [[People and Labs]] — NVIDIA researchers and groups, why they matter.
- [[Nebius Infrastructure]] — VM, Serverless Jobs, Endpoints, Token Factory, costs, resource IDs.

## NVIDIA stack (one note each)
Core: [[GEM-X]] · [[SONIC]] · [[Kimodo-G1]] · [[cuRoboV2]] · [[Cosmos 3]] · [[Nemotron]] · [[MuJoCo Warp]]
Fallback and stretch: [[Cosmos-Reason2]] · [[GR00T N1.7]] · [[Cosmos-Predict2.5 and Transfer2.5]]

Pipeline in one line: human RGB demo -> GEM-X+SOMA -> SONIC -> G1 (MuJoCo); wrist/object targets -> cuRoboV2 -> UR arm (MuJoCo); rollouts scored by simulator predicates -> Cosmos critic (scored against them) -> Nemotron 3 Super diagnosis -> Kimodo / cuRobo correction -> paired re-run in a Nebius Serverless Job.
