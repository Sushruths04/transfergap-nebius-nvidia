# Pose-estimator bake-off — pose_estimator_bakeoff_v3

Add a third estimator family (RTMW3D, OpenMMLab / Shanghai AI Lab, real-time whole-body 3D keypoints) and the author's own demo to the v1 bake-off; same clips, annotations, builder, frozen stacks, held-out seeds. Which estimator transfers human style best, per demo and overall?

| demo | estimator | fps (L40S) | pinch jitter mm | event err (grasp/release frames) | robot | pre-check | raw | with stack |
|---|---|---|---|---|---|---|---|---|
| pexels_8135753_notebook | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 31.1 | fail | ur5e | feasible | 0/60 | 57/60 |
| pexels_8135753_notebook | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 31.1 | fail | ur10e | feasible | 0/60 | 60/60 |
| pexels_8135753_markers | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 13.9 | fail | ur5e | infeasible | 0/60 | 51/60 |
| pexels_8135753_markers | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 13.9 | fail | ur10e | infeasible | 0/60 | 25/60 |
| pexels_8135753_orange_marker | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 19.1 | fail | ur5e | infeasible | 0/60 | 46/60 |
| pexels_8135753_orange_marker | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 19.1 | fail | ur10e | infeasible | 0/60 | 58/60 |
| pexels_8135753_notepad | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 14.7 | fail | ur5e | infeasible | 0/60 | 58/60 |
| pexels_8135753_notepad | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 14.7 | fail | ur10e | infeasible | 0/60 | 58/60 |
| pexels_7205253_woman_box | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 9.0 | 10/22 | ur5e | infeasible | 11/60 | 60/60 |
| pexels_7205253_woman_box | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 9.0 | 10/22 | ur10e | infeasible | 4/60 | 55/60 |
| user_take1_right | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 2.4 | fail | ur5e | infeasible | 35/60 | 59/60 |
| user_take1_right | gemx | 9.5-9.8 (live mode, window 30, measured 2026-10-02; offline export timing not recorded) | 2.4 | fail | ur10e | infeasible | 30/60 | 56/60 |
| pexels_8135753_notebook | fast_sam_3d_body | 6.163932927486623 | 48.0 | fail | ur5e | feasible | 0/60 | 58/60 |
| pexels_8135753_notebook | fast_sam_3d_body | 6.163932927486623 | 48.0 | fail | ur10e | feasible | 0/60 | 58/60 |
| pexels_8135753_markers | fast_sam_3d_body | 6.163932927486623 | 28.8 | 2/5 | ur5e | feasible | 0/60 | 60/60 |
| pexels_8135753_markers | fast_sam_3d_body | 6.163932927486623 | 28.8 | 2/5 | ur10e | feasible | 0/60 | 50/60 |
| pexels_8135753_orange_marker | fast_sam_3d_body | 6.163932927486623 | 33.4 | fail | ur5e | infeasible | 0/60 | 28/60 |
| pexels_8135753_orange_marker | fast_sam_3d_body | 6.163932927486623 | 33.4 | fail | ur10e | feasible | 0/60 | 16/60 |
| pexels_8135753_notepad | fast_sam_3d_body | 6.163932927486623 | 49.9 | fail | ur5e | infeasible | 0/60 | 60/60 |
| pexels_8135753_notepad | fast_sam_3d_body | 6.163932927486623 | 49.9 | fail | ur10e | infeasible | 0/60 | 57/60 |
| pexels_7205253_woman_box | fast_sam_3d_body | 5.174491244283316 | 121.2 | 1/69 | ur5e | infeasible | 9/60 | 12/60 |
| pexels_7205253_woman_box | fast_sam_3d_body | 5.174491244283316 | 121.2 | 1/69 | ur10e | infeasible | 21/60 | 60/60 |
| user_take1_right | fast_sam_3d_body | 4.609936886297684 | 27.7 | fail | ur5e | feasible | 36/60 | 60/60 |
| user_take1_right | fast_sam_3d_body | 4.609936886297684 | 27.7 | fail | ur10e | feasible | 37/60 | 60/60 |
| pexels_8135753_notebook | rtmw3d | 27.483883450857597 | 144.8 | 11/8 | ur5e | infeasible | 0/60 | 0/60 |
| pexels_8135753_notebook | rtmw3d | 27.483883450857597 | 144.8 | 11/8 | ur10e | infeasible | 0/60 | 0/60 |
| pexels_8135753_markers | rtmw3d | 27.483883450857597 | 167.5 | 4/15 | ur5e | infeasible | 0/60 | 0/60 |
| pexels_8135753_markers | rtmw3d | 27.483883450857597 | 167.5 | 4/15 | ur10e | infeasible | 0/60 | 0/60 |
| pexels_8135753_orange_marker | rtmw3d | 27.483883450857597 | 192.4 | 5/4 | ur5e | infeasible | 0/60 | 0/60 |
| pexels_8135753_orange_marker | rtmw3d | 27.483883450857597 | 192.4 | 5/4 | ur10e | infeasible | 0/60 | 0/60 |
| pexels_8135753_notepad | rtmw3d | 27.483883450857597 | 114.0 | 2/2 | ur5e | infeasible | 0/60 | 0/60 |
| pexels_8135753_notepad | rtmw3d | 27.483883450857597 | 114.0 | 2/2 | ur10e | infeasible | 0/60 | 0/60 |
| pexels_7205253_woman_box | rtmw3d | 26.978673223465012 | 422.0 | 10/52 | ur5e | infeasible | 0/60 | 0/60 |
| pexels_7205253_woman_box | rtmw3d | 26.978673223465012 | 422.0 | 10/52 | ur10e | infeasible | 0/60 | 0/60 |
| user_take1_right | rtmw3d | 26.57921255190453 | 18.0 | fail | ur5e | feasible | 27/60 | 58/60 |
| user_take1_right | rtmw3d | 26.57921255190453 | 18.0 | fail | ur10e | feasible | 32/60 | 60/60 |

## Reading (written after the run; nothing re-tuned)

- Sanity: every GEM-X and Fast SAM 3D Body cell of the five v1 demos reproduces pose_estimator_bakeoff_v1 exactly.
- Held-out successes with the frozen stacks, summed (UR5e + UR10e, n = 60 each):

| estimator | 5 internet clips (600) | author's own clip (120) | speed (L40S) | pinch jitter internet / own (mm) |
|---|---|---|---|---|
| GEM-X (NVIDIA, temporal) | **528** | 115 | ~10 fps live | 2.4–31 / 2.4 |
| Fast SAM 3D Body (Meta, per-frame) | 459 | **120** | 4.6–6.7 fps | 28–121 / 27.7 |
| RTMW3D (OpenMMLab / Shanghai AI Lab, per-frame) | **0** | 118 | **26.6–27.5 fps** | 114–422 / 18.0 |

- RTMW3D fails completely on the internet clips (partly occluded bodies behind a desk, a panning camera: the
  per-frame 3D hand path jumps by decimetres) but transfers as well as the others on a static, well-lit, full-body
  recording, at ~3x GEM-X live speed — the candidate for a fluent real-time mode with a proper camera setup.
- With a good camera setup the estimator choice matters little (115–120/120); on in-the-wild video it decides
  everything (0–528/600). Combined with v2 (per-demo selection 576/600), estimator choice is a transfer-gap stage.
