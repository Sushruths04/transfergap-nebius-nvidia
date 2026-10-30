#!/bin/bash
# Runs a few G1 hybrid rollouts INSIDE the unified `full` image (GPU Job). Weights are mounted from the project volume, not baked in.
# Usage (in the container): bash /ws/transfergap/runs/in_image_run.sh 1200-1202
set -uo pipefail
SEEDS=${1:-1200-1202}
VOL=/ws/transfergap
OUT=$VOL/runs/g1_cl/${OUTNAME:-in_image_v1}; mkdir -p $OUT/plans; exec > >(tee -a $OUT/job.log) 2>&1
echo "== start $(date -u) seeds=$SEEDS"; cat /etc/os-release | head -2; nvidia-smi -L || echo "NO GPU"
export HOME=/root
ln -sfn /opt/transfergap_src/transfergap $HOME/transfergap_g1
ln -sfn /opt/GR00T-WholeBodyControl $HOME/GR00T-WholeBodyControl
ln -sfn /opt/TensorRT-10.13.3.9 $HOME/TensorRT-10.13.3.9
export LD_LIBRARY_PATH=/opt/TensorRT-10.13.3.9/lib:/opt/onnxruntime/lib:${LD_LIBRARY_PATH:-} MUJOCO_GL=egl
SRC=$VOL/repo/GR00T-WholeBodyControl/gear_sonic_deploy; DST=/opt/GR00T-WholeBodyControl/gear_sonic_deploy
cp -f $SRC/policy/release/model_decoder.onnx $SRC/policy/release/model_encoder.onnx $DST/policy/release/
mkdir -p $DST/planner/target_vel/V2 && cp -f $SRC/planner/target_vel/V2/planner_sonic.onnx $DST/planner/target_vel/V2/
md5sum $DST/policy/release/model_decoder.onnx | grep -q 1d4391ad404d0ff36281abec349b23fd && md5sum $DST/policy/release/model_encoder.onnx | grep -q a21244b1cdceac9dc8625442a55d42e0 && echo "weights md5 ok" || { echo "WEIGHTS MD5 MISMATCH"; exit 2; }
echo "image checkout: $(git -C /opt/GR00T-WholeBodyControl rev-parse HEAD)"; ls /opt/GR00T-WholeBodyControl/.venv_sim/bin/python /opt/transfergap_src/transfergap/g1/run_trials.py
R=$OUT; cd $HOME/transfergap_g1/g1; . $HOME/GR00T-WholeBodyControl/.venv_sim/bin/activate
P="--grasp-dz 0.03 --pitch-down -0.2 --roll -0.4"; lo=${SEEDS%-*}; hi=${SEEDS#*-}
for s in $(seq $lo $hi); do
  xy=$(python -c "from scene import sample_block_xy; print(*sample_block_xy($s))")
  python plan_reach.py --sonic-root $HOME/GR00T-WholeBodyControl --out $R/plans/cl_seed$s.npz --target-xy $xy $P >/dev/null 2>&1
  python plan_reach.py --sonic-root $HOME/GR00T-WholeBodyControl --out $R/plans/ol_seed$s.npz --target-xy $xy --stance-offset -0.075 0.005 $P >/dev/null 2>&1
done
deactivate
HY="--mode rr --kr 1 --lim 0.6 --w-rot 0.05 --tail-traj $R/plans/ol_seed{seed}.npz --tail-from lift --blend-s 1.0"
python3 run_trials.py --traj "$R/plans/cl_seed{seed}.npz" --run-dir $R/hybrid --seeds $SEEDS --rollouts 1 --closed-loop "$HY" > $R/hybrid.out 2>&1
echo "run_trials exit=$?"; cat $R/hybrid.out | tail -5
$HOME/GR00T-WholeBodyControl/.venv_sim/bin/python $VOL/runs/drift_features.py $R/hybrid $SEEDS > $R/rows.json 2>$R/rows.err; echo "features exit=$?"
echo done > $R/in_image.done; echo "== end $(date -u)"
