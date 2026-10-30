# Sept 27 VM code (recovered 2026-10-01)

Authored on the L40S VM on Sept 27 and never committed until now. Copied verbatim from `~/transfergap_wheeled_arm/` on `transfergap-gpu-v2`; the mesh assets there are unmodified mujoco_menagerie files and are not copied.

- `build_scene.py`, `ur5e_ik.py`, `gripper_heuristic.py`, `ur5e_2f85_scene.xml`: the original GPU-side UR5e + 2F-85 scene and IK (superseded by `transfergap/sim/`, kept for provenance; source of the 7.2 mm IK residual noted in the Sept 28 review).
- `../evidence/gemx_test_walk_hpe_results.pt`: GEM-X SOMA motion recovered from the public-domain placeholder walking clip; this file drove SONIC on Sept 27.

Upstream pins on the VM (no local modifications; `git status` clean):

```
GEM-X https://github.com/NVlabs/GEM-X.git 32992550dba114c62243fb55e361311972dce8f9
  third_party/sam-3d-body b5c765a0d89d789985e186d396315e7590887b94
  third_party/soma e0f8ff0ecfa3edbbb6058b1e0f08822ee2f84ee5
  third_party/soma-retargeter (not checked out)
GR00T-WholeBodyControl https://github.com/NVlabs/GR00T-WholeBodyControl.git b042411fae38ee4d1af9aac82a37a1f8d14d6dd0
mujoco_menagerie https://github.com/google-deepmind/mujoco_menagerie.git c96a32d28fb5da84da38c1da4d749e7a13212855
dex-urdf https://github.com/dexsuite/dex-urdf.git f5e7132f22108164577fea4c25ef99b5cc0e1900
```
