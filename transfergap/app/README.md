---
title: TransferGap
emoji: 🤖
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 6.29.0
python_version: "3.10"
app_file: app.py
pinned: false
license: mit
short_description: CI for human-to-robot transfer
---

# TransferGap: CI for human-to-robot transfer

TransferGap tells you, before you fine-tune, where a human demonstration will break on each of your
robots, which pipeline stage is responsible, and whether a targeted fix repairs it on trials it has
never seen.

## What the app shows

| Tab | What it does | Data |
|---|---|---|
| Overview | Pitch, pipeline (human demo → robot → failure → stage attribution → correction → verified), headline held-out result | recorded |
| Gap Budget | Per-robot recovery per stage when that stage is replaced by simulator ground truth, with paired 95% CIs; success per condition with Wilson 95% CIs | recorded, auto-discovers every `results/<run>/summary.json` |
| Correction | Held-out success before and after the chosen fix, paired 95% CI, plain statement of whether it excludes zero | recorded |
| Upload & Score | Upload an episodes `.jsonl`; scored with `transfergap/metrics.py` (`summarize`, `score_episode`, `paired_gap`) | your file |
| Diagnose (live) | One Nemotron call through `transfergap/hosted.py` that proposes a fix from a fixed menu | live, needs `NEBIUS_API_KEY` |

Every recorded panel carries a provenance label: run name, date, commit and seed range.
All tabs except Diagnose work offline.

## Run locally

From the `transfergap/` project directory:

```bash
.venv/bin/pip install -r app/requirements.txt
.venv/bin/python app/app.py            # http://127.0.0.1:7860
```

Optional, for the live tab (the key is read from the environment, never shown or logged):

```bash
export NEBIUS_API_KEY=...              # Nebius Token Factory
export NEMOTRON_MODEL=...              # exact Nemotron model ID available to your account
```

Receipts of live calls are written to `runs/app_receipts/` (gitignored); they contain the request
hash, model identity, latency and usage, never credentials.

## Adding a robot

Write `results/<run>/summary.json` in the format produced by `python -m transfergap.sim.gap_budget`
and include a top-level `"robot"` string (and optionally `"recorded_at"`). The run appears in the
Gap Budget chart and tables on the next start. The budget stages are read from `dev.budget`, so a
humanoid run can report stages such as `retargeting` or `contact`.

## Hugging Face Space layout

The Space root is this folder plus three items copied from the project directory:

```
app.py  backend.py  requirements.txt  README.md
transfergap/        # the Python package (metrics.py, hosted.py, ...)
results/            # recorded runs
examples/           # fixture_episodes.jsonl for the "Load example" button
```

`backend.py` finds the package in `$TRANSFERGAP_ROOT`, then the parent folder (repo layout), then
its own folder (Space layout). Add `NEBIUS_API_KEY` and `NEMOTRON_MODEL` as Space secrets to enable
the live tab. Outside git, the recorded date falls back to `recorded_at` in `summary.json`.

## Honest scope

The gap-budget panels are simulated UR5e and UR10e arms with Robotiq 2F-85 grippers in MuJoCo with real contact
grasping and a scripted IK controller. The human-to-robot error magnitudes are stated assumptions,
frozen in `protocol.json` before held-out trials ran; no human demonstration drives the arm yet.
Nemotron's proposal is advisory and never defines success; only simulator-state scoring does.
