# Style transfer with depth perception in the loop (heldout)

Demo `demo1bc4be60` (4 cm cube) -> 5/6/7 cm cubes. success k/n; path RMSE cm to the clean retargeted human path (lower = closer); approach angle error deg; lift height error cm.

| robot | condition | cube | success | path RMSE cm | approach deg | lift err cm | failures |
|---|---|---|---|---|---|---|---|
| ur5e | truth | 50mm | 38/40 | 2.6 | 5.2 | 0.46 | not_released_and_settled_at_goal |
| ur5e | truth | 60mm | 40/40 | 2.6 | 5.2 | 0.53 | - |
| ur5e | truth | 70mm | 30/40 | 2.6 | 5.3 | 0.60 | no_lift, not_released_and_settled_at_goal |
| ur5e | depth | 50mm | 39/40 | 2.6 | 5.2 | 0.46 | not_released_and_settled_at_goal |
| ur5e | depth | 60mm | 40/40 | 2.6 | 5.2 | 0.53 | - |
| ur5e | depth | 70mm | 30/40 | 2.6 | 5.3 | 0.60 | no_lift, not_released_and_settled_at_goal |
| ur5e | depth_hard | 50mm | 35/40 | 2.8 | 5.2 | 0.45 | no_lift, not_released_and_settled_at_goal, perception_failed |
| ur5e | depth_hard | 60mm | 34/40 | 2.8 | 5.2 | 0.51 | no_lift, not_released_and_settled_at_goal |
| ur5e | depth_hard | 70mm | 19/40 | 2.8 | 5.4 | 0.58 | no_lift, not_released_and_settled_at_goal |
| ur10e | truth | 50mm | 40/40 | 1.5 | 2.7 | 0.18 | - |
| ur10e | truth | 60mm | 40/40 | 1.5 | 2.7 | 0.20 | - |
| ur10e | truth | 70mm | 31/40 | 1.5 | 2.7 | 0.23 | no_lift, not_released_and_settled_at_goal |
| ur10e | depth | 50mm | 40/40 | 1.5 | 2.7 | 0.18 | - |
| ur10e | depth | 60mm | 40/40 | 1.5 | 2.7 | 0.20 | - |
| ur10e | depth | 70mm | 32/40 | 1.5 | 2.7 | 0.23 | no_lift, not_released_and_settled_at_goal |
| ur10e | depth_hard | 50mm | 35/40 | 1.7 | 2.7 | 0.18 | no_lift, not_released_and_settled_at_goal, perception_failed |
| ur10e | depth_hard | 60mm | 33/40 | 1.7 | 2.7 | 0.20 | no_lift, not_released_and_settled_at_goal |
| ur10e | depth_hard | 70mm | 20/40 | 1.8 | 2.8 | 0.28 | no_lift, not_released_and_settled_at_goal |
| kairos | truth | 50mm | 38/40 | 1.5 | 2.7 | 0.22 | not_released_and_settled_at_goal |
| kairos | truth | 60mm | 40/40 | 1.5 | 2.7 | 0.25 | - |
| kairos | truth | 70mm | 40/40 | 1.5 | 2.7 | 0.28 | - |
| kairos | depth | 50mm | 40/40 | 1.5 | 2.7 | 0.22 | - |
| kairos | depth | 60mm | 40/40 | 1.5 | 2.7 | 0.25 | - |
| kairos | depth | 70mm | 40/40 | 1.5 | 2.7 | 0.28 | - |
| kairos | depth_hard | 50mm | 27/40 | 1.9 | 2.7 | 0.30 | no_lift, not_released_and_settled_at_goal, perception_failed |
| kairos | depth_hard | 60mm | 32/40 | 1.9 | 2.7 | 0.34 | no_lift, not_released_and_settled_at_goal |
| kairos | depth_hard | 70mm | 32/40 | 1.9 | 3.2 | 0.47 | no_lift, not_released_and_settled_at_goal |
