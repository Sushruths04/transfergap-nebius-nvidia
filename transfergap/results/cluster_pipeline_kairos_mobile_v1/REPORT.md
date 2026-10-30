# Pipeline report

input: `/ws/transfergap/demos/user_clip_rtmw3d_joints.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | ok | {"frames": 147, "events": "given", "pinch_extent_m": [0.722, 0.083, 0.574], "plausibility": "ok"} |
| feasibility | ok | {"kairos": {"verdict": "style infeasible for this robot", "reasons": ["collides: carry 0.7 cm, retreat 2.8 cm (g_left_pad, g_right_pad)"], "worst": {"max_ik_err_m": 0.0001997537951054221, "max_penetration_m": 0.027516268858181057}}, "kairos_mobile": {"verdict": "style infeasible for this robot", "re |
| rollouts | ok | {"kairos": {"raw": "41/60", "all_fixes": "60/60"}, "kairos_mobile": {"raw": "41/60", "all_fixes": "60/60"}} |
