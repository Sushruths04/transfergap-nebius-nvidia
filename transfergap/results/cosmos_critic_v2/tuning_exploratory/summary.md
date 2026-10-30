# Cosmos critic v2 tuning (EXPLORATORY)

Tuning split, seeds 2000-2019 (disjoint from v1 dev 0-59, the v2 scored split 2020-2079 and held-out 1000-1059). 17 rollout clips, balanced per stage {'grasp': 6, 'place': 5, 'none': 6}, plus static negative controls (arm never moves). Used only to choose one configuration; numbers here are not confirmatory and have wide intervals.

| config | model | prompt | camera | success acc | stage acc | predicted stages | static controls said success |
|---|---|---|---|---|---|---|---|
| t8b_v1_v1 | Cosmos-Reason2-8B | v1 | v1 | 35.3% (6/17), Wilson 95% [17.3, 58.7] | 35.3% (6/17), Wilson 95% [17.3, 58.7] | {'none': 17, 'grasp': 0, 'place': 0} | 1/2 |
| t8b_v1_close | Cosmos-Reason2-8B | v1 | close | 47.1% (8/17), Wilson 95% [26.2, 69.0] | 41.2% (7/17), Wilson 95% [21.6, 64.0] | {'none': 15, 'grasp': 1, 'place': 1} | 2/2 |
| t8b_v1_close_top | Cosmos-Reason2-8B | v1 | close_top | 35.3% (6/17), Wilson 95% [17.3, 58.7] | 35.3% (6/17), Wilson 95% [17.3, 58.7] | {'none': 17, 'grasp': 0, 'place': 0} | 0/2 |
| t8b_obs_v1 | Cosmos-Reason2-8B | obs | v1 | 35.3% (6/17), Wilson 95% [17.3, 58.7] | 35.3% (6/17), Wilson 95% [17.3, 58.7] | {'none': 17, 'grasp': 0, 'place': 0} | 0/2 |
| t8b_obs_close | Cosmos-Reason2-8B | obs | close | 52.9% (9/17), Wilson 95% [31.0, 73.8] | 52.9% (9/17), Wilson 95% [31.0, 73.8] | {'none': 14, 'grasp': 3, 'place': 0} | 0/2 |
| t8b_obs_close_top | Cosmos-Reason2-8B | obs | close_top | 52.9% (9/17), Wilson 95% [31.0, 73.8] | 52.9% (9/17), Wilson 95% [31.0, 73.8] | {'none': 14, 'grasp': 3, 'place': 0} | 0/2 |
