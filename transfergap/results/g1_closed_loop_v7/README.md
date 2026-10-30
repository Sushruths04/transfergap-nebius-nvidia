# G1 closed-loop test v7 (run on the GPU cluster GPU, copied here as evidence)

Pre-registered (`protocol.json`, written before the run): VR 3-point wrist feeding vs the frozen hybrid controller,
seeds 1100-1139, one rollout each, same seeds, decision rule = better only if >= +5 of 40 places and paired exact p < 0.05.

Result (scorer outputs in `scored_*`): hybrid touch 39/40, grasp 16/40, place **13/40**; VR 3-point touch 29/40, grasp 6/40,
place **3/40**. The hybrid stays the final G1 controller; VR 3-point is reported as worse.
Pooled hybrid over three fresh seed sets: 40/120 (33%) (see `docs/FINAL_REPORT.md`).

Raw rollouts (240 MB) stay on the cluster volume. `docs/` = the cluster-side report and work log, with the volume path
replaced by `<cluster-volume>`. The code that produced this is `g1/` (stream_cl.py, run_trials_vr3.py, stream_vr3.py,
plan_reach.py, sim_runner.py), applied from the cluster copy in this commit; it has been compile-checked here, not run.
