# Grasp-contact gap per robot (contact_gap_ee_v1), laptop CPU

Code: `transfergap/sim/contact_gap_ee.py`. Same clip (`demo.npz` of `results/showcase_r6_shoulder044`), 60 held-out seeds per robot and condition, frozen five-fix stack, MuJoCo 3.14.0 physics, no rendering. Exploratory, simulation only.

Grasp-contact gap = distance between the tool pinch point and the object centre at the end of the `close` phase. Release gap = horizontal object-to-goal distance at the start of the `open` phase.

| robot | condition | success | grasp gap median / p90 | release gap median / p90 |
|---|---|---|---|---|
| UR5e | raw | 31/60 | 2.02 / 4.09 cm | 2.29 / 35.48 cm |
| UR5e | all fixes | 60/60 | 0.45 / 0.72 cm | 0.44 / 0.69 cm |
| UR10e | raw | 35/60 | 2.03 / 4.14 cm | 2.18 / 35.45 cm |
| UR10e | all fixes | 60/60 | 0.46 / 0.73 cm | 0.40 / 0.72 cm |
| KAIROS | raw | 48/60 | 2.43 / 3.98 cm | 1.44 / 32.34 cm |
| KAIROS | all fixes | 60/60 | 0.66 / 1.08 cm | 0.61 / 1.13 cm |

Reading: the fixes cut the median grasp-contact gap from about 2.0-2.4 cm to 0.45-0.66 cm. HOI-Retarget reports 0.5 cm for its contact-point gap, but that is a different quantity on different data (human-object interaction clips, humanoid, optimisation); this is a cube in a simple scene with assumed perception errors, so the numbers are not comparable claims, only the same order of magnitude.
Success counts match the cluster showcase (31/60, 35/60 vs the official 34/60 for UR10e raw, which also checks collision and settle speed).
