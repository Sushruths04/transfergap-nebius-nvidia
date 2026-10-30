# g1_mimic_user_v1 (exploratory, one clip; the integrated demo of 2026-10-06)

The author's static-camera clip, run entirely on the GPU cluster:
1. RTMW3D-L pose (40 fps, 0 missed frames), 133 keypoints + 2D keypoints; rescaled to metric size (median shoulder width set to an ASSUMED 0.40 m, factor 0.3846; RTMW3D's own scale was about 2.6x too large).
2. `transfergap/human/analyze.py`: upper arm 29.8 cm, forearm 25.7 cm, hand 17.3 cm, elbow 107-172 deg, pinch aperture 5.0 cm (median) with overlay video. Monocular estimates, not validated against motion capture (`../human_analysis_user_v1/human_analysis.json`).
3. G1 mimicry in the unified image `full-2026-10-06c` (Job `tg-g1-mimic-r1`, code from the volume): wrists, neck and pinch -> SONIC VR-3-point -> G1 in MuJoCo. The robot did not fall (`robot_fell: false`), the block was not touched (this is mimicry, not a grasp).
   Wrist similarity (`mimic_fidelity.json`, G1 right wrist vs the person's right wrist, free time offset and one-to-one axis assignment, so r is optimistic; shuffled-time baseline 0.07 at the 95th percentile):
   sideways r = -0.95 (range ratio 1.18, sign = frame convention), up r = +0.41 (ratio 1.65: the G1 lifts the hand about 1.65x higher), forward r = -0.24 (ratio 1.03: the person's depth is weak from one camera). Best offset 6.3 s = the 6 s settle before the replay, an independent consistency check.
4. UR5e, UR10e and KAIROS (mobile) copy the same demo: `../cluster_pipeline_user_scaled_v1` (60 seeds) and one illustrative seed here (`robot_render_report.json`: seed 1001, no correction fails, fix stack places, all three robots).
Video: `deliverables/TransferGap_integrated_demo_2026-10-06.mp4` (80 s, untracked). One run, one clip, one person; a single G1 replay is not a statistic.
