# G1 contact attempt v1 (g1_sonic), protocol `g1_block_to_tray_v1`

Tier rates per rollout with Wilson 95% intervals [%]. Rollouts of one seed share the scene, so the
per-rollout intervals overstate independence; the per-trial table counts seeds where any of the
repeated rollouts reached the tier. Simulator labels only.

| condition | oracle | rollouts | touch | grasp (lift >= 5 cm in hand) | place (in tray, settled) |
|---|---|---|---|---|---|
| vr3 | fixed | 40 (40 seeds) | 72% (29/40) [57, 84] | 15% (6/40) [7, 29] | 8% (3/40) [3, 20] |

| condition | touch, any rollout | grasp, any rollout | place, any rollout | seeds with mixed place outcomes | robot fell | place failure reasons |
|---|---|---|---|---|---|---|
| vr3 | 72% (29/40) [57, 84] | 15% (6/40) [7, 29] | 8% (3/40) [3, 20] | 0 | 0 | no_lift:34, not_released_and_settled_at_goal:37 |

Per rollout (seed.rollout tiers T/G/P, max lift cm, block xy displacement cm, reasons):

- vr3: 1100.0 TG- 17.5 1.8 (not_released_and_settled_at_goal); 1101.0 T-- 0.0 0.7 (no_lift,not_released_and_settled_at_goal); 1102.0 TG- 14.9 2.1 (not_released_and_settled_at_goal); 1103.0 TGP 17.7 20.0; 1104.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1105.0 T-- 0.0 3.0 (no_lift,not_released_and_settled_at_goal); 1106.0 T-- 0.0 5.6 (no_lift,not_released_and_settled_at_goal); 1107.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1108.0 T-- 0.2 2.1 (no_lift,not_released_and_settled_at_goal); 1109.0 T-- 0.0 1.4 (no_lift,not_released_and_settled_at_goal); 1110.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1111.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1112.0 T-- 0.0 1.8 (no_lift,not_released_and_settled_at_goal); 1113.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1114.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1115.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1116.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1117.0 TGP 17.8 19.5; 1118.0 T-- 0.3 3.2 (no_lift,not_released_and_settled_at_goal); 1119.0 T-- 0.8 1.8 (no_lift,not_released_and_settled_at_goal); 1120.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1121.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1122.0 T-- 0.1 1.8 (no_lift,not_released_and_settled_at_goal); 1123.0 T-- 0.0 3.1 (no_lift,not_released_and_settled_at_goal); 1124.0 T-- 0.0 2.5 (no_lift,not_released_and_settled_at_goal); 1125.0 T-- 0.0 2.3 (no_lift,not_released_and_settled_at_goal); 1126.0 T-- 0.5 0.7 (no_lift,not_released_and_settled_at_goal); 1127.0 T-- 0.0 1.7 (no_lift,not_released_and_settled_at_goal); 1128.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1129.0 T-- 0.0 1.9 (no_lift,not_released_and_settled_at_goal); 1130.0 TGP 16.0 20.8; 1131.0 T-- 0.0 0.7 (no_lift,not_released_and_settled_at_goal); 1132.0 T-- 0.1 3.2 (no_lift,not_released_and_settled_at_goal); 1133.0 T-- 0.0 4.2 (no_lift,not_released_and_settled_at_goal); 1134.0 T-- 0.0 0.9 (no_lift,not_released_and_settled_at_goal); 1135.0 T-- 0.0 2.8 (no_lift,not_released_and_settled_at_goal); 1136.0 T-- 0.0 1.2 (no_lift,not_released_and_settled_at_goal); 1137.0 T-- 0.0 2.8 (no_lift,not_released_and_settled_at_goal); 1138.0 T-- 0.0 1.5 (no_lift,not_released_and_settled_at_goal); 1139.0 TG- 12.7 3.2 (not_released_and_settled_at_goal)
