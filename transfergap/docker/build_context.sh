#!/bin/bash
# Stage the docker build context from the COMMITTED code only (git archive): no results, runs, demos or secrets.
#   bash docker/build_context.sh /tmp/tg_ctx && docker build --target arm -f /tmp/tg_ctx/transfergap/docker/Dockerfile.unified \
#        -t transfergap:arm /tmp/tg_ctx/transfergap     (build from the transfergap/ folder of the context)
set -euo pipefail
OUT=${1:?usage: build_context.sh OUTDIR}
rm -rf "$OUT"; mkdir -p "$OUT"
ROOT=$(git rev-parse --show-toplevel)
# code + tests + small frozen-protocol/result files the tests read; no videos/arrays/jsonl, no large new run folders
git -C "$ROOT" archive HEAD transfergap/transfergap transfergap/tests transfergap/g1 transfergap/docker transfergap/live \
    transfergap/app transfergap/configs transfergap/scripts transfergap/examples transfergap/results ':(exclude)*.mp4' ':(exclude)*.npz' \
    ':(exclude)*.png' ':(exclude)transfergap/results/*.jsonl' ':(exclude)transfergap/results/perception_hard_*' \
    ':(exclude)transfergap/results/perception_calib_map_v1' ':(exclude)transfergap/results/g1_closed_loop_v7' | tar -x -C "$OUT"
echo "context at $OUT/transfergap from commit $(git -C "$ROOT" rev-parse --short HEAD)"
