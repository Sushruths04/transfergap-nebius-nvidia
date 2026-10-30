# Camera calibration tolerance map (DEV seeds 0-9, 6 cm cube, UR5e and KAIROS), final code

Rotation-only and translation-only camera calibration error (random axis/direction per seed, applied to the point-cloud
pose; the same magnitude for the overhead and the wrist camera, independent directions), with and without the wrist
look-again at hover and the tray look-again at the transport pose (`*_wrist_tray`). Table: `<robot>/dev/summary.md`.

Reading: rotation error is corrected by looking again from close range (error scales with range); translation error is
not (a camera offset cannot be seen in its own data and needs a calibration reference). The 2F-85 arms tolerate about
0.5 deg / 10 mm overhead-only, KAIROS about 1 deg / 20 mm; with the look-agains rotation tolerance extends to about 1-2 deg.
n = 10 per cell: differences of one or two successes are not meaningful. Dev only, not held-out.
