#!/bin/bash
# The G1 mimics a recorded person INSIDE the unified image (GPU cluster Job). SONIC weights are copied from $SONIC_WEIGHTS_SRC (md5-checked), as in image_g1_trials.sh.
#   JOINTS=/ws/transfergap/demos/user_clip_rtmw3d_joints.npz OUT=/ws/transfergap/g1_mimic_out SONIC_WEIGHTS_SRC=... bash g1/image_g1_mimic.sh
set -uo pipefail
SRC=${SONIC_WEIGHTS_SRC:?}; DST=/opt/GR00T-WholeBodyControl/gear_sonic_deploy; J=${JOINTS:?}; OUT=${OUT:?}; mkdir -p "$OUT"
export HOME=${HOME:-/root}; [ -w "$HOME" ] || export HOME=/tmp/home && mkdir -p $HOME
ln -sfn ${TG_CODE:-/opt/transfergap_src/transfergap} $HOME/transfergap_g1; ln -sfn /opt/GR00T-WholeBodyControl $HOME/GR00T-WholeBodyControl
ln -sfn /opt/TensorRT-10.13.3.9 $HOME/TensorRT-10.13.3.9
export LD_LIBRARY_PATH=/opt/TensorRT-10.13.3.9/lib:/opt/onnxruntime/lib:${LD_LIBRARY_PATH:-} MUJOCO_GL=egl
cp -f $SRC/policy/release/model_decoder.onnx $SRC/policy/release/model_encoder.onnx $DST/policy/release/
mkdir -p $DST/planner/target_vel/V2 && cp -f $SRC/planner/target_vel/V2/planner_sonic.onnx $DST/planner/target_vel/V2/
md5sum $DST/policy/release/model_decoder.onnx | grep -q 1d4391ad404d0ff36281abec349b23fd && md5sum $DST/policy/release/model_encoder.onnx | grep -q a21244b1cdceac9dc8625442a55d42e0 || { echo "WEIGHTS MD5 MISMATCH"; exit 2; }
echo "weights md5 ok"
cd $HOME/transfergap_g1
python3 live/g1_mimic_run.py --joints "$J" --run-dir "$OUT" ${FPS:+--fps $FPS}
