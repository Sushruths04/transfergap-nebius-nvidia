# G1: pre-check verdict of the executed plan vs rollout outcome (post-hoc, frozen 2 cm threshold)

| run | flagged seeds | flagged rollouts | not-flagged rollouts |
|---|---|---|---|
| person 1, human pace | 106 | 0/3 grasp, 0/3 place | 0/27 grasp, 0/27 place |
| person 1, speed cap 3 | 106 | 0/3 grasp, 0/3 place | 18/27 grasp, 8/27 place |
| person 1, robot pace | 106 | 0/3 grasp, 0/3 place | 24/27 grasp, 20/27 place |
| person 2, her pace | 100, 101, 102, 103, 104, 105, 106, 107, 108, 109 | 0/30 grasp, 0/30 place | - |
| person 2, robot pace | 100, 101, 102, 103, 104, 105, 106, 107, 108, 109 | 0/30 grasp, 0/30 place | - |
| person 2 + safe_path_v2, robot pace | 100, 101, 102, 103, 104, 105, 106, 107, 108, 109 | 0/30 grasp, 0/30 place | - |

All runs: flagged 0/99 grasped; not flagged 42/81 grasped (human-pace runs fail for a different reason: speed).
