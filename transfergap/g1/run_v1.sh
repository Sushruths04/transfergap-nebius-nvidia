#!/bin/bash
# Reproduce results/g1_contact_v1 on the GPU VM (code synced to ~/transfergap_g1/g1).
# Plans the motions (kinematics only), then runs 10 seeds x 3 rollouts for each condition.
set -e
G1=$HOME/transfergap_g1/g1
RUNS=$HOME/transfergap_g1/runs
P="--stance-offset -0.075 0.005 --grasp-dz 0.03 --pitch-down -0.2 --roll -0.4"
mkdir -p "$RUNS/plans"
cd "$G1"
source "$HOME/GR00T-WholeBodyControl/.venv_sim/bin/activate"
python plan_reach.py --out "$RUNS/plans/reach_nominal.npz" $P > /dev/null
for s in $(seq 100 109); do
  xy=$(python -c "from scene import sample_block_xy; print(*sample_block_xy($s))")
  python plan_reach.py --out "$RUNS/plans/reach_true_seed$s.npz" --target-xy $xy $P > /dev/null
done
deactivate
python3 "$G1/run_trials.py" --traj "$RUNS/plans/reach_nominal.npz" --run-dir "$RUNS/g1_v1_nominal" \
  --seeds 100-109 --rollouts 3
python3 "$G1/run_trials.py" --traj "$RUNS/plans/reach_true_seed{seed}.npz" --run-dir "$RUNS/g1_v1_true" \
  --seeds 100-109 --rollouts 3
