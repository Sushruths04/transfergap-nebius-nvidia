# Demo video script and storyboard (draft, 2026-10-29)

Target: recorded video, about 3 minutes. Simulation only, and the video says so.
Every number below comes from `STATUS_AND_OBJECTIVE.md` and the committed `results/` folders. Re-check each one before it goes on screen.

## One-sentence pitch
A person shows a pick-and-place once on video. The system measures the person, copies their picking style onto different robots, and when a robot fails it names the pipeline stage that failed.

## Storyboard

| # | Time | On screen | Voice-over | Source clip or evidence |
|---|---|---|---|---|
| 1 | 0:00-0:15 | Title card, then the author's raw clip | "One demonstration. Four robots. And when the copy fails, we say why." | author's clip |
| 2 | 0:15-0:40 | Pose overlay on the clip, with the measured limb lengths and elbow angle shown as text | "We measure the person: pose, limb lengths, hand opening. Monocular estimates, scaled from shoulder width." | `results/human_analysis_user_v1` |
| 3 | 0:40-1:10 | Side-by-side: UR5e, UR10e and KAIROS copying the style | "The same demonstration runs on three embodiments. On 60 seeds the success rate goes UR5e 35 to 60, UR10e 36 to 60, KAIROS 49 to 60." | `results/cluster_pipeline_user_scaled_v1`, `TransferGap_integrated_demo_2026-10-09_v2.mp4` |
| 4 | 1:10-1:30 | KAIROS mobile: drives to the table, then picks | "KAIROS is a mobile manipulator, so it drives to the table first." | `results/kairos_mobile_demo_v1`, `kairos_mobile_demo_2026-10-06.mp4` |
| 5 | 1:30-1:55 | Unitree G1 mimicking the wrists and neck | "The humanoid mimics the person's arms. It does not yet reproduce the grasp. We show that honestly." | `results/g1_mimic_user_v1` |
| 6 | 1:55-2:30 | Transfer Gap Budget chart: perception is the largest item, look-again is the best correction | "When a copy fails, we replace one stage at a time with ground truth. Perception costs the most. Look-again recovers +26.8 and +25.8 points on the two arms." | `results/gap_budget_v3` |
| 7 | 2:30-2:50 | Cosmos-Reason2 critic and Nemotron diagnosis, one example each | "A video critic and an LLM diagnosis read the rollouts." | `results/cosmos_critic_newdemo_v1` (critic 97.5% vs zero-shot 77.1%); Nemotron diagnosis is PARTIAL |
| 8 | 2:50-3:00 | Limits card | "Simulation only. One clip, one task. Error sizes are assumed, not measured." | |

## Must-say limits (on a card and in the voice-over)
- Simulation only; no real robot.
- G1 grasp is not working (0/30 open-loop on the author's demo).
- The shoulder width of 0.44 m is derived from "22 inches", not measured.
- Perception and calibration error sizes in the budget are assumed.
- Internet clips are refused by the plausibility gate; pose is verified on a static camera only.

## Needs the cluster GPU (blocked until it is free)
1. Re-render any shot that needs a fresh run (the integrated showcase: `tg-entrypoint showcase`).
2. Isaac Sim KAIROS footage, if we want it. The existing KAIROS clips are MuJoCo.

## Doesn't need a GPU, can start now
- Cut shots 1-8 from the existing videos in `deliverables/`.
- Draw the limits card and title card.
- Record the voice-over.
- UI: built (`transfergap/ui_demo/`: console.html, review.html, replay.html).

## Open questions for the author
- Is the submission 3 minutes or a different length? What is the exact upload target?
- Do you want the KAIROS MCP/Isaac work (the thesis project) in this video, or only TransferGap?
- Is a live webcam shot required? It has never been run with a real webcam.

## Screen assets per shot (updated by the loop, 2026-10-29)
| Shot | Use |
|---|---|
| 2 | `transfergap/ui_demo/media/human_overlay.mp4` (pose overlay) |
| 3 | `transfergap/ui_demo/review.html`, "Side by side" mode: raw vs fixed for UR5e, UR10e, KAIROS, with the 60-seed bars |
| 4 | `media/kairos_mobile_stack_seed1001.mp4` |
| 5 | G1 mimic clip from `deliverables/TransferGap_integrated_demo_2026-10-09_v2.mp4` |
| 6 | Budget chart from `results/gap_budget_v3` |
| live (only if the L40S frees) | `transfergap/ui_demo/console.html` connected to the cluster streams, screen-recorded; otherwise skip and say so |

Recording tip: record each page with the laptop screen recorder at 1080p; do not run the 3D prototype `live.html`, it is not part of the demo.


## Voice-over text for the 89 s cut (record this; edit freely; numbers are from the committed results)
| Time | Segment | Say |
|---|---|---|
| 0-4 s | Title | "One demonstration. Several robots. And when the copy fails, we tell you which stage failed." |
| 4-11 s | Your clip | "We measure the person from one video: limbs, elbow angle, pinch. It is a monocular estimate, and the shoulder width is derived, not measured." |
| 11-37 s | UR5e, UR10e, KAIROS | "Copying the style as is works about half the time. With the fixes found by the diagnosis, all three robots succeed on all 60 held-out seeds." |
| 37-63 s | Object size | "We resized the cube without retuning. The plain copy collapses at 7 centimetres; with the fixes the UR10e still succeeds 56 times out of 60. This is exploratory." |
| 63-73 s | G1 humanoid | "The G1 humanoid does closed-loop pick and place inside the container image: 31 of 40 placements on generic blocks. Copying your own grasp style is not solved yet." |
| 73-80 s | Budget chart | "Replacing one pipeline stage at a time with ground truth shows perception costs the most, and looking again is the best fix. The error sizes are assumed." |
| 80-89 s | Limits | "Simulation only, one clip, one person. The live webcam path is measured with a recorded clip so far." |


## Voice-over for the v2 cut (108 s, `deliverables/TransferGap_final_cut_v2_2026-10-29.mp4`)
Same as the 89 s table above, with these changes and additions (numbers from the committed results):
| Segment | Say |
|---|---|
| G1 (63-73 s) | "The G1 humanoid does closed-loop pick and place inside the container image: 52 of 72 placements pooled over every run on generic blocks. Copying your own grasp style is not solved yet." |
| Fingers (73-84 s) | "Your 21 hand keypoints drive a dexterous robot hand by fingertip inverse kinematics. Fingertip error is about a centimetre and a half, larger on the thumb, and part of it is noise in the single-camera keypoints." |
| Data engine (84-92 s) | "One demonstration becomes 120 physics-verified episodes with camera video across three robots. A Cosmos critic agrees on all of them and rejects 40 of 49 failures. This is training data from one demo; no policy has been trained on it yet." |
| Budget chart, limits | unchanged |


## Voice-over for the v4 cut (about 3 minutes; `deliverables/TransferGap_final_cut_v4_2026-10-30.mp4`, built by `transfergap/scripts/make_final_cut.py`)
Read it in one take; the captions on screen carry the numbers. Every number is in a committed result folder (`bc_policy_v1`, `groot_n15_v1`, `object_scale_v1`, `gap_budget_v3`); re-check before recording.
| Segment | Say |
|---|---|
| Title | "One demonstration. Several robots. And when the copy fails, we tell you which stage failed. Everything you see is simulation." |
| Your clip | "We measure the person from one video: limbs, elbow angle, pinch. It is a monocular estimate, and the shoulder width is derived, not measured." |
| Three robots, raw vs fixed | "Copying the style as is works about half the time. With the fixes found by the diagnosis, UR5e, UR10e and KAIROS succeed on all 60 held-out seeds." |
| Object size | "We resized the cube without retuning. The plain copy collapses at 7 centimetres; with the fixes the UR10e still succeeds 56 times out of 60. This is exploratory." |
| G1, fingers, data | "The humanoid does closed-loop pick and place but does not yet copy your grasp style. Your hand keypoints drive a robot hand to about a centimetre and a half. And one demonstration becomes 120 verified episodes with video." |
| Learned policy | "Then we trained a policy that no longer uses the scripted controller: it sees two camera images and joint positions and outputs actions." |
| First policy broke | "Trained only on the default cube and an empty table, it broke when the world changed: a 6 centimetre cube, or three extra objects. We fixed it with varied training data, not a bigger model." |
| One policy, four robots | "One policy, no robot id, drives the UR5e, the UR10e, the KAIROS arm and the KAIROS arm on its mobile base. It succeeds on all 60 held-out seeds in every one of twelve cells, standard, mixed sizes and clutter, and a hard case with a 6 centimetre cube and five distractors. A second training run gives the same result. The mobile base stays parked, so this is the arm, not navigation." |
| GR00T | "We also fine-tuned NVIDIA's GR00T N1.5 foundation model, three billion parameters, on the same data. At first it scored almost zero: the arm stopped a few centimetres short of the cube. By measuring that offset we found the cause and fixed it by executing the plan four steps ahead, without retraining. Now it succeeds on 25 of 30 fresh seeds on the UR10e and 27 of 30 on the KAIROS arm. It is still worse than our small policy, which gets all sixty, and a single model for three robots is weak on the two UR arms." |
| NVIDIA models on Nebius | "The diagnosis step is done by NVIDIA Nemotron-3-Super, called through the Nebius Token Factory API: it reads the failure statistics and picks the next fix, and the UR5e goes from 31 to 60 of 60 held-out seeds, the UR10e from 34 to 60. A Cosmos-Reason2 critic checks the simulated clips, GR00T N1.5 is fine-tuned on our data, and SONIC drives the humanoid." |
| Budget chart | "Replacing one pipeline stage at a time with ground truth shows perception costs the most, and looking again is the best fix. The error sizes are assumed." |
| Limits | "Simulation only. One demonstration, one task. The learned policies are trained on scripted rollouts, not on the video itself. The humanoid does not yet copy your grasp." |
