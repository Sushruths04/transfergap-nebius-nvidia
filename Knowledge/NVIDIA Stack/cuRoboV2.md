---
type: nvidia-model
updated: 2026-09-30
tags: [nvidia, curobo, ik, arm, core]
---

# cuRoboV2

**Role.** Core; replaces the home-made Pinocchio/DLS IK. (1) Collision-aware IK and trajectory optimization for the UR arm (batch solve over the human wrist trajectory). (2) Pre-execution kinematic feasibility score per embodiment (percentage of demo poses reachable collision-free), a cheap predictor for the gap. (3) Arm correction operator: re-solve with an object-relative offset. Also the "kinematics" oracle in the gap budget. Effort estimate 8-12 h.

| Field | Value | Tag |
|---|---|---|
| Code / paper | NVlabs/curobo; arXiv 2603.05493 (Sundaralingam, Murali, Birchfield, 2026) | VERIFIED (search/README) |
| License | Apache-2.0, commercial | VERIFIED |
| VRAM | GPU, small | |
| Scope | Advertises high-DoF and humanoid whole-body support | VERIFIED (abstract/README) |
| Status | Not run by us | |

**Gotchas / day-1 test.** Can cuRoboV2 load the UR5e URDF, and does its FK agree with the menagerie MJCF over multiple configurations? This settles the 7.2 mm IK residual (review finding #2). Background: the MuJoCo `base` has `quat="0 0 0 -1"` (180 degrees about Z), the URDF root does not; the fix was negating target X/Y, leaving a 7.2 mm residual because the MuJoCo `attachment_site` and URDF `ee_link` are not the identical point. Alternative solver noted in report 05: `mink` (Apache-2.0) directly on the MJCF. Authored scripts `ur5e_ik.py`, `build_scene.py` live only on the VM.

**Sources.** https://github.com/NVlabs/curobo · https://arxiv.org/abs/2603.05493 · [[10_nvidia_stack]] · [[05_embodiments_sim]] · [[Kimodo-G1]] · [[MuJoCo Warp]] · [[Lessons Learned]] · [[Knowledge/README|Knowledge]]
