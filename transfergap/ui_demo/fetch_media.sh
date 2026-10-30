#!/bin/bash
# Copy the showcase videos from the cluster volume into ui_demo/media (they are not in git), make them stream-friendly, rebuild data.js.
#   bash ui_demo/fetch_media.sh [REMOTE_DIR]      default /ws/transfergap/showcase_out_r6
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p media
S=${1:-/ws/transfergap/showcase_out_r6}
P=$(kubectl get pods -n isaac-sim -l app=tg-dev -o name | head -1 | cut -d/ -f2)
for f in human/human_overlay.mp4 human/human_metrics.npz g1/seed0_r0.mp4 robots/ur5e_raw_seed1001.mp4 robots/ur5e_stack_seed1001.mp4 robots/ur10e_raw_seed1001.mp4 robots/ur10e_stack_seed1001.mp4 robots/kairos_mobile_raw_seed1001.mp4 robots/kairos_mobile_stack_seed1001.mp4; do
  kubectl cp "isaac-sim/$P:$S/$f" "media/$(basename "$f")"
done
kubectl cp "isaac-sim/$P:$S/TransferGap_demo_v2.mp4" media/full_demo.mp4
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
for f in media/*.mp4; do "$FF" -loglevel error -y -i "$f" -c copy -movflags +faststart "$f.tmp.mp4" && mv "$f.tmp.mp4" "$f"; done
python3 build.py
