# Demo generalization v4 (pre-registered)

Second person, corrected object height, person-1 fix stack applied unchanged.

| robot | raw | fix stack | gap pp [95% CI] |
|---|---|---|---|
| ur5e | 11/60 | 0/60 | -18.3 [-28.3, -8.3] |
| ur10e | 4/60 | 0/60 | -6.7 [-13.3, -1.7] |

no universal fix recipe: the stack diagnosed on one person's demo (incl. safe_path) does not transfer to a different person's style; the per-demo diagnosis loop is required (demo_budget on this demo).
