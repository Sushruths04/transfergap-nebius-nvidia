# TransferGap: objective, what is built, what is not, and the bugs (honest status, 2026-10-06 night)

Written because the pieces were built one by one and had never been shown together on one video. Status markers: **VERIFIED** = run, with a committed result; **PARTIAL** = runs, with a stated gap; **NOT DONE** = not built or not run. Simulation only; no real robot.

## 1. Objective (one paragraph)

A person shows a task once on a video or a webcam. The system should (1) **measure the person**: body pose, limb lengths, joint angles, hand pose and grip; (2) **copy the style of the demonstration** (path, approach, lift, speed, release), not only the task, onto different robots: a **Unitree G1 humanoid**, **UR5e**, **UR10e** and the **KAIROS** mobile manipulator (all in MuJoCo); (3) when the copy fails, **say which stage of the pipeline failed** (perception, retargeting, calibration, execution timing) with a measured, paired budget, apply a targeted correction and check it on seeds frozen in advance. Stage (3), the *Transfer Gap Budget* with oracle substitution and pre-registered held-out validation, is the research contribution and the paper. Stages (1) and (2) are what make it a demo and what the hackathon audience sees.

What is different from a "video to robot" demo: every claim is a measured count from a committed result file, failures are reported (including that the G1 cannot yet reproduce the author's picking style), and the same pipeline is run on several embodiments with the same seeds, so differences are attributable.

> **Update (same night, after the cluster came back):** stages B and D now ran on the author's real clip on the cluster, and an 80 s integrated video exists (`deliverables/TransferGap_integrated_demo_2026-10-06.mp4`, evidence `results/g1_mimic_user_v1`). A **bug found on the way**: RTMW3D's 3D coordinates are not metric (about 2.6x too large), so the earlier arm runs copied an oversized path; they are marked SUPERSEDED and replaced by `results/cluster_pipeline_user_scaled_v1` (UR5e 35->60, UR10e 36->60, KAIROS 49->60, KAIROS mobile 49->60 of 60). The pipeline now rescales from the shoulder width (ASSUMED 0.40 m: please give your real one).

## 2. The chain and its state

```
video / webcam -> [A] pose (RTMW3D)   -> [B] person measurements   -> [C] demo (grasp, release, hand path)
                                                                          |
              [D] G1 mimics the person (SONIC) <---------------------------+--> [E] UR5e, UR10e, KAIROS execute the copied style
                                                                                    |
                                                  [F] Transfer Gap Budget: which stage failed -> correction -> held-out check
```

| Stage | State | Evidence / gap |
|---|---|---|
| A. Pose from video, GPU on the cluster | **VERIFIED** (static camera only) | RTMW3D-L, 42 fps, 0 missed frames on the author's clip (`results/cluster_pipeline_user_v1`). **Fails on internet clips** (`results/pose_estimator_bakeoff_v3`: 0/600; a Pexels clip is refused by the plausibility gate, `cluster_pipeline_pexels_refused_v1`). GEM-X and Fast SAM 3D Body did better there but exist only on the old Nebius VM, not on the cluster |
| B. Person measurements (limb lengths, angles, hand aperture, speed, overlay video) | **VERIFIED on the author's clip** (`transfergap/human/analyze.py`, 5 tests; `results/human_analysis_user_v1`): upper arm 29.8 cm, forearm 25.7 cm, hand 17.3 cm, elbow 107-172 deg, pinch 5.0 cm, after a metric rescale from an ASSUMED shoulder width | Monocular estimates, never validated against motion capture; lengths are reported with their spread over the clip |
| C. Demo extraction | **PARTIAL** | Grasp/release frames were hand-annotated for the author's clip. The automatic aperture segmenter is not validated on real clips. The object is NOT detected: it is assumed under the pinch point at grasp |
| D. G1 mimics the person (wrists, neck, hand via SONIC VR-3-point) | **PARTIAL (one run, one clip)**: ran in the image on the cluster (`live/g1_mimic_run.py`, `g1/image_g1_mimic.sh`, Job `tg-g1-mimic-r1`): no fall; wrist similarity to the person: sideways r = -0.95, up +0.41 (G1 lifts 1.65x higher), forward -0.24 (`results/g1_mimic_user_v1`) | Mimics wrists, neck, pinch only; no grasp (block untouched). On the VM a stock video made the G1 fall 3 times in 90 s before a safe-path rule |
| D'. G1 *reproduces the author's picking style* (grasp and place) | **NOT WORKING** | Open-loop copy: 0/30 grasps on the author's demo, five fixes tried and falsified (`results/g1_style_user_v1`). Closed-loop hybrid reaches 13/40 places on generic blocks (`g1_closed_loop_v7`) but its host-vs-image gap (11/40 vs 31/40) is unexplained |
| E. UR5e / UR10e / KAIROS execute the copied style | **VERIFIED** | Author's clip (metric-rescaled), 60 seeds, frozen five-fix stack: UR5e 35->60, UR10e 36->60, KAIROS 49->60, KAIROS mobile 49->60 (`results/cluster_pipeline_user_scaled_v1`; the earlier unscaled 25->58 / 7->60 / 41->60 are superseded); KAIROS also as a mobile robot that drives then picks (`results/kairos_mobile_demo_v1`). Only the **tool translation** is copied (no wrist orientation, no body posture) |
| F. Transfer Gap Budget | **VERIFIED for two arms** | 500 fresh seeds per arm, pre-registered: perception is the largest budget item; look-again the best correction (+26.8 / +25.8 pp). The perception and calibration error sizes are **assumed**, not measured |
| Depth perception in the loop | **VERIFIED in simulation** | 30 of 30 held-out acceptance cells on UR5e, UR10e, KAIROS; depth beliefs 0.8-1.7 pp above ground truth on style trials |
| LLM diagnosis (Nemotron) and video critic (Cosmos-Reason2) | **PARTIAL** | Verified earlier on the old VM (critic 63.6 -> 94.1% after LoRA); NOT wired into the new pipeline and not rerun on the new rollouts |
| Live webcam | **PARTIAL** | Relay, pose and arm viewer run through `kubectl port-forward` at 17-21 fps with a recorded video as the camera; never run with your real webcam; G1 live not ported |
| One image that runs it all | **VERIFIED** | `ghcr.io/sushruths04/transfergap:full-2026-10-06c`, 8 of 8 end-to-end stages on the cluster GPU (`results/e2e_cluster_r4_v1`). The new human-analysis, G1-mimic and render code is committed but NOT in that image yet (r5) |
| Scene twin (your measured box and target in the sim) and marker-based metric scale | **BUILT, tested on synthetic data and run with STAND-IN sizes on the clip; waiting for your measurements and a marker recording** | `sim/twin.py`, `human/marker.py`, `human/twin_from_video.py`, `RECORDING_PROTOCOL.md`; finding: object and container geometry drive the outcome, carry distance does not (`results/cluster_pipeline_twin_*`). Arms only; G1 scene and automatic object detection NOT done |
| Paper | **PARTIAL** | 4 body pages; the abstract, introduction and conclusion are yours to rewrite (corrected claims draft in `paper/`). Deadline end of Oct 7 AoE |

## 3. How much is built (counted)

286 commits on `lane-b/human-demo`. About 8,100 lines of Python in the package (29 simulation modules, 9 demo modules), 2,250 in the G1 code, 2,000 in the live-mode code, 2,750 in 20 test files (202 tests pass in the image, 3 skipped). 76 result folders. 72 markdown files (many historical, now marked). These are code-volume numbers, not a quality measure.

## 4. Bugs and gaps, ranked (what blocks the demo you asked for)

1. **Integration is by hand, not one command.** An integrated run now exists (video above) but it was assembled from separate steps (pipeline, `human/analyze`, G1 Job, `human/robots_render`, `human/showcase`); the G1 Job and the new modules are not yet in `tg-entrypoint` or the image (r5), and the G1 needs the GPU while the pod is paused.
2. **The G1 does not reproduce the author's picking style** (0/30 grasps open loop) and its closed-loop controller is unexplained across hosts (and breaks on MuJoCo 3.15). A G1 that *mimics the body* is a different, easier claim than a G1 that *picks the block the way you do*; we should show the first and say plainly that the second is open.
3. **The G1 mimic is one run on one clip.** It did not fall; its forward/depth wrist motion does not follow the person (weak monocular depth) and it lifts the hand 1.65x higher than the person.
4. **Pose model limits:** coordinates not metric (rescaled from an assumed shoulder width); static camera only; the automatic grasp/release detection and the missing object detector mean a real new video still needs a hand-given grasp and release frame.
5. **The budget depends on assumed error sizes** (perception, calibration). Real error measurement would need a real robot or a measured camera model.
6. **Only the tool translation is copied.** The arms do not copy wrist orientation or elbow posture.
7. **Evidence caveats:** the real-demo results are one clip from one person, evaluated on seeds reused from development (reported as paired results, not as a fresh test).
8. **Webcam never run live with you.** The 17-21 fps figure used a recorded video.
9. **NVIDIA stack is only partly load-bearing:** SONIC and TensorRT run the G1; the Cosmos critic and Nemotron diagnosis are not in the new pipeline.
10. **Housekeeping:** the 231-commit branch is not on GitHub, and its history contains assistant trailers that must be scrubbed before anything public; a GitHub token sits in a cluster secret.

## 5. What I need from you

- **Decide the G1 claim:** "mimics my body" (recommended, achievable next) vs "picks like me" (open research).
- **Your real shoulder width in cm** (or height) so the metric scale is a measurement, not an assumption.
- **A second and third clip** of yourself (different object or speed) so results are not one clip. The static camera, full body in view, as in your first video.
- **A 10-minute webcam session** at the laptop (`bash live/run_live_cluster.sh --robot kairos_mobile`).
- **OK to use the Token Factory key** for the Nemotron diagnosis on the new rollouts.
- The paper rewrite and the external reviewers reviews (prompt in `the review prompt`).

## 6. Next iterations (after the integrated video)

1. DONE (this iteration): integrated video from your clip. Next: make it one command.
2. Put the human analysis, G1 mimic and render into the image (r5) and into `tg-entrypoint`.
3. Wire the Cosmos critic and Nemotron diagnosis to the new rollouts, with the menu limited to operators that exist.
4. Replace assumptions with measurements where possible (camera calibration error from the sim camera model; object detection).
5. A second estimator (GEM-X or Fast SAM 3D Body) on the cluster for non-static video.


---

## Update 2026-10-29 (supersedes the table above where they differ; every item below is in a committed-style result folder or a script in this repo)

| Item | State now |
|---|---|
| Arms copy the author's style (UR5e, UR10e, KAIROS) | VERIFIED, unchanged: 31/34/48 -> 60/60 of 60. NEW: reproduced exactly on the laptop (CPU, MuJoCo 3.14.0): UR5e 31 -> 60, gap +48.3 pp |
| Object-size sweep 3-7 cm | NEW, exploratory (`results/object_scale_v1`, with Wilson intervals): raw collapses to 0/60 at 7 cm on UR arms, fixes keep 47-60/60 |
| Placement and grasp-contact gap | NEW (`contact_gap_v1`, `contact_gap_ee_v1`): grasp-contact gap 0.45-0.66 cm with fixes vs 2.0-2.4 cm raw. NOT comparable to HOI-Retarget's 0.5 cm |
| G1 closed-loop in the image | NEW replication on 12 fresh seeds (`g1_image_oct29_v1`): touch 12/12, grasp 11/12, place 7/12; pooled with the earlier image run place 38/52. Host-pod gap (27%) still unexplained. Copying the author's grasp style on the G1: still 0/30 |
| Live path | PARTIAL: relay + pose ~17 fps, camera-to-robot latency 77-79 ms, arm lag 0.8-3.4 cm, VERIFIED with a recorded clip as camera and `--autocalib`; real webcam NOT yet run; KAIROS live viewer shows the UR arm until a KAIROS channel exists; G1 live not ported |
| Fingers | PARTIAL: 21 keypoints per hand and per-finger bend angles published and drawn; robots still use only the pinch aperture; Dex3 retargeting not done |
| Rendering | NEW `TG_HQ=1` visuals (physics-identical); final clips re-rendered |
| UI | `ui_demo/console.html` (stream shell + finger panel), `review.html` (Before/After + object-size slider), `replay.html` (synced timeline). Not yet run against a real hub session |
| Video | First cut `deliverables/TransferGap_final_cut_2026-10-29.mp4` (89 s, silent) |
| Root causes and status of every weak point | `WEAKPOINTS_ROOT_CAUSES_2026-10-29.md` |

## Update 2026-10-30 (learned policies; every number is in `transfergap/results/bc_policy_v1` or `groot_n15_v1`, simulation only)

| Item | State now |
|---|---|
| One learned policy for four robots | MEASURED: one vision behaviour-cloning policy (no robot id; UR5e, UR10e, KAIROS arm, KAIROS arm on its parked mobile base; 1300 scripted episodes, 60 epochs) scores 60/60 in every one of 12 cells (4 robots x standard / mixed sizes + distractors / hard = 6 cm cube + 5 distractors) on 60 held-out seeds. A second training seed gives the same 60/60 in all 12 cells. Limits: two training runs, one set of 60 evaluation seeds, same simulator and cube shape as the training data, mobile base parked (arm only, no navigation) |
| Why it was not 60/60 earlier | Single-robot policies trained on one distribution varied from 23 to 60 of 60; a policy trained on one cube size scored 0-35 on a 6 cm cube and 1-13 with 3 distractors; adding mixed-size and distractor episodes fixed both (a data-coverage problem). DAgger did not help |
| GR00T-N1.5-3B fine-tuned on our simulation data | MEASURED, simulation only, 30 fresh seeds per cell (`results/groot_n15_v1/README.md`). First-step execution of the model's action chunks gave 0-1 of 30 for every checkpoint (UR10e-only) and 0-17 of 30 (three-arm). Measuring the gripper-to-cube offset showed the arm stalling 2-5 cm short of the cube; executing the chunk 4 steps ahead (`--look 4`, no retraining) gives: UR10e-only model on UR10e 25/16/21 of 30 (standard / mixed / hard), three-arm model on KAIROS 27/20/26, on UR10e 5/2/10, on UR5e 7/5/6. The small BC policy scores 60/60 in all of these cells. The look-ahead setting was chosen on 12 other seeds; one fine-tune per setting; a longer three-arm training run is in progress |
