# Demo generalization v2 (pre-registered in protocol.json)

One fixed stack (speed_cap_3, look_again, touch_probe_calibration, speed_cap_2, safe_path) applied unchanged to all four annotated cycles of Pexels clip 8135753. Held-out seeds 1000-1059, n=60 per cell. Style is scored against the UNprojected human path.

| demo | carry stretch | robot | no fix | fix stack | gain pp [95% CI] | path RMSE cm no fix -> stack |
|---|---|---|---|---|---|---|
| notebook | 3.7x | ur5e | 0/60 | 57/60 | +95.0 [+88.3, +100.0] | 13.9 -> 5.0 |
| notebook | 3.7x | ur10e | 0/60 | 60/60 | +100.0 [+100.0, +100.0] | 9.1 -> 2.9 |
| markers | 3.3x | ur5e | 0/60 | 51/60 | +85.0 [+75.0, +93.3] | 13.2 -> 5.9 |
| markers | 3.3x | ur10e | 0/60 | 25/60 | +41.7 [+28.3, +55.0] | 7.8 -> 4.3 |
| orange_marker | 7.0x | ur5e | 0/60 | 46/60 | +76.7 [+65.0, +86.7] | 15.6 -> 6.1 |
| orange_marker | 7.0x | ur10e | 0/60 | 58/60 | +96.7 [+91.7, +100.0] | 10.4 -> 4.9 |
| notepad | 7.8x | ur5e | 0/60 | 58/60 | +96.7 [+91.7, +100.0] | 14.5 -> 6.2 |
| notepad | 7.8x | ur10e | 0/60 | 58/60 | +96.7 [+91.7, +100.0] | 9.5 -> 5.0 |

Carry stretch = robot carry (~0.34 m) / human carry in xy. Simulation; assumed perception/calibration magnitudes as demo_budget_v1. Seeds 1000-1005 were also used in the exploratory perfect-stage diagnosis that motivated safe_path.
