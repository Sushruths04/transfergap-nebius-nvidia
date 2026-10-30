#!/bin/bash
# G1 copying the human's style (retargeted path of a real human demo), on the GPU VM.
# Code synced to ~/transfergap_g1/{g1,transfergap}; demo plan JSON at ~/transfergap_g1/demo_plan.json.
# Plan args frozen in results/g1_contact_v1/protocol.json; per-seed true block target (perception oracle);
# conditions differ only in execution speed: human pace, speed cap 3x, robot nominal.
set -e
G1=$HOME/transfergap_g1/g1
RUNS=$HOME/transfergap_g1/runs
DP=${DP:-$HOME/transfergap_g1/demo_plan.json}
TAG=${TAG:-}
P="--stance-offset ${STANCE:--0.075 0.005} --grasp-dz 0.03 --pitch-down -0.2 --roll -0.4 --grasp-dxy ${GDXY:-0 0}"
HUMAN=$(python3 -c "import json;print(json.load(open('$DP'))['timing_scale'])")
mkdir -p "$RUNS/plans_style$TAG"
cd "$G1"
source "$HOME/GR00T-WholeBodyControl/.venv_sim/bin/activate"
for s in $(seq ${SEED0:-100} ${SEED1:-109}); do
  xy=$(python -c "from scene import sample_block_xy; print(*sample_block_xy($s))")
  for c in human:$HUMAN cap3:3.0 nominal:1.0; do
    python plan_reach.py --out "$RUNS/plans_style$TAG/${c%%:*}_seed$s.npz" --target-xy $xy $P \
      --demo-plan "$DP" --timing-scale ${c##*:} > /dev/null
  done
done
deactivate
for c in ${CONDS:-nominal cap3 human}; do
  python3 "$G1/run_trials.py" --traj "$RUNS/plans_style$TAG/${c}_seed{seed}.npz" --run-dir "$RUNS/g1_style${TAG}_$c" \
    --seeds ${SEEDS:-100-109} --rollouts ${ROLLOUTS:-3}
done
