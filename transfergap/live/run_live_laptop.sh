#!/bin/bash
# Real-time session, laptop side. The GPU VM must already be RUNNING (started separately, with the user's approval);
# this script never starts or stops the VM.
#   bash live/run_live_laptop.sh <vm-ip> [--no-g1] [--robot ur10e] [--grip left_up] [--source 0]
# Run from transfergap/. Steps: sync code -> webcam MJPEG on 127.0.0.1:8090 -> one SSH connection carrying the
# webcam to the VM (-R 8090) and the three views back (-L 8091 arm+viewer, 8092 camera, 8093 G1) -> start the VM
# side (live/run_live_vm.py) -> open the viewer. Ctrl-C stops everything (and the VM-side processes).
set -euo pipefail
VM=${1:?usage: run_live_laptop.sh <vm-ip> [run_live_vm.py args] [--source N]}
shift
SRC=0
ARGS=()
while [ $# -gt 0 ]; do
  if [ "$1" = "--source" ]; then SRC=$2; shift 2; else ARGS+=("$1"); shift; fi
done
KEY=~/.ssh/transfergap_gpu
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "ubuntu@$VM")
echo "[1/5] sync code to the VM"
rsync -az -e "ssh -i $KEY" --exclude __pycache__ g1 live ubuntu@"$VM":transfergap_g1/
rsync -az -e "ssh -i $KEY" --exclude __pycache__ --exclude 'assets/menagerie/*/.git' -L transfergap ubuntu@"$VM":transfergap_g1/
echo "[2/5] webcam $SRC -> http://127.0.0.1:8090/stream.mjpg"
python3 live/cam_server.py --source "$SRC" --port 8090 --width 640 --fps 12 --quality 60 &
CAM=$!
cleanup() {
  "${SSH[@]}" "python3 ~/transfergap_g1/live/run_live_vm.py --stop" || true
  kill $CAM $TUN 2>/dev/null || true
  pkill -P $TUN 2>/dev/null || true
}
trap cleanup EXIT
sleep 2
echo "[3/5] tunnels"
# the tunnel reconnects by itself (a dropped connection must not end the session; only Ctrl-C does)
( while true; do "${SSH[@]}" -N -o ServerAliveInterval=5 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=no \
    -R 8090:127.0.0.1:8090 -L 8091:127.0.0.1:8091 -L 8092:127.0.0.1:8092 -L 8093:127.0.0.1:8093; sleep 2; done ) &
TUN=$!
sleep 3
echo "[4/5] VM side (G1 start-up takes ~2 min)"
"${SSH[@]}" "rm -f /tmp/live-orch.log; tmux kill-session -t =live-orch 2>/dev/null; tmux new-session -d -s live-orch 'python3 ~/transfergap_g1/live/run_live_vm.py --supervise ${ARGS[*]:-} 2>&1 | tee /tmp/live-orch.log'; \
  for i in \$(seq 600); do grep -q 'live session up' /tmp/live-orch.log 2>/dev/null && break; grep -m1 -E 'Error|Timeout' /tmp/live-orch.log && exit 1; sleep 1; done; tail -1 /tmp/live-orch.log"
echo "[5/5] viewer: http://127.0.0.1:8091/  — stand ~2 m from the camera, right hand still for 2 s to calibrate"
xdg-open http://127.0.0.1:8091/ >/dev/null 2>&1 || true
echo "session running; Ctrl-C here ends it (and saves the recording on the VM)"
wait $CAM
