# Per-demo pose-estimator selection — pose_estimator_bakeoff_v2 (held-out)

| demo | arm | dev (gemx / fsam / fsam smooth, n=20) | selected | held-out gemx | held-out selected | gap pp [95% CI] |
|---|---|---|---|---|---|---|
| pexels_8135753_notebook | ur5e | 20/20 / 19/20 / 3/20 | gemx | 57/60 | 57/60 | +0.0 [+0.0, +0.0] |
| pexels_8135753_notebook | ur10e | 20/20 / 20/20 / 7/20 | gemx | 60/60 | 60/60 | +0.0 [+0.0, +0.0] |
| pexels_8135753_markers | ur5e | 17/20 / 20/20 / 17/20 | fast_sam_3d_body | 51/60 | 60/60 | +15.0 [+6.7, +25.0] |
| pexels_8135753_markers | ur10e | 10/20 / 19/20 / 20/20 | fast_sam_3d_body_smooth | 25/60 | 60/60 | +58.3 [+45.0, +71.7] |
| pexels_8135753_orange_marker | ur5e | 17/20 / 5/20 / 14/20 | gemx | 46/60 | 46/60 | +0.0 [+0.0, +0.0] |
| pexels_8135753_orange_marker | ur10e | 19/20 / 3/20 / 17/20 | gemx | 58/60 | 58/60 | +0.0 [+0.0, +0.0] |
| pexels_8135753_notepad | ur5e | 20/20 / 20/20 / 20/20 | gemx | 58/60 | 58/60 | +0.0 [+0.0, +0.0] |
| pexels_8135753_notepad | ur10e | 19/20 / 20/20 / 20/20 | fast_sam_3d_body | 58/60 | 57/60 | -1.7 [-10.0, +5.0] |
| pexels_7205253_woman_box | ur5e | 20/20 / 0/20 / 0/20 | gemx | 60/60 | 60/60 | +0.0 [+0.0, +0.0] |
| pexels_7205253_woman_box | ur10e | 19/20 / 20/20 / 0/20 | fast_sam_3d_body | 55/60 | 60/60 | +8.3 [+1.7, +15.0] |

Total held-out: gemx 528/600, per-demo selected 576/600.
