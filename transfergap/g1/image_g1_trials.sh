#!/bin/bash
# G1 closed-loop hybrid rollouts inside the unified image, using only image-local code (unlike g1/in_image_run.sh, which reads helper
# scripts from the cluster volume). SONIC weights are NOT in the image: they are copied from $SONIC_WEIGHTS_SRC (a gear_sonic_deploy folder with
# policy/release/model_{decoder,encoder}.onnx and planner/target_vel/V2/planner_sonic.onnx) after an md5 check.
# Usage: SONIC_WEIGHTS_SRC=... G1_OUT_ROOT=... OUTNAME=e2e_g1 bash g1/image_g1_trials.sh 1200-1201
set -uo pipefail
SEEDS=${1:-1200-1201}; OUT=${G1_OUT_ROOT:?}/${OUTNAME:-e2e_g1}; mkdir -p $OUT/plans
SRC=${SONIC_WEIGHTS_SRC:?}; DST=/opt/GR00T-WholeBodyControl/gear_sonic_deploy
export HOME=${HOME:-/root}; [ -w "$HOME" ] || export HOME=/tmp/home && mkdir -p $HOME
ln -sfn /opt/transfergap_src/transfergap $HOME/transfergap_g1; ln -sfn /opt/GR00T-WholeBodyControl $HOME/GR00T-WholeBodyControl
ln -sfn /opt/TensorRT-10.13.3.9 $HOME/TensorRT-10.13.3.9
export LD_LIBRARY_PATH=/opt/TensorRT-10.13.3.9/lib:/opt/onnxruntime/lib:${LD_LIBRARY_PATH:-} MUJOCO_GL=egl
cp -f $SRC/policy/release/model_decoder.onnx $SRC/policy/release/model_encoder.onnx $DST/policy/release/
mkdir -p $DST/planner/target_vel/V2 && cp -f $SRC/planner/target_vel/V2/planner_sonic.onnx $DST/planner/target_vel/V2/
md5sum $DST/policy/release/model_decoder.onnx | grep -q 1d4391ad404d0ff36281abec349b23fd && md5sum $DST/policy/release/model_encoder.onnx | grep -q a21244b1cdceac9dc8625442a55d42e0 || { echo "WEIGHTS MD5 MISMATCH"; exit 2; }
echo "weights md5 ok"
cd $HOME/transfergap_g1/g1; . $HOME/GR00T-WholeBodyControl/.venv_sim/bin/activate
P="--grasp-dz 0.03 --pitch-down -0.2 --roll -0.4"; lo=${SEEDS%-*}; hi=${SEEDS#*-}
for s in $(seq $lo $hi); do
  xy=$(python -c "from scene import sample_block_xy; print(*sample_block_xy($s))")
  python plan_reach.py --sonic-root $HOME/GR00T-WholeBodyControl --out $OUT/plans/cl_seed$s.npz --target-xy $xy $P >/dev/null 2>&1 || exit 3
  python plan_reach.py --sonic-root $HOME/GR00T-WholeBodyControl --out $OUT/plans/ol_seed$s.npz --target-xy $xy --stance-offset -0.075 0.005 $P >/dev/null 2>&1 || exit 3
done
deactivate
HY="--mode rr --kr 1 --lim 0.6 --w-rot 0.05 --tail-traj $OUT/plans/ol_seed{seed}.npz --tail-from lift --blend-s 1.0"
python3 run_trials.py --traj "$OUT/plans/cl_seed{seed}.npz" --run-dir $OUT/hybrid --seeds $SEEDS --rollouts 1 --closed-loop "$HY" > $OUT/hybrid.out 2>&1 || exit 4
$HOME/GR00T-WholeBodyControl/.venv_sim/bin/python $HOME/transfergap_g1/g1/drift_features.py $OUT/hybrid $SEEDS > $OUT/rows.json 2>$OUT/rows.err || exit 5
echo done
