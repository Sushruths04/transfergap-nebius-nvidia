# cluster_pipeline_twin_standin_v1 (ILLUSTRATIVE; stand-in geometry, not a measurement; not in the paper)

First end-to-end run of the **scene twin** (`sim/twin.py`, `pipeline --scene`) on the author's clip, GPU cluster, seeds 1000-1059, frozen five-fix stack, UR5e, UR10e, KAIROS mobile.
The twin is a STAND-IN: the object-to-target vector comes from the author's own pose (26 cm, so the carry is preserved), but the object (6x4x3 cm) and the target (12x10 cm inside, 6 cm walls) are ASSUMED sizes.
The real objects were never measured. Replace `twin_standin.json` with tape-measured numbers (see `DEEP_ANALYSIS_REALISM_AND_REALTIME.md`) and rerun.

| arm | no correction | fix stack | (fixed default layout, `../cluster_pipeline_user_scaled_v1`) |
|---|---|---|---|
| UR5e | 7/60 | 52/60 | 35 -> 60 |
| UR10e | 9/60 | 51/60 | 36 -> 60 |
| KAIROS mobile | 13/60 | 60/60 | 49 -> 60 |

What it shows: with the real carry direction and distance preserved (and a taller container than the default tray), the uncorrected copy fails far more often and the stack no longer fixes everything on the arms; the pre-check calls UR5e and UR10e infeasible
(collisions in carry and retreat). So the fixed-layout counts are not a stable estimate of what happens in a real scene; they depend on the task geometry. The ablation `../cluster_pipeline_twin_carry_only_v1` separates the two: with the real carry but the default cube and tray sizes the counts do not change (36/33/47 -> 60), so the drop here comes from the ASSUMED box and the taller container, not from the carry distance or direction.
