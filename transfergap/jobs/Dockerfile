# TransferGap CPU sweep image for Nebius Serverless AI Jobs.
# Build from the transfergap/ project directory (the build context must be transfergap/, not the repo root):
#   docker build -f jobs/Dockerfile --build-arg TRANSFERGAP_GIT_COMMIT=$(git rev-parse HEAD) -t transfergap-sweep:dev .
# mujoco_menagerie assets (UR5e, Robotiq 2F-85) are Apache-2.0 (c) Google DeepMind and contributors; fetched at
# a pinned commit, not redistributed in this repo.

ARG PYTHON_IMAGE=python:3.12-slim

FROM ${PYTHON_IMAGE} AS assets
ARG MENAGERIE_COMMIT=4d038b3feae26ec82b46a4d586379114012a8ac7
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone -q --filter=blob:none --no-checkout https://github.com/google-deepmind/mujoco_menagerie /menagerie \
    && git -C /menagerie sparse-checkout set universal_robots_ur5e universal_robots_ur10e robotiq_2f85 \
    && git -C /menagerie checkout -q "${MENAGERIE_COMMIT}" \
    && test "$(git -C /menagerie rev-parse HEAD)" = "${MENAGERIE_COMMIT}" \
    && rm -rf /menagerie/.git

FROM ${PYTHON_IMAGE}
ARG MENAGERIE_COMMIT=4d038b3feae26ec82b46a4d586379114012a8ac7
ARG TRANSFERGAP_GIT_COMMIT=unknown
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 \
    TRANSFERGAP_GIT_COMMIT=${TRANSFERGAP_GIT_COMMIT} MENAGERIE_COMMIT=${MENAGERIE_COMMIT} \
    TG_PROJECT_DIR=/opt/transfergap TG_OUT=/data/out
# Pinned to the versions the local test suite ran against (mujoco 3.14.0, numpy 2.2.6).
RUN pip install --no-cache-dir "mujoco==3.14.0" "numpy==2.2.6"
WORKDIR /opt/transfergap
COPY pyproject.toml README.md ./
COPY transfergap/ transfergap/
COPY tests/ tests/
COPY results/ results/
# real human demo (Pexels-licensed clip -> GEM-X -> HumanDemo); staged by the build command, not in git
COPY jobs/data/ runs/demos/
COPY jobs/run_sweep.sh jobs/run_sweep.sh
COPY --from=assets /menagerie transfergap/sim/assets/menagerie
RUN echo "${MENAGERIE_COMMIT}" > transfergap/sim/assets/MENAGERIE_COMMIT \
    && chmod +x jobs/run_sweep.sh \
    && python -c "import mujoco; from transfergap.sim.scene import Scene; Scene(0); print('mujoco', mujoco.__version__, 'scene ok')"
ENTRYPOINT ["/opt/transfergap/jobs/run_sweep.sh"]
CMD []
