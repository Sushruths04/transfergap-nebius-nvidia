# Pipeline report

input: `/ws/transfergap/internet_v1/pexels_6894444_clothes_bin.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | FAILED | {"metric_scale": 1.0, "shoulder_width_ref_m": null, "frames": 111, "events": "given", "pinch_extent_m": [1.206, 3.179, 0.586], "plausibility": ["hand path extent [1.21, 3.18, 0.59] m exceeds 1.5 m (pose estimate is not metric or failed)"]} |
| feasibility | skipped (earlier stage failed) | "" |
| rollouts | skipped (earlier stage failed) | "" |
