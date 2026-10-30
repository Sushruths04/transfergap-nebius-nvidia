# Pipeline report

input: `/tmp/clip_full_joints.npz`

| stage | status | detail |
|---|---|---|
| perceive | ok | "" |
| demo | FAILED | {"frames": 479, "events": "auto (aperture segmenter)", "pinch_extent_m": [5.866, 0.627, 4.43], "plausibility": ["hand path extent [5.87, 0.63, 4.43] m exceeds 1.5 m (pose estimate is not metric or failed)"]} |
| feasibility | skipped (earlier stage failed) | "" |
| rollouts | skipped (earlier stage failed) | "" |
