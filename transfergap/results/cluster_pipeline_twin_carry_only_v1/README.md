# cluster_pipeline_twin_carry_only_v1 (ABLATION of `../cluster_pipeline_twin_standin_v1`; illustrative; not in the paper)

Same clip, seeds, robots and fix stack, and the same real carry vector (26 cm, direction preserved by the scene twin), but the simulator's DEFAULT object and container sizes (4 cm cube, 14 cm tray, 2.5 cm walls).
Successes (no correction -> fix stack, of 60): UR5e 36 -> 60, UR10e 33 -> 60, KAIROS mobile 47 -> 60; the pre-check calls UR5e and UR10e feasible.

Compared with the fixed default layout (35/36/49 -> 60) these are essentially the same, so **the carry distance and direction hardly change the outcome**. The large drop in the stand-in run (7/9/13 -> 52/51/60) therefore came from
the ASSUMED larger box and the taller, narrower container (6 cm walls), i.e. from object and container geometry. This corrects the emphasis in `DEEP_ANALYSIS_REALISM_AND_REALTIME.md` section 1: the real distance is still not the sim's, but object size and container height are what matter for the result.
