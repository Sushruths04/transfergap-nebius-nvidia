# G1 hybrid controller inside the unified `full` image vs the host run (same seeds)

What: the frozen hybrid G1 controller (g1/CLOSED_LOOP.md settings) run for seeds 1200-1239 INSIDE the `full` container image
(`ghcr.io/sushruths04/transfergap:full-2026-10-05`, digest sha256:32b7f59ab3bc67157ac74b5d27e27790693ba4b888e82cc233e3bdc8a366252f, built with kaniko
from `docker/Dockerfile.unified.flat`) on the GPU cluster L40S, via Jobs `docker/cluster/g1-in-image.yaml` (seeds 1200-1202) and `g1-in-image-v2.yaml` (1203-1239).
Weights are not in the image: the Job copies the SONIC ONNX files from the project volume and checks the pinned md5 sums (ok in both Jobs).
Comparison: the host run of the same seeds from `results/g1_pelvis_drift_v1` (cluster pod `tg-dev`). Both scored with the repo scorer `g1/score.py` (summaries here).

Result (VERIFIED from the logged episodes):
| | touch | grasp (lift >= 5 cm) | place in tray |
|---|---|---|---|
| inside the image | 40/40 | 38/40 | 31/40 (77.5%) |
| host run, same seeds | 38/40 | 15/40 | 11/40 (27.5%) |
Paired on placement: 20 seeds placed only in the image, 0 only on the host, exact McNemar two-sided p = 1.9e-6. Videos for seeds 1200 and 1201 (host vs image, same seed): `videos/`.

NOT explained. This is a large unexplained difference, not a demonstrated improvement of the controller:
- Ruled out by direct comparison: the `g1/` code (identical files that matter: stream_cl, sim_runner, run_trials, scene, plan_reach), the SONIC commit (pinned b042411 in both),
  weights (same md5), installed Python packages in `.venv_sim` (identical except patch versions of filelock and zipp; mujoco 3.14.0, numpy 1.26.4), deploy build type (Release in both),
  onnxruntime (1.16.3 in both), TensorRT (10.13.3.9 in both), CPU (host pod had MORE: limit 32 vs 12), real-time factor (about 1.07 in both).
- Follow-up tests on the SAME seeds 1200-1209 (rows in this folder; lift >= 5 cm counted as grasp; the sim is not deterministic: the same seed can differ between runs):
  | setup | grasps of 10 | median pelvis drift |
  |---|---|---|
  | host setup, original run (pelvis_drift_v1) | 1/10 | 7.6 cm |
  | host setup in a FRESH pod (stale-state test, `g1/host_fresh_rerun.sh`) | 1/10 | 8.2 cm |
  | host setup, cached TensorRT engines moved aside (`g1/host_nocache_rerun.sh`) | 3/10 | 8.2 cm |
  | inside the image, Job resources identical to the host pod (cpu 16/32, mem 48/64 Gi, shm 16 Gi; `docker/cluster/g1-in-image-v3-hostlike.yaml`) | 10/10 | 5.6 cm |
  | inside the image, first Jobs (cpu 6/12) | 9/10 (38/40 over 1200-1239) | 5.7 cm |
  | inside the image as a long-lived DEPLOYMENT pod, `kubectl exec` (host-like resources, `docker/cluster/g1-image-deploy.yaml`, rows_image_deployment_pod_1200_1209.json) | 8/10 (the two misses lifted 0.7-0.8 cm) | 5.7 cm |
  | inside the image, host-pod CUDA user space (same pinned cuBLAS 12.8.3.14 and cuDNN 9.7.0.66 installed, CUDA 12.8 runtime instead of 12.4; `g1/in_image_run_hostlibs.sh`, rows_image_hostlike_cuda_libs_1200_1209.json) | 9/10 | 4.7 cm |
  | inside the image, the HOST-built deploy binaries copied in (the 3 compiled files that differed; md5 identical to the host's; rows_image_host_binaries_1200_1209.json) | 10/10 | 5.1 cm |
  | host setup, same day as the image variants, rerun 1 (`g1/host_sameday_rerun.sh`, rows_host_sameday_v2_1200_1209.json) | 7/10 | 7.8 cm |
  | host setup, same day, rerun 2 (node loadavg 3.8 at start, `g1/host_sameday_rerun3.sh`, rows_host_sameday_v3_1200_1209.json) | 3/10 | 8.0 cm |
- Also ruled out: stale processes/state in the old pod (fresh pod still bad), cached TensorRT engines, CPU/memory/shm size (image still 10/10 with host-identical resources), all 3,357 small files of the SONIC checkout
  (identical hashes, only 3 compiled binaries differ), C++ compiler and flags (gcc 11.4, Release in both), deploy log content (same engine conversion messages), GL/driver env (same NVIDIA_DRIVER_CAPABILITIES, MUJOCO_GL).
- Still open (untested): the pod base image (host pod `nvidia/cuda:12.8.0-cudnn-devel` vs image `nvidia/cuda:12.8.0-base` plus our layers), process start order/timing jitter,
  kernel/node-level effects at different times of day. Pod type is now ruled out (Deployment pod 8/10, 2026-10-05). Remaining cheapest test: rebuild the image on the host's `cudnn-devel` base, or run the image's Python/deploy tree inside the host pod.
  Over the 40 paired seeds the median pelvis drift is 6.5 cm on the host vs 5.5 cm in the image, and in host failures the hand is often 10-24 cm off the block at close, so the host setup degrades the body's balance/tracking, not only the grasp.
- Consequence: the earlier G1 numbers (hybrid 33% place, v7 VR 3-point vs hybrid, pelvis-drift analysis) were all measured on the host setup. Their comparisons are internally consistent, but their absolute level may not represent the controller.
  The image is a reproducible environment in which the same controller works much better; until the cause is found, quote both and do not call it an improvement of the controller.
- Caveats: simulation only, one block and tray, one run per seed in the image, small follow-up samples (10 seeds).

## Update 2026-10-05 evening: more tests, same open question
Also compared on the shared volume: the reach plans (`cl_`/`ol_` seed npz) generated in the host run and in the image are IDENTICAL (max abs difference 0.0 on every array, seeds 1200/1201/1204/1208), so planning is not the difference.
Pod type (Deployment vs Job), the CUDA 12.4 vs 12.8 runtime, cuBLAS/cuDNN presence and version, and the compiled deploy binaries are ruled out: each image variant still gives 8-10 of 10 grasps.
Over repeated runs of the SAME seeds 1200-1209: host setup 1, 1, 3, 7, 3 of 10 (15/50), image variants 9, 10, 8, 9, 10 of 10 (46/50). The host result is itself variable (7/10 in one rerun), so quote the pooled rates, not one run.
The gap is real but its cause is still unknown. Remaining untested: the base image content (cudnn-devel vs base: compilers/headers only), the host pod's overlay/volume I/O and CPU scheduling, and unobserved neighbours on the node (a kubectl user here cannot list other tenants' pods).
