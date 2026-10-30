# perception_hard dev pass B (estimator with plane levelling, adaptive depth median filter, untrimmed fill score)

DEV split (seeds 0-9), 3 block sizes, 21 conditions, 3 robots. Not held-out. Compare with `perception_hard_dev_a`.
Condition definitions: `CONDITIONS` in `transfergap/sim/perception_hard_eval.py` (also stored in each results.json).
`*_retry`: first look fails with the arm in view, the arm retracts home, the controller looks again (retract time not simulated).
`*_wrist`: look-again from a simulated wrist depth camera at the hover pose (mount is a stand-in, not the real D455 holder).
`truth_*`: ground-truth belief ceilings in the same scenes.
