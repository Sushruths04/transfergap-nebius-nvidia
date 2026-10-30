# Cosmos-Reason2-2B critic on the NEW pipeline's rollouts (2026-10-09, GPU cluster, no Nebius)

Clips: the showcase demo (`showcase_r6_shoulder044`, shoulder width 0.44 m DERIVED) on UR5e and UR10e, raw vs frozen five-fix stack, seeds 1000-1059 (240 clips).
Labels = simulator success; they reproduce the pipeline counts exactly (31/60, 60/60, 34/60, 60/60: `counts.json`).
The LoRA adapter (`runs/cosmos_critic_adapter`, trained earlier on other demos' clips, seeds 2000-2049) was NOT retrained; this demo and these seeds are new to it.

| | accuracy | balanced acc. | catches failures (TNR) | keeps successes (TPR) |
|---|---|---|---|---|
| zero-shot | 77.1% (= majority class) | 0.50 | 0% | 100% |
| with adapter | 97.5% | 0.946 | 89.1% (49/55) | 100% |

Failures exist only in the raw cells: UR5e raw 93.3% accuracy (TNR 86.2%), UR10e raw 96.7% (TNR 92.3%). The fix cells are 100% success, so they only test that the critic does not raise false alarms (it raised none).
Caveats: simulator renders only, one demo, one person, one camera; the adapter was selected on earlier clips and these seeds overlap the development seeds of the pipeline (not used for training the critic).
