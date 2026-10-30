# Pipeline report

input: `/ws/transfergap/fsam_cmp/user_fsam.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | ok | {"metric_scale": 1.2337, "shoulder_width_ref_m": 0.44, "frames": 147, "events": "given", "pinch_extent_m": [0.32, 0.654, 0.293], "plausibility": "ok"} |
| feasibility | ok | {"ur5e": {"verdict": "style infeasible for this robot", "reasons": ["collides: carry 2.2 cm, retreat 1.4 cm (g_left_pad, g_right_pad)"], "worst": {"max_ik_err_m": 0.0001843275388662994, "max_penetration_m": 0.021759679060715804}}, "ur10e": {"verdict": "style infeasible for this robot", "reasons": [" |
| rollouts | ok | {"ur5e": {"raw": "27/60", "all_fixes": "59/60"}, "ur10e": {"raw": "30/60", "all_fixes": "60/60"}, "kairos": {"raw": "45/60", "all_fixes": "60/60"}} |
