# Pipeline report

input: `/ws/transfergap/internet_v1/pexels_7205253_woman_box.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | ok | {"metric_scale": 1.0, "shoulder_width_ref_m": null, "frames": 101, "events": "given", "pinch_extent_m": [0.678, 0.85, 0.386], "plausibility": "ok"} |
| feasibility | ok | {"ur5e": {"verdict": "style infeasible for this robot", "reasons": ["collides: reach 6.7 cm, retreat 4.8 cm (g_base, g_left_coupler, g_left_follower, g_left_pad, g_left_spring_link, g_right_coupler, g_right_follower, g_right_pad, g_right_spring_link)"], "worst": {"max_ik_err_m": 0.000199427935292167 |
| rollouts | ok | {"ur5e": {"raw": "0/60", "all_fixes": "0/60"}, "ur10e": {"raw": "0/60", "all_fixes": "0/60"}, "kairos": {"raw": "0/60", "all_fixes": "33/60"}} |
