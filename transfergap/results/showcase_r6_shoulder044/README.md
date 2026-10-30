# One-command showcase, image r6 (2026-10-09, GPU cluster, Job tg-showcase-r6)

`tg-entrypoint showcase --video user_clip.mp4 --window 60 206 --events 102 166 --shoulder-width-m 0.44` ; all 7 steps PASS (`showcase_status.json`).
Image `ghcr.io/sushruths04/transfergap:full-2026-10-09b`. Video: `deliverables/TransferGap_integrated_demo_2026-10-09.mp4`.

**Shoulder width 0.44 m is DERIVED, not measured**: the user gave "22 inches" outer shoulder width; 0.44 m is my estimate of the joint-to-joint width. Every length below scales with it.
Same author clip and hand-given grasp/release frames as `cluster_pipeline_user_scaled_v1` (which used the assumed 0.40 m). Seeds 1000-1059 are reused from development: paired results, not a fresh test.

| robot | no correction | frozen five-fix stack |
|---|---|---|
| UR5e | 31/60 | 60/60 |
| UR10e | 34/60 | 60/60 |
| KAIROS arm | 48/60 | 60/60 |

(KAIROS mobile was rendered, not re-run for counts here.)

Person (monocular, never validated against motion capture): upper arm 38.2 cm, forearm 31.0 cm, hand 21.8 cm, elbow 107-156 deg, pinch aperture median 6.1 cm, peak hand speed 0.68 m/s.
These follow from the 0.44 m scale; with 0.40 m they were 29.8 / 25.7 / 17.3 cm.

G1 mimic (one run, one clip, wrists only, no grasp): correlation with the person's wrist, sideways r = -0.94, up r = +0.33 (G1 range 1.57x the person's), forward r = -0.20 (weak monocular depth); mean |r| 0.49 vs shuffled baseline 0.07.
