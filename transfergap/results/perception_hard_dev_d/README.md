# perception_hard dev pass D: final code before the freeze (DEV seeds 0-9, 24 conditions, 3 robots)

Run on the committed controller/estimator (grasp yaw only when the cube would not clear the opening by 25 mm). The shard/merge
options of the runner were added afterwards; a 72-cell comparison of a sharded rerun against these results showed zero
differences (the simulation is deterministic and cells are independent). Not held-out; the held-out protocol was declared
from this table (see `results/perception_hard_v1/protocol.json`).
