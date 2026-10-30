# Object-size sweep (object_scale_v1), run on the laptop, CPU only

Exploratory, not pre-registered. Code: `transfergap/sim/object_scale.py` (idea from HOI-Retarget's object-scale experiments). Same author's clip (`demo.npz` of `results/showcase_r6_shoulder044`), same 60 held-out seeds, same frozen five-fix stack, MuJoCo 3.14.0 physics without rendering; only the cube edge changes (same density). The stack was tuned at 4 cm; other sizes were never used for tuning. Simulation only. Per-episode logs are in `runs/local_repro/scale/` (not committed, about 40 MB each).

Reproduction check: rerunning the default 4 cm case locally gives UR5e 31 -> 60, a +48.3 pp gap, identical to the cluster result.

| cube edge | UR5e raw -> fixes | UR10e raw -> fixes | KAIROS raw -> fixes |
|---|---|---|---|
| 3 cm | 34 -> 60 | 32 -> 60 | 42 -> 60 |
| 4 cm (default) | 31 -> 60 | 34 -> 60 | 48 -> 60 |
| 5 cm | 26 -> 58 | 32 -> 60 | 50 -> 60 |
| 6 cm | 15 -> 57 | 19 -> 59 | 50 -> 60 |
| 7 cm | 0 -> 47 | 0 -> 56 | 51 -> 60 |

Reading: the raw copy degrades as the object grows on the UR arms (0/60 at 7 cm), while the fix stack keeps 47-60 of 60 everywhere, so the style transfer survives resizing without re-tuning; the UR5e at 7 cm (47/60) is the weak point, near its 8.5 cm gripper opening. KAIROS (12.8 cm opening) is unaffected.
Limits: one clip, one person, one object shape (cube), sizes chosen by us, no confidence intervals computed here.


## 95% Wilson intervals (added 2026-10-29)
Success counts with 95% Wilson intervals for a binomial proportion (60 seeds per cell; `object_scale_wilson_ci.json`). Intervals describe seed sampling only, not clip or person variation.

| cube | UR5e raw | UR5e fixes | UR10e raw | UR10e fixes | KAIROS raw | KAIROS fixes |
|---|---|---|---|---|---|---|
| 3cm | 34/60 (0.44-0.68) | 60/60 (0.94-1.00) | 32/60 (0.41-0.65) | 60/60 (0.94-1.00) | 42/60 (0.57-0.80) | 60/60 (0.94-1.00) |
| 4cm | 31/60 (0.39-0.64) | 60/60 (0.94-1.00) | 34/60 (0.44-0.68) | 60/60 (0.94-1.00) | 48/60 (0.68-0.88) | 60/60 (0.94-1.00) |
| 5cm | 26/60 (0.32-0.56) | 58/60 (0.89-0.99) | 32/60 (0.41-0.65) | 60/60 (0.94-1.00) | 50/60 (0.72-0.91) | 60/60 (0.94-1.00) |
| 6cm | 15/60 (0.16-0.37) | 57/60 (0.86-0.98) | 19/60 (0.21-0.44) | 59/60 (0.91-1.00) | 50/60 (0.72-0.91) | 60/60 (0.94-1.00) |
| 7cm | 0/60 (0.00-0.06) | 47/60 (0.66-0.87) | 0/60 (0.00-0.06) | 56/60 (0.84-0.97) | 51/60 (0.74-0.92) | 60/60 (0.94-1.00) |
