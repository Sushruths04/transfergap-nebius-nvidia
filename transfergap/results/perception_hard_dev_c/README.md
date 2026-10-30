# perception_hard dev pass C (final code before the freeze)

DEV split (seeds 0-9), 3 block sizes, 24 conditions, 3 robots; code commit af26454 (tray-floor fix included). Not held-out.
The 21 conditions that existed in pass B reproduce pass B cell for cell except the `*_wrist_tray` ones, which are new,
so the simulation is deterministic. Pass B's tray look-again results are void (they were run before the tray-floor fix).
