# G1 contact attempt v1 (g1_sonic), protocol `g1_block_to_tray_v1`

Tier rates per rollout with Wilson 95% intervals [%]. Rollouts of one seed share the scene, so the
per-rollout intervals overstate independence; the per-trial table counts seeds where any of the
repeated rollouts reached the tier. Simulator labels only.

| condition | oracle | rollouts | touch | grasp (lift >= 5 cm in hand) | place (in tray, settled) |
|---|---|---|---|---|---|
| hybrid | none | 12 (12 seeds) | 100% (12/12) [76, 100] | 92% (11/12) [65, 98] | 58% (7/12) [32, 81] |

| condition | touch, any rollout | grasp, any rollout | place, any rollout | seeds with mixed place outcomes | robot fell | place failure reasons |
|---|---|---|---|---|---|---|
| hybrid | 100% (12/12) [76, 100] | 92% (11/12) [65, 98] | 58% (7/12) [32, 81] | 0 | 0 | no_lift:1, not_released_and_settled_at_goal:5 |

Per rollout (seed.rollout tiers T/G/P, max lift cm, block xy displacement cm, reasons):

- hybrid: 1300.0 T-- 0.7 0.2 (no_lift,not_released_and_settled_at_goal); 1301.0 TG- 15.4 16.4 (not_released_and_settled_at_goal); 1302.0 TG- 15.4 15.7 (not_released_and_settled_at_goal); 1303.0 TGP 15.0 18.3; 1304.0 TGP 16.0 18.6; 1305.0 TGP 13.8 17.6; 1306.0 TG- 15.0 23.2 (not_released_and_settled_at_goal); 1307.0 TGP 14.7 17.6; 1308.0 TGP 12.1 19.5; 1309.0 TGP 15.1 18.7; 1310.0 TG- 15.8 17.7 (not_released_and_settled_at_goal); 1311.0 TGP 12.8 18.7
