#!/bin/bash
# Same internet-clip pipeline run as fsam_compare.sh but WITHOUT the shoulder-width rescale (the 2026-10 bake-off used Fast SAM joints as they come).
set -uo pipefail
C=/ws/transfergap/ctx_unified_r6; O=/ws/transfergap/fsam_cmp
cd $C && export MUJOCO_GL=egl PYTHONPATH=$C OMP_NUM_THREADS=1
PY=/ws/transfergap/envs/render/bin/python
$PY -m transfergap.pipeline --joints $O/pexels_fsam.npz --window 195 249 --events 212 233 --shoulder-width-m 0 --robots ur5e ur10e --out $O/pipe_pexels_noscale 2>&1 | tail -3
$PY -m transfergap.pipeline --joints $O/user_fsam.npz --window 60 206 --events 102 166 --shoulder-width-m 0 --robots ur5e ur10e --out $O/pipe_user_noscale 2>&1 | tail -3
echo NOSCALE DONE
