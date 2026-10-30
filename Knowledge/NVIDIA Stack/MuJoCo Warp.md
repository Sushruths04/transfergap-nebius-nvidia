---
type: nvidia-tool
updated: 2026-09-30
tags: [nvidia, mujoco, warp, simulation, optional]
---

# MuJoCo Warp

**Role.** Optional, for statistics. Batch-simulate hundreds or thousands of arm episodes (cuRobo trajectories on the UR + 2F-85 MJCF) on the L40S or a Serverless Job, making the 60 paired trials per condition cheap. The G1/SONIC loop stays on CPU MuJoCo with the real-time C++ deploy, so G1 trial counts stay small: state that honestly. CPU MuJoCo (3.14.0, the version SONIC's `.venv_sim` installs) is the default for scripted arm episodes; run N processes.

| Field | Value | Tag |
|---|---|---|
| Repo | google-deepmind/mujoco_warp (NVIDIA co-developed) | VERIFIED (repo title) |
| Effort | 10-16 h (report 10 estimate) | estimate |
| Upgrade path | Newton 1.0 (newton-physics/newton; NVIDIA + DeepMind + Disney, Linux Foundation; MuJoCo Warp primary backend). Mention, do not adopt. Licence Apache-2.0 UNVERIFIED | VERIFIED existence |

**Not adopted.** Isaac Sim / Isaac Lab port (align vocabulary with Isaac Lab-Arena instead: `grasp, lift, transport, place`, RoboLab graded score and SPARC smoothness); Omniverse NuRec.

**Gotchas.** `MUJOCO_GL=egl` for headless rendering (worked on the L40S and locally). CPU arm sims: one 4 cm / 50 g block, scripted DLS-IK, real contact only (a test asserts no weld constraints).

**Sources.** https://github.com/google-deepmind/mujoco_warp · https://github.com/newton-physics/newton · https://github.com/isaac-sim/IsaacLab-Arena · [[10_nvidia_stack]] · [[05_embodiments_sim]] · [[cuRoboV2]] · [[Knowledge/README|Knowledge]]
