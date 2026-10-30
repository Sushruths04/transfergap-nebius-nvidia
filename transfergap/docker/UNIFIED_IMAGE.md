# One image, one launcher (laptop, GPU cluster, Nebius)

> **Update 2026-10-06 (cluster only; Nebius is out of scope).** Built and verified on the GPU cluster with kaniko (`cluster/kaniko-full-r*.yaml`, recipe
> `Dockerfile.unified.flat`), pushed with skopeo to the private `ghcr.io/sushruths04/transfergap` (the GitLab registry is dropped). `tg-entrypoint e2e` passes 6 of 6 stages in
> the `full-2026-10-06b` image (`results/e2e_cluster_v1`). The `full` stage HAS been built and a G1 rollout HAS run inside it (older "Not verified" lines below are superseded).
> The sim venv is pinned (mujoco 3.14.0; 3.15.0 broke the closed-loop G1). New in the r4 recipe: the RTMW3D pose venv (`/opt/rtmw3d`, `rtmw3d_pins.txt`) and the tasks
> `tg-entrypoint perceive` and `tg-entrypoint pipeline` (see `../../PIPELINE.md`). Status of the r4 image: `../../HANDOFF.md`.

Files: `Dockerfile.unified` (stages `arm` and `full`), `entrypoint.sh` (tasks), `launch.sh` (the single launcher),
`build_context.sh` (build context from committed files only). The older `Dockerfile` (live GEM-X/SONIC VM image) is separate.

## What is in it
- `arm` (1.75 GB): UR5e, UR10e and KAIROS (UR10e + 2F-140) simulation, depth perception, style transfer, the tests, menagerie
  assets at the pinned commit, Python 3.10, numpy 2.2.6, mujoco 3.14.0 (the versions the results were produced with).
- `full`: `arm` + GEAR-SONIC deploy (TensorRT 10.13) and the MuJoCo sim venv, from the cluster-validated recipe, for G1.
- Not in it on purpose: model weights (your own HF token), human demos (`runs/demos`, mount with `--demos`), the KAIROS gripper
  description (mount the folder with `--kairos`, or already generated assets with `--kairos-assets`), results/runs, secrets.

## Use
```
bash docker/build_context.sh /tmp/tg_ctx
docker build --network host --target arm -f /tmp/tg_ctx/transfergap/docker/Dockerfile.unified -t transfergap:arm /tmp/tg_ctx/transfergap
bash docker/launch.sh --gpu --kairos-assets <generated kairos assets dir> test
bash docker/launch.sh --gpu --kairos-assets <dir> perception-dev --robot kairos --seeds 0-3
bash docker/launch.sh --where cluster --image <registry image> perception-dev --robot ur5e      # prints a Job; add --apply
```
`--network host` was needed for the build on the laptop (DNS inside the default build network failed).
Outputs go to `$TG_DATA/out` (default `~/tg_data/out`).

## Verified (2026-10-04, on the laptop: Docker 29.5, RTX A2000, driver 590)
- `arm` builds; `info` shows python/numpy/mujoco versions, KAIROS assets present, EGL render ok (GPU) and with software
  rendering (`launch.sh` without `--gpu`).
- The full test suite inside the container: 195 tests, OK, 9 skipped (same counts as on the host).
- Reproducibility: 96 dev episodes (UR5e and KAIROS, 6 conditions, 2 cube sizes, seeds 0-3) run inside the container with GPU EGL
  match the committed host results exactly: 0 outcome differences, 0 difference in the estimate errors.
- With software rendering (no GPU): outcomes identical (24/24 episodes) but estimate errors differ by up to about 2 mm
  (rendering backend), so use GPU EGL for numbers you want to compare with the committed results.

## Not verified
- The `full` stage has not been built (the cluster recipe it copies was built with kaniko: 19 GB, hours) and no G1 rollout has run
  inside any image. The cluster build is free but heavy; it needs the user's go-ahead and the tg-dev pod's volume (single-attach).
- `launch.sh --where cluster` prints a valid-looking Job but was not applied. The cluster volume is single-attach: a Job on another
  node stays in ContainerCreating (Multi-Attach error) while the idle `tg-dev` pod holds it (observed today).
- Registry digests: the GitLab registry returned HTTP 503 on manifest reads again on 2026-10-04 (3 retries, from the cluster), so the
  digests of the pushed images stay unverified.
- A Nebius run is `launch.sh` on a VM the user starts and approves; nothing here starts paid resources. Not run.
- Licences: non-commercial research use (menagerie Apache-2.0; SONIC/GEAR weights, SAM, SMPL/MANO and the recorded demos carry their own).
