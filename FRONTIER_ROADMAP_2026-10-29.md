# Frontier scouting and an ambitious plan (2026-10-29)

Sources: web search summaries only (titles below are what the search returned; I did not read the full papers, and each claim is the authors' own).

## What the field is doing (2026)
| Direction | Examples (arXiv / project) | Common ingredients |
|---|---|---|
| Egocentric human video as robot data | EgoScale (20,854 h, log-linear scaling with human data), EgoVLA, EgoEngine (Aria glasses to XHand humanoid), EgoInfinity (web-scale 4D hand-object data engine) | wrist-level retargeting, large pre-training, a little robot data to adapt |
| Fingertip-aligned dexterous retargeting | UniDex (fingertip targets via IK with a 6-DoF base offset), Do As I Do (monocular hand-object reconstruction to multi-finger hands) | match fingertip trajectories in 3D, allow a global hand-base offset |
| Real-to-sim data engines from one video | Video2Robo (one phone video, 3D Gaussian splats, 6D object tracks replayed by a Franka with augmentation), RoboWheel (physics refinement + Isaac Sim augmentation, 150k trajectories), JoyAI-Sim (lift video to metric 3D motion, run in a simulator because direct retargeting is unreliable), RoboPaint | reconstruct, physically refine, augment, export trajectories |
| NVIDIA stack | Cosmos Reason 2 (reasoning VLM, usable for data annotation and critique), GR00T N1.6 (with LeRobot integration for fine-tuning and Isaac Lab-Arena evaluation), SONIC (whole-body tracking, BONES-SEED motion data) | open weights, LeRobot-format datasets |

## Where TransferGap already sits
It is a real-to-sim data engine for one demonstration (pose, person model, retarget, physics rollouts on three embodiments) with something the others do not report in what I read: a measured, paired **diagnosis of which stage failed** and fixes verified on held-out seeds. A Cosmos-Reason2 video critic (97.5% vs 77.1% zero-shot on our rollouts) is already built.

## Additions, ranked by (win value x feasibility in the time left)
1. **Verified data engine (started today).** One demonstration -> many physics-verified trajectories across UR5e, UR10e, KAIROS, exported as a LeRobot-style dataset with failures excluded and labelled by the diagnosis. Built: `scripts/export_dataset.py` (rollouts with joint-state/action traces) and `scripts/to_lerobot.py` (parquet + meta; tested on 5 episodes). Next: render camera frames on the GPU, add Cosmos-critic verification to the filter, publish dataset statistics. Claim allowed: training DATA from one demo, not a trained policy.
2. **Critic-in-the-loop self-repair (partly built).** Failure -> Cosmos critic explains -> Nemotron picks a fix from the menu -> rerun. Pieces exist (`critic.py`, `demo_agent.py`, `diagnose.py`); the earlier Nemotron loop found no useful fix on one demo, so it needs a fresh honest run before it is shown.
3. **Fingertip retargeting to a dexterous hand.** 21 hand keypoints and bend angles are already published; add fingertip-target IK on a MuJoCo hand model (Allegro/Shadow/Dex3). Biggest visual win, needs the hand model assets and a day of tuning; not started.
4. **Fine-tune GR00T N1.6 on the exported dataset.** Highest ambition, highest risk: needs camera frames, an embodiment config for a UR arm, and GPU hours; only attempt after items 1 and 3.
5. **Scene twin from a phone video** (marker-based scale, measured box and tray): built earlier, waiting for your tape measurements.

## What was done today toward this
`TG_HQ` visuals, object-size and apple sweeps, grasp-contact gap, style-fidelity baseline, finger keypoints and bend angles, orientation retargeting code (behind `--orient`, math unit-tested, direction unverified until tested with you), G1 replication runs, data-engine export (items above).

## Status at the end of 2026-10-29
1. Verified data engine: DONE for state + video (120 verified episodes, `runs/dataset_v1_lerobot`, 52 MB) and critic-verified (`results/critic_dataset_v1`).
2. Critic-in-the-loop self-repair: critic part measured; the Nemotron fix-picking loop still needs a fresh honest run (not done).
3. Fingertip retargeting: DONE offline (`results/hand_retarget_v1`) and wired into the live session (`live/hand_live.py`); real-hand check pending.
4. GR00T N1.6 fine-tune: NOT started; blockers listed in `GROOT_FINETUNE_PLAN_2026-10-29.md` (policy repo and weights are not on the volume, embodiment config needed).
5. Scene twin from a phone video: waiting for tape measurements.
