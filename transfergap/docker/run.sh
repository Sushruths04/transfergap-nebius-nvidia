#!/bin/bash
# Run the image on any NVIDIA GPU host: host networking (the live mode uses localhost ports 5556/5557/8090-8093 and
# DDS on loopback), the HF cache on the host (weights download once, with your own token), and runs/ for results.
#   HF_TOKEN=... bash docker/run.sh [command]
set -euo pipefail
mkdir -p "$HOME/.cache/huggingface" "$HOME/tg_runs"
exec docker run --rm -it --gpus all -e NVIDIA_DRIVER_CAPABILITIES=all --network host --ipc host \
  -e HF_TOKEN="${HF_TOKEN:-}" \
  -v "$HOME/.cache/huggingface:/home/ubuntu/.cache/huggingface" \
  -v "$HOME/tg_runs:/home/ubuntu/live_runs" \
  ${IMAGE:-transfergap-live} "${@:-bash}"
