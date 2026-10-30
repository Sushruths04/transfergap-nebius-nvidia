---
type: nvidia-model
updated: 2026-09-30
tags: [nvidia, cosmos, world-model, stretch]
---

# Cosmos-Predict2.5 and Cosmos-Transfer2.5

Both stretch, only after the core result exists. See [[Cosmos 3]] for the primary Cosmos role.

## Cosmos-Predict2.5-2B (Tier 2 world model)

- **Role.** Action-conditioned arm world model post-trained on our own MuJoCo rollouts; tier 2 of the predictor (Tier 0 critic scored on sim labels; Tier 1 early-frame failure prediction with cross-embodiment readout transfer). High risk. No Cosmos checkpoint with G1 action conditioning was found.
- **IDs.** `nvidia/Cosmos-Predict2.5-2B` (`robot/action-cond`, `robot/policy`, ...); NVIDIA Open Model License weights, Apache-2 code (VERIFIED, README). Superseded by Cosmos 3, "limited maintenance".
- **Fit.** Bridge/IRASim format: per-frame state `[x,y,z,roll,pitch,yaw]` + gripper, 7D action, paired MP4; 256x320, 13-frame sequences, 1 GPU (VERIFIED, docs). Our arm log maps onto it exactly. Training time and VRAM on L40S are undocumented (UNVERIFIED): measure. 2B at 256x320 is the only Cosmos WM plausibly trainable on one L40S. NIM wants at least 80 GB.
- Cosmos Policy (`nvlabs/cosmos-policy`) is cut: a third policy family that duplicates GR00T.

## Cosmos-Transfer2.5-2B (photoreal re-render)

- **ID and licence.** `nvidia/Cosmos-Transfer2.5-2B`; NVIDIA Open Model License, commercial OK (VERIFIED).
- **VRAM.** 65.4 GB minimum, BF16, Ampere/Hopper/Blackwell; about 12-15 min per clip on H100 (285.8 s B200, 719.4 s H100 NVL, 870.3 s H100 PCIe); 720p at 16 fps. Does **not** fit the L40S; use an H100/H200 spot Serverless Job ($0.79/h).
- **Role.** Only load-bearing as an ablation: re-render rollouts photoreal and test whether the critic's diagnosis accuracy holds; otherwise decorative. A handful of demo shots only. Notice: "Built on NVIDIA Cosmos" in NOTICE.

**Sources.** https://huggingface.co/nvidia/Cosmos-Transfer2.5-2B · https://github.com/nvidia-cosmos/cosmos-predict2.5 · [[11_cosmos_worldmodel]] · [[10_nvidia_stack]] · [[Ideas Backlog]] · [[Knowledge/README|Knowledge]]
