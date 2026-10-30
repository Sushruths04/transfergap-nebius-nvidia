#!/bin/bash
# G1 copying the human's style (the g1_style_v1 protocol: seeds 100-109 x 3 rollouts, conditions differ only in speed)
# but run INSIDE the unified `full` image. Open-loop plan, same plan args and conditions as g1/run_style.sh.
# Usage in the image pod: OUTNAME=in_image_style_v1 bash /ws/transfergap/runs/in_image_style_run.sh
# Needs the demo plan JSON at /ws/transfergap/runs/pexels_8135753_notebook.plan.json (gitignored, copied from the laptop).
set -uo pipefail
VOL=/ws/transfergap; OUT=$VOL/runs/g1_cl/${OUTNAME:-in_image_style_v1}; mkdir -p $OUT/plans; exec > >(tee -a $OUT/job.log) 2>&1
echo "== start $(date -u)"; nvidia-smi -L || echo "NO GPU"
export HOME=/root
ln -sfn /opt/transfergap_src/transfergap $HOME/transfergap_g1; ln -sfn /opt/GR00T-WholeBodyControl $HOME/GR00T-WholeBodyControl
ln -sfn /opt/TensorRT-10.13.3.9 $HOME/TensorRT-10.13.3.9
export LD_LIBRARY_PATH=/opt/TensorRT-10.13.3.9/lib:/opt/onnxruntime/lib:${LD_LIBRARY_PATH:-} MUJOCO_GL=egl
SRC=$VOL/repo/GR00T-WholeBodyControl/gear_sonic_deploy; DST=/opt/GR00T-WholeBodyControl/gear_sonic_deploy
cp -f $SRC/policy/release/model_decoder.onnx $SRC/policy/release/model_encoder.onnx $DST/policy/release/
mkdir -p $DST/planner/target_vel/V2 && cp -f $SRC/planner/target_vel/V2/planner_sonic.onnx $DST/planner/target_vel/V2/
md5sum $DST/policy/release/model_decoder.onnx | grep -q 1d4391ad404d0ff36281abec349b23fd && md5sum $DST/policy/release/model_encoder.onnx | grep -q a21244b1cdceac9dc8625442a55d42e0 && echo "weights md5 ok" || { echo "WEIGHTS MD5 MISMATCH"; exit 2; }
DP=$VOL/runs/pexels_8135753_notebook.plan.json; [ -f $DP ] || { echo "demo plan missing"; exit 3; }
P="--stance-offset -0.075 0.005 --grasp-dz 0.03 --pitch-down -0.2 --roll -0.4 --grasp-dxy 0 0"
HUMAN=$(python3 -c "import json;print(json.load(open('$DP'))['timing_scale'])"); echo "human timing_scale=$HUMAN"
cd $HOME/transfergap_g1/g1; . $HOME/GR00T-WholeBodyControl/.venv_sim/bin/activate
for s in $(seq 100 109); do
  xy=$(python -c "from scene import sample_block_xy; print(*sample_block_xy($s))")
  for c in human:$HUMAN cap3:3.0 nominal:1.0; do
    python plan_reach.py --sonic-root $HOME/GR00T-WholeBodyControl --out $OUT/plans/${c%%:*}_seed$s.npz --target-xy $xy $P --demo-plan $DP --timing-scale ${c##*:} > /dev/null 2>&1
  done
done
deactivate
for c in nominal cap3 human; do
  python3 run_trials.py --traj "$OUT/plans/${c}_seed{seed}.npz" --run-dir "$OUT/g1_style_$c" --seeds 100-109 --rollouts 3 > $OUT/$c.out 2>&1
  echo "$c run_trials exit=$? $(date -u)"
done
echo done > $OUT/in_image_style.done; echo "== end $(date -u)"
