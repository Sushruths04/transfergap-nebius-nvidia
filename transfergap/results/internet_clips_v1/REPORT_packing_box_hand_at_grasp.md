# Pipeline report

input: `/ws/transfergap/fsam_cmp/pexels_fsam.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | ok | {"metric_scale": 1.0, "shoulder_width_ref_m": null, "frames": 55, "events": "given", "pinch_extent_m": [0.254, 0.469, 0.384], "plausibility": "ok"} |
| feasibility | ok | {"ur5e": {"verdict": "style infeasible for this robot", "reasons": ["collides: carry 4.3 cm, retreat 4.8 cm (carried_block, g_base, g_left_coupler, g_left_follower, g_left_pad, g_left_spring_link, g_right_coupler, g_right_follower, g_right_pad)"], "worst": {"max_ik_err_m": 0.0001963339836377855, "ma |
| rollouts | ok | {"ur5e": {"raw": "0/60", "all_fixes": "0/60"}, "ur10e": {"raw": "0/60", "all_fixes": "0/60"}, "kairos": {"raw": "0/60", "all_fixes": "0/60"}} |
