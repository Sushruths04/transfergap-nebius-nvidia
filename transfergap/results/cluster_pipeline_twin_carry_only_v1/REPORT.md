# Pipeline report

input: `/ws/transfergap/ctx_cam/user_pose_v2.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | ok | {"metric_scale": 0.3846, "shoulder_width_ref_m": 0.4, "frames": 147, "events": "given", "pinch_extent_m": [0.278, 0.032, 0.221], "plausibility": "ok", "scene": "ABLATION: real carry vector, default cube and tray sizes", "scene_sha": "81b2af1fabcf", "human_carry_m": 0.259, "scene_carry_m": 0.259, "ca |
| feasibility | ok | {"ur5e": {"verdict": "feasible", "reasons": [], "worst": {"max_ik_err_m": 0.00019628312794906202, "max_penetration_m": 0.0025825397635881667}}, "ur10e": {"verdict": "feasible", "reasons": [], "worst": {"max_ik_err_m": 0.00019960493664018353, "max_penetration_m": 0.0025825397635881667}}, "kairos_mobi |
| rollouts | ok | {"ur5e": {"raw": "36/60", "all_fixes": "60/60"}, "ur10e": {"raw": "33/60", "all_fixes": "60/60"}, "kairos_mobile": {"raw": "47/60", "all_fixes": "60/60"}} |
