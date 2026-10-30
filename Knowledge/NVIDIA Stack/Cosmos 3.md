---
type: nvidia-model
updated: 2026-09-30
tags: [nvidia, cosmos, critic, world-model]
---

# Cosmos 3

**Role.** Core video critic and event extractor: (a) segments the human demo into timed skill steps, (b) explains each rollout failure and names the failing stage, (c) labels are scored against simulator labels, so it never defines benchmark success. Stretch: forward dynamics to preview a correction. Fallback: [[Cosmos-Reason2]]. Decision: [[Decision Log]] (Sept 30).

| Field | Value | Tag |
|---|---|---|
| ID | `nvidia/Cosmos3-Nano` (16B = 8B reasoner + 8B generator); Super is 64B (datacenter only, out of budget) | VERIFIED (HF card) |
| Released | about May 31 / June 1, 2026; arXiv 2606.02800 | VERIFIED |
| License | OpenMDW 1.1, commercial and non-commercial | VERIFIED |
| Hardware | Card lists Ampere/Hopper/Blackwell, BF16 only; tested on H100 and GB200. L40S (Ada) not listed | VERIFIED; L40S fit UNVERIFIED |
| VRAM | About 34 GB for inference (third-party Spheron calculator); 16B x 2 bytes is about 32 GB weights alone | UNVERIFIED |
| Status | Not yet run by us. Token Factory listing UNVERIFIED (Sept 27 catalog of 25 models had no Cosmos model; a third-party site lists `cosmos3-super-reasoner` at $0.10/$0.30 per 1M tokens) | UNVERIFIED |

**Serving (reasoner only), VERIFIED at recipes.vllm.ai:**
`vllm serve nvidia/Cosmos3-Nano --hf-overrides '{"architectures": ["Cosmos3ReasonerForConditionalGeneration"]}' --tensor-parallel-size 1 --mm-encoder-tp-mode data --async-scheduling --allowed-local-media-path / --media-io-kwargs '{"video": {"num_frames": -1}}'`. The recipe baseline is 1x H200; `--enable-layerwise-offload` exists for small GPUs. A Reasoner NIM exists but its support matrix does not list L40S. Read the source before running (project rule).

**Generator / forward dynamics.** `vllm serve nvidia/Cosmos3-Nano --omni --init-timeout 1800`. The NIM Cosmos3-Generator nano needs at least 79 GiB per device, so it will not fit the L40S; use an H100/H200 spot Serverless Job ($0.79/h spot). The card lists UR (10D) among forward-dynamics embodiments; the Unitree G1 is not listed, so no zero-shot G1 forward dynamics. Action parameters in `extra_params["action"]` are UNVERIFIED (search snippet).

**Gotchas.**
- The card says "Video: 5 frames max" while the vLLM reasoner recipe uses `num_frames: -1`. It is UNVERIFIED which limit applies to reasoner video understanding. Test with a real 10 s rollout on day 1; the result decides Cosmos 3 versus Reason2.
- Input limits: text 4096 tokens; action trajectories 16 to 400 frames.
- Day-1 test: does it load on the L40S under vLLM, and does `GET /v1/models` on Token Factory list any Cosmos model? Save a receipt.

**Sources.** https://huggingface.co/nvidia/Cosmos3-Nano · https://recipes.vllm.ai/nvidia/Cosmos3-Nano · https://docs.nvidia.com/nim/cosmos/3.0.0/support-matrix.html · https://arxiv.org/abs/2606.02800 · reports [[10_nvidia_stack]], [[03_nebius_infra_cosmos]], [[11_cosmos_worldmodel]].

Related: [[Cosmos-Predict2.5 and Transfer2.5]] · [[GR00T N1.7]] · [[Nemotron]] · [[Nebius Infrastructure]] · [[Knowledge/README|Knowledge]]
