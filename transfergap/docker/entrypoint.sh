#!/bin/bash
# Container entrypoint: the same tasks run identically wherever the image runs (laptop, cluster Job, Nebius VM).
#   tg-entrypoint test
#   tg-entrypoint perception-dev   --robot ur5e|ur10e|kairos [perception_hard_eval args]
#   tg-entrypoint style-dev        [style_perception args]            (needs the demo mounted at runs/demos)
#   tg-entrypoint perceive --video V --out joints.npz   (RTMW3D pose, GPU)
#   tg-entrypoint pipeline --video V --out DIR [--window A B --events G R] [--robots ...]   (video -> robots, see transfergap/pipeline.py)
#   tg-entrypoint showcase --video V --out DIR [--window A B --events G R --shoulder-width-m M]   ONE command: pose, robots, measurements, G1 mimic, integrated video (docker/showcase.sh)
#   tg-entrypoint e2e              end-to-end check (tests, arm reproduction, perception, style, G1); see docker/e2e.sh
#   tg-entrypoint info | shell | <any command>
# Mounts: /data (outputs go to $TG_OUT=/data/out), /kairos_src (optional: KAIROS gripper description, "urdf/gripper").
set -euo pipefail
cd /opt/transfergap_src/transfergap
mkdir -p "$TG_OUT"
A=transfergap/sim/assets/kairos
if [ ! -d "$A" ] && [ -d /kairos_src ]; then
  python -m transfergap.sim.kairos_model prepare --src /kairos_src --out "$A" >/dev/null
fi
# RTMW3D weights: reuse a cached copy on the mounted volume when present (else they are fetched on first use)
if [ -d "${TG_CACHE:-/data/cache}/rtmpose3d_ckpt" ]; then mkdir -p /root/.cache/rtmpose3d && ln -sfn "${TG_CACHE:-/data/cache}/rtmpose3d_ckpt" /root/.cache/rtmpose3d/checkpoints; fi
task=${1:-test}; shift || true
case "$task" in
  test) exec python -m unittest discover -s tests -q ;;
  perception-dev) exec python -m transfergap.sim.perception_hard_eval --split dev --out "$TG_OUT/perception_hard_dev" "$@" ;;
  style-dev) exec python -m transfergap.sim.style_perception dev --out "$TG_OUT/style_perception_dev" "$@" ;;
  perceive) exec "$TG_POSE_PY" transfergap/demo/tools/rtmw3d_export_joints.py "$@" ;;
  pipeline) exec python -m transfergap.pipeline "$@" ;;
  e2e) exec bash docker/e2e.sh ;;
  showcase) exec bash docker/showcase.sh "$@" ;;
  info) python - <<PY
import mujoco, numpy, platform, os
print("python", platform.python_version(), "numpy", numpy.__version__, "mujoco", mujoco.__version__, "MUJOCO_GL", os.environ.get("MUJOCO_GL"))
from transfergap.sim import scene
print("kairos assets:", "present" if scene.robot_ready("kairos") else "absent (mount /kairos_src)", "| ur5e:", scene.robot_ready("ur5e"))
try:
    r = mujoco.Renderer(scene.Scene(0, "ur5e").model, 64, 64); r.close(); print("EGL render: ok")
except Exception as e:
    print("EGL render: FAILED", str(e)[:100])
PY
  ;;
  shell) exec bash ;;
  *) exec "$task" "$@" ;;
esac
