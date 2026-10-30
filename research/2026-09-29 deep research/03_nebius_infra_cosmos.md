# 03 — Nebius infrastructure, Cosmos/Nemotron serving, hackathon rules

Research agent 3 of 6. Date: 2026-09-29. Method: WebFetch of docs.nebius.com, nebius.com, HF model cards, GitHub READMEs, devpost. WebFetch passes pages through a summarizer — items marked **VERIFIED** were stated explicitly on the cited official page; **UNVERIFIED** = third-party, inferred, or not found. No Nebius resources were created or changed.

---

## 1. Hackathon: what actually gets scored

Sources: https://nebiusglobalaihackathon.devpost.com/ , https://nebiusglobalaihackathon.devpost.com/rules

| Item | Fact | Status |
|---|---|---|
| Deadline | Friday Oct 30, 2026, 10:00am PT | VERIFIED |
| Tracks | Coding & Agentic Engineering; Best Apps & Agents; Personal AI; **Physical AI** | VERIFIED |
| Physical AI description | "Build embodied and edge agents that sense and act in the real world: robotics, IoT, and on-device intelligence, powered by Nemotron, GROOT, Cosmos and Sonic models and coordinated through an agent runtime." | VERIFIED (rules) |
| Footage | Video <3 min; must include ≥1-min clip of "the physical hardware/robot actually operating, or — if your Project has no physical hardware component — the key application modules in action." (The overview page omits the "or" clause; the **rules** page is the binding text.) | VERIFIED |
| Required tech | ≥1 NVIDIA open-source model; run on Nebius Token Factory or Nebius AI Cloud; Physical AI rules text calls out "Nebius Serverless Jobs to run simulations, generate synthetic data, evaluate robot policies, or process sensor data at scale." | VERIFIED |
| Pre-existing work | Must be new, or "significantly updated after the start of the Hackathon Submission Period." | VERIFIED |
| Judging | 4 **equally weighted**: Technological Implementation (effective use of Nebius + NVIDIA tech); **Design** ("complete, coherent product experience — not just proof-of-concept"); Potential Impact (credible real problem/audience); Quality of the Idea | VERIFIED |
| Prizes | Grand $20k, 2nd $10k, 3rd $6k (cross-track); each track winner gets a Jetson Orin Nano; Best use of Tavily $3k; 20× City winners $500; 10× feedback $100 | VERIFIED (overview) |
| Submission | Public repo w/ OSS license + README setup; working demo URL / hosted app; text description; public YouTube video | VERIFIED (rules, fetched previous night) |
| Scale | ~14,302 registrants; 20 judges from NVIDIA, Nebius, Tavily | VERIFIED |
| Past winners / judge preferences | Not found — appears to be first edition | UNVERIFIED |

**Implications for TransferGap:**
- Money is in the **cross-track** Grand/2nd/3rd; track win only = Jetson. You compete against all 4 tracks on the same 4 criteria, so "Design" (product completeness) counts as much as the tech.
- A hosted, clickable **demo URL** is mandatory — a notebook/log is not enough. Plan a small web app (report viewer / "upload a demo video → see transfer-gap report") behind a Nebius endpoint.
- Using **Serverless Jobs** visibly (eval sweeps / synthetic data) directly maps to the rules text → Technological Implementation points.
- Sim-only is allowed ("key application modules in action"); no need to fake hardware.

---

## 2. Nebius compute prices

Source: https://nebius.com/prices (VERIFIED; page shows no per-region differences)

| GPU | On-demand $/GPU-h | Spot "from" $/GPU-h |
|---|---|---|
| L40S (Intel) | 1.55 | 0.74 |
| L40S (AMD) | 1.82 | 0.90 |
| RTX PRO 6000 | 1.80 | 0.79 |
| H100 | 3.85 | 0.79 (H100&H200) |
| H200 | 4.50 | 0.79 (H100&H200) |
| B200 | 7.15 | 0.99 |
| B300 | 7.85 | 0.99 |

- Managed Kubernetes: listed "Free" on nebius.com/prices; docs say nodes are billed as Compute VMs. Control-plane fee: none found → effectively free. (VERIFIED-ish: https://docs.nebius.com/kubernetes/resources/pricing.md)
- Serverless AI (Jobs + Endpoints): "does not have its own quotas and pricing; the service applies the quotas and pricing of Compute." Billing only while running; stopped endpoints not charged for compute (volumes still charged). (VERIFIED: https://docs.nebius.com/serverless/pricing-quotas.md, endpoints page)
- Billing granularity (per-second vs per-hour): **unknown**.
- Disk/snapshot/object-storage prices: **not collected** — see https://docs.nebius.com/object-storage/resources/pricing.md.
- Our own experience (project log, VERIFIED in `Implementation Status.md`): L40S only in `eu-north1` for this account; `1gpu-8vcpu-32gb` capacity ran out region-wide on Sept 27; `1gpu-16vcpu-64gb` worked. Spot preempted mid-build. Preemptible spec cannot be removed after creation.
- Preemption: SIGTERM 60 s before stop, then SIGKILL (VERIFIED: https://docs.nebius.com/compute/virtual-machines/preemptible.md). → any spot training must checkpoint frequently (GR00T `--save-steps` well below default 5000).

---

## 3. Options compared

### 3a. Managed Kubernetes (mk8s)
Sources: https://docs.nebius.com/kubernetes/quickstart , https://docs.nebius.com/kubernetes/gpu/set-up , https://docs.nebius.com/kubernetes/node-groups/autoscaling.md

Commands (VERIFIED from docs; placeholders in `<>`):
```bash
export CLUSTER_ID=$(nebius mk8s cluster create \
  --name transfergap \
  --control-plane-subnet-id $SUBNET_ID \
  --control-plane-endpoints-public-endpoint=true \
  --format jsonpath='{.metadata.id}')

# CPU system pool (docs: needed so the GPU pool can scale down)
nebius mk8s node-group create --parent-id $CLUSTER_ID --name sys \
  --fixed-node-count 2 \
  --template-resources-platform cpu-e2 --template-resources-preset 2vcpu-8gb \
  --template-boot-disk-type network_ssd --template-boot-disk-size-bytes 137438953472 \
  --template-network-interfaces "[{\"subnet_id\": \"$SUBNET_ID\"}]"

# GPU pool
nebius mk8s node-group create --parent-id $CLUSTER_ID --name l40s \
  --template-resources-platform gpu-l40s-a --template-resources-preset 1gpu-16vcpu-64gb \
  --template-gpu-settings-drivers-preset cuda13.0 \
  --autoscaling-min-node-count <N> --autoscaling-max-node-count <M> \
  --template-network-interfaces "[{\"subnet_id\": \"$SUBNET_ID\"}]"
```
- Driver presets: `cuda12.8` (570.x) or `cuda13.0` (580.x). Alternative: omit preset and `helm install gpu-operator oci://cr.eu-north1.nebius.cloud/marketplace/nebius/nvidia-gpu-operator/chart/gpu-operator`. (VERIFIED)
- Docs explicitly say: add a CPU node group with ≥2 nodes "so that the GPU node group can scale down and reduce your costs." → strongly implies scale-down of GPU pool; **whether min=0 is accepted is not stated** (UNVERIFIED — test with `nebius mk8s node-group create --help`).
- Preemptible node groups: **flag not found in docs** (UNVERIFIED; check `--help` for `--template-preemptible*`).
- Batch Job / vLLM Deployment: standard Kubernetes `Job` / `Deployment` + `Service type=LoadBalancer`; no Nebius-specific syntax needed beyond `nvidia.com/gpu: 1` resource limits. (Standard k8s — not Nebius-verified.)
- Cost of cluster itself: CPU pool 2×2vCPU nodes runs 24/7 (price not collected, small). Setup overhead: 30–90 min for someone new to mk8s (estimate).

### 3b. Serverless AI Jobs — the rules-named service
Source: https://docs.nebius.com/serverless/jobs , https://docs.nebius.com/serverless/quickstart/jobs.md

```bash
nebius ai job create \
  --name tg-eval-sweep-001 \
  --image <registry>/transfergap-eval:<tag> \
  --container-command bash \
  --args "-c 'python -m transfergap_eval.sweep --shard 0 --of 8 --out /out'" \
  --platform gpu-l40s-a --preset 1gpu-8vcpu-32gb \
  --timeout 4h \
  --volume s3://<bucket>:/out:rw \
  --env PROTOCOL_ID=pnp-v1 \
  --preemptible --follows-spot-price
nebius ai job logs <job_id> --follow
nebius ai job list | cancel <id> | delete <id>
```
Flags VERIFIED: `--image`, `--container-command`, `--args`, `--working-dir`, `--timeout` (min 1h, max 168h, default 24h), `--env`, `--env-secret` (SecretStash), `--disk-size` (default 250Gi), `--volume source:path[:mode]` or `s3://bucket:/path[:mode[:profile]]`, `--inject-file` (read-only, ≤64 KiB), `--shm-size` (default 16Gi), `--platform`, `--preset`, `--preemptible`, `--follows-spot-price`, `--subnet-id`, `--ssh-key`.
- **Syntax discrepancy:** the jobs reference page shows `nebius ai job create`; the quickstart shows `nebius ai create --type job`. Check `nebius ai --help` on the installed CLI version before scripting. (VERIFIED discrepancy)
- Quickstart example uses `gpu-l40s-a / 1gpu-8vcpu-32gb` — the exact preset that hit capacity exhaustion for us on Sept 27; have `1gpu-16vcpu-64gb` as fallback.
- Container requirement: any OCI image with CUDA userspace; needs a registry (Nebius Container Registry: https://docs.nebius.com/container-registry/quickstart.md) or public Docker Hub. The Sonic C++ deploy needs TensorRT 10.13 inside the image (gated NVIDIA download → must be baked in by us, cannot be pulled publicly — license check needed before pushing to a *public* registry; use a private Nebius registry).
- Billing only while running; min timeout 1h is a *limit*, not a minimum charge (billing granularity unknown).
- **How to shard a MuJoCo eval sweep:** one image containing MuJoCo + Sonic deploy + our `transfergap` scorer; N jobs, each gets `--shard i --of N`, writes episode JSONL + MP4 to the S3 volume; a final local `python -m transfergap evaluate` over the merged JSONL. Arm-only (UR5e+IK, no neural policy) episodes are CPU-bound → a CPU platform preset would be cheaper (CPU preset names/prices not collected).

### 3c. Serverless AI Endpoints
Source: https://docs.nebius.com/serverless/endpoints
```bash
nebius ai endpoint create --name tg-cosmos \
  --image vllm/vllm-openai:<pinned-tag> \
  --container-command "vllm serve nvidia/Cosmos-Reason2-8B --max-model-len 16384 --reasoning-parser qwen3 --media-io-kwargs '{\"video\": {\"num_frames\": -1}}' --port 8000" \
  --container-port 8000 \
  --platform gpu-l40s-a --preset 1gpu-16vcpu-64gb \
  --auth token --token <secret> --public
```
Flags VERIFIED (`--image --container-command --container-port --env --platform --preset --auth token --token --public`). Scale-to-zero/autoscaling: **not documented** — stop it manually; stopped endpoints aren't charged for compute. Needs `HF_TOKEN` env if the model is gated.

### 3d. Soperator (Slurm)
Source: https://docs.nebius.com/slurm-soperator — open-source Slurm-on-Kubernetes; managed and self-deployed options; min size / setup time / price not stated in fetched text. **Overkill for a 1-GPU hackathon project — do not use.**

### 3e. Current single VM
Known-good, has every install on a 200 GB disk + snapshot. Best for interactive dev. Weakness: we pay for idle hours and it's one box.

---

## 4. Recommendation for TransferGap

| Workload | Use | Why |
|---|---|---|
| Interactive dev, debugging Sonic/GEM-X/data collection | **Existing VM** `transfergap-gpu-v2` (on-demand L40S), **stop when idle** | Everything already installed; don't rebuild environments under deadline. |
| (a) GR00T N1.7 fine-tune | **Same VM** for the first pilot; then **Serverless Job** for the "real" run | Hardware doc: 1× L40-class 40GB+ is the documented demo-dataset tier, default tuning <~35 GB. Running it as a Serverless Job (image = Isaac-GR00T + our dataset on S3 volume) gives visible rules-aligned usage and frees the VM. On spot: set `--save-steps` ≤1000 (60 s preemption notice). |
| (b) Parallel MuJoCo eval sweeps | **Serverless Jobs, sharded** (N small jobs) | This is literally the rules' example ("evaluate robot policies… at scale"). Paired-trial design in `metrics.py` maps cleanly to per-shard JSONL. Spot + short shards tolerate preemption. |
| (c) Cosmos reasoning/critic | First check Token Factory `GET /v1/models` for a Cosmos 3 reasoner (third-party site lists `cosmos3-super-reasoner` on Nebius at $0.10/$0.30 per 1M tokens — **UNVERIFIED**; our Sept 27 catalog of 25 models listed **no** Cosmos model). If absent → **Serverless Endpoint** with vLLM + Cosmos-Reason2-8B (32 GB fits L40S 48 GB), started only during eval batches. | Hosted = zero ops. Self-hosted endpoint is billed like a VM; stop between batches. |
| (d) Public demo endpoint | **Serverless Endpoint, CPU or smallest GPU**, serving a static/precomputed report viewer + an "upload clip → queue a Serverless Job" path; or simply a static site with precomputed results + a live Nemotron call | Judges need a working URL; it must not depend on an L40S running 24/7 during judging (after Oct 30). Precomputed results + cheap live calls to Token Factory is the robust choice. |
| mk8s | **Skip unless time remains** | Free control plane, but setup overhead + unknown scale-to-zero/preemptible flags. Serverless Jobs/Endpoints cover every need with less ops risk. Mention as "production path" in the pitch, not build it. |

### Cost estimate, Sept 29 → Oct 30 (ESTIMATE, on-demand L40S $1.55/h unless noted; storage excluded)

| Line | Assumption | Cost |
|---|---|---|
| Dev VM | ~8 h/day × 25 days | ~$310 |
| GR00T pilot + 2 real fine-tunes | ~30 GPU-h total (run time for 20k steps on 1×L40S **unknown**; guess) | ~$46 on-demand / ~$22 spot |
| Eval sweeps (Serverless Jobs) | ~20–40 GPU-h spot | ~$15–30 |
| Cosmos endpoint | ~20 h during eval batches | ~$31 (≈$0 if hosted on Token Factory at token prices) |
| Nemotron via Token Factory | Nano 30B-A3B $0.05 in / $0.20 out per 1M (third-party-reported, UNVERIFIED); a few thousand calls | <$5 |
| **Total** | | **~$400–450**, dominated by idle dev-VM hours → the single biggest saving is stopping the VM when not in use |

Disk (200 GB network SSD) + snapshot + object storage: price not collected — add it.

---

## 5. Cosmos: Reason2 vs Cosmos 3 (major update)

### Cosmos-Reason2 (what the project plan names)
Sources: https://huggingface.co/nvidia/Cosmos-Reason2-8B , https://github.com/nvidia-cosmos/cosmos-reason2
- Sizes/IDs: `nvidia/Cosmos-Reason2-2B`, `nvidia/Cosmos-Reason2-8B` (8.77B), `nvidia/Cosmos-Reason2-32B`. (VERIFIED)
- Base: post-trained from Qwen3-VL-8B-Instruct. License: NVIDIA Open Model License (commercial use OK); code Apache-2.0. (VERIFIED)
- VRAM: 2B → 24 GB, 8B → 32 GB (GitHub table); card says min 32 GB, tested H100/A100, BF16; card lists Hopper/Blackwell as supported archs — **L40S (Ada) not listed as tested** (UNVERIFIED that it works; very likely fine via vLLM but check).
- vLLM (VERIFIED, repo):
  ```bash
  vllm serve nvidia/Cosmos-Reason2-8B \
    --allowed-local-media-path "$(pwd)" \
    --max-model-len 16384 \
    --media-io-kwargs '{"video": {"num_frames": -1}}' \
    --reasoning-parser qwen3 --port 8000
  ```
  `num_frames: -1` lets per-request fps override; card recommends **fps=4** to match training.
- Prompt format (VERIFIED, card): append "Answer the question using the following format: <think>\nYour reasoning.\n</think>\n\nWrite your final answer immediately after the </think> tag." Set max output ≥4096 tokens to avoid truncating the reasoning.
- Benchmarks (8B, card): embodied reasoning 69.34%, AV 67.85%. **No published robot task-success/failure-detection numbers found.**
- Our `hosted.py` sends OpenAI-style `video_url` data-URI MP4 — matches vLLM's OpenAI server format; must add fps (via `mm_processor_kwargs`/media kwargs — exact request field UNVERIFIED) and the `<think>` suffix.
- **The repo states it is "no longer under active development" and tells users to migrate to Cosmos 3.** (VERIFIED)

### Cosmos 3 (released ~May 31 / June 1, 2026)
Sources: https://huggingface.co/nvidia/Cosmos3-Nano , https://developer.nvidia.com/blog/develop-physical-ai-reasoning-world-and-action-models-with-nvidia-cosmos-3/ , https://huggingface.co/blog/nvidia/cosmos-3-for-physical-ai , https://www.hpcwire.com/aiwire/2026/06/01/nvidia-launches-cosmos-3-the-open-frontier-foundation-model-for-physical-ai/
- One omni-model, Mixture-of-Transformers: **Reasoner tower** (VLM) + **Generator tower** (diffusion: video + actions). Nano **16B** (workstation, RTX PRO 6000), Super **64B** (Hopper/Blackwell), Edge variant (details not found). License OpenMDW-1.1 (VERIFIED on Nano card).
- Capabilities: VQA/scene understanding/robot planning; text/image→video, video prediction; **forward dynamics (action→future video) and inverse dynamics (video→actions)**; action outputs listed for Franka Panda, UR, Agibot, AV. Leads RoboLab and R-Bench per NVIDIA blog. (VERIFIED as claims on NVIDIA pages)
- Input limits (Nano card): text 4096 tokens; **video input up to 5 frames** (!); action trajectories 16–400 frames. The 5-frame limit may apply to the generator conditioning; unclear for the reasoner path — UNVERIFIED which.
- Serving: `vllm serve nvidia/Cosmos3-Nano --omni ...` (vLLM-Omni) or reasoner-only `vllm serve nvidia/Cosmos3-Nano --hf-overrides '{"architectures": ["Cosmos3ReasonerForConditionalGeneration"]}'`; NIM `nvcr.io/nim/nvidia/cosmos3-reasoner:latest` with `NIM_MODEL_SIZE=nano`, needs `NGC_API_KEY`; FP8/NVFP4 options. (VERIFIED)
- VRAM on L40S 48 GB: 16B BF16 ≈ 32 GB weights → probably fits for reasoner-only with short context; **UNVERIFIED**; FP8 NIM safer.
- Relationship to GR00T: not stated in fetched sources.
- Token Factory: third-party calculator lists `cosmos3-super-reasoner` on Nebius ($0.10/$0.30 per 1M) — **UNVERIFIED; verify with the account's `/v1/models`**.

**Recommendation:** keep the project's Cosmos role as a *video critic/event extractor* (never the benchmark label), but target **Cosmos 3 Reasoner** first (hosted on Token Factory if listed, else NIM/vLLM on the L40S), with **Cosmos-Reason2-8B as the fallback** because its vLLM path is documented and simple. A strong optional "wow" feature: Cosmos 3 **forward dynamics** to preview a proposed correction before running it in sim — but only as a stretch goal; unproven on our embodiments.

---

## 6. Nemotron on Token Factory

- VERIFIED from our own Sept 27 catalog (project log): `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/Nemotron-3_5-Lightning`, `nvidia/Nemotron-3-Ultra-550b-a55b`, `nvidia/nemotron-3-super-120b-a12b`. Nano call worked (2.2 s, 490 tokens).
- Nemotron 3 Super: `nvidia/nemotron-3-super-120b-a12b`, 120B/12B active, up to 1M context, MTP; dedicated endpoints, EU/US regions, optional zero-retention (VERIFIED: https://nebius.com/blog/posts/nemotron3-super-now-available). Price not on that page.
- Prices: Nano $0.05 in / $0.20 out per 1M tokens (search-result/OpenRouter-reported, **UNVERIFIED on Nebius**); Super median across providers $0.30/$0.80 (UNVERIFIED). Token Factory prices page did not render through the fetcher → check in console.
- Fine-tuning: the project already recorded Nemotron is **not** in the Token Factory fine-tuning list (VERIFIED in project doc). No Nemotron VLM found on Token Factory.
- Suggested split: Nano for cheap high-volume step planning/validation; Super for the "diagnosis report" (long context over episode logs + Cosmos outputs) — it's the flagship model judges will recognize.

---

## 7. Open items to verify on the machine (cheap, read-only)

1. `nebius ai --help` / `nebius ai job create --help` → confirm job syntax.
2. `nebius mk8s node-group create --help | grep -i -E 'preempt|autoscaling'` → confirm min=0 / preemptible (only if mk8s is pursued).
3. Token Factory `GET /v1/models` → is any Cosmos (esp. Cosmos 3 reasoner) listed? Record receipt.
4. Compute quotas for `gpu-l40s-a` in eu-north1 (how many concurrent GPUs for sharded jobs).
5. Whether TensorRT 10.13 may be redistributed inside a container image (license) → keep images in a private registry regardless.
