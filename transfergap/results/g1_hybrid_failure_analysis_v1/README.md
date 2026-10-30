# G1 hybrid controller: why do rollouts close at a good hand position and still not grasp? (exploratory)

Data: 120 rollouts of the frozen hybrid controller on three fresh seed sets (v4 710-749, v6 800-839, v7 1100-1139);
51 grasped (lift >= 5 cm), 69 not. Per-rollout features in `features.json`, taken at the moment the hand closes from the
cluster logs (measured hand position vs block, hand speed, IK error, controller correction, pelvis drift, contacts).
Extracted by a script run read-only on the cluster volume; raw rollouts stay there.

Findings (association only; analysis done AFTER seeing the results, 5 features tested, so p < 0.01 is the bar):
- Hand-to-block offset at close separates grasps from non-grasps. Grasped: dx +2.0 cm (IQR 1.0..3.5), dy -0.6, dz +2.7
  (very tight). Inside the grasped mean +- 2 sd window: 43 grasped and 23 not grasped (P(grasp) = 0.65); outside it: 8
  grasped and 46 not (P = 0.15). So position matters, but is not sufficient.
- The 23 non-grasps inside the window had more pelvis drift (median 6.6 vs 4.7 cm, permutation p = 0.005) and a larger
  controller correction (p = 0.004). IK error, block pushed before closing, and hand speed show no reliable difference
  (p = 0.69, 0.36, 0.10).
- Every rollout touched the block before closing (contact_before_close is true for all 51 grasps and for 52 of 69 non-grasps).

Not established: a mechanism. Pelvis drift is consistent with the body moving the hand's orientation or the held-block
geometry while the measured fingertip position still looks right, but wrist orientation is not logged, so this was not tested.
A test would need a new pre-registered run (for example logging wrist orientation, or limiting pelvis drift) on fresh seeds.
