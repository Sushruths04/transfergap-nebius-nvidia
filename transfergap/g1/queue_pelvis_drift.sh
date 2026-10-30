#!/bin/bash
# Pre-registered run results/g1_pelvis_drift_v1: frozen hybrid controller on fresh seeds 1200-1279 (same recipe as the v7 hybrid arm).
. /ws/transfergap/envs/home_layout.sh
R=/ws/transfergap/runs/g1_cl; H=$R/pelvis_drift_v1; mkdir -p $H $R/plans; cd $HOME/transfergap_g1/g1; . $HOME/GR00T-WholeBodyControl/.venv_sim/bin/activate
P="--grasp-dz 0.03 --pitch-down -0.2 --roll -0.4"
for s in $(seq 1200 1279); do
  xy=$(python -c "from scene import sample_block_xy; print(*sample_block_xy($s))")
  python plan_reach.py --sonic-root $HOME/GR00T-WholeBodyControl --out $R/plans/cl_seed$s.npz --target-xy $xy $P >/dev/null 2>&1
  python plan_reach.py --sonic-root $HOME/GR00T-WholeBodyControl --out $R/plans/ol_seed$s.npz --target-xy $xy --stance-offset -0.075 0.005 $P >/dev/null 2>&1
done
deactivate
HY="--mode rr --kr 1 --lim 0.6 --w-rot 0.05 --tail-traj $R/plans/ol_seed{seed}.npz --tail-from lift --blend-s 1.0"
python3 run_trials.py --traj "$R/plans/cl_seed{seed}.npz" --run-dir $H/hybrid --seeds 1200-1279 --rollouts 1 --closed-loop "$HY" > $H/hybrid.out 2>&1
echo done > $H/run.done
