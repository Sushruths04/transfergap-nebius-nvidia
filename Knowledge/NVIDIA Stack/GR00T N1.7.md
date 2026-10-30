---
type: nvidia-model
updated: 2026-09-30
tags: [nvidia, groot, vla, stretch]
---

# GR00T N1.7

**Role.** Stretch autonomy condition. User decision Sept 30: stretch goal, arm-only pilot, gated on at least 100 MimicGen-lite episodes; it does not block the core claim ([[Decision Log]]). G1 GR00T fine-tune only after at least 20 successful sim G1 grasps.

| Field | Value | Tag |
|---|---|---|
| ID | `nvidia/GR00T-N1.7-3B`; repo NVIDIA/Isaac-GR00T pinned at `51d4c89f72fda44cbf77285c6a8114b52676b8a1` | VERIFIED |
| License | NVIDIA Open Model License | VERIFIED per report 10; report 01 says confirm on card |
| Backbone | `nvidia/Cosmos-Reason2-2B`, **gated** on HF (`GatedRepoError`/401 without access) | VERIFIED |
| VRAM | Fine-tune minimum 1 GPU 40 GB+; L40-class OK for demo datasets; default tuning under about 35 GB. `--tune-llm/--tune-visual` need 80 GB+ (avoid) | VERIFIED |
| Single-GPU command | `NUM_GPUS=1`, `--global-batch-size 32`, `--max-steps 2000` on the 5-episode demo set; by default only projector and diffusion head train | VERIFIED |
| Data guidance | Simple fixed pick-place about 100 trajectories; complex 500+; humanoid 2,000+. Only published G1+SONIC policy: about 150 episodes, 20k iterations, 8/12 real-robot success | VERIFIED |
| Status | Not run by us | |

**Gotchas.**
- Gated backbone: request HF access now.
- One human clip is a demo, not a dataset. Multiply with MimicGen-lite (about 150 lines, expect 30-50% generation yield until measured); skip DreamGen/GR00T-Dreams.
- G1 route via GEM-X streams wrists/fingers as zeros, so G1 hands never close; `UNITREE_G1_SONIC` action = 64 motion-token + 7 + 7 hand joints (78-D). Exporter writes zeros if hand joints are absent. Check the parquet after the first recorded episode: all-zero `motion_token` means G1 GR00T is blocked.
- G1 MuJoCo scene has no table or object; only `ego_view` 640x480 camera.
- **LeRobot v2.1 required** at the pinned commit; current `pip install lerobot` writes v3. Reuse `gear_sonic.data.exporter.Gr00tDataExporter` (pins lerobot `a445d9c9...`) or write parquet/MP4 mirroring `demo_data/cube_to_bowl_5`.
- Ports: 5555 is taken on the Nebius image; pass `--camera-port 5560` and `--port 5550`. Set `USE_WANDB=0`.
- Recording toggle key `c` (discard `x`) goes over a ZMQ keyboard publisher on port 5580; without the PICO pane something must publish it.
- Do not run the fine-tune command from a paraphrase; read the primary doc on the machine. Use `--save-steps` at most 1000 on spot (60 s preemption notice).
- SONIC+MuJoCo is nondeterministic (upstream issue #274): run several rollouts per G1 trial.

**Sources.** https://huggingface.co/nvidia/GR00T-N1.7-3B (card looked conflated in report 01) · [[02_groot_finetune]] · [[13_synthetic_data]] · [[10_nvidia_stack]] · [[SONIC]] · [[Cosmos-Reason2]] · [[Lessons Learned]] · [[Knowledge/README|Knowledge]]
