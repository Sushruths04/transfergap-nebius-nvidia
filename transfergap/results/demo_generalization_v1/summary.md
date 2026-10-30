# Demo generalization v1 (pre-registered in protocol.json)

Fix stack chosen on the notebook demo, applied unchanged. Held-out seeds 1000-1059, n=60 per cell.

| demo | carry stretch | robot | no fix | 4 fixes | gain pp [95% CI] | path RMSE cm no fix -> fixes |
|---|---|---|---|---|---|---|
| markers | 3.3x | ur5e | 0/60 | 0/60 | +0.0 [+0.0, +0.0] | 13.2 -> 4.4 |
| markers | 3.3x | ur10e | 0/60 | 0/60 | +0.0 [+0.0, +0.0] | 7.8 -> 2.4 |
| orange_marker | 7.0x | ur5e | 0/60 | 0/60 | +0.0 [+0.0, +0.0] | 15.6 -> 3.6 |
| orange_marker | 7.0x | ur10e | 0/60 | 0/60 | +0.0 [+0.0, +0.0] | 10.4 -> 2.2 |
| notepad | 7.8x | ur5e | 0/60 | 0/60 | +0.0 [+0.0, +0.0] | 14.5 -> 4.1 |
| notepad | 7.8x | ur10e | 0/60 | 0/60 | +0.0 [+0.0, +0.0] | 9.5 -> 2.3 |

Carry stretch = robot carry (~0.34 m) / human carry in xy. Simulation; assumed perception/calibration magnitudes as demo_budget_v1.
