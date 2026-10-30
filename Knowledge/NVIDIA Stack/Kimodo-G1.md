---
type: nvidia-model
updated: 2026-09-30
tags: [nvidia, kimodo, g1, correction, core]
---

# Kimodo-G1

**Role.** Core, new. (1) G1 correction operator: regenerate the human-demo motion with a hand-position constraint at the perceived (or true) object position, the object-relative correction, native to the G1. (2) Controlled augmentation: constraint-perturbed variants of the one demo (paired-trial pool). Effort estimate 8-14 h (report 10 estimate).

| Field | Value | Tag |
|---|---|---|
| IDs | `nvidia/Kimodo-G1-RP-v1`, `-SEED-v1`; `nvidia/Kimodo-SOMA-RP-v1.1`; code nv-tlabs/kimodo (Toronto AI Lab, released March 2026) | VERIFIED |
| License | Code Apache-2.0; Kimodo-G1-RP-v1 NVIDIA Open Model License, commercial OK; SMPLX-RP is R&D only | VERIFIED |
| VRAM | About 17 GB, or under 3 GB with `TEXT_ENCODER_DEVICE=cpu` | VERIFIED |
| Capability | G1-feasible motion under end-effector position constraints (hands/feet), full-body keyframes, 2D root paths; outputs MuJoCo qpos CSV for G1 | VERIFIED |
| Status | Not run by us | |

**Gotchas.** README says it interoperates with GEAR-SONIC for "interactive tracking" (VERIFIED wording); the exact interface is UNVERIFIED. Day-1 test: does Kimodo-G1 CSV output play through SONIC in our MuJoCo loop, or only through its own `mujoco_load`?

**Sources.** https://github.com/nv-tlabs/kimodo · https://huggingface.co/nvidia/Kimodo-G1-RP-v1 · [[10_nvidia_stack]] · [[SONIC]] · [[cuRoboV2]] (the arm counterpart) · [[Ideas Backlog]] · [[Knowledge/README|Knowledge]]
