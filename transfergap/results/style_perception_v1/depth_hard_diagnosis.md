# Why is `depth_hard` lower in the style setting than in the scripted test? (diagnosis, UR5e, dev-range seeds)

Held-out `depth_hard` success is 73-76% for the style plan, but the same stressors with the scripted plan
(`perception_hard_v1`, `depth_combined_wrist_tray`) were 120/120. Diagnosis (exploratory, not held-out, not used to change
any frozen code):

1. Ablation, 6 cm cube, seeds 0-19: all stressors 14/20; without the wrist/tray look-agains 14/20; without edge jitter 14/20;
   without distractors 15/20; without dropout/flying pixels 14/20; with 2 mm instead of 5 mm noise 13/20; **without the
   0.5 deg / 5 mm calibration error 18/20**. Only the calibration error matters.
2. The wrist look-again never contributes in the style plan. Logged on seeds 0-2 and 20-22: the look at the end of the
   "align" phase returns `block missing` (3 to 11 clusters, only fingers and the tray edge are seen) and the controller falls
   back silently to the overhead belief. Moving the look later along the reach leg did not help: at 50/70/85/95% of the
   leg the block was found in 0 of 20 episodes each (seeds 20-39). At those hand poses the stand-in wrist camera (mounted on
   the tool side, 8 cm off axis, 20 cm minimum range) does not see the block. The scripted plan has a hover pose 12 cm above
   the block from which it does see it (sub-millimetre estimates), which is why the look-again helps there.
3. Consequence: in the style setting the block belief is effectively overhead-only, so its calibration tolerance is the
   overhead-only one (about 0.5 deg / 10 mm for the 2F-85 arms, see `perception_calib_map_v1`).

Fix options, not done: a hover-and-look pose before the reach (changes the copied style: a pause), or a wrist camera mounted
so that it sees the grasp region (hardware/mount choice; the real D455 holder is not modelled here).
