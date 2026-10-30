# GPU bootstrap runbook — run this on the rented Nebius AI Cloud L40S, not locally

This machine has only an 8GB RTX A2000 laptop GPU — confirmed insufficient (GR00T alone
needs 16GB+ for inference). Nothing below runs until the L40S exists and is reachable.
Every command here is quoted or paraphrased from primary NVIDIA sources, not guessed;
gaps are marked explicitly rather than filled in.

## 0. Before running anything

- [ ] L40S instance provisioned on Nebius AI Cloud, reachable (SSH or notebook).
- [ ] `NEBIUS_API_KEY` exported in the shell (see `transfergap/.env.example`).
- [ ] Hugging Face token authenticated (`huggingface-cli login`) — GR00T-N1.7,
      GEAR-SONIC, and GEM-X may be gated behind license acceptance.
- [ ] A recorded clip of the human demo (walk to table, reach, pick, place) copied
      onto this machine.

## 1. Sonic — MuJoCo quickstart (verified commands, from the official quickstart page)

```bash
git clone https://github.com/NVlabs/GR00T-WholeBodyControl
cd GR00T-WholeBodyControl

# Follow the repo's own Installation Guide first — this page does not state the
# required Python version or CUDA version; check the Installation Guide doc,
# not this file, before proceeding.

bash install_scripts/install_mujoco_sim.sh

# Pretrained G1 checkpoint:
python download_from_hf.py
# For training/evaluation instead of just inference:
python download_from_hf.py --training --no-smpl
python download_from_hf.py --sample
```

Run the demo in two terminals (exact commands from the quickstart page):

```bash
# Terminal 1
source .venv_sim/bin/activate
python gear_sonic/scripts/run_sim_loop.py

# Terminal 2
bash deploy.sh sim
```

**Gate:** the G1 walks/balances in MuJoCo using the pretrained checkpoint, no fine-tuning.
This is Line A's guaranteed floor from the build schedule in `TransferGap.md`.

## 2. GEM-X — live camera / recorded-video bridge into Sonic

Documented tutorial: https://nvlabs.github.io/GR00T-WholeBodyControl/tutorials/live_camera_teleop.html
Exact install/run commands were **not fetched yet** — read that page directly on the
GPU machine before running anything; do not guess flags.

**Gate:** the recorded human demo clip drives the G1 in MuJoCo via GEM-X → Sonic.

## 3. GR00T N1.7 — one compatible example, then fine-tuning

Repo: https://github.com/NVIDIA/Isaac-GR00T
Hardware guide (already verified): inference needs 16GB+ VRAM; light/head-only
fine-tuning fits ~35GB peak on the L40S; `--tune-llm`/`--tune-visual` needs 80GB+ — do
not attempt those on this GPU.

For the Sonic-compatible fine-tune, the embodiment tag is confirmed real:
```bash
--embodiment-tag UNITREE_G1_SONIC
```
Read `tutorials/vla_workflow.html` on the GPU machine for the full fine-tune command
before running it — do not run a fine-tune job from a paraphrased command.

## 4. Cosmos-Reason2

Not self-hosted — call the Nebius Serverless Endpoint from `.env`
(`COSMOS_BASE_URL`/`COSMOS_API_KEY`/`COSMOS_MODEL`). If no endpoint exists yet, it
must be provisioned on Nebius AI Cloud first; this is a prerequisite, not a code change.

## 5. Report back after each numbered section

For each section above, report: exact command run, exact output/error, and GPU memory
used (`nvidia-smi` during the run). Do not report a section as done from log text
alone if there is any doubt — paste the actual terminal output.
