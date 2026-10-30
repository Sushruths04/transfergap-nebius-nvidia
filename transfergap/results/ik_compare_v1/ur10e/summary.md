# IK comparison v1 (ur10e)

Success = position <= 1 mm, orientation <= 0.5 deg, no joint-limit violation, judged by independent forward kinematics. Reach (max sampled shoulder-to-pinch distance): 1.475 m. Largest difference between the controller's clip range and the joint range: 9e-05 rad.

## Reachable 6-DoF targets (from the home pose)

| method | n | success | median mm | p90 mm | median deg | p90 deg | limit viol. | ms/solve |
|---|---|---|---|---|---|---|---|---|
| dls_4 | 300 | 5 | 392 | 1.25e+03 | 58.3 | 151 | 0 | 0.865 |
| dls_100 | 300 | 185 | 5.33e-13 | 290 | 4.52e-06 | 48.6 | 0 | 8.72 |
| mink | 300 | 228 | 0.118 | 215 | 0.00168 | 1.89 | 0 | 2.31 |

Tool-down targets: 200 of 200 reachable by the multi-restart reference.

## Tool-down targets, all

| method | n | success | median mm | p90 mm | median deg | p90 deg | limit viol. | ms/solve |
|---|---|---|---|---|---|---|---|---|
| dls_4 | 200 | 5 | 134 | 406 | 9.72 | 85.1 | 0 | 0.858 |
| dls_100 | 200 | 181 | 2e-13 | 0.00309 | 2.7e-06 | 0.000533 | 0 | 8.7 |
| mink | 200 | 156 | 0.0345 | 234 | 0.0007 | 2.9 | 0 | 1.95 |

## Tool-down targets, reachable subset

| method | n | success | median mm | p90 mm | median deg | p90 deg | limit viol. | ms/solve |
|---|---|---|---|---|---|---|---|---|
| dls_4 | 200 | 5 | 134 | 406 | 9.72 | 85.1 | 0 | 0.858 |
| dls_100 | 200 | 181 | 2e-13 | 0.00309 | 2.7e-06 | 0.000533 | 0 | 8.7 |
| mink | 200 | 156 | 0.0345 | 234 | 0.0007 | 2.9 | 0 | 1.95 |

## Unreachable targets (bound violations column below)

| method | n | success | median mm | p90 mm | median deg | p90 deg | limit viol. | ms/solve |
|---|---|---|---|---|---|---|---|---|
| dls_4 | 100 | 0 | 2.54e+03 | 3.23e+03 | 120 | 172 | 0 | 0.858 |
| dls_100 | 100 | 0 | 2.59e+03 | 3.22e+03 | 180 | 180 | 0 | 8.79 |
| mink | 100 | 0 | 2.43e+03 | 3.11e+03 | 29.2 | 90.4 | 0 | 17.4 |

Bound violations (position error below the geometric lower bound; must be 0): dls_4=0, dls_100=0, mink=0

## Path tracking (33 lines used)

## Per-waypoint tracking error

| method | n | success | median mm | p90 mm | median deg | p90 deg | limit viol. | ms/solve |
|---|---|---|---|---|---|---|---|---|
| dls_4 | 3300 | 3300 | 3.62e-08 | 5.21e-06 | 2.09e-06 | 3.42e-06 | 0 | 0.829 |
| mink_1 | 3300 | 3300 | 0.0247 | 0.0693 | 0.000371 | 0.000931 | 0 | 1.23 |
