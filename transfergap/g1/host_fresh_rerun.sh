#!/bin/bash
# Host-setup rerun in a FRESH tg-dev pod (volume repo + venv, cached TensorRT engine), seeds 1200-1209, to test the 'stale pod state' explanation
# of the gap in results/g1_in_image_v1. Same recipe as g1/queue_pelvis_drift.sh; plans from that run are reused.
set -uo pipefail
V=/ws/transfergap; H=$V/runs/g1_cl/host_fresh_v1; mkdir -p $H; exec > >(tee -a $H/job.log) 2>&1
echo "== start $(date -u)"; bash $V/envs/bootstrap_pod.sh 2>&1 | tail -2
pip3 install -q uv==0.12.22 2>&1 | tail -1; export PATH=$HOME/.local/bin:$PATH
uv python install 3.10 2>&1 | tail -2; ls $HOME/.local/share/uv/python/
. $V/envs/home_layout.sh
$HOME/GR00T-WholeBodyControl/.venv_sim/bin/python -c "import sys,mujoco,numpy;print(sys.version.split()[0],mujoco.__version__,numpy.__version__)" || { echo "VENV BROKEN"; exit 3; }
ps aux | grep -E "sim_runner|deploy|stream_|tmux" | grep -v grep | wc -l | xargs echo "leftover processes at start:"
R=$V/runs/g1_cl; cd $HOME/transfergap_g1/g1; . $HOME/GR00T-WholeBodyControl/.venv_sim/bin/activate
HY="--mode rr --kr 1 --lim 0.6 --w-rot 0.05 --tail-traj $R/plans/ol_seed{seed}.npz --tail-from lift --blend-s 1.0"
python3 run_trials.py --traj "$R/plans/cl_seed{seed}.npz" --run-dir $H/hybrid --seeds 1200-1209 --rollouts 1 --closed-loop "$HY" > $H/hybrid.out 2>&1
echo "run_trials exit=$?"; python $V/runs/drift_features.py $H/hybrid 1200-1209 > $H/rows.json 2>$H/rows.err; echo done > $H/run.done; echo "== end $(date -u)"
