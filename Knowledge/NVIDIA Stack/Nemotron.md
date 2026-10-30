---
type: nvidia-model
updated: 2026-09-30
tags: [nvidia, nemotron, token-factory, agent, core]
---

# Nemotron (Token Factory)

**Role.** Nano plans skill steps (goal -> validated skill graph `reach/grasp/lift/place/release`, in `adapters.py`; smoke-tested). **Super is the load-bearing diagnosis agent:** reads simulator per-stage predicates, cuRobo feasibility and the Cosmos critic output, and emits a structured correction proposal `{target_stage, operator: kimodo_constraint | curobo_offset | timing_scale, params}` from a fixed menu; the proposal is executed and verified with paired trials. The red team named this the biggest lever (report 09).

| Model | ID | Notes | Tag |
|---|---|---|---|
| Nemotron 3 Nano | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | On our Token Factory catalog; smoke call succeeded Sept 27 | VERIFIED (project log) |
| Nemotron 3 Super | `nvidia/nemotron-3-super-120b-a12b` (120B / 12B active, up to 1M context) | On our catalog; dedicated endpoints EU/US, optional zero-retention | VERIFIED |
| Nemotron 3.5 Lightning | `nvidia/Nemotron-3_5-Lightning` | On catalog; possible low-latency Nano replacement in the live demo; not needed | |
| Nemotron 3 Ultra | `nvidia/Nemotron-3-Ultra-550b-a55b` | On catalog; cut (cost, no distinct role) | |
| Nemotron 3 Nano Omni | `nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16` (video+audio+image, released Apr 28 2026) | Not on our catalog; self-host FP8 about 30 GB UNVERIFIED. Optional second independent video critic, only if scored | VERIFIED existence |
| Safety Guard | ID UNVERIFIED | Decorative, cut | |

**Smoke receipt (Sept 27).** Response `chatcmpl-bcc65a3f-5479-4c5a-b18e-02d767f5d14d`, about 2.20 s, 103 prompt + 387 completion = 490 tokens; validated against the allowed-skill and shape checks. Receipt: `transfergap/runs/nemotron-access-smoke.json` (gitignored `runs/`; adding it needs the user's `git add -f`). Catalog returned 25 models. Token Factory catalog does not enumerate Serverless endpoints and does not establish fine-tuning support; Nemotron is not in the fine-tuning list.

**Prices (UNVERIFIED on Nebius).** Nano $0.05 in / $0.20 out per 1M tokens (OpenRouter-reported); Super median across providers $0.30 / $0.80. Check the console.

**Gotchas.** A rejected plan must still complete the receipt with `validated: false` and `validation_error` (fixed Sept 28). No correction may read simulator success. Check `NEBIUS_API_KEY` and model env vars still valid before use.

**Sources.** https://nebius.com/blog/posts/nemotron3-super-now-available · [[03_nebius_infra_cosmos]] · [[10_nvidia_stack]] · [[Implementation Status]] · [[Nebius Infrastructure]] · [[Cosmos 3]] · [[Knowledge/README|Knowledge]]
