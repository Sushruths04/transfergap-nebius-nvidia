#!/bin/bash
# Fast SAM 3D Body vs RTMW3D on the cluster: pose on the author's clip and on the internet clip RTMW3D refused, then the one-command pipeline on each.
# Run inside the tg-dev pod:  bash /ws/transfergap/envs/fsam_compare.sh > /ws/transfergap/fsam_compare.log 2>&1
set -uo pipefail
R=/ws/transfergap/repo/Fast-SAM-3D-Body; E=/ws/transfergap/envs/fsam; C=/ws/transfergap/ctx_unified_r6; O=/ws/transfergap/fsam_cmp
export HF_HOME=/ws/transfergap/cache/huggingface TORCH_HOME=/ws/transfergap/cache/torch MPLCONFIGDIR=/tmp/mpl YOLO_CONFIG_DIR=/tmp/yolo_cfg
mkdir -p $O
pose() {  # video out
  ( cd $R && PYTHONPATH=$R $E/bin/python $C/transfergap/demo/tools/fsam_export_joints.py --video "$1" --out "$2" 2>&1 | tr '\r' '\n' | grep -E "^wrote|Traceback|Error" ) ; echo "pose exit for $2: done"
}
pose /ws/transfergap/demos/user_clip.mp4 $O/user_fsam.npz
pose /ws/transfergap/demos/pexels_8135753_packing_box.mp4 $O/pexels_fsam.npz
cd $C && export MUJOCO_GL=egl PYTHONPATH=$C OMP_NUM_THREADS=1
PY=/ws/transfergap/envs/render/bin/python
echo "== pipeline: author's clip, fsam joints"
$PY -m transfergap.pipeline --joints $O/user_fsam.npz --window 60 206 --events 102 166 --shoulder-width-m 0.44 --robots ur5e ur10e kairos --out $O/pipe_user 2>&1 | tail -3
echo "== pipeline: internet clip (RTMW3D refused it), fsam joints"
$PY -m transfergap.pipeline --joints $O/pexels_fsam.npz --window 195 249 --events 212 233 --robots ur5e ur10e --out $O/pipe_pexels 2>&1 | tail -3
echo ALL DONE
