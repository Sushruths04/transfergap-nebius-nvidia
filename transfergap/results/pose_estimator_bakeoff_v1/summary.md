# Pose-estimator bake-off — pose_estimator_bakeoff_v1

Same clips, annotations, demo builder, fix stacks and held-out seeds as demo_generalization_v5; only the human pose estimator differs: GEM-X (NVIDIA, used so far) vs Fast SAM 3D Body (ECCV 2026; SAM 3D Body weights, Meta). Does the newer estimator change how well the human style transfers to the robots?

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

## Reading (written after the run; nothing re-tuned)

- Sanity: every GEM-X cell reproduces demo_generalization_v5 exactly (10/10 cells).
- Held-out success with the frozen stacks, summed over 5 demos x 2 arms: **GEM-X 528/600 (88%)**, **Fast SAM 3D Body
  459/600 (77%)**. Neither dominates: Fast SAM 3D Body fixes the weakest cell (markers, UR10e 25 → 50/60; UR5e
  51 → 60/60) and ties on notebook/notepad, but loses the orange-marker flick (46 → 28, 58 → 16) and person 2 on the
  UR5e (60 → 12/60).
- Why (measured): Fast SAM 3D Body is a per-frame model; its pinch path is 1.5–13x less steady (RMS second
  difference 29–121 mm vs 9–31 mm for the temporal GEM-X), worst on the 4K clip of the walking person 2.
- Event detection from the estimated hand aperture alone fails for most demos with both estimators (monocular finger
  opening is too weak a signal); the hand annotations (or the live pinch command) remain necessary.
- Speed on the L40S without TensorRT: 6.2 fps (1080p), 5.2 fps (4K); GEM-X live mode 9.5–9.8 fps.
- Conclusion: the human pose estimator is itself a stage of the transfer gap — newer is not automatically better for
  the robot; the choice should be made per demo, like the fixes (follow-up: pose_estimator_bakeoff_v2).
