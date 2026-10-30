#!/bin/bash
# Is the bake-off discrepancy the object-height rule? Same Fast SAM joints, pipeline with --object-height lowest_hand (the bake-off default) on the internet clip.
set -uo pipefail
C=/ws/transfergap/ctx_unified_r6; O=/ws/transfergap/fsam_cmp
cd $C && export MUJOCO_GL=egl PYTHONPATH=$C OMP_NUM_THREADS=1
PY=/ws/transfergap/envs/render/bin/python
$PY -m transfergap.pipeline --joints $O/pexels_fsam.npz --window 195 249 --events 212 233 --object-height lowest_hand --shoulder-width-m 0 --robots ur5e ur10e --out $O/pipe_pexels_lowesthand 2>&1 | tail -2
grep "^| demo\|^| rollouts" $O/pipe_pexels_lowesthand/REPORT.md | cut -c1-300
echo OBJH DONE
