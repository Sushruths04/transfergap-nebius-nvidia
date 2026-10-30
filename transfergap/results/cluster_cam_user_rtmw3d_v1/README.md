# cluster_cam_user_rtmw3d_v1 (exploratory, not in the paper)

Chain run entirely on the GPU cluster: the author's static-camera clip (frames 760-1030 of `user_take1_21fps.mp4`) -> RTMW3D-L pose
(`demo/tools/rtmw3d_export_joints.py`, 40 fps, 0 missed frames) -> HumanDemo (window 60-206, grasp 102, release 166 in clip frames, the same
hand-annotated events as `user_demo_v1`) -> `sim.demo_repro` with the frozen stack of `demo_generalization_v5`, no retuning.

Successes on seeds 1000-1059 (these seeds were also used by earlier demo experiments):
| arm | no correction | frozen stack |
|---|---|---|
| UR5e | 25/60 | 58/60 |
| UR10e | 7/60 | 60/60 |

Caveats: a different pose estimator than `user_demo_v1` (GEM-X: 30 -> 56 on UR10e, 35 -> 59 on UR5e), so the numbers are not comparable cell by cell;
one clip, one person; the pre-check (`sim.feasibility`) called both arms "style infeasible" (collisions in carry and retreat) for the raw path;
RTMW3D is unusable on internet clips (earlier bake-off 0/600 and a garbage pinch range on a Pexels clip here). Only `repro_summary.json` is kept.

> **SUPERSEDED 2026-10-06:** this run used RTMW3D coordinates that are not metric (about 2.6x too large). Use `../cluster_pipeline_user_scaled_v1`. Kept for the record.
