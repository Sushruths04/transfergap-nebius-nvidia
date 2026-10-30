# Reproduction on Nebius AI Cloud, 2026-10-30

Short, honest reproduction of two parts of TransferGap on a Nebius AI Cloud GPU VM, to show the code and the multi-robot BC policy run outside an earlier GPU cluster.

## Resource
- Instance `computeinstance-e00d2kw410gxdtxkhx` (name `transfergap-gpu-v2`), platform `gpu-l40s-a`, preset `1gpu-16vcpu-64gb` (1x NVIDIA L40S, 16 vCPU, 62 GB RAM), project `project-e00rt2zapr004vtt8961b5`, region `eu-north1`. Boot disk from the September snapshot; SSH user `ubuntu`.
- Proof: `nvidia-smi.txt` (hostname `computeinstance-e00d2kw410gxdtxkhx`, `uname -a`, `date -u` 2026-10-30 13:57:45 UTC, L40S driver 580.173.02).
- Timeline (UTC, `date` on the laptop): start command 13:49, stop confirmed STOPPED at 14:00. About 11 minutes of wall clock, roughly 0.2 VM-hours; at about $1.55/h that is about $0.30 (an upper estimate; the real invoice may round differently). The 400 GB boot disk keeps costing storage while stopped. Nothing was deleted or created besides starting/stopping this instance.
- Final state after `nebius compute instance stop`: **STOPPED** (verified with `nebius compute instance get`).

## What was copied
Only source: `transfergap/`, `scripts/`, `examples/`, `tests/`, `pyproject.toml` (no mp4, npz, results, paper, `.env`, no SSH keys or Nebius credentials), the policy `models_multi4/policy_vision.pt` (multi-robot, training seed 1, from the backup tgz) and `demo_in/demo.npz` (from `runs/local_repro/demo.npz`, 5 KB). The git-ignored KAIROS gripper/base model files (`transfergap/sim/assets/kairos`, 2 MB, needed for `kairos_mobile`) were included in the source tarball. The VM's old venv was not used: a new venv with `mujoco 3.17.0` and `torch 2.15.0+cpu` was built by `transfergap/sim/setup_sim.sh` (Menagerie commit pinned in the repo) plus `pip install torch` (CPU wheel).

## Commands and results
1. `python -m transfergap doctor`, `python -m transfergap evaluate examples/fixture_episodes.jsonl --allow-fixtures`, `python -m unittest tests.test_sim` (log: `smoke.log`): doctor reports torch, mujoco and the L40S; the fixture evaluation prints 1/2 (fixtures); the 5 MuJoCo sim tests passed (33 s).
2. Closed-loop evaluation of the multi-robot vision BC policy, spec `std`, seeds 7000-7029, `--exec ensemble` (exact commands in `eval_cmds.txt`):
   `python scripts/eval_bc.py --ckpt models_multi4/policy_vision.pt --robot <robot> --seeds 7000-7029 --demo demo_in/demo.npz --out out/eval_multi4s1_<robot>_std_7000-7029.json --workers 14 --exec ensemble`

| robot | policy success (30 seeds) | 95% Wilson | scripted fix stack, same seeds | earlier result (an earlier GPU cluster, same policy, seeds 7000-7119) |
|---|---|---|---|---|
| ur10e | 30 / 30 | 88.6-100% | 30 / 30 | 120 / 120 |
| kairos_mobile | 30 / 30 | 88.6-100% | 30 / 30 | 120 / 120 (the earlier table lists "KAIROS"; I did not check that it is the same variant as `kairos_mobile`) |
| ur5e | 30 / 30 | 88.6-100% | 30 / 30 | 120 / 120 |

Files: `eval_multi4s1_*_std_7000-7029.json`, `eval_*.log`. The 30 seeds are a subset of the earlier 120, so this is a re-run of the same policy and seeds on different hardware, not a new held-out test; matching counts show the pipeline reproduces, not new evidence of generalisation.

## Caveats and what was not run
- The policy evaluation ran on the VM's CPUs (CPU torch, MuJoCo with EGL rendering, 14 workers); the L40S GPU was present (nvidia-smi) but not used by these evaluations. The "GPU run" claim is therefore limited to: the VM has the GPU, the code ran on that VM.
- Not run: GR00T fine-tuning/inference (no weights or checkpoints on the VM, not copied), BC training, Cosmos, hosted-API (Nebius Token Factory) calls (no API key was copied), seed-2 policy, `mixed` and `hard` specs, the 500-seed gap-budget studies.
- Single run per robot, no repeats.
