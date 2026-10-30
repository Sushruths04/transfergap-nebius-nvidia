# Held-out scorecard, protocol style_perception_v1 (code commit ef2770b)

Seeds 200-239; rule: pass if (truth success - depth success) <= success_margin_pp AND (depth path RMSE - truth path RMSE) <= path_rmse_margin_cm

| robot | truth success | depth success | gap pp | truth RMSE cm | depth RMSE cm | RMSE gap cm | verdict | depth_hard success |
|---|---|---|---|---|---|---|---|---|
| ur5e | 108/120 | 109/120 | -0.8 | 2.59 | 2.58 | -0.01 | MET | 88/120 |
| ur10e | 111/120 | 112/120 | -0.8 | 1.48 | 1.48 | -0.00 | MET | 88/120 |
| kairos | 118/120 | 120/120 | -1.7 | 1.48 | 1.48 | -0.00 | MET | 91/120 |

**Non-inferiority bar met for 3 of 3 robots.**
