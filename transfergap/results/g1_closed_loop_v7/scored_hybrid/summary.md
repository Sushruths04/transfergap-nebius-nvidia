# G1 contact attempt v1 (g1_sonic), protocol `g1_block_to_tray_v1`

Tier rates per rollout with Wilson 95% intervals [%]. Rollouts of one seed share the scene, so the
per-rollout intervals overstate independence; the per-trial table counts seeds where any of the
repeated rollouts reached the tier. Simulator labels only.

| condition | oracle | rollouts | touch | grasp (lift >= 5 cm in hand) | place (in tray, settled) |
|---|---|---|---|---|---|
| hybrid | fixed | 40 (40 seeds) | 98% (39/40) [87, 100] | 40% (16/40) [26, 55] | 32% (13/40) [20, 48] |

| condition | touch, any rollout | grasp, any rollout | place, any rollout | seeds with mixed place outcomes | robot fell | place failure reasons |
|---|---|---|---|---|---|---|
| hybrid | 98% (39/40) [87, 100] | 40% (16/40) [26, 55] | 32% (13/40) [20, 48] | 0 | 0 | no_lift:24, not_released_and_settled_at_goal:27 |

Per rollout (seed.rollout tiers T/G/P, max lift cm, block xy displacement cm, reasons):

- hybrid: 1100.0 T-- 0.5 2.2 (no_lift,not_released_and_settled_at_goal); 1101.0 TG- 12.1 26.1 (not_released_and_settled_at_goal); 1102.0 T-- 0.4 2.2 (no_lift,not_released_and_settled_at_goal); 1103.0 T-- 1.2 2.9 (no_lift,not_released_and_settled_at_goal); 1104.0 T-- 0.3 5.3 (no_lift,not_released_and_settled_at_goal); 1105.0 TGP 11.9 24.2; 1106.0 T-- 0.2 1.3 (no_lift,not_released_and_settled_at_goal); 1107.0 TG- 10.2 1.8 (not_released_and_settled_at_goal); 1108.0 T-- 0.0 2.2 (no_lift,not_released_and_settled_at_goal); 1109.0 T-- 0.4 3.8 (no_lift,not_released_and_settled_at_goal); 1110.0 T-- 0.8 0.8 (no_lift,not_released_and_settled_at_goal); 1111.0 T-- 0.8 2.5 (no_lift,not_released_and_settled_at_goal); 1112.0 TGP 12.0 20.0; 1113.0 TGP 12.3 23.7; 1114.0 --- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 1115.0 TGP 16.8 21.3; 1116.0 T-- 0.3 0.9 (no_lift,not_released_and_settled_at_goal); 1117.0 TGP 12.9 21.3; 1118.0 TGP 14.8 20.1; 1119.0 TGP 13.9 23.5; 1120.0 T-- 0.5 0.4 (no_lift,not_released_and_settled_at_goal); 1121.0 TGP 11.9 20.8; 1122.0 T-- 1.0 1.2 (no_lift,not_released_and_settled_at_goal); 1123.0 T-- 0.3 2.7 (no_lift,not_released_and_settled_at_goal); 1124.0 TGP 12.6 21.7; 1125.0 T-- 0.1 1.7 (no_lift,not_released_and_settled_at_goal); 1126.0 TGP 15.6 18.4; 1127.0 T-- 0.0 0.2 (no_lift,not_released_and_settled_at_goal); 1128.0 TGP 13.8 23.9; 1129.0 TG- 15.5 26.0 (not_released_and_settled_at_goal); 1130.0 T-- 0.8 6.7 (no_lift,not_released_and_settled_at_goal); 1131.0 T-- 0.2 2.0 (no_lift,not_released_and_settled_at_goal); 1132.0 TGP 13.2 21.1; 1133.0 T-- 0.4 1.9 (no_lift,not_released_and_settled_at_goal); 1134.0 T-- 0.8 3.3 (no_lift,not_released_and_settled_at_goal); 1135.0 T-- 1.2 2.5 (no_lift,not_released_and_settled_at_goal); 1136.0 T-- 0.0 2.0 (no_lift,not_released_and_settled_at_goal); 1137.0 T-- 0.2 6.6 (no_lift,not_released_and_settled_at_goal); 1138.0 TGP 13.8 20.9; 1139.0 T-- 0.3 2.0 (no_lift,not_released_and_settled_at_goal)
