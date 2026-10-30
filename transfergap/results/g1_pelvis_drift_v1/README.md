# G1 pelvis drift vs grasp: replication on fresh seeds (pre-registered)

Protocol: `protocol.json` (amended once, before any outcome of the new seeds was read; see its `amendment` field).
Data: frozen hybrid controller, seeds 1200-1279 (never used before), 1 rollout each, cluster run `runs/g1_cl/pelvis_drift_v1`
(80/80 rollouts finished, none failed). Per-rollout features: `rows.json` (`g1/drift_features.py`); test: `g1/drift_test.py`; result: `result.json`.

Result (rule fixed in advance: difference >= 0.25 and one-sided Fisher p < 0.05):
- 32/80 rollouts grasped (lift >= 5 cm) overall.
- In the frozen position window: 40 rollouts. Drift below 6.25 cm: 16/19 grasped (84%). Drift at or above: 11/21 (52%).
- Difference 0.32, one-sided Fisher p = 0.034. The pre-declared criterion is met, narrowly.

What this does and does not show:
- The association between pelvis drift and failure to grasp, given a good hand position, replicates on fresh seeds. The p-value is only just
  under the bar and rests on 40 in-window rollouts; the dev estimate (87% vs 50%) was a little more optimistic than the new one.
- It does NOT show that drift causes the failures. Drift could be a symptom of something else (for example the stance or the wrist orientation).
  A causal test needs an intervention that limits drift and is a separate pre-registration.
- Wrist orientation at close was not analysed (the secondary item in the protocol); the full joint states are logged in the `*.diag.npz` files on the cluster.
- Features are a reimplementation of the dev analysis (the original extraction script was not kept), re-derived on the same 120 dev rollouts.
