# perception_hard dev pass A (estimator BEFORE the plane-levelling / median-filter / fill fixes)

DEV split (seeds 0-9). Run with the first version of `sim/perception.py` that had min-area-rectangle yaw, shape
selection and depth-continuous components, but no table-plane levelling, no depth median filter, and a trimmed fill
score. Kept as the "before" record; pass B (`perception_hard_dev_b`) uses the fixed estimator. Not held-out.
Table: `<robot>/dev/summary.md`; per-episode rows: `<robot>/dev/results.json`.
