# TransferGap sweeps as Nebius Serverless AI Jobs

CPU-only image: `python:3.12-slim` + `mujoco==3.14.0` + `numpy==2.2.6` + mujoco_menagerie (UR5e, Robotiq 2F-85) at
commit `4d038b3f`. Entry point `jobs/run_sweep.sh`, which writes results, `log.txt` and `receipt.json` (git commit,
start/end UTC, hostname, platform, CPU model, nproc, memory, Python and MuJoCo versions, sha256 of every output) to
`$TG_OUT/<run id>/` (default `/data/out`). It also prints the receipt to stdout as one line starting with
`TRANSFERGAP_RECEIPT`, so the job logs hold it even if no volume is mounted.

| Mode (`TG_MODE` or first arg) | What runs |
|---|---|
| `gap_budget_sweep` (default) | `transfergap.sim.gap_budget sweep`: success against error magnitude, seeds 2000-2029, n=30 per level |
| `sweep` | `transfergap.sim.sweep --n $TG_N [--only $TG_ONLY]` |
| `diagnose` | `transfergap diagnose` on **dev seeds only**. Nemotron is called only if `NEBIUS_API_KEY` is set |
| `test` | the unit-test suite inside the image |

No mode runs held-out trials. Held-out runs need the committed-protocol check in `sim/gap_budget.py`, which needs
the git checkout, so they are not packaged here.

Locally verified on 2026-10-01: the image builds (477 MB on disk), `docker run transfergap-sweep:dev test` passes
51/51, and a 3-episode `sweep` wrote `episodes.jsonl`, `log.txt` and `receipt.json` to a mounted directory.
`run_sweep.sh` also runs outside Docker (`TG_PYTHON=.venv/bin/python TG_OUT=/tmp/x jobs/run_sweep.sh sweep`).

## Commands (run from `transfergap/`, after `nebius profile create`)

```bash
# 1. Registry + push (Container Registry quickstart)
nebius registry create --name transfergap --format json | jq -r ".metadata.id" | cut -d- -f 2   # -> REGISTRY_PATH
nebius registry configure-helper
IMAGE=cr.eu-north1.nebius.cloud/$REGISTRY_PATH/transfergap-sweep:$(git rev-parse --short HEAD)
docker build -f jobs/Dockerfile --build-arg TRANSFERGAP_GIT_COMMIT=$(git rev-parse HEAD) -t "$IMAGE" .
docker push "$IMAGE"

# 2. Validate the request without creating anything
nebius ai job create --dry-run \
  --name tg-gap-sweep-$(date -u +%m%d-%H%M) \
  --image "$IMAGE" \
  --platform cpu-d3 --preset 16vcpu-64gb \
  --timeout 1h --disk-size 50Gi \
  --env TG_MODE=gap_budget_sweep --env TG_PROCS=16

# 3. Create it for real (same flags, without --dry-run), then
nebius ai job get <JOB_ID>
nebius ai job logs <JOB_ID> --follow | tee runs/jobs/<JOB_ID>.log
grep '^TRANSFERGAP_RECEIPT ' runs/jobs/<JOB_ID>.log | cut -d' ' -f2- > runs/jobs/<JOB_ID>.receipt.json
nebius ai job get <JOB_ID> --format json > runs/jobs/<JOB_ID>.job.json      # Nebius-side job record
```

To keep the result files as well as the logs, add an object-storage volume:
`--volume s3://<bucket>:/data/out:rw:<profile>` (format from `nebius ai job create --help`; S3 credentials via an
AWS profile or `PROFILE@SECRET_SELECTOR` for MysteryBox).

Diagnosis loop as a job: `--env TG_MODE=diagnose --env-secret NEBIUS_API_KEY=<mysterybox-secret-selector>`
(`--env-secret` takes `KEY=SECRET_SELECTOR`). Without the secret it runs the rule-based baseline only.

## What is verified, and how

- **CLI syntax: both forms exist.** In the installed CLI (`nebius` 0.12.280), `nebius ai job create --help` describes
  it as "deterministic and non-interactive. Use it for scripts, config-driven workflows, CI, and agents", and
  `nebius ai create` as the "guided ... wizard" ("Interactively creates a Serverless AI job or endpoint"). The docs
  use both: the jobs quickstart uses `nebius ai create --type job`
  (https://docs.nebius.com/serverless/quickstart/jobs) and the jobs management page uses `nebius ai job create`
  (https://docs.nebius.com/serverless/jobs/manage). **Use `nebius ai job create` in scripts.** This closes the
  syntax question in Research Synthesis section 9.
- Flags, from local `--help`: `--image --container-command --args --working-dir --env --env-secret --volume
  --inject-file --disk-size --shm-size --platform --preset --preemptible --on-demand --follows-spot-price
  --restart-policy {never,on-failure} --timeout (1h-168h, default 24h) --registry-secret --dry-run --async`.
  **`--platform` defaults to `gpu-h100-sxm` in eu-north1**, so a CPU job must set `--platform` explicitly.
- `cpu-d3` (AMD EPYC 9654) presets `2vcpu-8gb` up to `32vcpu-128gb` in eu-north1:
  https://docs.nebius.com/compute/virtual-machines/types.
- Registry commands and the image URL format `cr.<region>.nebius.cloud/<registry_path>/<image>:<tag>`:
  https://docs.nebius.com/container-registry/quickstart.
- Logs and status (`nebius ai job logs <id> --follow`, `nebius ai job get <id>`): the two jobs pages above.

## Not verified (check with `--dry-run` or the first real job)

- Whether Serverless Jobs accept a **CPU-only** platform (`cpu-d3`). All doc examples are GPU (`gpu-l40s-a`). If
  the dry run rejects it, fall back to `--platform gpu-l40s-a --preset 1gpu-8vcpu-32gb` (L40S, about $1.55/h, and the
  sweep needs well under 1 h) or `--preemptible`.
- Whether a job can pull from a private registry in the same project without `--registry-secret` or
  `--registry-username/--registry-password`.
- How `--args` is split into argv. That is why the mode is passed with `--env TG_MODE=...`.
- The S3 volume credentials setup, and whether `/data/out` survives without a volume (assume it does not; the
  receipt in the logs is the fallback).
- Billing granularity and the CPU job price.
