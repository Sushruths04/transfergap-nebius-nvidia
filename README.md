# TransferGap

> **Demo video (2:35):** https://youtu.be/5eu5UJMBBcY  (file: `deliverables/TransferGap_final_cut_v6_2026-10-30.mp4`)

## Quick start (5 commands, laptop CPU, no GPU, no API key)

```bash
cd transfergap
bash transfergap/sim/setup_sim.sh        # creates .venv with mujoco>=3.2, numpy, imageio; fetches UR5e/UR10e/2F-85 models (mujoco_menagerie, Apache-2.0)
python3 -m transfergap doctor            # shows which optional keys/GPUs are present; none are required here
python3 -m transfergap evaluate examples/fixture_episodes.jsonl --allow-fixtures
.venv/bin/python -m unittest tests.test_sim   # about 20 s, MuJoCo contact-grasp tests
.venv/bin/python -m transfergap.sim.sweep --n 2 --only baseline --out runs/sim/sweep.jsonl   # about 3 s, prints a success rate per condition
```

## Reproduce the headline results (CPU only)

All results live in `transfergap/results/`. Seeds, protocols and error models are frozen in each
`protocol.json`; every error magnitude is an assumption, not a measurement.

```bash
cd transfergap
.venv/bin/python -m transfergap.sim.gap_budget dev  --protocol v2 --robot ur5e   # seeds 0-59, picks the correction
.venv/bin/python -m transfergap.sim.gap_budget heldout --protocol v2 --robot ur5e  # seeds 1000-1059; refuses unless protocol.json is committed
.venv/bin/python -m transfergap.sim.gap_budget_large protocol                    # 500-seed confirmation, seeds 3000-3499
.venv/bin/python -m transfergap.sim.gap_budget_large run                         # long: minutes to hours on CPU, use cores
```

Where to look: 60-seed study `transfergap/results/gap_budget_v2_ur5e/summary.md` (and `_ur10e`);
500-seed confirmation `transfergap/results/gap_budget_v3/OUTCOME.md` (look-again +26.8 pp on UR5e, +25.8 pp on UR10e;
two of the four pre-registered hypotheses were not supported, see the file); other results are listed in [DOC_INDEX.md](DOC_INDEX.md).
Note: the gap_budget commands expect to be run once in order (dev, then heldout) and they refuse to run on uncommitted protocols
when executed inside a git checkout.

## NVIDIA models and Nebius

| Model / service | Role in this repo | Where to look |
|---|---|---|
| NVIDIA Nemotron 3 Super (`nvidia/nemotron-3-super-120b-a12b`) via Nebius Token Factory | Diagnosis agent: reads a failure trace and picks a correction from a fixed menu, then the correction is scored on held-out simulator seeds. A rule-based baseline runs alongside; every call writes a receipt (requested model, endpoint host, returned model, usage). | `transfergap/transfergap/diagnose.py`, `transfergap/transfergap/hosted.py`, `transfergap/results/demo_agent_loop_*` |
| NVIDIA Cosmos-Reason2 (2B and 8B) | Critic of rollout clips, scored against simulator labels. Self-hosted with vLLM, not through Token Factory. The untuned model scored below the majority baseline; the LoRA-fine-tuned critic reaches 96.3% accuracy on 240 simulated clips and rejects 40 of 49 failures (`critic_dataset_v1`). | `transfergap/results/cosmos_critic_v2/`, `python3 -m transfergap critic` |
| NVIDIA GR00T-N1.5-3B | Fine-tuned on simulation data for the block-to-tray task; 25/30 to 27/30 in the best settings, worse than the small behaviour-cloning policy (60/60). | `transfergap/results/groot_n15_v1/README.md`, `transfergap/scripts/eval_groot.py` |
| NVIDIA SONIC (GR00T whole-body control) | Whole-body controller for the Unitree G1 closed-loop rollouts. Weights are not redistributed. | `transfergap/results/g1_in_image_v1/README.md`, `transfergap/g1/` |

**Where Token Factory sped up the workflow:** the diagnosis loop calls the OpenAI-compatible endpoint
`https://api.tokenfactory.nebius.com/v1` (default in `hosted.py`), so Nemotron 3 Super is queried without
hosting a 120B model ourselves. The simulation then runs on the cluster and only the key stays on the user's machine.
**Nebius AI Cloud:** on 2026-10-30 a Nebius GPU VM (L40S, `gpu-l40s-a`, eu-north1) was started to reproduce the install, the simulator tests and the four-robot policy evaluation (30 seeds per robot: UR10e, UR5e and KAIROS mobile all 30/30). The evaluation itself ran on the VM's CPUs; see `transfergap/results/nebius_ai_cloud_repro_2026-10-30/` (nvidia-smi, logs, JSON). The main experiments, training and the GR00T fine-tune ran on an NVIDIA L40S GPU cluster, not on Nebius.
Set `NEBIUS_API_KEY` and `NEMOTRON_MODEL` as environment variables to reproduce the hosted call.

## What was significantly updated during the Hackathon Submission Period (Aug 26 - Oct 30, 2026)

The git history of this branch spans 2026-09-28 to 2026-10-30; everything in it was built inside the period. Main additions:
the MuJoCo UR5e/UR10e arm simulator and frozen gap-budget protocols (v1, v2, 500-seed v3); the Unitree G1 SONIC closed-loop pilot;
the Nemotron diagnosis loop with receipts; the Cosmos-Reason2 critic experiments; the KAIROS mobile manipulator model; the
behaviour-cloning policy; the GR00T-N1.5 fine-tune and evaluation (2026-10-30); and the demo videos in `deliverables/`.

## What needs a GPU or the cluster

- Isaac Sim / KAIROS stack, GR00T N1.5 fine-tuning and evaluation (`transfergap/scripts/eval_groot.py`, `gen_groot_data.py`), Cosmos-Reason2 critic,
  GEM-X / human-video pose stage, and G1 closed-loop SONIC rollouts: NVIDIA GPU (we used an L40S on the GPU cluster).
  Cluster commands are in [COMMANDS.md](COMMANDS.md); GPU setup notes in `transfergap/scripts/gpu_bootstrap.md`.
- Hosted Nemotron calls (`python3 -m transfergap diagnose`) need an API key, set as an environment variable (see `transfergap/.env.example`). Never commit a real `.env`.

## Limits

Simulation only. The arm experiments use a scripted controller and assumed error models. The G1 pilot uses IK keyframes, not a human
reaching demonstration. Cosmos-Reason2 critic scores were below the majority baseline. GR00T fine-tuning and a matched
two-embodiment comparison remain open (see below and [Implementation Status](Implementation%20Status.md)).

---

Nebius × NVIDIA Global AI Hackathon — Physical AI track.

One human demonstration, two robot embodiments (a Unitree G1 humanoid and a wheeled
single-arm manipulator): measure where execution transfer fails, diagnose the cause,
and test whether a targeted correction improves it.

**Project status (Oct 6, 2026):** everything runs and is tested on the GPU cluster only (Nebius is out of scope). One Docker
image (`ghcr.io/sushruths04/transfergap:full-2026-10-06b`, private) passes a six-stage end-to-end check there: environment, 198
unit tests, the 500-seed arm study reproduced exactly, depth-perception and style-transfer smoke runs, and G1 closed-loop
rollouts (4 of 4 grasped). Results are in `transfergap/results/`; `HANDOFF.md` has the open items and resume commands. The KAIROS mobile robot (Summit XLS base + UR10e + 2F-140) is also modelled in MuJoCo (`sim/kairos_mobile.py`), with a drive-then-pick demo. Open:
the closed-loop G1 host-versus-image gap is unexplained, the human-video pose stage is not yet in the cluster image, and the
live webcam mode has only been run with a stock video. Simulation only. Read [Implementation Status](Implementation%20Status.md)
and `HANDOFF.md` before trusting any specific claim.

**Documents:** [DOC_INDEX.md](DOC_INDEX.md) lists every file with its status (current / new / historical). Read [STATUS_AND_OBJECTIVE.md](STATUS_AND_OBJECTIVE.md) and [DEEP_ANALYSIS_REALISM_AND_REALTIME.md](DEEP_ANALYSIS_REALISM_AND_REALTIME.md) first.

## Start here

- [Research Synthesis 2026-09-30](Research%20Synthesis%202026-09-30.md) — final decisions from the 13-report research phase (claim, NVIDIA stack, dated plan). Read first.
- [Agent Handoff](Agent%20Handoff.md) — current state, next actions, open decisions and project rules.
- [Execution Plan 2026-10-01](Execution%20Plan%202026-10-01.md) — recovery work, exact artifacts, and local next steps.
- [TransferGap](TransferGap.md) — the locked project plan and architecture.
- [Implementation Status](Implementation%20Status.md) — what is actually done, with
  evidence, updated per session. **Read its top banner before touching the GPU
  instance or making any billing claim.**
- [Research review](TransferGap%20Research%20Review.md) and
  [Review and Next Plan](Review%20and%20Next%20Plan%202026-09-28.md) — an independent
  pass over the evidence, with a dated completion-gate schedule.
- [KAIROS Stack Audit](KAIROS%20Stack%20Audit.md) — the target real robot's documented
  stack (ROS 2 Humble, UR10, Robotiq, MoveIt2, Nav2, Isaac Sim 4.2).
- [transfergap/](transfergap/README.md) — the local starter package (episode scoring,
  paired comparison, robot/action contracts, hosted NVIDIA model calls).

## Quick start (local, no GPU required)

```bash
cd transfergap
python3 -m transfergap doctor
python3 -m unittest discover -s tests -v
python3 -m transfergap evaluate examples/fixture_episodes.jsonl --allow-fixtures
```

GPU-dependent work (Sonic/MuJoCo, GEM-X, GR00T fine-tuning, Cosmos) runs on a rented
Nebius AI Cloud L40S instance, not this machine — see `transfergap/scripts/gpu_bootstrap.md`
and the dated milestone entries in [Implementation Status](Implementation%20Status.md)
for exact reproduction commands.

## What's real vs. planned

The local UR5e and UR10e MuJoCo experiments use a scripted controller and assumed errors.
Their held-out look-again correction raised success from 31/60 to 50/60 and from 33/60
to 46/60, respectively. The separate G1 SONIC contact pilot placed in 19/30 nominal
rollouts and 17/30 oracle-target rollouts; it uses IK keyframes, not a human reaching
demonstration. Cosmos-Reason2-8B scored 40/120 success labels in v1 and 62/116 in v2,
both below the respective majority baselines. These are different clip splits. The
[static report](transfergap/static_report/README.md) shows the recorded results without
live API calls. GR00T fine-tuning, a human-demo-driven scored pick/lift/release episode,
and a matched two-embodiment comparison remain open.

## License

MIT for this repository's own code and docs (see [LICENSE](LICENSE)). Third-party
models and code (GR00T, SONIC, GEM-X, Nemotron, Cosmos) are used via their own
licenses/hosted APIs and are not redistributed here.
