# G1 contact attempt v1 (g1_sonic), protocol `g1_block_to_tray_v1`

Tier rates per rollout with Wilson 95% intervals [%]. Rollouts of one seed share the scene, so the
per-rollout intervals overstate independence; the per-trial table counts seeds where any of the
repeated rollouts reached the tier. Simulator labels only.

| condition | oracle | rollouts | touch | grasp (lift >= 5 cm in hand) | place (in tray, settled) |
|---|---|---|---|---|---|
| user_stance_above_robot_pace | perception | 30 (10 seeds) | 63% (19/30) [46, 78] | 0% (0/30) [0, 11] | 0% (0/30) [0, 11] |

| condition | touch, any rollout | grasp, any rollout | place, any rollout | seeds with mixed place outcomes | robot fell | place failure reasons |
|---|---|---|---|---|---|---|
| user_stance_above_robot_pace | 80% (8/10) [49, 94] | 0% (0/10) [0, 28] | 0% (0/10) [0, 28] | 0 | 0 | no_lift:30, not_released_and_settled_at_goal:30 |

Per rollout (seed.rollout tiers T/G/P, max lift cm, block xy displacement cm, reasons):

- user_stance_above_robot_pace: 110.0 T-- 0.0 0.1 (no_lift,not_released_and_settled_at_goal); 110.1 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 110.2 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 111.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 111.1 T-- 0.0 0.8 (no_lift,not_released_and_settled_at_goal); 111.2 T-- 0.0 0.7 (no_lift,not_released_and_settled_at_goal); 112.0 T-- 0.0 0.4 (no_lift,not_released_and_settled_at_goal); 112.1 T-- 0.0 0.6 (no_lift,not_released_and_settled_at_goal); 112.2 T-- 0.1 0.4 (no_lift,not_released_and_settled_at_goal); 113.0 T-- 0.0 0.5 (no_lift,not_released_and_settled_at_goal); 113.1 T-- 0.1 2.4 (no_lift,not_released_and_settled_at_goal); 113.2 T-- 0.0 1.0 (no_lift,not_released_and_settled_at_goal); 114.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 114.1 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 114.2 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 115.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 115.1 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 115.2 T-- 0.0 0.4 (no_lift,not_released_and_settled_at_goal); 116.0 T-- 0.0 0.6 (no_lift,not_released_and_settled_at_goal); 116.1 T-- 0.1 0.6 (no_lift,not_released_and_settled_at_goal); 116.2 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 117.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 117.1 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 117.2 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 118.0 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 118.1 T-- 0.0 0.1 (no_lift,not_released_and_settled_at_goal); 118.2 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 119.0 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 119.1 T-- 0.0 0.1 (no_lift,not_released_and_settled_at_goal); 119.2 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal)
