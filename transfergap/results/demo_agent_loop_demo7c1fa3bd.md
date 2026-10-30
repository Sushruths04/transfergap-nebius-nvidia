# Nemotron-3-Super diagnosing the NEW demo (2026-10-09; simulation on the GPU cluster, LLM call via Nebius Token Factory, user-approved)

Demo `demo7c1fa3bd` (author's clip, shoulder width 0.44 m DERIVED). Pre-registered protocol demo_budget_v1: dev seeds 0-59 pick the correction, the choice (rule and Nemotron) is
committed in the cluster checkout BEFORE the held-out seeds 1000-1059 run. Only aggregate dev statistics were sent to the model (key stayed on the laptop). Receipts: `agent_receipt.json` in each folder.

| arm | round | Nemotron | rule | held-out gain of the step (paired, 95% CI) |
|---|---|---|---|---|
| UR5e | 1 | look_again | look_again | +40.0 pp [26.7, 55.0] |
| UR5e | 2 | touch_probe_calibration | same | +8.3 pp [1.7, 15.0] |
| UR5e | 3 | (diagnosis stops: no useful fix left) | | |
| UR10e | 1 | look_again | look_again | +38.3 pp [25.0, 51.7] |
| UR10e | 2 | touch_probe_calibration | same | +5.0 pp [0, 11.7] |
| UR10e | 3 | (diagnosis stops) | | |

Final stack (two fixes) on held-out seeds: UR5e 31/60 -> 60/60 (+48.3 pp [35.0, 61.7]), UR10e 34/60 -> 60/60 (+43.3 pp [31.7, 56.7]). The earlier frozen five-fix stack also reaches 60/60 here, so the loop finds a smaller stack that does as well on this demo.
Nemotron agreed with the deterministic rule at every step (4/4), so the LLM did not change a decision here; it is in the loop and its answers were valid, but this run does not show that it does better than the rule.
Held-out seeds were already used by the earlier showcase run with the frozen stack (paired comparison, not a fresh test). One clip, one person, simulation only.
