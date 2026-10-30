# Pipeline report

input: `/tmp/user_clip.mp4`

| stage | status | detail |
|---|---|---|
| perceive | ok | {"estimator": "RTMW3D-L", "wall_s": 12.6, "log_tail": ["wrote /ws/transfergap/ctx_cam/pipe_user_v2/joints.npz: (270, 133, 3), median 42.3 fps, missing 0"]} |
| demo | ok | {"frames": 147, "events": "given", "pinch_extent_m": [0.722, 0.083, 0.574], "plausibility": "ok"} |
| feasibility | ok | {"ur5e": {"verdict": "style infeasible for this robot", "reasons": ["collides: carry 0.7 cm, retreat 1.9 cm (carried_block, g_left_follower, g_left_pad, g_right_follower, g_right_pad)"], "worst": {"max_ik_err_m": 0.00019941934443022295, "max_penetration_m": 0.018555879224906414}}, "ur10e": {"verdict |
| rollouts | ok | {"ur5e": {"raw": "25/60", "all_fixes": "58/60"}, "ur10e": {"raw": "7/60", "all_fixes": "60/60"}, "kairos": {"raw": "41/60", "all_fixes": "60/60"}} |
