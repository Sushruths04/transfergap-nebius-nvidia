# G1 style conditions (g1_style_v1 protocol) re-run INSIDE the `full` image

Same protocol as `results/g1_style_v1` (open-loop reach along the retargeted human path of the notebook demo, seeds 100-109 x 3 rollouts,
conditions differ only in speed: nominal, 3x cap, human pace 5.92x, per-seed true block target), run on the GPU cluster in the image
`ghcr.io/sushruths04/transfergap:full-2026-10-05` via a Deployment pod and `g1/in_image_style_run.sh` (2026-10-05, 19:19-20:57 UTC).
Scored with the repo scorer (`g1/score.py`): this folder holds `episodes_*.jsonl`, `summary.json`, `summary.md`.

| condition | VM run (g1_style_v1) touch / grasp / place | in image touch / grasp / place |
|---|---|---|
| human pace | 30 / 0 / 0 of 30 | 30 / 0 / 0 of 30 |
| 3x speed cap | 30 / 18 / 8 of 30 | 30 / 15 / 2 of 30 |
| robot nominal | 30 / 24 / 20 of 30 | 29 / 24 / 14 of 30 |

Reading: for this OPEN-LOOP controller the image does NOT do better than the earlier VM run (placements are lower at cap 3x and nominal; the sim is nondeterministic,
10 seeds x 3 rollouts). The large image-vs-host gap in `results/g1_in_image_v1` was measured on the CLOSED-LOOP hybrid controller, so it is specific to that
controller/environment combination, not a general effect of the image. Not paired by rollout; no test run.
