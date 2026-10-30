# Behaviour-cloned policy from the verified data engine (bc_policy_v1), UR5e

A policy trained ONLY on simulated episodes derived from one human demonstration (299 scripted fix-stack successes, seeds 2000-2299), then run closed-loop in MuJoCo on 60 fresh seeds (6000-6059) with no scripted controller and scored by the same scorer as every other result. Simulation only; one robot; one task and one demonstration family. Code: `scripts/gen_bc_data.py`, `train_bc.py`, `eval_bc.py` (copies here).

| policy | observations | success on 60 fresh seeds | 95% Wilson |
|---|---|---|---|
| vision | two 96x128 camera images (third-person + wrist), joint positions, last gripper command | **38 / 60 (63%)** | 51-74% |
| lowdim (privileged, no images) | joint positions, last gripper command, block offset, time since start | 11 / 60 (18%) | 11-30% |
| scripted fix stack (reference, same seeds) | privileged controller | 60 / 60 | |

Training: small CNN encoder (4 conv layers, GroupNorm) per camera + MLP, 8-step action chunk at 25 Hz, L1 loss on normalised actions, random-shift augmentation, 40 epochs, 263 s on the L40S (vision). Failure reasons (vision): 22 episodes never lifted the block, 2 forbidden collisions.

Honest notes:
- The data are scripted-controller rollouts of one demonstration's style, so this shows that the exported data are learnable, not that a policy learned from the human video directly.
- A first evaluation scored 0/60 because the evaluator applied the command that had PRODUCED each observation (the first action of the chunk); using the next one fixed it. The 0/60 run is not a result of the policy and is not counted.
- The privileged low-dimensional policy is worse than the vision one here (it gets a coarse, scaled block offset but has to infer the phase from time and joints); it is a baseline, not an upper bound.
- No hyper-parameter search, one training run per policy, 60 evaluation seeds (wide intervals).

## Update 2026-10-29 night: how the predicted actions are executed matters more than the data amount
All numbers: 60 fresh seeds (6000-6059), UR5e/UR10e/KAIROS vision policies, same scorer; `eval_*.json` hold the per-seed results. `first` = apply only the newest prediction every 25 Hz step; `open4` = run each predicted chunk open loop for 4 steps; `ensemble` = temporal ensemble (exponentially weighted average of the chunks that already cover the current step; the ACT idea).

| policy (one training run each) | first | open4 | ensemble |
|---|---|---|---|
| UR5e, 299 episodes | 38 | 46 | 44 |
| UR5e, 800 episodes | 19 | 32 | 39 |
| UR10e, 300 episodes | 21 | 45 | **52 (87%, 95% CI 76-93%)** |
| KAIROS, 300 episodes | 3 | pending | pending |

Reading: re-planning from every observation makes the policy jitter; smoothing the executed actions raises success on every checkpoint (UR10e 21 -> 52). More data (299 -> 800 episodes) did not help by itself in single runs, and one training run can differ a lot from another (38 vs 19 with the same mode on different data), so a variance study (3 more seeds) is in progress; do not quote a single run as the policy's level. The scripted reference stays 60/60 on the same seeds.

## Update 2026-10-29 late: variance across training runs and longer training (smoothed `ensemble` execution, 60 fresh seeds each)
| policy | training runs | successes of 60 |
|---|---|---|
| UR5e, 299 episodes, 40 epochs | 4 runs (seed unset, 1, 2, 3) | 45, 45, 35, 42 (mean 41.8, 70%) |
| UR5e, 299 episodes, 100 epochs | 1 run | 25 |
| UR5e, 800 episodes, 40 epochs | 1 run | 39 |
| UR10e, 300 episodes, 40 epochs | 1 run | 52 |
| UR10e, 300 episodes, 100 epochs | 1 run | **60 (100%)** |
| KAIROS, 300 episodes, 40 epochs | 1 run | 40 |
| KAIROS, 300 episodes, 100 epochs | 1 run | 56 (93%) |
Reading: for UR10e and KAIROS, longer training helped (52 -> 60, 40 -> 56); for UR5e a 100-epoch run was worse (25) while four 40-epoch runs averaged 42 (spread 35-45), so UR5e is the least stable robot and a single run is not representative; I would quote the 4-run mean for UR5e and treat the single-run UR10e/KAIROS numbers as one sample each (no confidence beyond the 60-seed Wilson interval, which is wide at 40-52 of 60). The scripted controller is 60/60 on the same seeds. Data are scripted rollouts of one human demonstration's style; this shows the exported data are learnable closed loop, not that a policy learned from the human video itself.

## Update 2026-10-30 01:10: three 100-epoch runs per robot (smoothed execution, 60 fresh seeds)
| robot | runs (successes of 60) | mean |
|---|---|---|
| UR10e | 60, 54, 54 | 56 (93%) |
| KAIROS | 56, 23, 27 | 35 (58%); unstable: the weak runs fail mostly at release and settling |
| UR5e (40 epochs, 4 runs) | 45, 45, 35, 42 | 42 (70%) |
A DAgger-style variant (roll out the policy, label the states it visited with the scripted run's targets of the same seed, retrain on the union) is being tested to reduce this run-to-run spread; see the next update.

## Headline (2026-10-30 02:55): one multi-robot policy matches the scripted controller on three robots
A single vision policy (a one-hot robot id appended to the joint-position input; 900 training episodes = 300 each for UR5e, UR10e, KAIROS; 60 epochs; trained on the scripted fix-stack rollouts of one human demonstration's style) was evaluated closed loop, with no scripted controller, on seeds never used for training (training seeds 2000-2299):

| training run | seeds 6000-6059 (UR5e / UR10e / KAIROS) | seeds 7000-7119 (UR5e / UR10e / KAIROS) |
|---|---|---|
| multi, seed 1 | 60/60, 60/60, 60/60 | 120/120, 120/120, 120/120 |
| multi, seed 2 | 60/60, 60/60, 60/60 | not run |
| scripted fix stack (reference) | 60/60 | 60/60 (earlier runs) |
Per robot, 120/120 gives a 95% Wilson lower bound of 96.9%; the 360 episodes of seed 1 on the second seed set give 99.0%. The same recipe trained on ONE robot's 300 episodes gave 23-60/60 depending on the run, so combining robots (with the robot id) is what stabilised it here; I have not isolated why (more data, shared structure across embodiments, or regularisation), and a data-scaling run is queued to separate these.

Conditions and limits (important):
- The result needs the temporal-ensemble execution (exponentially weighted average of overlapping predicted chunks). With the "first" mode (only the newest prediction each step) the same multi policy scored 8/60 on UR5e seeds 7000-7059.
- Simulation only; one task (block to tray), one demonstration's style; the data are scripted rollouts, so this shows the exported data are learnable closed loop, not that a policy learned from the human video itself. Block position jitter is +-3 cm; no distractors, no new object shapes.
- Two training runs; the evaluation seeds are different from the training seeds, but the physics, scene and robots are the same ones used to generate the data.
- DAgger-style correction data did NOT help: KAIROS 50 and 38 of 60 (plain runs 56, 23, 27) and UR10e 9 of 60 for the first seed (plain 60, 54, 54); the second UR10e seed was stopped. The label used (the scripted run's target at the same time step) can be inconsistent with the state the policy has actually reached, which may explain it; it was not investigated further.

## Data scaling of the multi-robot policy (60 epochs, seed 1, one run each, 60 fresh seeds 6000-6059, ensemble execution)
| episodes per robot (total) | UR5e | UR10e | KAIROS |
|---|---|---|---|
| 33 (99) | 36 | 50 | 54 |
| 100 (300) | 44 | 60 | 60 |
| 300 (900) | 60 | 60 | 60 |
Success rises monotonically with data for every robot; UR5e needs the most. The no-robot-id ablation (same 900 episodes) and an out-of-distribution test (larger cubes, three distractors) are running. Single runs: treat differences of a few episodes as noise.

## Ablation: is the robot id needed? And how far does the policy generalise? (2026-10-30)
Same 900 episodes, 60 epochs, seed 1, ensemble execution, 60 fresh seeds (6000-6059):
| policy | UR5e | UR10e | KAIROS |
|---|---|---|---|
| multi with robot one-hot (`multi_s1`) | 60 | 60 | 60 |
| multi WITHOUT robot id (`multi3`) | 60 | 60 | 60 |
So the robot id is not what makes the combined policy work: the network infers the embodiment from the images and joint positions. The stabilising factor is the pooled data across robots (plus the shared structure of the three scripted trajectories); this experiment does not separate "more data" from "shared structure", but the data-scaling table above shows data amount alone matters for each robot.

Out-of-distribution test of `multi_s1` (trained only on the default 4 cm cube, no distractors; 60 seeds per cell; the scripted fix stack handles these cases, e.g. 57/60 at 6 cm on UR5e in `object_scale_v1`):
| test condition | UR5e | UR10e | KAIROS |
|---|---|---|---|
| 5 cm cube (half edge 2.5 cm) | 35 | 59 | 60 |
| 6 cm cube (half edge 3 cm) | 0 | 4 | 0 |
| 4 cm cube + 3 distractor objects | 13 | 1 | 5 |
The policy does NOT generalise beyond its training distribution: small changes in cube size or clutter break it, which is the expected weakness of cloning a narrow set of demonstrations. A policy trained on mixed cube sizes (3-7 cm) and distractors (`multi_mixed`, 100 standard + 300 mixed episodes per robot) is being tested on the same conditions.

## Generalisation fixed by mixed training data (2026-10-30 04:40): `multi_mixed`
Training data per robot: 100 standard episodes + 300 episodes with a random cube size (3-7 cm) and 0 or 3 distractor objects (scripted fix-stack successes only); one multi-robot policy without a robot id, 60 epochs, seed 1, ensemble execution, 60 fresh seeds per cell. All numbers are successes of 60.
| condition (unseen seeds) | UR5e | UR10e | KAIROS |
|---|---|---|---|
| standard 4 cm cube | 60 | 60 | 60 |
| mixed sizes + distractors (training distribution) | 60 | 60 | 60 |
| 6 cm cube | 60 | 60 | 60 |
| 4 cm cube + 3 distractors | 60 | 60 | 60 |
| 2.5 cm cube (outside the training sizes) | 60 (scripted 60) | 60 (60) | 60 (60) |
| 4 cm cube + 5 distractors (more than in training) | 60 (60) | 60 (60) | 60 (60) |
| 6 cm cube + 5 distractors | 60 (56) | 60 (59) | 60 (60) |
| 7 cm cube + 5 distractors | 60 (48) | 60 (58) | 58 (60) |
(brackets: the scripted fix stack on the same seeds). The earlier single-distribution policy `multi_s1` scored 0-35 on the 6 cm cube and 1-13 on 3 distractors, so the failure was a data-coverage problem, not a limit of the model.
Notes: (1) in the hardest cells the learned policy matches or beats the scripted controller (UR5e 60 vs 48 at 7 cm with 5 distractors); one reading is that the vision policy adapts its grasp where the open-loop scripted plan cannot, but this was not isolated, and the training set contains only scripted SUCCESSES, which may bias it toward easy-to-grasp configurations; (2) one training run, one seed per cell; (3) still simulation only, the same simulator, scene and robots that produced the data, a single cube shape (box), no new objects or table appearance, no sensor noise.


## Four robots in one policy (`multi4`, 2026-10-30 05:20): UR5e, UR10e, KAIROS arm and KAIROS on its mobile base (parked)
One policy, no robot id, 80 standard + 240 mixed episodes per robot (1300 episodes), 60 epochs, seed 1, ensemble execution, 60 fresh seeds (6000-6059). Successes of 60 (the scripted fix stack on the same seeds in brackets); `hard` = 6 cm cube + 5 distractors.
| robot | standard | mixed sizes + distractors | hard |
|---|---|---|---|
| ur5e | 60 (scripted 60) | 60 (scripted 59) | 60 (scripted 56) |
| ur10e | 60 (scripted 60) | 60 (scripted 59) | 60 (scripted 59) |
| kairos | 60 (scripted 60) | 60 (scripted 60) | 60 (scripted 60) |
| kairos_mobile | 60 (scripted 60) | 60 (scripted 60) | 60 (scripted 60) |
The mobile base stays parked at its set-point (only the arm and gripper are commanded); this is the arm on the mobile platform, not navigation. One training run; simulation only; same limits as above.

### multi4, second training seed (seed 2, 2026-10-30 08:25)
Same data (1300 episodes), same recipe, only the training seed differs (val L1 0.0139); same 60 held-out seeds (6000-6059), ensemble execution. Successes of 60 (scripted fix stack in brackets); files `eval_multi4s2_*.json`.
| robot | standard | mixed sizes + distractors | hard |
|---|---|---|---|
| ur5e | 60 (scripted 60) | 60 (scripted 59) | 60 (scripted 56) |
| ur10e | 60 (scripted 60) | 60 (scripted 59) | 60 (scripted 59) |
| kairos | 60 (scripted 60) | 60 (scripted 60) | 60 (scripted 60) |
| kairos_mobile | 60 (scripted 60) | 60 (scripted 60) | 60 (scripted 60) |
Both training seeds of `multi4` reach 60/60 in all 12 cells, so the four-robot result is not a one-run accident (two seeds, same 60 evaluation seeds, so this does not measure variation across evaluation seeds). Limits unchanged: simulation only, same simulator and cube shape as the training data, mobile base parked.

### multi4, both training seeds on 60 NEW evaluation seeds (7000-7059, 2026-10-30 12:25)
Same two trained policies, evaluation seeds never used before (files `eval_multi4s1_new_*.json`, `eval_multi4s2_new_*.json`); successes of 60, ensemble execution.
- Training seed 1: 60/60 in 10 of 12 cells; UR5e mixed 59/60 and UR10e mixed 59/60 (the scripted controller scores 59 and 60 on the same seeds).
- Training seed 2: 60/60 in all 12 cells.
So the four-robot result holds on a second, independent set of evaluation seeds (24 cells over two policies: 22 at 60/60, two at 59/60). Limits unchanged: two training runs, simulation only, same simulator and cube shape as the training data, mobile base parked.
