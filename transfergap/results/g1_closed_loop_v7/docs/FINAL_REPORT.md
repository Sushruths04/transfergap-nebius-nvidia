# G1 pick-and-place on the cluster: final report (2026-10-04)

## What was asked
Build a working prototype of the G1 humanoid picking a block from a table and placing it in a tray (simulation), test it
properly, fix what breaks, and package it as a Docker image that can run on the cluster and on Nebius machines.

## What was built
- A dev pod on the free L40S node with its own 300 Gi volume (the shared volume is untouched). Everything is reproducible
  from `docs/RUNBOOK.md` and `envs/bootstrap_pod.sh`.
- The full G1 simulation chain running on the cluster: MuJoCo sim, GEAR-SONIC deploy built from source against
  TensorRT 10.13.3.9, weights verified by checksum, all pinned versions matched.
- A closed-loop streamer (`g1/stream_cl.py`) that corrects the arm commands from the robot's own joint state, plus a
  hybrid mode: closed loop through approach, descend and close, then the open-loop plan for the carry.
- A VR 3-point streamer (`g1/stream_vr3.py`): written and unit-tested, not run in the simulator.
- 167 tests (23 skipped, they need data files that are not in git); new tests cover the privacy of the closed-loop inputs
  (robot joints and pelvis pose only, never the block or scene), the correction maths, the carry offset, and the settle option.
- A Docker image built on the cluster with Kaniko and pushed to the GitLab registry (see below).

## Root cause found
The deployed controller follows commanded wrist-pitch and elbow angles only partly (a wrist pitch commanded to -1.15 rad
reaches about -0.4 rad; the rest-pose wrist sits at -0.4 rad although 0 is commanded), and the pelvis slides back 5-20 cm
during a reach. An open-loop plan therefore puts the hand 10 cm or more from where it was planned. Static balance is not
the cause (the centre of mass moves under 1 cm during the reach).

## Results (simulator labels, repo scorer, every test pre-registered with a protocol file, seeds never reused)
| test | seeds | touch | grasp (lift >= 5 cm) | place in tray |
|---|---|---|---|---|
| open loop, v1 + v2 + v4 sets pooled | 80 | | 17/80 (21%) | 12/80 (15%, Wilson 95% 9-24) |
| closed loop only, v1 (orientation weight 0.25) | 20 | 19/20 | 7/20 | 0/20 |
| closed loop only, v2 (orientation weight 0.05) | 20 | 18/20 | 9/20 | 0/20 |
| closed loop + carry offset, v3 | 40 | 36/40 | 23/40 | 4/40 |
| refinement v5 (longer settle) | 40 | 36/40 | 12/40 | 6/40 (rejected by the pre-set rule) |
| hybrid v4 | 40 | 40/40 | 23/40 | 17/40 (42.5%) |
| open loop on the same seeds as v4 | 40 | 37/40 | 6/40 | 4/40 (10%) |
| hybrid v6 confirmation, frozen | 40 | 36/40 | 12/40 | 10/40 (25%) |
| **hybrid v4 + v6 pooled (80 fresh seeds)** | 80 | 76/80 | **35/80 (44%)** | **27/80 (34%, 24-45)** |
| hybrid repeatability, 10 seeds x 3 | 30 | 28/30 | 16/30 | 9/30; 7 of 10 seeds placed at least once |

Statistics: paired on the v4 seeds, place only-hybrid 15 vs only-open 2 (McNemar exact p = 0.0023). Pooled hybrid vs pooled
open loop: place p = 0.009, grasp p = 0.004 (Fisher). The headline number to quote is the pooled 34% place rate (about one
attempt in three), against 15% for the open-loop stream, not the best single set (42.5%).

## What did not work (all reported)
- Pure closed loop for the whole motion: more grasps, but the carry wobbles and the block misses the tray (v1, v2, v3).
- Higher loop gains (1.5 and 2): unstable, pelvis slides back. A resolved-rate loop run before fixing jittery joint
  velocities: oscillated.
- The first closed-loop dev results (3 of 5 grasps) did not replicate on held-out seeds: small dev samples misled.
- A carry offset measured on earlier rollouts moved the carry about twice as far as commanded (overshoot).
- Settling longer before closing (v5): worse (grasp 12/40, place 6/40); the reason was not found.

## Limits, stated plainly
- Simulation only: one block, one tray. Not tested on a real robot.
- About one attempt in three places the block. Outcomes are stochastic even for the same scene.
- The grasp rate varied between 40-seed sets (30% to 57%) for the same method; the cause was not found (timing was
  identical across sets, no failed rollouts). The pooled estimate is the honest figure.
- 12 of 17 non-grasps in v4 closed at plausible hand positions; why they failed to lift was not established.
- The VR 3-point input was not run in the simulator.
- Fine-tuned Cosmos critic, pose-estimator bake-offs: not rerun here (earlier results stand). A zero-shot Cosmos check on
  the G1 videos worked (balanced accuracy 0.83 for placed, 0.87 for grasped).

## Docker image
`registry.example` tags `2026-10-04` and `latest` (the earlier tag `2026-10-03`
is the pre-hybrid version). Built on the cluster; the 167 tests ran inside the build. Weights are not included: run
`docker/fetch_weights.sh` with your `HF_TOKEN` at first start. A GPU rollout from inside the image has not been run yet
(the cluster pod has no container runtime): the first real check is a `docker run --gpus all` on a Docker host.

## Where everything is
- Volume `<cluster-volume>`: `docs/` (PLAN.md, RUNBOOK.md, work_log.md, FINAL_REPORT.md, scored results, protocols),
  `runs/g1_cl/` (all rollouts and protocols), `repo/` (code), `images/` (image tars).
- Code changes for your repo as a reviewable patch (13 files): scratchpad `tg-cluster/closed_loop.patch`, not applied.
- Method note in the repo: `transfergap/g1/CLOSED_LOOP.md`.

## Suggested next steps
1. Run the image with a GPU on a Docker host and confirm one rollout and the tests there.
2. Apply the patch to the repo after review.
3. Look into why the 12 plausible-position closes fail to lift (finger closure timing, hand orientation at close).
4. Try the VR 3-point streamer; it targets the root cause (joint-angle tracking) directly.
5. Revoke the GitLab token when finished.
