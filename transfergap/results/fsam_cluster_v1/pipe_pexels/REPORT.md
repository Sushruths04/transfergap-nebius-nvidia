# Pipeline report

input: `/ws/transfergap/fsam_cmp/pexels_fsam.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | ok | {"metric_scale": 1.0651, "shoulder_width_ref_m": 0.4, "frames": 55, "events": "given", "pinch_extent_m": [0.27, 0.499, 0.409], "plausibility": "ok"} |
| feasibility | ok | {"ur5e": {"verdict": "style infeasible for this robot", "reasons": ["collides: carry 4.6 cm, retreat 5.4 cm (carried_block, g_base, g_left_coupler, g_left_follower, g_left_pad, g_left_spring_link, g_right_coupler, g_right_follower, g_right_pad)"], "worst": {"max_ik_err_m": 0.00019952281804315897, "m |
| rollouts | ok | {"ur5e": {"raw": "0/60", "all_fixes": "1/60"}, "ur10e": {"raw": "0/60", "all_fixes": "0/60"}} |
