# Demo generalization v3 (pre-registered) — NEGATIVE

Second person (Pexels 7205253), same fixed stack: UR5e 0/60 -> 0/60, UR10e 0/60 -> 0/60 (all no_lift).

GEM-X has no object detector; the default 'lowest_hand' rule put the table under her lowest hand point, but she lifts the box off a stack and sets it lower, so the inferred grasp was ~4 cm above the object -> no_lift on every trial. Fixed by an explicit object_height='hand_at_grasp' option (demo/gemx.py) used for this clip only; see demo_generalization_v4.
