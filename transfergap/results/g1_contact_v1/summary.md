# G1 contact attempt v1 (g1_sonic), protocol `g1_block_to_tray_v1`

Tier rates per rollout with Wilson 95% intervals [%]. Rollouts of one seed share the scene, so the
per-rollout intervals overstate independence; the per-trial table counts seeds where any of the
repeated rollouts reached the tier. Simulator labels only.

| condition | oracle | rollouts | touch | grasp (lift >= 5 cm in hand) | place (in tray, settled) |
|---|---|---|---|---|---|
| nominal_target | none | 30 (10 seeds) | 100% (30/30) [89, 100] | 63% (19/30) [46, 78] | 63% (19/30) [46, 78] |
| true_target | perception | 30 (10 seeds) | 100% (30/30) [89, 100] | 60% (18/30) [42, 75] | 57% (17/30) [39, 73] |

| condition | touch, any rollout | grasp, any rollout | place, any rollout | seeds with mixed place outcomes | robot fell | place failure reasons |
|---|---|---|---|---|---|---|
| nominal_target | 100% (10/10) [72, 100] | 100% (10/10) [72, 100] | 100% (10/10) [72, 100] | 9 | 0 | no_lift:11, not_released_and_settled_at_goal:11 |
| true_target | 100% (10/10) [72, 100] | 90% (9/10) [60, 98] | 90% (9/10) [60, 98] | 6 | 0 | no_lift:12, not_released_and_settled_at_goal:13 |

Per rollout (seed.rollout tiers T/G/P, max lift cm, block xy displacement cm, reasons):

- nominal_target: 100.0 T-- 2.3 2.9 (no_lift,not_released_and_settled_at_goal); 100.1 TGP 12.6 19.2; 100.2 TGP 12.5 18.8; 101.0 TGP 12.8 19.9; 101.1 TGP 14.2 17.9; 101.2 T-- 0.0 0.1 (no_lift,not_released_and_settled_at_goal); 102.0 T-- 0.1 2.2 (no_lift,not_released_and_settled_at_goal); 102.1 TGP 12.4 19.4; 102.2 TGP 12.8 16.8; 103.0 TGP 12.6 18.8; 103.1 T-- 0.1 0.3 (no_lift,not_released_and_settled_at_goal); 103.2 T-- 0.1 0.9 (no_lift,not_released_and_settled_at_goal); 104.0 TGP 12.8 19.8; 104.1 T-- 3.1 1.8 (no_lift,not_released_and_settled_at_goal); 104.2 TGP 14.4 17.5; 105.0 TGP 12.7 20.1; 105.1 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 105.2 TGP 12.7 18.6; 106.0 T-- 0.0 0.2 (no_lift,not_released_and_settled_at_goal); 106.1 T-- 0.1 0.8 (no_lift,not_released_and_settled_at_goal); 106.2 TGP 12.7 20.8; 107.0 TGP 12.5 20.6; 107.1 TGP 12.7 19.4; 107.2 TGP 13.1 16.1; 108.0 T-- 0.5 0.4 (no_lift,not_released_and_settled_at_goal); 108.1 TGP 12.9 17.8; 108.2 TGP 12.5 20.1; 109.0 TGP 14.4 16.9; 109.1 TGP 12.6 19.5; 109.2 T-- 2.0 1.6 (no_lift,not_released_and_settled_at_goal)
- true_target: 100.0 T-- 4.6 3.7 (no_lift,not_released_and_settled_at_goal); 100.1 T-- 0.2 1.6 (no_lift,not_released_and_settled_at_goal); 100.2 T-- 4.1 0.8 (no_lift,not_released_and_settled_at_goal); 101.0 TGP 12.2 19.6; 101.1 T-- 0.0 1.5 (no_lift,not_released_and_settled_at_goal); 101.2 TGP 12.3 19.2; 102.0 T-- 0.1 2.0 (no_lift,not_released_and_settled_at_goal); 102.1 T-- 0.0 2.5 (no_lift,not_released_and_settled_at_goal); 102.2 TGP 15.4 18.8; 103.0 TGP 12.3 20.8; 103.1 TGP 12.1 23.7; 103.2 TGP 13.6 21.0; 104.0 T-- 0.0 0.0 (no_lift,not_released_and_settled_at_goal); 104.1 TGP 12.6 19.8; 104.2 TGP 12.2 19.0; 105.0 T-- 0.0 2.0 (no_lift,not_released_and_settled_at_goal); 105.1 T-- 0.7 1.2 (no_lift,not_released_and_settled_at_goal); 105.2 TGP 12.3 18.7; 106.0 TGP 12.0 21.5; 106.1 TGP 12.0 20.7; 106.2 TGP 12.0 21.4; 107.0 TGP 11.8 17.8; 107.1 TGP 12.1 18.9; 107.2 TGP 12.7 17.9; 108.0 T-- 0.7 2.1 (no_lift,not_released_and_settled_at_goal); 108.1 TG- 8.5 5.1 (not_released_and_settled_at_goal); 108.2 TGP 12.4 19.3; 109.0 T-- 0.3 1.2 (no_lift,not_released_and_settled_at_goal); 109.1 T-- 0.4 3.4 (no_lift,not_released_and_settled_at_goal); 109.2 TGP 13.0 16.1
