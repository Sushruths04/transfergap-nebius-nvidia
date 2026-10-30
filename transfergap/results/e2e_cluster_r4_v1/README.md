# e2e_cluster_r4_v1

`tg-entrypoint`-style end-to-end check of image `ghcr.io/sushruths04/transfergap:full-2026-10-06c` (digest sha256:947ee7e4c86a5db7b6bf0e61062f8cc6cf189ce75a256ed46f9f7b241e20b14e, built with kaniko on the GPU cluster)
as Job `tg-e2e-r4`, one L40S. All 8 stages PASS: info, tests (202 OK, 3 skipped), arm_repro (500-seed counts reproduced exactly), perception, style, perceive (RTMW3D, 30 frames, 41.7 fps),
pipeline (one-command pipeline reproduces `../cluster_pipeline_user_v1` counts exactly: UR5e 25/58, UR10e 7/60, KAIROS 41/60), g1 (4/4 grasped).
The Job ran the newer `e2e.sh` from the volume (the r4 image bakes the older one without the perceive and pipeline stages; r5 will include it). The perceive and pipeline
stages use the author's private clip and its joints from the volume (not in git). Smoke runs, not new scientific evidence.
