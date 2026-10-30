# Pipeline report

input: `/ws/transfergap/ctx_cam/user_pose_v2.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | ok | {"metric_scale": 0.3846, "shoulder_width_ref_m": 0.4, "frames": 147, "events": "given", "pinch_extent_m": [0.278, 0.032, 0.221], "plausibility": "ok"} |
| feasibility | ok | {"ur5e": {"verdict": "feasible", "reasons": [], "worst": {"max_ik_err_m": 0.0001998279289387459, "max_penetration_m": 0.0025825397635881667}}, "ur10e": {"verdict": "feasible", "reasons": [], "worst": {"max_ik_err_m": 0.00019802330536345105, "max_penetration_m": 0.0025825397635881667}}, "kairos": {"v |
| rollouts | ok | {"ur5e": {"raw": "35/60", "all_fixes": "60/60"}, "ur10e": {"raw": "36/60", "all_fixes": "60/60"}, "kairos": {"raw": "49/60", "all_fixes": "60/60"}, "kairos_mobile": {"raw": "49/60", "all_fixes": "60/60"}} |
