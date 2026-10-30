# Cosmos-Reason2-2B critic on the data-engine clips (critic_dataset_v1)

240 clips rendered from the author's demo (seeds 1000-1039, UR5e / UR10e / KAIROS, raw copy and the frozen fix stack; 191 physics successes, 49 failures; `counts.json`) scored by Cosmos-Reason2-2B zero-shot and with the LoRA critic adapter trained earlier on OTHER demos' clips (seeds 2000-2049), no training here (`cosmos_critic_eval.py`, L40S). Labels are the physics scorer's success/failure.

| | accuracy | balanced accuracy | true-positive rate | true-negative rate |
|---|---|---|---|---|
| zero-shot | 79.6% | 0.50 | 100% | 0% (answers "success" for every clip) |
| LoRA critic | 96.25% | 0.908 | 100% | 81.6% |

Use in the data engine: the critic agrees with the physics verdict on all 120 fix-stack clips of the exported dataset (so the "critic-verified" subset equals the physics-verified one, 120/120) and rejects 81.6% of the raw-copy failures (40/49). Per cell, the adapter's raw-copy negative rates are KAIROS 0.60, UR10e 0.89, UR5e 0.85. Caveats: one demo, one clip family, simulated video only; the critic never saw this demo, but it was trained on the same simulator and task family, so this is not evidence about real video. 9 failure clips were still accepted.

## Filter applied to the dataset (`scripts/critic_filter.py`, summary in `critic_filter_summary.json`)
- All 120 exported episodes pass the LoRA critic (smallest margin, log P(success) - log P(failure): +1.125), so `meta/episodes_filtered.jsonl` equals `meta/episodes.jsonl` for this dataset; each episode now carries `critic_pass` and `critic_margin`.
- Why it matters when failures are in the pool (all 240 clips: 191 successes): admitting everything gives 79.6% purity; the zero-shot critic admits everything too (79.6%); the LoRA critic admits 200 clips of which 191 are physically successful: **purity 95.5%**. The 9 contaminating clips are raw-copy failures the critic accepted.
- A critic-only filter is therefore a useful cheap pre-filter when no physics label exists (for example real video), but it is not a substitute for it; here the physics label stays the ground truth. Not tested on real video.
