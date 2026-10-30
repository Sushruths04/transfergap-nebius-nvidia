#!/bin/bash
# Real-time session on the GPU cluster (no VM, no SSH): laptop webcam -> `kubectl port-forward` -> pod (RTMW3D -> arm sim) -> viewer.
#   bash live/run_live_cluster.sh [--robot ur5e|ur10e|kairos] [--source 0|file.mp4] [--seconds N]
# Run from transfergap/. Syncs the code to the pod first. The pod needs the one GPU (tg-dev holds it).
# Ctrl-C stops the session in the pod and the port-forwards. Viewer: http://127.0.0.1:8091/   (stand ~2 m from the camera, right hand still 2 s)
set -euo pipefail
NS=${TG_NAMESPACE:-isaac-sim}; TARGET=${TG_POD_TARGET:-deploy/tg-dev}; CODE=${TG_POD_CODE:-/ws/transfergap/ctx_cam/transfergap}
ROBOT=ur5e; SRC=0; SECS=0; AUTOCAL=0; ARMX=""
while [ $# -gt 0 ]; do case "$1" in --robot) ROBOT=$2; shift 2;; --source) SRC=$2; shift 2;; --seconds) SECS=$2; shift 2;; --autocalib) AUTOCAL=1; shift;; --orient) ARMX="$ARMX --orient"; shift;; --orient-sign) ARMX="$ARMX --orient-sign $2"; shift 2;; *) echo "unknown $1"; exit 2;; esac; done
POSE=/ws/transfergap/envs/rtmw3d/bin/python; SIM=/ws/transfergap/envs/tg/bin/python
ENVS="TG_ARM_EXTRA='$ARMX' TG_POSE_PY=$POSE TG_SIM_PY=$SIM PYTHONPATH=. HF_HOME=/ws/transfergap/cache/huggingface"
echo "[1/4] sync live/ and transfergap/ to the pod ($CODE)"
tar czf - --exclude=__pycache__ --exclude='transfergap/sim/assets' live transfergap | kubectl exec -i -n "$NS" "$TARGET" -- sh -c "cd $CODE && tar xzf -"
echo "[2/4] start the pod side"
kubectl exec -n "$NS" "$TARGET" -- sh -c "cd $CODE && $ENVS bash live/cluster_session.sh start --robot $ROBOT"
echo "[3/4] port-forwards: relay 8095, viewer 8091, camera view 8092"
# the forward restarts by itself if it drops (a dropped forward must not end the session; only Ctrl-C does)
setsid bash -c 'while true; do kubectl port-forward -n "$0" "$1" 8095:8090 8091:8091 8092:8092 8094:8094 >/dev/null 2>&1; sleep 1; done' "$NS" "$TARGET" & PF=$!
cleanup() { kill ${WARN:-0} 2>/dev/null || true; pkill -P $PF 2>/dev/null || true; kill $PF 2>/dev/null || true; kubectl exec -n "$NS" "$TARGET" -- sh -c "cd $CODE && $ENVS bash live/cluster_session.sh stop" || true; }
trap cleanup EXIT
for i in $(seq 60); do curl -s -m 2 http://127.0.0.1:8095/status >/dev/null 2>&1 && break; sleep 1; done
echo "[4/4] viewer http://127.0.0.1:8091/ ; pushing camera $SRC (Ctrl-C ends)"
xdg-open http://127.0.0.1:8091/ >/dev/null 2>&1 || true
# --autocalib: send the two calibration commands the viewer buttons send (for a recorded-clip dry run; with a live person do them by hand)
if [ "$AUTOCAL" = 1 ]; then ( sleep 8; curl -s -m 5 http://127.0.0.1:8091/cmd/g1calib >/dev/null; sleep 8; curl -s -m 5 http://127.0.0.1:8091/cmd/tablecalib >/dev/null ) & fi
# warn when the pose stage sees nobody (a 15-minute session once ran with 0 poses and no message)
( sleep 20; while sleep 15; do h=$(curl -s -m 3 http://127.0.0.1:8092/hands.json); case "$h" in *'"seq"'*) ;; *) echo "[warn] no person detected: stand 1.5-2 m from the camera, upper body fully in view, good light";; esac; done ) & WARN=$!
EXTRA=(); [ "$SECS" != 0 ] && EXTRA+=(--seconds "$SECS"); [[ "$SRC" == *.mp4 ]] && EXTRA+=(--loop)
python3 live/push_cam.py --source "$SRC" --url http://127.0.0.1:8095/push "${EXTRA[@]}"
