# cluster_pipeline_user_scaled_v1 (exploratory, not in the paper; SUPERSEDES cluster_pipeline_user_v1 and cluster_cam_user_rtmw3d_v1)

The one-command pipeline on the author's clip, GPU cluster, robots UR5e, UR10e, KAIROS arm and KAIROS mobile, seeds 1000-1059, frozen five-fix stack, with the pose rescaled to metric size.
Successes (no correction -> fix stack, of 60): UR5e 35 -> 60, UR10e 36 -> 60, KAIROS 49 -> 60, KAIROS mobile 49 -> 60. The pre-check now calls UR5e and UR10e feasible.

Why this replaces the earlier runs: RTMW3D's 3D coordinates are NOT metric. On this clip the median shoulder width came out 1.04 m, the upper arm 0.77 m and a 6 cm box grasp an aperture of 13.8 cm, about 2.6x too large, so
the earlier runs copied a path that was too big (and with almost no depth range). The pipeline now rescales so the median shoulder width equals 0.40 m (an ASSUMED adult value, factor 0.3846 here; measure the person's own).
After scaling: upper arm 29.8 cm, forearm 25.7 cm, hand 17.3 cm, pinch aperture 5.0 cm (consistent with adult proportions and the box); the vertical hand extent (0.22 m) matches the GEM-X-based demo of the same take (0.21 m),
and the arm counts are close to the GEM-X-based `user_demo_v1` (UR5e 35 -> 59, UR10e 30 -> 56). Depth from a monocular estimate remains weak (depth extent 3 cm).
Caveats unchanged: one clip, one person, hand-annotated grasp and release frames, seeds reused from earlier development, injected (assumed) perception and calibration errors.
