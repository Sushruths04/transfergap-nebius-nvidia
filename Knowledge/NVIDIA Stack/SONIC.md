---
type: nvidia-model
updated: 2026-09-30
tags: [nvidia, sonic, g1, control, core]
---

# SONIC (GEAR-SONIC)

**Role.** Core. Whole-body tracking of the human motion stream on the Unitree G1 in MuJoCo. Proven on Sept 27 (GEM-X -> SONIC -> G1 loop running). See [[GEM-X]] for the input side.

| Field | Value | Tag |
|---|---|---|
| ID | `nvidia/GEAR-SONIC` weights; code NVlabs/GR00T-WholeBodyControl pinned at `b042411fae38ee4d1af9aac82a37a1f8d14d6dd0` | VERIFIED |
| License | Code Apache-2.0; weights NVIDIA Open Model License (commercial with attribution) | VERIFIED |
| Papers | arXiv 2511.07820 (Science Robotics 2026) | cited in report 12 |
| Runtime | Needs TensorRT 10.13 exactly (x86_64/CUDA 13): the repo warns other versions give incorrect inference; gated NVIDIA developer download. Weights download unauthenticated | VERIFIED |
| Status | Loop running Sept 27; policy 994D, encoder 1762D dimensions matched. Code exists only on the stopped VM until copied into git | [[Implementation Status]] |

**Gotchas (all hit or read in source).**
- `deploy.sh sim` has an undocumented interactive `[Y/n]` prompt; under `nohup` it hits EOF and exits. Run it in `tmux`.
- Switching input to ZMQ (`#` key) does not start control; press `]` too (`ProgramState::WAIT_FOR_CONTROL`).
- Candidate flag route: `deploy.sh --input-type zmq --zmq-host localhost sim` (real flag). Do not add `--zmq-port/--zmq-topic`; unrecognized flags are swallowed as the positional `sim`/`real` argument. The short README contradicts the tutorial; follow the tutorial. Whether this publishes the motion token to the data exporter is UNVERIFIED.
- `MUJOCO_GL=egl` for headless rendering; port 5555 is taken (`nv-hostengine`), use `--camera-port 5560`.
- GEM-X path streams wrists and fingers as zeros, so no G1 grasp yet. Nobody has shown a simulated SONIC-G1 grasp (UNVERIFIED): score touch, grasp, place tiers.
- Nondeterministic with MuJoCo (issue #274). Container images need TensorRT baked in: check licence, keep the registry private.
- Only the default sim scene: add table, block, tray and a third-person camera (recipe in [[05_embodiments_sim]]).

**Sources.** https://nvlabs.github.io/GEAR-SONIC/ · https://huggingface.co/nvidia/GEAR-SONIC · [[10_nvidia_stack]] · [[02_groot_finetune]] · [[Lessons Learned]] · [[GR00T N1.7]] · [[Kimodo-G1]] · [[Knowledge/README|Knowledge]]
