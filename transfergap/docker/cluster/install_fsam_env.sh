#!/bin/bash
# Fast SAM 3D Body environment on the GPU cluster volume (no conda: uv venv), run INSIDE the tg-dev pod. Log: /ws/transfergap/envs/fsam_install.log
#   kubectl cp transfergap/docker/cluster/install_fsam_env.sh isaac-sim/<pod>:/ws/transfergap/envs/ && kubectl exec <pod> -- bash /ws/transfergap/envs/install_fsam_env.sh
# Mirrors the repo's setup_env.sh (python 3.11, torch 2.5.1+cu124, same dependency list); TensorRT and detectron2 are optional and handled after the first smoke test.
set -uo pipefail
export PATH=/root/.local/bin:$PATH
E=/ws/transfergap/envs/fsam
cd /ws/transfergap/envs
[ -d $E ] || uv venv --python 3.11 $E
PIP="uv pip install --python $E/bin/python -q"
$PIP torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124 || { echo "FAIL torch"; exit 1; }
$PIP pytorch-lightning pyrender opencv-python yacs scikit-image einops timm dill pandas rich hydra-core hydra-submitit-launcher hydra-colorlog \
     pyrootutils webdataset networkx==3.2.1 roma joblib seaborn appdirs cython jsonlines pytest loguru optree fvcore pycocotools huggingface_hub \
     ultralytics smplx scipy tqdm pyzmq onnx onnxruntime-gpu "numpy<2" || echo "WARN deps"
$PIP xtcocotools chump || echo "WARN xtcocotools/chump"
$PIP "git+https://github.com/microsoft/MoGe.git" || echo "WARN MoGe"
$PIP chumpy --no-build-isolation || echo "WARN chumpy"
$E/bin/python - <<'PY'
import torch; print("torch", torch.__version__, "cuda", torch.cuda.is_available())
PY
echo "install script done"
