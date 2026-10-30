#!/bin/bash
# The single launcher. Same image and same tasks everywhere; --where only changes how the container is started.
#   bash docker/launch.sh [--where local|cluster] [--image IMG] [--gpu] [--data DIR] [--kairos DIR | --kairos-assets DIR] [--demos DIR] TASK [ARGS]
#   TASK: test | perception-dev --robot R | style-dev | info | shell | any command
# local    docker run on this machine (laptop, or a Nebius VM with Docker + nvidia-container-toolkit). Add --gpu for GPU/EGL.
# cluster  prints (or with --apply creates) a Kubernetes Job for the GPU cluster. The volume there is single-attach: the
#          idle dev pod must be scaled to 0 first, otherwise the Job stays in ContainerCreating (Multi-Attach error).
# Nothing here spends money or publishes anything: a Nebius run is just `--where local` on a VM you started yourself.
set -euo pipefail
WHERE=local; IMAGE=${IMAGE:-transfergap:arm}; GPU=0; APPLY=0
DATA=${TG_DATA:-$HOME/tg_data}; KAIROS=""; KASSETS=""; DEMOS=""; NS=${TG_NAMESPACE:-isaac-sim}; PVC=${TG_PVC:-tg-dev-data}
while [ $# -gt 0 ]; do case "$1" in
  --where) WHERE=$2; shift 2;; --image) IMAGE=$2; shift 2;; --gpu) GPU=1; shift;; --apply) APPLY=1; shift;;
  --data) DATA=$2; shift 2;; --kairos) KAIROS=$2; shift 2;; --demos) DEMOS=$2; shift 2;; --kairos-assets) KASSETS=$2; shift 2;; *) break;; esac; done
[ $# -ge 1 ] || { sed -n 2,11p "$0"; exit 2; }
case "$WHERE" in
local)
  mkdir -p "$DATA"
  args=(--rm -v "$DATA:/data" -u "$(id -u):$(id -g)" -e HOME=/tmp)
  [ "$GPU" = 1 ] && args+=(--gpus all -e NVIDIA_DRIVER_CAPABILITIES=all) || args+=(-e MUJOCO_GL=osmesa -e PYOPENGL_PLATFORM=osmesa)
  [ -n "$KAIROS" ] && args+=(-v "$KAIROS:/kairos_src:ro")
  [ -n "$KASSETS" ] && args+=(-v "$KASSETS:/opt/transfergap_src/transfergap/transfergap/sim/assets/kairos:ro")
  [ -n "$DEMOS" ] && args+=(-v "$DEMOS:/opt/transfergap_src/transfergap/runs/demos:ro")
  exec docker run "${args[@]}" "$IMAGE" "$@" ;;
cluster)
  name="tg-$(echo "$1" | tr -c 'a-z0-9\n' '-' | cut -c1-20)-$(date +%H%M%S)"
  cmd=$(printf '"%s", ' "$@"); cmd="[${cmd%, }]"
  manifest=$(cat <<YAML
apiVersion: batch/v1
kind: Job
metadata: {name: $name, namespace: $NS, labels: {project: transfergap}}
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 86400
  template:
    metadata: {labels: {project: transfergap}}
    spec:
      restartPolicy: Never
      containers:
      - name: tg
        image: $IMAGE
        args: $cmd
        env: [{name: MUJOCO_GL, value: egl}, {name: NVIDIA_DRIVER_CAPABILITIES, value: all}]
        resources: {limits: {nvidia.com/gpu: ${TG_GPUS:-1}}}
        volumeMounts: [{name: data, mountPath: /data}]
      volumes: [{name: data, persistentVolumeClaim: {claimName: $PVC}}]
YAML
)
  if [ "$APPLY" = 1 ]; then echo "$manifest" | kubectl apply -f -; else echo "$manifest"; echo "# not applied (add --apply)" >&2; fi ;;
*) echo "unknown --where $WHERE" >&2; exit 2 ;;
esac
