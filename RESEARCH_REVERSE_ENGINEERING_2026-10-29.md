# Reverse-engineering the references: what they do, what we take (2026-10-29)

Sources read today (project pages and search summaries, not the full papers; marked where I could not verify):
HOI-Retarget (https://shinben0327.github.io/hoi-retarget/), HiPHI (https://huggingface.co/datasets/noitomrobotics/HiPHI), dex-retargeting / AnyTeleop / DexPilot
(https://github.com/dexsuite/dex-retargeting), NVIDIA GR00T Whole-Body Control / GEAR-SONIC (https://github.com/NVlabs/GR00T-WholeBodyControl), Foxglove layouts.

## 1. HOI-Retarget: decomposition
| Part | What it does (from the project page) | Our counterpart | Gap / what to take |
|---|---|---|---|
| Representation | Contacts are targets in the object's frame; they move with the surface when the object is resized | Grasp/release frames + hand path warped onto the scene (`demo/style.py`); object assumed under the pinch point | Express grasp and release as object-frame targets. Partly done as a metric (grasp-contact gap 0.45-0.66 cm, `contact_gap_ee_v1`); the planner itself still uses the warped path |
| Scale | Object mesh and trajectory scaled by robot/human height ratio | Shoulder-width scale of the person (0.44 m derived) and per-robot reach | The size sweep (`object_scale_v1`) tests object scale 3-7 cm; robot-height-ratio scaling for the G1 is NOT done |
| Optimisation | Windowed trajectory optimisation: body tracking, foot support, smoothness, kinematic limits (exact terms and weights are not on the page: unverified) | Scripted IK keyframes + fix stack; G1 via SONIC tracking | No optimisation over a window; the closed-loop hybrid re-plans from the measured wrist, which addresses the same "robot does not follow the plan" problem |
| Dynamics | Downstream refinement (RL tracker or MuJoCo-based optimiser) because kinematic retargets are not physically feasible | MuJoCo physics in every rollout; G1 whole-body controller | Our rollouts are physical; the G1's 7 cm wrist tracking error is the same feasibility issue they refine away |
| Evaluation | Contact-point gap 0.5 cm vs 18.3 cm for the closest (unnamed) baseline; 4.6x faster than an interaction-aware baseline | Placement and grasp-contact gaps; 60-seed held-out counts | Different tasks and data: report ours, never compare numbers directly |
| Hands | Not described on the page | Parallel grippers (UR, KAIROS), Dex3 via SONIC on G1 | See section 2 |
| UI ideas | Side-by-side human and robots with a shared camera, object-scale slider, before/after toggle, contact overlay | Before/After page with object-size slider (done), console shell | Contact overlay and synced timeline still TODO |

## 2. Fingers: dex-retargeting / AnyTeleop / DexPilot
- Retargeting is posed as an optimisation: choose robot joints so forward kinematics matches the observed human keypoints; the vector-based variant matches inter-joint and finger-to-palm vectors (robust to morphology mismatch) (search summary; original papers not read).
- Caveat quoted in the search result: retargeting alone often fails to give good manipulation because it ignores the object and self-collision.
- Ours: the pose model gives 21 keypoints per hand; `live/hands_pub.py` now publishes all 21 plus per-finger bend angles (`hands_detail`, verified in the live dry run). The console draws them. The robots still use only the pinch aperture.
- Next step (not done): feed fingertip-to-palm vectors to the G1's Dex3 hand through the SONIC hand interface (`compute_hand_joints_from_inputs` exists in the SONIC stack) and test grasp success; needs GPU time and is risky.

## 3. NVIDIA GR00T Whole-Body Control / GEAR-SONIC (search summary, partly unverified)
- SONIC: a motion-tracking foundation model (about 42M parameters, trained on over 100M frames of motion capture, released Feb 2026) with C++/TensorRT deployment and PyTorch checkpoints for Isaac Lab; supports VR teleoperation, planning, and a monocular video-to-motion mode (the 60+ FPS claim comes from one secondary article: unverified).
- BONES-SEED: an open human motion dataset (142K+ motions, about 288 hours) with Unitree G1 MuJoCo-compatible trajectories (2026-03-16). Apache-2.0 repo. This is a usable open alternative to HiPHI (gated, 215 GB) for validating or training, but we did not download it.
- Consequence for us: the G1 controller we use is the "newer generalist controller"; our root-cause finding (about 7 cm wrist tracking error) is a property of whole-body tracking, so a precise grasp needs a closed loop on the measured wrist.

## 4. HiPHI
Gated optical motion-capture dataset: 617.5 h, 90 Hz BVH, 245.7 h of human-object interaction with object meshes and trajectories, 132 performers, mirrored copies; access by questionnaire; 215 GB. Not usable in two days. Use: cite as ground truth for validating monocular pose; future work.

## 5. What we adopt in the remaining time (ranked)
1. DONE: object-size sweep (HOI-Retarget idea) and grasp-contact gap metric.
2. DONE: finger keypoints and bend angles published and displayed.
3. TODO: contact overlay and synced timeline in the UI (Foxglove idea).
4. TODO (risky, GPU): Dex3 fingertip-vector retargeting test on the G1.
5. Future: robot-height-ratio scaling, windowed optimisation, BONES-SEED / HiPHI validation.
