# Pipeline report

input: `/ws/transfergap/showcase_out_r6/joints.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | ok | {"metric_scale": 0.4231, "shoulder_width_ref_m": 0.44, "frames": 147, "events": "given", "pinch_extent_m": [0.305, 0.035, 0.243], "plausibility": "ok"} |
| feasibility | ok | {"ur5e": {"verdict": "feasible", "reasons": [], "worst": {"max_ik_err_m": 0.00019939030272319734, "max_penetration_m": 0.002830528995547539}}, "ur10e": {"verdict": "feasible", "reasons": [], "worst": {"max_ik_err_m": 0.00019676681604271248, "max_penetration_m": 0.002830528995547539}}, "kairos": {"ve |
| rollouts | ok | {"ur5e": {"raw": "31/60", "all_fixes": "60/60"}, "ur10e": {"raw": "34/60", "all_fixes": "60/60"}, "kairos": {"raw": "48/60", "all_fixes": "60/60"}} |
