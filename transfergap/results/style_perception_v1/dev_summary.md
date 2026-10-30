# Style transfer with depth perception in the loop (dev)

Demo `demo1bc4be60` (4 cm cube) -> 5/6/7 cm cubes. success k/n; path RMSE cm to the clean retargeted human path (lower = closer); approach angle error deg; lift height error cm.

| robot | condition | cube | success | path RMSE cm | approach deg | lift err cm | failures |
|---|---|---|---|---|---|---|---|
| ur5e | truth | 50mm | 10/10 | 2.6 | 5.2 | 0.46 | - |
| ur5e | truth | 60mm | 10/10 | 2.6 | 5.2 | 0.52 | - |
| ur5e | truth | 70mm | 5/10 | 2.6 | 5.3 | 0.56 | no_lift, not_released_and_settled_at_goal |
| ur5e | depth | 50mm | 8/10 | 2.6 | 5.2 | 0.46 | not_released_and_settled_at_goal |
| ur5e | depth | 60mm | 10/10 | 2.6 | 5.2 | 0.53 | - |
| ur5e | depth | 70mm | 5/10 | 2.6 | 5.3 | 0.55 | no_lift, not_released_and_settled_at_goal |
| ur5e | depth_hard | 50mm | 9/10 | 2.9 | 5.2 | 0.43 | no_lift, not_released_and_settled_at_goal |
| ur5e | depth_hard | 60mm | 6/10 | 2.8 | 5.3 | 0.47 | no_lift, not_released_and_settled_at_goal |
| ur5e | depth_hard | 70mm | 2/10 | 2.8 | 5.4 | 0.51 | no_lift, not_released_and_settled_at_goal |
| ur10e | truth | 50mm | 10/10 | 1.5 | 2.7 | 0.18 | - |
| ur10e | truth | 60mm | 10/10 | 1.5 | 2.7 | 0.20 | - |
| ur10e | truth | 70mm | 5/10 | 1.5 | 2.7 | 0.22 | no_lift, not_released_and_settled_at_goal |
| ur10e | depth | 50mm | 10/10 | 1.5 | 2.7 | 0.19 | - |
| ur10e | depth | 60mm | 10/10 | 1.5 | 2.7 | 0.20 | - |
| ur10e | depth | 70mm | 6/10 | 1.5 | 2.7 | 0.23 | no_lift, not_released_and_settled_at_goal |
| ur10e | depth_hard | 50mm | 7/10 | 1.9 | 2.7 | 0.17 | no_lift, not_released_and_settled_at_goal |
| ur10e | depth_hard | 60mm | 4/10 | 1.8 | 2.7 | 0.19 | no_lift, not_released_and_settled_at_goal |
| ur10e | depth_hard | 70mm | 1/10 | 1.8 | 2.7 | 0.25 | no_lift, not_released_and_settled_at_goal |
| kairos | truth | 50mm | 10/10 | 1.5 | 2.7 | 0.23 | - |
| kairos | truth | 60mm | 10/10 | 1.5 | 2.7 | 0.26 | - |
| kairos | truth | 70mm | 10/10 | 1.5 | 2.7 | 0.29 | - |
| kairos | depth | 50mm | 10/10 | 1.5 | 2.7 | 0.23 | - |
| kairos | depth | 60mm | 10/10 | 1.5 | 2.7 | 0.26 | - |
| kairos | depth | 70mm | 10/10 | 1.5 | 2.7 | 0.29 | - |
| kairos | depth_hard | 50mm | 7/10 | 2.1 | 2.7 | 0.25 | no_lift, not_released_and_settled_at_goal |
| kairos | depth_hard | 60mm | 8/10 | 2.0 | 2.7 | 0.28 | no_lift, not_released_and_settled_at_goal |
| kairos | depth_hard | 70mm | 8/10 | 2.0 | 3.5 | 0.47 | no_lift, not_released_and_settled_at_goal |
