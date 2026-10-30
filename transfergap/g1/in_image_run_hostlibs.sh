#!/bin/bash
# Same as in_image_run.sh, but first makes the image's CUDA user-space look like the host pod's: installs the SAME pinned
# cuBLAS / cuDNN debs the host pod has (libcublas-12-8 12.8.3.14-1, libcudnn9-cuda-12 9.7.0.66-1 if available) and puts the
# CUDA 12.8 runtime ahead of the CUDA 12.4 one the image's deploy binary otherwise loads. HOSTLIBS=cudart for cudart only.
# Usage in the image pod: OUTNAME=... HOSTLIBS=all bash /ws/transfergap/runs/in_image_run_hostlibs.sh 1200-1209
set -uo pipefail
if [ "${HOSTLIBS:-all}" = "all" ]; then
  apt-get update -qq >/dev/null 2>&1
  CUDNN=$(apt-cache madison libcudnn9-cuda-12 | awk '{print $3}' | grep -m1 '^9\.7\.0' || true)
  apt-get install -y -qq libcublas-12-8=12.8.3.14-1 libcudnn9-cuda-12${CUDNN:+=$CUDNN} 2>&1 | tail -2
  echo "installed: $(dpkg -l | grep -E 'libcublas-12-8|libcudnn9-cuda-12' | awk '{print $2, $3}' | tr '\n' ' ')"
fi
export LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64
echo "cudart the deploy binary will load:"; LD_LIBRARY_PATH=/opt/TensorRT-10.13.3.9/lib:/opt/onnxruntime/lib:$LD_LIBRARY_PATH ldd /opt/GR00T-WholeBodyControl/gear_sonic_deploy/target/release/g1_deploy_onnx_ref | grep -E "cudart|cublas|cudnn"
exec bash /ws/transfergap/runs/in_image_run.sh "$@"
