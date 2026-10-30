# End-to-end check of the unified image on the GPU cluster (2026-10-06, simulation only)

One Kubernetes Job (`docker/cluster/e2e-job.yaml`), one L40S GPU, running `tg-entrypoint e2e` (`docker/e2e.sh`) inside the private image
`ghcr.io/sushruths04/transfergap:full-2026-10-06b` (digest sha256:bb27dec9fc09bdec84cb3b5df875f3e11b05e175e69438921187f6903fdc1b27), built on the cluster with kaniko from commit `e387ce8`
and pushed with skopeo. Weights, the demo npz and the KAIROS gripper description are mounted from the project volume (not in the image). Machine-readable result: `report.json`.

| stage | status | what it checks |
|---|---|---|
| info | PASS | python 3.10.12, numpy 2.2.6, mujoco 3.14.0, EGL rendering, L40S visible |
| tests | PASS | full unit-test suite inside the image: 198 tests OK, 3 skipped (the G1 tests need pyzmq, now in the image; KAIROS tests run because the assets are mounted) |
| arm_repro | PASS | 500-seed arm study re-run in the image reproduces the committed counts EXACTLY: UR5e full 232 / look-again 366, UR10e full 240 / look-again 369 (`results/gap_budget_v3`) |
| perception | PASS | depth-perception smoke run, UR5e dev seeds 0-1 (2/2 per cell shown in `perception.log.tail.txt`) |
| style | PASS | style transfer with depth perception smoke run, 3 arms, dev seeds 0-1 (`style_dev_summary.md`) |
| g1 | PASS | 4 closed-loop G1 rollouts (seeds 1200-1203) ran and logged; 4 of 4 grasped (lifts 8.5, 15.7, 13.0, 14.6 cm; `g1_rows.json`) |

Caveats: the perception, style and G1 stages are smoke runs (few seeds), not new evidence; the G1 PASS bar is "every rollout logged and at least half grasped" (a coarse sanity bar because the
simulator is nondeterministic and the closed-loop controller is sensitive to the environment, see `results/g1_mujoco_version_v1`). The first two image builds of this day failed this check for
real reasons that are fixed in the image: unit tests needing pyzmq and the KAIROS files, a stdin-based multiprocessing script, and an unpinned sim venv that pulled mujoco 3.15.0 (0/4 grasps).
Logs are tails only (`*.tail.txt`); full logs stay on the cluster volume (`/ws/transfergap/e2e_out/e2e`).
