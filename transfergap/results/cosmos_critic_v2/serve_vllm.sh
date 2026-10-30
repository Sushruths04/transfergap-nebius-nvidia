#!/bin/bash
# Cosmos-Reason2-8B critic server (vLLM). Bound to localhost; reach it through an SSH tunnel.
# Serve flags follow github.com/nvidia-cosmos/cosmos-reason2; GPU share capped at 0.45 (GPU is shared).
# --limit-mm-per-prompt caps the video size used for memory profiling (our clips: 640x480, <= 64 frames at fps 4).
source ~/cosmos/.venv/bin/activate
exec vllm serve nvidia/Cosmos-Reason2-8B \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 16384 \
  --media-io-kwargs "{\"video\": {\"num_frames\": -1}}" \
  --reasoning-parser qwen3 \
  --limit-mm-per-prompt "{\"image\": 0, \"video\": {\"count\": 1, \"num_frames\": 64, \"width\": 640, \"height\": 480}}" \
  --max-num-seqs 8 \
  --gpu-memory-utilization 0.45
