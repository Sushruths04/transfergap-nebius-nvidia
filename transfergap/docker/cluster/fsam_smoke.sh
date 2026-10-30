#!/bin/bash
# Fast SAM 3D Body smoke test on the cluster (inside the tg-dev pod, GPU free for it): pose on the first N frames of the author's clip.
#   bash fsam_smoke.sh [N_FRAMES] [OUT_NPZ]
set -uo pipefail
N=${1:-30}; OUT=${2:-/ws/transfergap/fsam_smoke/clip_fsam_joints.npz}
R=/ws/transfergap/repo/Fast-SAM-3D-Body; E=/ws/transfergap/envs/fsam
export HF_HOME=/ws/transfergap/cache/huggingface TORCH_HOME=/ws/transfergap/cache/torch
export MPLCONFIGDIR=/tmp/mpl YOLO_CONFIG_DIR=/tmp/yolo_cfg
mkdir -p "$(dirname "$OUT")" $R/checkpoints/yolo
cd $R
if [ ! -s checkpoints/yolo/yolo11m-pose.pt ]; then
  for tag in v8.3.0 v8.2.0 v0.0.0; do
    curl -sfL -o checkpoints/yolo/yolo11m-pose.pt "https://github.com/ultralytics/assets/releases/download/$tag/yolo11m-pose.pt" && break
  done
fi
ls -la checkpoints/yolo
export PYTHONPATH=$R
$E/bin/python /ws/transfergap/ctx_unified_r6/transfergap/demo/tools/fsam_export_joints.py --video /ws/transfergap/demos/user_clip.mp4 --out "$OUT" --max-frames "$N"
echo "exit $?"
