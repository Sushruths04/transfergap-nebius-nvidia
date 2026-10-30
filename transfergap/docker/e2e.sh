#!/bin/bash
# End-to-end check of the unified `full` image on one GPU host (GPU cluster Job or any Docker + nvidia host).
#   tg-entrypoint e2e            (runs inside the image; see docker/cluster/e2e-job.yaml for the cluster Job)
# Stages (each writes PASS / FAIL / SKIP into $TG_OUT/e2e/report.json; exit 1 if any FAIL):
#   info        versions, GPU, EGL render
#   tests       the full unit-test suite (expected: OK)
#   arm_repro   500-seed arm study re-run in the image (full and look_again, UR5e and UR10e) must reproduce the committed
#               results/gap_budget_v3/summary.json successes EXACTLY (MuJoCo is deterministic for these scripted controllers)
#   perception  depth-perception smoke run (UR5e dev seeds 0-1)
#   style       style transfer with depth perception smoke run, needs the demo at $DEMO_NPZ (else SKIP)
#   perceive    RTMW3D pose on the first 30 frames of $CLIP_MP4 (GPU + weights; else SKIP): 30 frames, none without a person
#   pipeline    the one-command pipeline from $PIPE_JOINTS (the author's clip joints, private, on the volume) for UR5e, UR10e and KAIROS must
#               reproduce the committed results/cluster_pipeline_user_scaled_v1/repro_summary.json successes EXACTLY (the e2e robots only) (else SKIP)
#   g1          G1 closed-loop rollouts (hybrid) of seeds $G1_SEEDS, needs the SONIC weights under $SONIC_WEIGHTS_SRC and a GPU (else SKIP);
#               PASS = every rollout ran and logged AND at least half grasped (a coarse sanity bar: the G1 sim is nondeterministic, the validated environment grasps 8-10 of 10)
set -uo pipefail
cd /opt/transfergap_src/transfergap
OUT=${TG_OUT:-/data/out}/e2e; mkdir -p "$OUT"; REP=$OUT/report.json; echo '{}' > "$REP"
DEMO_NPZ=${DEMO_NPZ:-/data/demos/pexels_8135753_notebook.npz}
SONIC_WEIGHTS_SRC=${SONIC_WEIGHTS_SRC:-/data/weights/gear_sonic_deploy}
G1_SEEDS=${G1_SEEDS:-1200-1201}
CLIP_MP4=${CLIP_MP4:-/data/demos/user_clip.mp4}
PIPE_JOINTS=${PIPE_JOINTS:-/data/demos/user_clip_rtmw3d_joints.npz}
FAIL=0
# KAIROS gripper description is a lab asset and is not in the image: mount it and link it in (else the KAIROS tests skip, the style stage fails)
KAIROS_ASSETS=${KAIROS_ASSETS:-/data/kairos_assets}
[ -d "$KAIROS_ASSETS" ] && [ ! -e transfergap/sim/assets/kairos ] && ln -s "$KAIROS_ASSETS" transfergap/sim/assets/kairos
rec() { python - "$REP" "$1" "$2" "$3" <<'PY'
import json,sys
p,k,s,d=sys.argv[1:5]; r=json.load(open(p)); r[k]={"status":s,"detail":d}; json.dump(r,open(p,"w"),indent=1)
PY
echo "[e2e] $1: $2 $3"; [ "$2" = FAIL ] && FAIL=1; return 0; }

# --- info
info=$(python -c "
import mujoco,numpy,platform
from transfergap.sim import scene
r=mujoco.Renderer(scene.Scene(0,'ur5e').model,64,64); r.close()
print('python',platform.python_version(),'numpy',numpy.__version__,'mujoco',mujoco.__version__,'EGL ok')" 2>&1 | tail -1)
gpu=$(nvidia-smi -L 2>/dev/null | head -1 || echo "no GPU")
case "$info" in *"EGL ok"*) rec info PASS "$info | $gpu";; *) rec info FAIL "$info";; esac

# --- tests
python -m unittest discover -s tests -q > "$OUT/tests.log" 2>&1; tl=$(tail -3 "$OUT/tests.log" | tr '\n' ' ')
case "$tl" in *OK*) rec tests PASS "$tl";; *) rec tests FAIL "$tl";; esac

# --- arm reproduction of the committed 500-seed result
python "${E2E_DOCKER_DIR:-docker}/e2e_arm_repro.py" > "$OUT/arm_repro.log" 2>&1
rc=$?; rec arm_repro $([ $rc = 0 ] && echo PASS || echo FAIL) "$(tr '\n' ' ' < "$OUT/arm_repro.log" | cut -c1-300)"

# --- perception smoke
python -m transfergap.sim.perception_hard_eval --robot ur5e --split dev --seeds 0-1 --out "$OUT/perception" > "$OUT/perception.log" 2>&1
rec perception $([ $? = 0 ] && echo PASS || echo FAIL) "$(tail -2 "$OUT/perception.log" | tr '\n' ' ' | cut -c1-200)"

# --- style transfer with depth perception smoke
if [ -f "$DEMO_NPZ" ]; then
  mkdir -p runs/demos; ln -sf "$DEMO_NPZ" runs/demos/pexels_8135753_notebook.npz
  python -m transfergap.sim.style_perception dev --seeds 0-1 --out "$OUT/style" > "$OUT/style.log" 2>&1
  rec style $([ $? = 0 ] && echo PASS || echo FAIL) "$(tail -2 "$OUT/style.log" | tr '\n' ' ' | cut -c1-200)"
else rec style SKIP "demo not mounted at $DEMO_NPZ"; fi

# --- pose stage (RTMW3D) smoke
if [ -f "$CLIP_MP4" ] && [ -x "${TG_POSE_PY:-/nonexistent}" ] && nvidia-smi -L >/dev/null 2>&1; then
  "$TG_POSE_PY" transfergap/demo/tools/rtmw3d_export_joints.py --video "$CLIP_MP4" --out "$OUT/perceive_joints.npz" --max-frames 30 > "$OUT/perceive.log" 2>&1
  d=$(python - "$OUT/perceive_joints.npz" <<'PY'
import json,sys
import numpy as np
z=np.load(sys.argv[1]); m=json.loads(str(z["meta"])); n=z["joints"].shape[0]; w=m.get("frames_without_person")
print(("OK " if n==30 and w==0 else "BAD ")+f"{n} frames, {w} without a person"); sys.exit(0 if n==30 and w==0 else 1)
PY
  2>&1 | tail -1); rec perceive $(case "$d" in OK*) echo PASS;; *) echo FAIL;; esac) "$d | $(tail -1 "$OUT/perceive.log" | cut -c1-100)"
else rec perceive SKIP "no clip at $CLIP_MP4, no TG_POSE_PY or no GPU"; fi

# --- one-command pipeline reproduces the committed cluster result exactly
if [ -f "$PIPE_JOINTS" ]; then
  python -m transfergap.pipeline --joints "$PIPE_JOINTS" --window 60 206 --events 102 166 --robots ur5e ur10e kairos --out "$OUT/pipeline" > "$OUT/pipeline.log" 2>&1
  d=$(python - "$OUT/pipeline/rollouts/repro_summary.json" results/cluster_pipeline_user_scaled_v1/repro_summary.json <<'PY'
import json,sys
a,b=(json.load(open(f))["robots"] for f in sys.argv[1:3])
g=lambda r:{k:{c:v["successes"] for c,v in x["conditions"].items()} for k,x in r.items()}
ga=g(a); gb={k:v for k,v in g(b).items() if k in ga}; print(("MATCH " if ga==gb else "MISMATCH ")+json.dumps(ga)); sys.exit(0 if ga==gb else 1)
PY
  2>&1 | tail -1); rec pipeline $(case "$d" in MATCH*) echo PASS;; *) echo FAIL;; esac) "$d"
else rec pipeline SKIP "no joints at $PIPE_JOINTS"; fi

# --- G1 closed-loop rollouts
if [ -d "$SONIC_WEIGHTS_SRC/policy/release" ] && nvidia-smi -L >/dev/null 2>&1; then
  OUTNAME=e2e_g1 SONIC_WEIGHTS_SRC=$SONIC_WEIGHTS_SRC G1_OUT_ROOT=$OUT bash g1/image_g1_trials.sh $G1_SEEDS > "$OUT/g1.log" 2>&1
  rc=$?; rows=$OUT/e2e_g1/rows.json
  if [ $rc = 0 ] && [ -s "$rows" ]; then
    d=$(python - "$rows" "$G1_SEEDS" <<'PY'
import json,sys
r=json.load(open(sys.argv[1])); lo,hi=map(int,sys.argv[2].split("-"))
print(f"{len(r)}/{hi-lo+1} rollouts logged, {sum(x['lift_cm']>=5 for x in r)} grasped (lift>=5 cm); lifts cm: "+", ".join(f"{x['lift_cm']:.1f}" for x in r))
n=hi-lo+1; g=sum(x['lift_cm']>=5 for x in r)
sys.exit(0 if len(r)==n and 2*g>=n else 1)   # sanity bar: at least half grasp (8-10 of 10 in the validated environment; 0 of 4 with mujoco 3.15)
PY
); rec g1 $([ $? = 0 ] && echo PASS || echo FAIL) "$d"
  else rec g1 FAIL "exit=$rc, see g1.log: $(tail -2 "$OUT/g1.log" | tr '\n' ' ' | cut -c1-200)"; fi
else rec g1 SKIP "no GPU or no SONIC weights at $SONIC_WEIGHTS_SRC"; fi

echo "== e2e report"; cat "$REP"; exit $FAIL
