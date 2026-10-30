# G1 right arm + waist IK reachability (kinematics only)

`g1/ik_table.py`: the plans' own IK (`plan_reach.G1Kin.solve`, hand pitched down 0.35 rad) solved from the standing pose
over a 20 x 32 grid (x 0.18..0.54 m, y -0.40..0.22 m) at the grasp height (z 0.752 m) and the lift height (z 0.872 m).
A target counts as reachable if the final grasp-point error is under 10 mm. Figure: `reachability.png`; numbers:
`ik_summary.json`; solved fields: `grid.npz`.

| variant | reachable, grasp height | reachable, lift height | block region (nominal +- 2 cm) | tray centre |
|---|---|---|---|---|
| arm only (waist frozen) | 38% | 65% | 6/6 | 1/1 |
| arm + waist (cost 20, as in the plans) | 100% | 100% | 6/6 | 1/1 |
| arm + waist (cost 1) | 100% | 100% | 6/6 | 1/1 |

Conclusions that the data supports:
- The task's block region and the tray are inside the kinematic workspace in every variant, so IK reachability is not why
  the G1 fails to grasp (consistent with the cluster finding that the robot does not follow the commanded joints).
- The arm alone cannot reach the far part of the table at grasp height (x beyond about 0.40 m); the waist is what extends it.
- At the farthest targets the waist roll/pitch hit their joint limits (0.52 rad), so the far corners are at the edge.

Not claimed: anything about balance, torque or whether SONIC would actually execute these joint targets (it was not run here).
