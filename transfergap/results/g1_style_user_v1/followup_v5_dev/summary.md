# G1 contact attempt v1 (g1_sonic), protocol `g1_block_to_tray_v1`

Tier rates per rollout with Wilson 95% intervals [%]. Rollouts of one seed share the scene, so the
per-rollout intervals overstate independence; the per-trial table counts seeds where any of the
repeated rollouts reached the tier. Simulator labels only.

| condition | oracle | rollouts | touch | grasp (lift >= 5 cm in hand) | place (in tray, settled) |
|---|---|---|---|---|---|
| dev_dx0.04 | perception | 10 (10 seeds) | 20% (2/10) [6, 51] | 0% (0/10) [0, 28] | 0% (0/10) [0, 28] |
| dev_dx0.06 | perception | 10 (10 seeds) | 20% (2/10) [6, 51] | 0% (0/10) [0, 28] | 0% (0/10) [0, 28] |
| dev_dx0.08 | perception | 10 (10 seeds) | 20% (2/10) [6, 51] | 0% (0/10) [0, 28] | 0% (0/10) [0, 28] |

| condition | touch, any rollout | grasp, any rollout | place, any rollout | seeds with mixed place outcomes | robot fell | place failure reasons |
|---|---|---|---|---|---|---|
| dev_dx0.04 | 20% (2/10) [6, 51] | 0% (0/10) [0, 28] | 0% (0/10) [0, 28] | 0 | 0 | no_lift:10, not_released_and_settled_at_goal:10 |
| dev_dx0.06 | 20% (2/10) [6, 51] | 0% (0/10) [0, 28] | 0% (0/10) [0, 28] | 0 | 0 | no_lift:10, not_released_and_settled_at_goal:10 |
| dev_dx0.08 | 20% (2/10) [6, 51] | 0% (0/10) [0, 28] | 0% (0/10) [0, 28] | 0 | 0 | no_lift:10, not_released_and_settled_at_goal:10 |

Per rollout (seed.rollout tiers T/G/P, max lift cm, block xy displacement cm, reasons):

- dev_dx0.04: 120.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 121.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 122.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 123.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 124.0 T-- 0.0 0.1 (no_lift,not_released_and_settled_at_goal); 125.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 126.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 127.0 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 128.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 129.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal)
- dev_dx0.06: 120.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 121.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 122.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 123.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 124.0 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 125.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 126.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 127.0 T-- 0.0 0.6 (no_lift,not_released_and_settled_at_goal); 128.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 129.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal)
- dev_dx0.08: 120.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 121.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 122.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 123.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 124.0 T-- 0.0 1.4 (no_lift,not_released_and_settled_at_goal); 125.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 126.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 127.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 128.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 129.0 T-- 0.0 1.5 (no_lift,not_released_and_settled_at_goal)
