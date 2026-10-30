#!/bin/bash
# Run INSIDE the tg-dev pod after every restart (scale 0 -> 1): reinstall system packages, uv and the uv Python the .venv_sim symlinks point to.
#   kubectl cp transfergap/docker/cluster/restore_tg_dev.sh isaac-sim/<pod>:/ws/transfergap/runs/ && kubectl exec -n isaac-sim <pod> -- bash /ws/transfergap/runs/restore_tg_dev.sh
set -e
bash /ws/transfergap/envs/bootstrap_pod.sh 2>&1 | tail -1
pip3 install -q uv==0.12.22 2>&1 | tail -1; export PATH=$HOME/.local/bin:$PATH; uv python install 3.10 2>&1 | tail -1; uv python install 3.11 2>&1 | tail -1
. /ws/transfergap/envs/home_layout.sh
$HOME/GR00T-WholeBodyControl/.venv_sim/bin/python -c "import sys,mujoco,numpy;print('venv ok',sys.version.split()[0],mujoco.__version__,numpy.__version__)"
