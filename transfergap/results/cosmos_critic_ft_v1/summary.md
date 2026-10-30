# Cosmos-Reason2-2B fine-tuned as a pick-and-place success critic (pre-registered, protocol.json)

LoRA (r=16, 17.4 M trainable parameters, 0.7%) on 640 labelled simulator rollout clips (UR5e/UR10e, 4 human-demo
plans, with/without the fix stack), 2 epochs on one L40S (Nebius VM); epoch kept by the val split (ep1, val 95.0%).
Test = 220 clips never trained on: 160 new seeds of the training demos + 60 clips of an unseen person's demo.

| test set | zero-shot accuracy | fine-tuned accuracy | gain pp [95% CI, paired bootstrap] | fine-tuned TPR / TNR |
|---|---|---|---|---|
| all (n=220; majority class 55.9%) | 63.6% (bal. 0.59) | **94.1%** (bal. 0.93) | +30.5 [24.5, 36.8] | 1.00 / 0.87 |
| seen demos, new seeds (n=160) | 58.8% | **94.4%** | +35.6 [28.1, 43.1] | 1.00 / 0.89 |
| unseen person's demo (n=60) | 76.7% (says "success" to all) | **93.3%** | +16.7 [8.3, 26.7] | 1.00 / 0.71 |

Zero-shot Cosmos-Reason2-2B calls 92% of clips a success and catches 17.5% of the failures — the same optimism as
our earlier zero-shot critics (cosmos_critic_v1/v2). After fine-tuning it catches 86.6% of the failures and keeps
every success. Adapter (67 MB) kept outside git (`runs/cosmos_critic_adapter/`); per-clip predictions committed.
Caveat: simulator renders only (same camera and scene family); not tested on real-robot video.
