#!/bin/bash
# ONE command from a person's video to the integrated demo video, inside the image.
#   tg-entrypoint showcase --video V [--joints J.npz] --out DIR [--window A B --events G R] [--shoulder-width-m M] [--robots ...] [--no-g1]
# Steps (each logs to DIR/logs; a failed step is named and the later ones that depend on it are skipped):
#   1 pose (RTMW3D, GPU)  2 pipeline (metric rescale, demo, feasibility, robot rollouts)  3 person measurements + overlay
#   4 robot videos (without / with the fix stack)  5 G1 mimic (needs SONIC weights + GPU, else skipped)  6 mimic fidelity  7 composed video
# Every number in the video is read from the result files written here. Simulation only.
set -uo pipefail
cd /opt/transfergap_src/transfergap
# KAIROS gripper description is a lab asset, mounted from the volume (as in e2e.sh)
KA=${KAIROS_ASSETS:-/data/kairos_assets}; [ -d "$KA" ] && [ ! -e transfergap/sim/assets/kairos ] && ln -s "$KA" transfergap/sim/assets/kairos
VIDEO=""; JOINTS=""; OUT=""; WIN=(); EV=(); SW=0.40; ROBOTS=(ur5e ur10e kairos); G1=1
while [ $# -gt 0 ]; do case "$1" in
  --video) VIDEO=$2; shift 2;; --joints) JOINTS=$2; shift 2;; --out) OUT=$2; shift 2;;
  --window) WIN=(--window $2 $3); shift 3;; --events) EV=(--events $2 $3); shift 3;;
  --shoulder-width-m) SW=$2; shift 2;; --no-g1) G1=0; shift;;
  --robots) shift; ROBOTS=(); while [ $# -gt 0 ] && [[ $1 != --* ]]; do ROBOTS+=("$1"); shift; done;;
  *) echo "unknown arg $1"; exit 2;; esac; done
[ -n "$OUT" ] && { [ -n "$VIDEO" ] || [ -n "$JOINTS" ]; } || { echo "usage: showcase --video V|--joints J --out DIR [...]"; exit 2; }
mkdir -p "$OUT/logs"; ST="$OUT/showcase_status.json"; echo '{}' > "$ST"
st() { python - "$ST" "$1" "$2" "$3" <<'PY'
import json,sys
p,k,s,d=sys.argv[1:5]; r=json.load(open(p)); r[k]={"status":s,"detail":d}; json.dump(r,open(p,"w"),indent=1)
PY
echo "[showcase] $1: $2 $3"; }
run() { local name=$1; shift; "$@" > "$OUT/logs/$name.log" 2>&1; local rc=$?
  if [ $rc = 0 ]; then st "$name" PASS ""; else st "$name" FAIL "exit $rc: $(tail -2 "$OUT/logs/$name.log" | tr '\n' ' ' | cut -c1-200)"; fi; return $rc; }

# 1 pose
if [ -z "$JOINTS" ]; then
  JOINTS=$OUT/joints.npz
  run pose "$TG_POSE_PY" transfergap/demo/tools/rtmw3d_export_joints.py --video "$VIDEO" --out "$JOINTS" || exit 1
else st pose SKIP "joints given"; fi
# 2 pipeline (rescales to metric, writes joints_scaled.npz, demo.npz, rollouts/repro_summary.json)
run pipeline python -m transfergap.pipeline --joints "$JOINTS" --out "$OUT/pipe" --robots "${ROBOTS[@]}" --shoulder-width-m "$SW" "${WIN[@]}" "${EV[@]}" || exit 1
SCALED=$OUT/pipe/joints_scaled.npz; [ -f "$SCALED" ] || SCALED=$JOINTS
# 3 person measurements
VID=(); [ -n "$VIDEO" ] && VID=(--video "$VIDEO")
run analyze python -m transfergap.human.analyze --joints "$JOINTS" "${VID[@]}" "${WIN[@]}" --shoulder-width-m "$SW" --out "$OUT/human"
# 4 robot videos
RR=(); for r in "${ROBOTS[@]}"; do [ "$r" = kairos ] && r=kairos_mobile; RR+=("$r"); done
run robots_render python -m transfergap.human.robots_render --demo "$OUT/pipe/demo.npz" --robots "${RR[@]}" --out "$OUT/robots"
# 5/6 G1 mimic
G1ARGS=()
if [ $G1 = 1 ] && [ -d "${SONIC_WEIGHTS_SRC:-/data/weights/gear_sonic_deploy}/policy/release" ] && nvidia-smi -L >/dev/null 2>&1; then
  if run g1_mimic env JOINTS="$SCALED" OUT="$OUT/g1" SONIC_WEIGHTS_SRC="${SONIC_WEIGHTS_SRC:-/data/weights/gear_sonic_deploy}" bash g1/image_g1_mimic.sh && [ -f "$OUT/g1/seed0_r0.mp4" ]; then
    G1ARGS=(--g1 "$OUT/g1/seed0_r0.mp4")
    if run mimic_fidelity bash -c "python -m transfergap.human.mimic_fidelity --joints \"$SCALED\" --episode \"$OUT/g1/seed0_r0.episode.json\" > \"$OUT/g1/mimic_fidelity.json\""; then
      G1ARGS+=(--g1-fidelity "$OUT/g1/mimic_fidelity.json"); fi
  fi
else st g1_mimic SKIP "disabled, or no GPU / no SONIC weights"; fi
# 7 compose
HUM=(); [ -f "$OUT/human/human_overlay.mp4" ] && HUM=(--human "$OUT/human/human_overlay.mp4")
[ ${#HUM[@]} -gt 0 ] || { st showcase FAIL "no overlay video (pass --video)"; exit 1; }
run showcase python -m transfergap.human.showcase "${HUM[@]}" --robots-dir "$OUT/robots" --counts "$OUT/pipe/rollouts/repro_summary.json" "${G1ARGS[@]}" --out "$OUT/TransferGap_demo.mp4"
rc=$?; cat "$ST"; exit $rc
