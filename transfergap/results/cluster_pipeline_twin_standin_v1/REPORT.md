# Pipeline report

input: `/ws/transfergap/ctx_cam/user_pose_v2.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | ok | {"metric_scale": 0.3846, "shoulder_width_ref_m": 0.4, "frames": 147, "events": "given", "pinch_extent_m": [0.278, 0.032, 0.221], "plausibility": "ok", "scene": "STAND-IN twin from the author's pose (sizes ASSUMED, not measured)", "scene_sha": "6875929c3e57", "human_carry_m": 0.259, "scene_carry_m":  |
| feasibility | ok | {"ur5e": {"verdict": "style infeasible for this robot", "reasons": ["collides: carry 1.4 cm, retreat 1.6 cm (g_left_follower, g_right_follower)"], "worst": {"max_ik_err_m": 0.0001965729127497628, "max_penetration_m": 0.01613360790082624}}, "ur10e": {"verdict": "style infeasible for this robot", "rea |
| rollouts | ok | {"ur5e": {"raw": "7/60", "all_fixes": "52/60"}, "ur10e": {"raw": "9/60", "all_fixes": "51/60"}, "kairos_mobile": {"raw": "13/60", "all_fixes": "60/60"}} |
