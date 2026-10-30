#!/bin/bash
# Stage a trimmed copy of the verified VM environments as the docker build context (run ON the VM).
# Drops caches, outputs, docs/media, conda package cache and every model weight (re-downloaded at run time).
set -euo pipefail
CTX=${CTX:-$HOME/tg_docker_ctx}
H=$CTX/home
mkdir -p "$H"
R="rsync -a --delete --exclude __pycache__ --exclude .git"
$R --exclude outputs --exclude '*.mp4' --exclude '*.mov' --exclude '*.avi' "$HOME/GEM-X" "$H/"
$R --exclude media --exclude docs --exclude '*.mp4' "$HOME/GR00T-WholeBodyControl" "$H/"
$R --exclude samples --exclude data --exclude doc "$HOME/TensorRT-10.13.3.9" "$H/"
$R --exclude 'checkpoints/sam-3d-body-*' --exclude output "$HOME/Fast-SAM-3D-Body" "$H/"
mkdir -p "$H/miniforge3/envs" "$H/.local/share"
$R --exclude pkgs --exclude envs "$HOME/miniforge3" "$H/"
$R "$HOME/miniforge3/envs/fast_sam_3d_body" "$H/miniforge3/envs/"
$R "$HOME/.local/share/uv" "$H/.local/share/"
$R "$HOME/.local/bin" "$H/.local/"
$R --exclude runs --exclude '*.mp4' --exclude '*.plan.json' "$HOME/transfergap_g1" "$H/"
du -sh "$CTX"
