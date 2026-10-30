# cluster_pipeline_user_v1 (exploratory, not in the paper)

`python -m transfergap.pipeline --video user_clip.mp4 --window 60 206 --events 102 166 --robots ur5e ur10e kairos` on the GPU cluster
(one command: RTMW3D pose 42 fps -> demo -> feasibility -> held-out rollouts, no correction vs the frozen five-fix stack, seeds 1000-1059).
Successes: UR5e 25 -> 58, UR10e 7 -> 60, KAIROS (UR10e + 2F-140) 41 -> 60, of 60. UR5e and UR10e match `../cluster_cam_user_rtmw3d_v1` exactly.
Same caveats: one clip, one person, hand-annotated events, seeds reused from earlier demo experiments, injected (assumed) perception/calibration errors.

> **SUPERSEDED 2026-10-06:** this run used RTMW3D coordinates that are not metric (about 2.6x too large). Use `../cluster_pipeline_user_scaled_v1`. Kept for the record.
