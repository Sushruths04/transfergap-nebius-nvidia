# TransferGap live/GPU stack in one image: GEM-X (live pose), SONIC (G1 whole-body controller + MuJoCo sim, built
# deploy binary), TensorRT 10.13, Fast SAM 3D Body (conda env), the TransferGap code. Built FROM the environments that
# were verified on the Nebius L40S VM (Ubuntu 24.04), copied to the SAME absolute paths so the uv/conda virtualenvs
# work unchanged. Model weights are NOT baked in (licences: SAM License, NVIDIA model licences, MANO/SMPL): they
# download on first use into the mounted HF cache with the user's own token.
#   build: bash docker/stage.sh && docker build -t transfergap-live -f docker/Dockerfile /home/ubuntu/tg_docker_ctx
#   run:   bash docker/run.sh   (needs NVIDIA driver >= 580 + nvidia-container-toolkit on the host)
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive TZ=UTC
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git tmux ffmpeg rsync python3 python3-venv \
      libzmq5 libsodium23 libpgm-5.3-0t64 libnorm1t64 libbsd0 libgssapi-krb5-2 \
      libegl1 libgl1 libgl1-mesa-dri libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/* \
    && (id ubuntu >/dev/null 2>&1 || useradd -m -s /bin/bash ubuntu)
USER ubuntu
WORKDIR /home/ubuntu
# same layout as the VM (paths are baked into the virtualenvs)
COPY --chown=ubuntu:ubuntu home/ /home/ubuntu/
ENV NVIDIA_DRIVER_CAPABILITIES=all MUJOCO_GL=egl PYOPENGL_PLATFORM=egl HF_HOME=/home/ubuntu/.cache/huggingface \
    TensorRT_ROOT=/home/ubuntu/TensorRT-10.13.3.9 \
    LD_LIBRARY_PATH=/home/ubuntu/TensorRT-10.13.3.9/lib
# smoke test of the python stacks at build time (no GPU needed)
RUN GR00T-WholeBodyControl/.venv_sim/bin/python -c "import mujoco, zmq; print('sim venv ok', mujoco.__version__)" \
 && GEM-X/.venv/bin/python -c "import torch; print('gemx venv ok', torch.__version__)"
CMD ["bash"]
