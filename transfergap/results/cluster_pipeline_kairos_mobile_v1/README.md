# cluster_pipeline_kairos_mobile_v1 (exploratory, not in the paper)

The one-command pipeline on the author's clip with robots `kairos` (fixed arm) and `kairos_mobile` (same arm on the Summit XLS base parked at the origin), GPU cluster, seeds 1000-1059,
frozen five-fix stack: both 41 -> 60 of 60. Equal counts are expected: the base is parked and the task geometry relative to the arm is unchanged; this shows the mobile model
does not disturb the task, not that the base adds anything. Caveats as in `../cluster_pipeline_user_v1`.
