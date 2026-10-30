#!/bin/bash
# Pod side of the cluster real-time mode (arm only, no G1): frame relay :8090 -> RTMW3D hands :8092 -> arm viewer :8091.
#   bash live/cluster_session.sh start [--robot ur5e|ur10e|kairos]     bash live/cluster_session.sh stop|status
# Run from transfergap/ in the pod or the image. Needs $TG_POSE_PY (RTMW3D venv) and the sim python in $TG_SIM_PY (default python).
# Processes are tracked by PID files in $TG_LIVE_RUN (default /tmp/tg_live); stop never uses pattern kills.
set -uo pipefail
RUN=${TG_LIVE_RUN:-/tmp/tg_live}; SIMPY=${TG_SIM_PY:-python}; POSEPY=${TG_POSE_PY:?set TG_POSE_PY}
export MUJOCO_GL=${MUJOCO_GL:-egl} PYTHONPATH=${PYTHONPATH:-.}
cmd=${1:-status}; shift || true
case "$cmd" in
  start)
    mkdir -p "$RUN"; ROBOT=ur5e
    while [ $# -gt 0 ]; do if [ "$1" = "--robot" ]; then ROBOT=$2; shift; fi; shift; done
    "$0" stop >/dev/null 2>&1
    nohup $SIMPY live/frame_relay.py --port 8090 > "$RUN/relay.log" 2>&1 & echo $! > "$RUN/relay.pid"
    nohup $POSEPY live/hands_pub.py --estimator rtmw3d --port 8092 --source http://127.0.0.1:8090/stream.mjpg > "$RUN/hands.log" 2>&1 & echo $! > "$RUN/hands.pid"
    nohup $SIMPY live/arm_live.py --robot "$ROBOT" --port 8091 --hands http://127.0.0.1:8092/hands.jsonl --out "$RUN/session" ${TG_ARM_EXTRA:-} > "$RUN/arm.log" 2>&1 & echo $! > "$RUN/arm.pid"
    nohup $SIMPY live/hand_live.py --model "${TG_HAND_MODEL:-/ws/transfergap/hand_v1/allegro/scene_right.xml}" --port 8094 --hands http://127.0.0.1:8092/hands.jsonl > "$RUN/handik.log" 2>&1 & echo $! > "$RUN/handik.pid"
    sleep 2; echo "started relay $(cat $RUN/relay.pid) hands $(cat $RUN/hands.pid) arm $(cat $RUN/arm.pid) (robot $ROBOT)";;
  stop)
    for n in handik arm hands relay; do
      if [ -f "$RUN/$n.pid" ]; then kill -INT "$(cat "$RUN/$n.pid")" 2>/dev/null; fi
    done
    sleep 3
    for n in handik arm hands relay; do
      if [ -f "$RUN/$n.pid" ]; then kill "$(cat "$RUN/$n.pid")" 2>/dev/null; rm -f "${RUN:?}/${n:?}.pid"; fi
    done; echo stopped;;
  status)
    for n in relay hands arm handik; do
      p=$(cat "$RUN/$n.pid" 2>/dev/null); if [ -n "${p:-}" ] && kill -0 "$p" 2>/dev/null; then echo "$n up ($p)"; else echo "$n DOWN"; fi
    done
    curl -s -m 2 http://127.0.0.1:8090/status; echo;;
  *) echo "usage: cluster_session.sh start|stop|status"; exit 2;;
esac
