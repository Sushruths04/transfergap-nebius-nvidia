---
type: nvidia-model
updated: 2026-09-30
tags: [nvidia, cosmos, critic, fallback]
---

# Cosmos-Reason2

**Role.** Fallback critic if [[Cosmos 3]] fails on the L40S or its frame limit bites. The 2B variant is also the backbone of [[GR00T N1.7]], so any GR00T fine-tune uses Cosmos (say so in the write-up).

| Field | Value | Tag |
|---|---|---|
| IDs | `nvidia/Cosmos-Reason2-2B`, `-8B` (8.77B), `-32B` | VERIFIED |
| Base and license | Post-trained from Qwen3-VL-8B-Instruct; NVIDIA Open Model License (commercial OK); code Apache-2.0 | VERIFIED |
| VRAM | 2B: 24 GB; 8B: 32 GB (card min 32 GB, tested H100/A100, BF16). Fits the L40S 48 GB | fit UNVERIFIED (Ada not listed) |
| Status | The repo says "no longer under active development" and points to Cosmos 3 | VERIFIED |
| Our state | Endpoint not provisioned (as of Sept 28); the 2B is gated on Hugging Face: request access | [[Implementation Status]] |
| Benchmarks | 8B: embodied reasoning 69.34%. No published robot success/failure-detection numbers found | VERIFIED |

**Serving (VERIFIED, repo):** `vllm serve nvidia/Cosmos-Reason2-8B --allowed-local-media-path "$(pwd)" --max-model-len 16384 --media-io-kwargs '{"video": {"num_frames": -1}}' --reasoning-parser qwen3 --port 8000`. Use fps=4 (matches training). Append the `<think>` format instruction from the card and allow at least 4096 output tokens.

**Gotchas.** The existing `hosted.py` sends OpenAI-style `video_url` data-URI MP4; it must add fps and the `<think>` suffix (exact request field UNVERIFIED). Gated 2B: the user must request access, then `huggingface-cli login` or set `HF_TOKEN` on the box.

**Sources.** https://huggingface.co/nvidia/Cosmos-Reason2-8B · https://github.com/nvidia-cosmos/cosmos-reason2 · [[03_nebius_infra_cosmos]] · [[10_nvidia_stack]] · [[Knowledge/README|Knowledge]]
