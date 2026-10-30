# Cosmos-Reason2-2B critic retrained on a larger same-demo set (critic_v2)

LoRA fine-tune (same recipe as `cosmos_critic_ft.py`: r=16, 2 epochs) on 480 train + 120 val clips of the author's demo (3 robots x seeds 2000-2099, raw copy and fix stack), tested on the 240 clips of `critic_dataset_v1` (seeds 1000-1039). Simulated video only.

| | accuracy | balanced accuracy | true-positive | true-negative |
|---|---|---|---|---|
| zero-shot | 79.6% | 0.50 | 100% | 0% |
| old adapter (other demos' clips) | 96.25% | 0.908 | 100% | 81.6% (40/49) |
| critic_v2 (this run) | 96.25% | 0.908 | 100% | 81.6% (40/49) |

Finding: v2 makes exactly the same decisions as the old adapter on all 240 test clips (the log-likelihood margins differ by 3.0 log units on average, so it is a different adapter), and both miss the same 9 failures. Of those 9, 8 are `not_released_and_settled_at_goal` without a lifting failure and 1 is a forbidden collision, while all 38 clips that never lifted the block and 2 more placement failures are caught: the critic recognises gross failures (the block never leaves the table) but not subtle placement failures. More same-demo training data did not change that, so the next lever is the failure type, not the data amount (for example clips that focus on release and settling, higher frame rate or resolution, or a second look at the last second of the video). Per-clip predictions: `fine_tuned_test.jsonl`; metrics: `report.json`.
