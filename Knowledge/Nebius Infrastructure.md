---
type: infrastructure
updated: 2026-09-30
tags: [nebius, infrastructure, costs, billing]
---

# Nebius Infrastructure

Sources: [[Implementation Status]] (banner and incident sections), [[03_nebius_infra_cosmos]], [[Research Synthesis 2026-09-30]] §4. Back to [[Home]] · [[Knowledge/README|Knowledge]].

## Billing rule

Do not claim anything is or is not billing without a current console check or a working CLI call. The user stopped `transfergap-gpu-v2` in the console (Sept 28); no tool verified it. The CLI (`nebius`) has no auth profile until the user runs `nebius profile create` interactively (browser login; keep `federation`; pick tenant/project). Source of truth: console.nebius.com, region `eu-north1`, Compute -> Instances.

## Resource IDs (from the Implementation Status banner)

| Resource | Value |
|---|---|
| Instance | `computeinstance-e00d2kw410gxdtxkhx`, name `transfergap-gpu-v2` |
| Project / region | `project-e00rt2zapr004vtt8961b5` / `eu-north1` |
| Platform / preset | `gpu-l40s-a` / `1gpu-16vcpu-64gb`, on-demand (about $1.55/GPU-h) |
| Boot disk | `computedisk-e00q30kv4vbhahq8sf` (200 GB) |
| Safety snapshot (recovery point, keep) | `computedisksnapshot-e00szmmw37dc50mn5s` |
| Public IP (Sept 27 on this instance) | `89.169.108.43` (may change on restart) |
| Image projects | region-scoped: `project-e00public-images` for `eu-north1`; `project-e07public-images` only resolves `eu-south1` |
| SSH key | `~/.ssh/transfergap_gpu` |
| Check state | `nebius compute instance get --id computeinstance-e00d2kw410gxdtxkhx` |

The original preempted instance and its disk were deleted; billing audit Sept 27: one instance, one 200 GB disk, one snapshot.

## Services and how we use them

| Service | Use | Notes |
|---|---|---|
| Dev VM (L40S) | Interactive dev, SONIC/GEM-X; first action: copy all authored code off the VM into the repo; stop (not delete) when idle | Idle hours dominate cost |
| **Serverless Jobs** | Sharded evaluation sweeps; held-out correction test; make at least one real Job | The rules name it. Syntax discrepancy: reference page `nebius ai job create` vs quickstart `nebius ai create --type job`; check `nebius ai --help` |
| Serverless Endpoints | Cosmos via vLLM if not on Token Factory; stop manually (scale-to-zero not documented) | Flags `--image --container-command --container-port --env --platform --preset --auth token --token --public`; needs `HF_TOKEN` for gated models |
| **Token Factory** | Nemotron Nano/Super; check `GET /v1/models` for Cosmos 3 and save a receipt | See [[Nemotron]] |
| Managed Kubernetes | **Skipped** ([[Decision Log]]) | Not named in the rules; GPU pool min=0 and preemptible flags unconfirmed |
| Soperator (Slurm) | Not used | Overkill for one GPU |

Job flags (VERIFIED): `--image --container-command --args --working-dir --timeout` (min 1 h, max 168 h, default 24 h) `--env --env-secret --disk-size` (default 250Gi) `--volume` (including `s3://bucket:/path[:mode]`) `--inject-file --shm-size --platform --preset --preemptible --follows-spot-price`. Use a private Nebius Container Registry if TensorRT is baked into an image. Shard a sweep as N jobs with `--shard i --of N` writing JSONL to an S3 volume.

## Prices (nebius.com/prices, VERIFIED)

| GPU | On-demand $/GPU-h | Spot from |
|---|---|---|
| L40S (Intel) | 1.55 | 0.74 |
| L40S (AMD) | 1.82 | 0.90 |
| RTX PRO 6000 | 1.80 | 0.79 |
| H100 | 3.85 | 0.79 |
| H200 | 4.50 | 0.79 |
| B200 | 7.15 | 0.99 |

Serverless AI uses Compute quotas and pricing, billed while running. Billing granularity unknown. Disk, snapshot and object-storage prices not collected.

**Estimated cost to Oct 30: about $400-450** (dev VM about $310, GR00T pilot about $22-46, sweeps about $15-30, Cosmos endpoint about $31, Nemotron under $5; storage excluded). Biggest saving: stop the VM when idle.

## CLI and platform gotchas

- Preemption: SIGTERM 60 s before stop, then SIGKILL; checkpoint often.
- Preemptible spec cannot be removed after creation; preemptible needs `--recovery-policy fail` and `--preemptible-on-preemption stop`.
- Preset cannot be changed on an existing instance; capacity bin `1gpu-8vcpu-32gb` in `eu-north1` was exhausted region-wide on Sept 27 (even on-demand); `1gpu-16vcpu-64gb` worked. L40S exists only in `eu-north1` for this account.
- Verify on the machine: L40S quota; whether TensorRT can be packaged into a container image; Jobs CLI syntax.

See [[Lessons Learned]], [[Cosmos 3]], [[Cosmos-Reason2]], [[Deadlines]].
