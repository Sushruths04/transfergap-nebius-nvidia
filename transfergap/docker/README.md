# TransferGap GPU image (private Nebius registry)

> **HISTORICAL (2026-10-06).** This describes the old Nebius VM image (`transfergap-live`). Nebius is out of scope. The current image, its build
> and the one-command pipeline are in `UNIFIED_IMAGE.md` (this folder), `../../PIPELINE.md` and `../../HANDOFF.md`.


One image with everything verified on the Nebius L40S VM: GEM-X (live + offline pose), RTMW3D (OpenMMLab) and
Fast SAM 3D Body environments, GR00T-WholeBodyControl / SONIC (built deploy + MuJoCo sim venv), TensorRT 10.13,
the Cosmos venv (vLLM + PEFT), and the TransferGap code (`~/transfergap_g1`). No recorded videos or personal data;
model weights that live in the Hugging Face cache download on first use with your own token.

Image: `cr.eu-north1.nebius.cloud/e00x55kgpmznfqapgg/transfergap-live:2026-10-03` (67 GB).

## On a fresh GPU VM (NVIDIA driver >= 580, Docker + nvidia-container-toolkit)
```bash
nebius iam get-access-token | sudo docker login cr.eu-north1.nebius.cloud --username iam --password-stdin
sudo docker pull cr.eu-north1.nebius.cloud/e00x55kgpmznfqapgg/transfergap-live:2026-10-03
IMAGE=cr.eu-north1.nebius.cloud/e00x55kgpmznfqapgg/transfergap-live:2026-10-03 HF_TOKEN=... bash docker/run.sh
```
Inside: the same paths as on the VM, e.g. the live session (`python3 ~/transfergap_g1/live/run_live_vm.py
--supervise [--estimator rtmw3d]`) with the laptop side `bash live/run_live_laptop.sh <vm-ip> --source <camera>`.
Verified inside the container: L40S visible, CUDA in the GEM-X venv, MuJoCo EGL rendering
(`NVIDIA_DRIVER_CAPABILITIES=all`, set in the image and in run.sh).
Rebuild: `bash docker/stage.sh && sudo docker build -t transfergap-live -f docker/Dockerfile ~/tg_docker_ctx` on a
VM that has the environments (needs ~140 GB free).
