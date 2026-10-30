# IK comparison v1 (ur5e)

Success = position <= 1 mm, orientation <= 0.5 deg, no joint-limit violation, judged by independent forward kinematics. Reach (max sampled shoulder-to-pinch distance): 1.099 m. Largest difference between the controller's clip range and the joint range: 9e-05 rad.

## Reachable 6-DoF targets (from the home pose)

| method | n | success | median mm | p90 mm | median deg | p90 deg | limit viol. | ms/solve |
|---|---|---|---|---|---|---|---|---|
| dls_4 | 300 | 5 | 236 | 886 | 43.2 | 148 | 0 | 0.878 |
| dls_100 | 300 | 201 | 3.29e-13 | 178 | 4.35e-06 | 35.7 | 0 | 8.98 |
| mink | 300 | 243 | 0.117 | 83.5 | 0.00135 | 0.559 | 0 | 2.26 |

Tool-down targets: 200 of 200 reachable by the multi-restart reference.

## Tool-down targets, all

| method | n | success | median mm | p90 mm | median deg | p90 deg | limit viol. | ms/solve |
|---|---|---|---|---|---|---|---|---|
| dls_4 | 200 | 5 | 177 | 617 | 16.1 | 102 | 0 | 0.87 |
| dls_100 | 200 | 168 | 1.8e-13 | 77.3 | 2.7e-06 | 13.1 | 0 | 8.94 |
| mink | 200 | 172 | 0.037 | 31 | 0.000447 | 0.455 | 0 | 1.93 |

## Tool-down targets, reachable subset

| method | n | success | median mm | p90 mm | median deg | p90 deg | limit viol. | ms/solve |
|---|---|---|---|---|---|---|---|---|
| dls_4 | 200 | 5 | 177 | 617 | 16.1 | 102 | 0 | 0.87 |
| dls_100 | 200 | 168 | 1.8e-13 | 77.3 | 2.7e-06 | 13.1 | 0 | 8.94 |
| mink | 200 | 172 | 0.037 | 31 | 0.000447 | 0.455 | 0 | 1.93 |

## Unreachable targets (bound violations column below)

| method | n | success | median mm | p90 mm | median deg | p90 deg | limit viol. | ms/solve |
|---|---|---|---|---|---|---|---|---|
| dls_4 | 100 | 0 | 1.85e+03 | 2.35e+03 | 111 | 167 | 0 | 0.862 |
| dls_100 | 100 | 0 | 1.95e+03 | 2.45e+03 | 165 | 180 | 0 | 8.97 |
| mink | 100 | 0 | 1.86e+03 | 2.33e+03 | 24.9 | 90 | 0 | 17.3 |

Bound violations (position error below the geometric lower bound; must be 0): dls_4=0, dls_100=0, mink=0

## Path tracking (25 lines used)

## Per-waypoint tracking error

| method | n | success | median mm | p90 mm | median deg | p90 deg | limit viol. | ms/solve |
|---|---|---|---|---|---|---|---|---|
| dls_4 | 2500 | 2500 | 7.12e-07 | 5.92e-06 | 2.09e-06 | 3.42e-06 | 0 | 0.824 |
| mink_1 | 2500 | 2500 | 0.0476 | 0.09 | 0.000721 | 0.00113 | 0 | 1.21 |
