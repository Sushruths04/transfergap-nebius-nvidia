# Wrist orientation vs grasp outcome (exploratory, zero GPU)

Question left open by `results/g1_pelvis_drift_v1`: does wrist orientation at the hand-close frame separate grasping from non-grasping rollouts?
Data: the 80 logged `*.diag.npz` of that run (hybrid controller, seeds 1200-1279, host pod). Script: `g1/wrist_orientation.py` (forward kinematics of the
logged qpos at t_go + 6 s, the same frame as `g1/drift_features.py`; outcome = block lift >= 5 cm, 32/80 grasped, matching the drift study).
Rows: `rows.json`; statistics: `summary.json` (AUC with bootstrap 95% interval, two-sided permutation p, 5000 permutations).

| feature | AUC for grasp [95% CI] | p (uncorrected) | median grasp vs no grasp |
|---|---|---|---|
| pelvis drift (reference) | 0.33 [0.22, 0.46] | 0.011 | 6.1 vs 7.3 cm |
| wrist link tilt from vertical, x axis | 0.46 [0.34, 0.58] | 0.55 | 85.1 vs 85.5 deg |
| ... y axis | 0.46 [0.34, 0.59] | 0.58 | 64.7 vs 64.5 deg |
| ... z axis | 0.51 [0.38, 0.64] | 0.86 | 25.9 vs 25.9 deg |
| wrist roll vs pelvis | 0.46 [0.34, 0.58] | 0.55 | -25.6 vs -25.4 deg |
| wrist pitch vs pelvis | 0.65 [0.53, 0.76] | 0.027 | 6.7 vs 4.5 deg |
| wrist yaw vs pelvis | 0.45 [0.33, 0.58] | 0.43 | -14.3 vs -12.5 deg |

Reading: no wrist-orientation feature is a strong separator. Only relative pitch has an uncorrected p below 0.05, and with 7 features examined that does not survive a
multiplicity correction (Bonferroni threshold 0.007) and the median difference is 2 degrees. Pelvis drift remains the strongest single feature (consistent with the drift study).
Exploratory, association only, one controller on the host setup (the setup whose absolute level is in question, see `results/g1_in_image_v1`). Not for the paper's claims.
