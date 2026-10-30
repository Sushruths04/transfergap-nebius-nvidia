# Style transfer with depth perception in the loop (dev)

Demo `demo1bc4be60` (4 cm cube) -> 5/6/7 cm cubes. success k/n; path RMSE cm to the clean retargeted human path (lower = closer); approach angle error deg; lift height error cm.

| robot | condition | cube | success | path RMSE cm | approach deg | lift err cm | failures |
|---|---|---|---|---|---|---|---|
| ur5e | truth | 50mm | 2/2 | 2.6 | 5.2 | 0.47 | - |
| ur5e | truth | 60mm | 2/2 | 2.6 | 5.2 | 0.52 | - |
| ur5e | truth | 70mm | 1/2 | 2.6 | 5.3 | 0.56 | no_lift, not_released_and_settled_at_goal |
| ur5e | depth | 50mm | 2/2 | 2.6 | 5.2 | 0.47 | - |
| ur5e | depth | 60mm | 2/2 | 2.6 | 5.2 | 0.53 | - |
| ur5e | depth | 70mm | 1/2 | 2.6 | 5.3 | 0.54 | no_lift, not_released_and_settled_at_goal |
| ur5e | depth_hard | 50mm | 2/2 | 2.7 | 5.2 | 0.46 | - |
| ur5e | depth_hard | 60mm | 2/2 | 2.6 | 5.2 | 0.54 | - |
| ur5e | depth_hard | 70mm | 1/2 | 2.6 | 5.4 | 0.58 | no_lift, not_released_and_settled_at_goal |
| ur10e | truth | 50mm | 2/2 | 1.5 | 2.7 | 0.18 | - |
| ur10e | truth | 60mm | 2/2 | 1.5 | 2.7 | 0.19 | - |
| ur10e | truth | 70mm | 1/2 | 1.5 | 2.7 | 0.23 | no_lift, not_released_and_settled_at_goal |
| ur10e | depth | 50mm | 2/2 | 1.5 | 2.7 | 0.19 | - |
| ur10e | depth | 60mm | 2/2 | 1.5 | 2.7 | 0.20 | - |
| ur10e | depth | 70mm | 1/2 | 1.5 | 2.7 | 0.23 | no_lift, not_released_and_settled_at_goal |
| ur10e | depth_hard | 50mm | 1/2 | 1.7 | 2.7 | 0.18 | no_lift, not_released_and_settled_at_goal |
| ur10e | depth_hard | 60mm | 2/2 | 1.7 | 2.7 | 0.19 | - |
| ur10e | depth_hard | 70mm | 0/2 | 1.6 | 2.7 | 0.22 | no_lift, not_released_and_settled_at_goal |
| kairos | truth | 50mm | 2/2 | 1.5 | 2.7 | 0.23 | - |
| kairos | truth | 60mm | 2/2 | 1.5 | 2.7 | 0.25 | - |
| kairos | truth | 70mm | 2/2 | 1.5 | 2.7 | 0.28 | - |
| kairos | depth | 50mm | 2/2 | 1.5 | 2.7 | 0.23 | - |
| kairos | depth | 60mm | 2/2 | 1.5 | 2.7 | 0.26 | - |
| kairos | depth | 70mm | 2/2 | 1.5 | 2.7 | 0.28 | - |
| kairos | depth_hard | 50mm | 1/2 | 1.8 | 2.7 | 0.26 | no_lift, not_released_and_settled_at_goal |
| kairos | depth_hard | 60mm | 1/2 | 1.8 | 2.7 | 0.29 | no_lift, not_released_and_settled_at_goal |
| kairos | depth_hard | 70mm | 1/2 | 1.8 | 2.7 | 0.32 | no_lift, not_released_and_settled_at_goal |
