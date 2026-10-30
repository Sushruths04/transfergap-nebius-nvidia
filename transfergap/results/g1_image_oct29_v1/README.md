# G1 closed-loop hybrid in the image, 12 fresh seeds (g1_image_oct29_v1)

Job `docker/cluster/g1-in-image-oct29.yaml` (image `ghcr.io/sushruths04/transfergap:full-2026-10-09b`, script `g1/image_g1_trials.sh`, seeds 1300-1311, one rollout each, L40S, 15 min). Scored with `g1/score.py` (same scorer as `g1_in_image_v1`). Simulation only; generic block and tray, NOT the author's grasp style.

| tier | result |
|---|---|
| touch | 12/12 |
| grasp (lift >= 5 cm) | 11/12 (seed 1300 lifted 0.7 cm) |
| place in tray | 7/12 |

Compared with `g1_in_image_v1` (seeds 1200-1239 in the image: touch 40/40, grasp 38/40, place 31/40): grasping replicates; the place rate here (58%, 7/12) is lower than 77.5% but 12 seeds is a small sample (exact 95% CI roughly 28-85%), so it does not show a change. Pooled over both image runs: grasp 49/52, place 38/52 (73%). The host-pod number (27.5%) remains unexplained (see that README).
Per-seed rows (hand offset at close, pelvis drift, lift): `rows_seeds_1300_1311.json`. Raw rollouts stay on the cluster volume (`/ws/transfergap/g1_out/g1_image_oct29`).

## Update: 20 more fresh seeds (1312-1331), same Job spec (`docker/cluster/g1-in-image-oct29b.yaml`, 24 min)
touch 20/20, grasp 18/20, place 13/20 (`summary_1312_1331.json`, `rows_seeds_1312_1331.json`).

Pooled over the 32 fresh seeds 1300-1331: touch 32/32, grasp 29/32 (91%, 95% Wilson 76-97%), place 20/32 (62.5%, 95% Wilson 45-77%).
Pooled over every image run (1200-1239 earlier + these 32): place 52/72 (72%, Wilson 61-82%). The first 40 seeds (77.5%) and these 32 (62.5%) differ by 15 points; with these sample sizes that is within chance (the earlier README's host-pod value, 27.5%, is still far below all of them). Quote the pooled 52/72 with its interval, not 31/40 alone.
