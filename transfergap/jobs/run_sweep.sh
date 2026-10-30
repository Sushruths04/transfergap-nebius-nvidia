#!/usr/bin/env bash
# TransferGap sweep entrypoint (container ENTRYPOINT for Nebius Serverless AI Jobs; also runs locally).
#
# Mode: first argument, else $TG_MODE, else "gap_budget_sweep".
#   gap_budget_sweep  success vs error magnitude, random directions, n=30/level, seeds 2000-2029
#   sweep             legacy perturbation sweep (transfergap.sim.sweep), $TG_N seeds per perturbation (default 30)
#   diagnose          diagnosis loop on DEV seeds only (rule baseline; Nemotron only if NEBIUS_API_KEY is set)
#   test              run the unit-test suite inside the image (smoke check)
# Output: $TG_OUT/<run id>/ (default /data/out; mount a volume there to keep results), containing the mode's
# results, log.txt and receipt.json (git commit, start/end UTC, host info, output sha256). The receipt is also
# printed to stdout so `nebius ai job logs` holds it even if no volume is mounted.
# Never runs held-out trials: held-out verification needs a committed protocol and is run deliberately, not here.
set -uo pipefail

MODE="${1:-${TG_MODE:-gap_budget_sweep}}"
PROJECT="${TG_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
PY="${TG_PYTHON:-python3}"
START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="${TG_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-${MODE}-$(hostname | tr -c 'A-Za-z0-9_.\n-' '_')}"
OUT="${TG_OUT:-/data/out}/${RUN_ID}"
mkdir -p "$OUT" || { echo "cannot create $OUT" >&2; exit 1; }
cd "$PROJECT" || exit 1
export PYTHONPATH="$PROJECT${PYTHONPATH:+:$PYTHONPATH}"
PROCS="${TG_PROCS:-$(nproc)}"

write_receipt() {
  local code=$1
  TG_R_MODE="$MODE" TG_R_START="$START" TG_R_END="$(date -u +%Y-%m-%dT%H:%M:%SZ)" TG_R_CODE="$code" \
  TG_R_OUT="$OUT" TG_R_PROJECT="$PROJECT" TG_R_PROCS="$PROCS" "$PY" - <<'PY'
import hashlib, json, os, platform, socket, subprocess, sys
from pathlib import Path
env = os.environ
out = Path(env["TG_R_OUT"])
def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=env["TG_R_PROJECT"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return env.get("TRANSFERGAP_GIT_COMMIT", "unknown")
def meminfo():
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemTotal"):
                return line.split(":", 1)[1].strip()
    except OSError:
        return None
def cpu_model():
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        return None
try:
    import mujoco; mj = mujoco.__version__
except Exception:
    mj = None
menagerie = Path(env["TG_R_PROJECT"]) / "transfergap/sim/assets/MENAGERIE_COMMIT"
files = {str(p.relative_to(out)): {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
         for p in sorted(out.rglob("*")) if p.is_file() and p.name not in ("receipt.json", "log.txt")}
receipt = {"schema": "transfergap.job_receipt/v1", "mode": env["TG_R_MODE"], "exit_code": int(env["TG_R_CODE"]),
           "started_at": env["TG_R_START"], "ended_at": env["TG_R_END"], "git_commit": git_commit(),
           "image_git_commit": env.get("TRANSFERGAP_GIT_COMMIT"),
           "menagerie_commit": env.get("MENAGERIE_COMMIT") or (menagerie.read_text().strip() if menagerie.exists() else None),
           "host": {"hostname": socket.gethostname(), "platform": platform.platform(), "machine": platform.machine(),
                    "cpu_model": cpu_model(), "nproc": os.cpu_count(), "mem_total": meminfo(),
                    "procs_used": int(env["TG_R_PROCS"])},
           "python": sys.version.split()[0], "mujoco": mj, "outputs": files}
(out / "receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
print("TRANSFERGAP_RECEIPT " + json.dumps(receipt))
PY
}

run_mode() {
  case "$MODE" in
    gap_budget_sweep)
      # gap_budget writes to fixed project paths; copy them into the run directory afterwards.
      "$PY" -m transfergap.sim.gap_budget sweep || return $?
      cp results/gap_budget_v1/sweep_random_dir.json "$OUT/" && cp runs/gap_budget/sweep_random_dir.jsonl "$OUT/" \
        && cat "$OUT/sweep_random_dir.json" ;;
    sweep)
      # shellcheck disable=SC2086
      "$PY" -m transfergap.sim.sweep --n "${TG_N:-30}" --procs "$PROCS" --out "$OUT/episodes.jsonl" \
        ${TG_ONLY:+--only $TG_ONLY} ;;
    diagnose)
      "$PY" -m transfergap diagnose --llm "${TG_LLM:-auto}" --out-dir "$OUT/diagnose" --procs "$PROCS" \
        ${TG_SEEDS_LIMIT:+--seeds-limit "$TG_SEEDS_LIMIT"} > "$OUT/diagnose_report.json" \
        && cat "$OUT/diagnose_report.json" ;;
    demo_repro)
      "$PY" -m transfergap.sim.demo_repro --demo "${TG_DEMO:-runs/demos/pexels_8135753_notebook.npz}" \
        --fixes "${TG_FIXES:-speed_cap_3,look_again,touch_probe_calibration}" --out "$OUT" \
        && cat "$OUT/repro_summary.json" | head -c 4000 ;;
    test)
      "$PY" -m unittest discover -s tests ;;
    *)
      echo "unknown mode: $MODE (gap_budget_sweep | sweep | diagnose | demo_repro | test)" >&2; return 64 ;;
  esac
}

echo "transfergap job: mode=$MODE out=$OUT start=$START procs=$PROCS"
run_mode > >(tee "$OUT/log.txt") 2>&1
CODE=$?
wait
write_receipt "$CODE"
exit "$CODE"
