# G1 copying the author's demo — results (all pre-registered in protocol.json)

| condition | seeds x rollouts | touch | grasp | place |
|---|---|---|---|---|
| v1 copied path, robot pace | 100-109 x 3 | 13/30 | 0/30 | 0/30 |
| v1 copied path, the author's own pace | 100-109 x 3 | 15/30 | 0/30 | 0/30 |
| v2 + safe_path_v2 | 100-109 x 3 | 11/30 | 0/30 | 0/30 |
| v3 approach_from_above (top-down final approach) | 100-109 x 3 | 13/30 | 0/30 | 0/30 |
| v4 stance offset measured on v1-v3 (0.00, 0.02), copied path | 110-119 x 3 | 13/30 | 0/30 | 0/30 |
| v4 stance + approach_from_above | 110-119 x 3 | 19/30 | 0/30 | 0/30 |
| v5 dev: forward grasp offset 4 / 6 / 8 cm | 120-129 x 1 each | 2/10 each | 0/10 each | 0/10 each (test not run) |

Reference: person 1 with the same pipeline places 20/30 (g1_style_v1). Five hypotheses, five falsified predictions.
What the logs show: the G1 tracks every planned wrist path ~7 cm short; at the end of the author's reach the planned
wrist is already 10.3 cm behind the block (person 1: 4.3 cm), and person 1's copied carry then sweeps the hand
forward through the block (to 6.8 cm), scooping it — the author lifts straight up. So the G1 grasp in this pipeline
(IK keyframes tracked by SONIC, Dex3 calibration frozen on person-1-style motion) depends on the demonstrator's
motion, and none of the tried per-demo fixes (path safety, approach direction, stance, grasp offset) recovers it.
Arms (UR5e/UR10e) on the same demo: 59/60 and 56/60 (user_demo_v1). Open: closed-loop grasping on the G1
(re-planning from the measured wrist) instead of open-loop IK keyframes.
