# G1 pick-and-place: closed-loop grasp + open-loop carry (hybrid)

Method (what `stream_cl.py` does with the settings below):
1. Plan the reach with the usual IK planner (`plan_reach.py`), once with stance offset 0 (closed-loop plan, "cl")
   and once with the calibrated stance offset -0.075 0.005 (open-loop plan, "ol"). Same timing, same phases.
2. Until the lift phase: `stream_cl.py --mode rr` corrects the arm joint commands from the robot's own measured
   joints and pelvis pose (resolved-rate loop on the measured grasp point). No block or scene state is used.
3. From the lift phase: a 1.0 s min-jerk cross-fade to the open-loop plan's joint targets for the carry and place.

Frozen settings: `--mode rr --kr 1 --lim 0.6 --w-rot 0.05 --tail-traj OL_PLAN --tail-from lift --blend-s 1.0`,
plans with `--grasp-dz 0.03 --pitch-down -0.2 --roll -0.4`.

    python plan_reach.py --out cl.npz --target-xy X Y --grasp-dz 0.03 --pitch-down -0.2 --roll -0.4
    python plan_reach.py --out ol.npz --target-xy X Y --grasp-dz 0.03 --pitch-down -0.2 --roll -0.4 --stance-offset -0.075 0.005
    python run_trials.py --traj cl.npz --run-dir RUN --seeds 800-839 --rollouts 1 \
        --closed-loop "--mode rr --kr 1 --lim 0.6 --w-rot 0.05 --tail-traj ol.npz --tail-from lift --blend-s 1.0"
    python score.py --run RUN:hybrid:fixed:cl.json --out OUT --seeds 800-839 --rollouts 1

Results (simulator labels, repo scorer; every test was pre-registered, seeds never reused):

| test | seeds | grasp | place in tray |
|---|---|---|---|
| open loop (v1, v2, v4 sets pooled) | 80 | 17/80 (21%) | 12/80 (15%) |
| hybrid v4 | 40 | 23/40 | 17/40 (42.5%) |
| open loop, same seeds as v4 | 40 | 6/40 | 4/40 (10%) |
| hybrid v6 confirmation (frozen) | 40 | 12/40 | 10/40 (25%) |
| hybrid pooled v4 + v6 | 80 | 35/80 (44%) | 27/80 (34%, Wilson 95% 24-45) |
| hybrid repeatability, 10 seeds x 3 | 30 | 16/30 | 9/30; 7 of 10 seeds placed at least once |

Tested and rejected: pure closed loop for the whole motion (more grasps, carry too imprecise: place 0/40 then 4/40
with a carry offset), closed loop with longer settle before closing (grasp 12/40, place 6/40), higher loop gains
(unstable).

Why this is needed: the deployed controller follows commanded wrist-pitch and elbow angles only partly (a wrist pitch
commanded to -1.15 rad reaches about -0.4 rad), so an open-loop plan puts the hand 10 cm or more away from where it
was planned. Limits: simulation only; one block, one tray; success is about one attempt in three; the cause of the
spread between 40-seed sets (grasp 30% to 57%) was not found.
Not tried: the SONIC VR 3-point input (`stream_vr3.py` is written and unit-tested but has not been run in the sim).
