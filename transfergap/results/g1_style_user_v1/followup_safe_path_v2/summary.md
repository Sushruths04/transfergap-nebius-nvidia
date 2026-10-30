# G1 contact attempt v1 (g1_sonic), protocol `g1_block_to_tray_v1`

Tier rates per rollout with Wilson 95% intervals [%]. Rollouts of one seed share the scene, so the
per-rollout intervals overstate independence; the per-trial table counts seeds where any of the
repeated rollouts reached the tier. Simulator labels only.

| condition | oracle | rollouts | touch | grasp (lift >= 5 cm in hand) | place (in tray, settled) |
|---|---|---|---|---|---|
| user_safe_path_v2_robot_pace | perception | 30 (10 seeds) | 37% (11/30) [22, 55] | 0% (0/30) [0, 11] | 0% (0/30) [0, 11] |

| condition | touch, any rollout | grasp, any rollout | place, any rollout | seeds with mixed place outcomes | robot fell | place failure reasons |
|---|---|---|---|---|---|---|
| user_safe_path_v2_robot_pace | 60% (6/10) [31, 83] | 0% (0/10) [0, 28] | 0% (0/10) [0, 28] | 0 | 0 | no_lift:30, not_released_and_settled_at_goal:30 |

Per rollout (seed.rollout tiers T/G/P, max lift cm, block xy displacement cm, reasons):

- user_safe_path_v2_robot_pace: 100.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 100.1 T-- 0.0 0.1 (no_lift,not_released_and_settled_at_goal); 100.2 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 101.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 101.1 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 101.2 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 102.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 102.1 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 102.2 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 103.0 T-- 0.0 0.3 (no_lift,not_released_and_settled_at_goal); 103.1 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 103.2 T-- 0.0 0.2 (no_lift,not_released_and_settled_at_goal); 104.0 T-- 0.0 0.1 (no_lift,not_released_and_settled_at_goal); 104.1 T-- 0.0 0.1 (no_lift,not_released_and_settled_at_goal); 104.2 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 105.0 T-- 0.0 0.1 (no_lift,not_released_and_settled_at_goal); 105.1 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 105.2 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 106.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 106.1 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 106.2 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 107.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 107.1 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 107.2 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 108.0 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 108.1 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 108.2 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 109.0 T-- 0.0 0.1 (no_lift,not_released_and_settled_at_goal); 109.1 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 109.2 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal)
