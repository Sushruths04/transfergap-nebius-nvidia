# Pipeline report

input: `/ws/transfergap/fsam_cmp/pexels_fsam.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | ok | {"metric_scale": 1.0, "shoulder_width_ref_m": null, "frames": 55, "events": "given", "pinch_extent_m": [0.254, 0.469, 0.384], "plausibility": "ok"} |
| feasibility | ok | {"ur5e": {"verdict": "feasible", "reasons": [], "worst": {"max_ik_err_m": 0.00019974152617837474, "max_penetration_m": 0.0}}, "ur10e": {"verdict": "feasible", "reasons": [], "worst": {"max_ik_err_m": 0.00019993292639288558, "max_penetration_m": 0.0}}, "kairos": {"verdict": "feasible", "reasons": [], |
| rollouts | ok | {"ur5e": {"raw": "0/60", "all_fixes": "51/60"}, "ur10e": {"raw": "0/60", "all_fixes": "52/60"}, "kairos": {"raw": "0/60", "all_fixes": "60/60"}} |
