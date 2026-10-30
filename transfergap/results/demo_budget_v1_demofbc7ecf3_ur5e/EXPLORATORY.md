# Exploratory (dev only, not frozen for held-out)

Demo: HiPHI `Cause_motion-lift_0041` (two-handed box lift from the floor, motion capture; ModalityNet
non-commercial licence — only aggregate statistics are kept here, no raw data).

Finding: with every pipeline stage replaced by its oracle (`oracle_all`) the block still reaches the tray, but
nearly every trial is flagged `forbidden_collision`: the human sets the heavy box down by pushing it to the
floor, and copying that carry leg drives the robot's links into the tray/table. Stage oracles cannot close this
gap — the *style itself* is infeasible for this robot and task. Object-normalised offsets were added before this
run (hands sat ~24 cm above the box centre; without them every condition was 0%).
