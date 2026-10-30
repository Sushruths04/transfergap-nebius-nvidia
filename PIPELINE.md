# PIPELINE: from a human video (or a webcam) to robot results, on the GPU cluster

Last updated 2026-10-06. Scope: **cluster only** (Nebius is out of scope). Status markers: VERIFIED = observed on the cluster with a committed result; UNVERIFIED = written, not yet run.

## What it does

```
video / webcam -> pose (RTMW3D, GPU) -> HumanDemo (grasp, release, hand path) -> plausibility gate
               -> feasibility pre-check (CPU, per robot) -> held-out rollouts: no correction vs the frozen fix stack -> REPORT.md
```
Robots: UR5e, UR10e, KAIROS arm (`kairos`: UR10e + Robotiq 2F-140, fixed base) and `kairos_mobile` (the same arm on the KAIROS mobile base, see below). All simulation (MuJoCo); no Isaac Sim. The G1 humanoid is a separate path (`g1/`, see `HANDOFF.md`).

## One command (offline video)

```
python -m transfergap.pipeline --video clip.mp4 --window 60 206 --events 102 166 --robots ur5e ur10e kairos --out runs/pipe1
#   --events G R   grasp / release frame NUMBERS OF THE SOURCE VIDEO (omit for the automatic aperture segmenter; hand-given events are more reliable)
#   --joints J.npz skip pose estimation;  --pose-python / $TG_POSE_PY  the RTMW3D interpreter
```
Output: `<out>/REPORT.md`, `pipeline_report.json` (per-stage status, a failed stage stops the later ones and is named), `demo.npz`, `joints.npz`, `feasibility.json`, `rollouts/repro_summary.json`.
In the image: `tg-entrypoint pipeline --video ... --out /data/out/pipe1` (the pose stage is `tg-entrypoint perceive`).

**Plausibility gate** (`pipeline.plausibility`): a hand path wider than 1.5 m or a median finger aperture above 0.30 m is treated as a failed pose estimate and the pipeline stops at the demo stage instead of simulating garbage.

## Verified runs (cluster, committed)

| What | Result | Where |
|---|---|---|
| Author's static-camera clip, rescaled to metric size, 4 robots, frozen five-fix stack, seeds 1000-1059 | UR5e 35 -> 60, UR10e 36 -> 60, KAIROS 49 -> 60, KAIROS mobile 49 -> 60 (of 60) | `transfergap/results/cluster_pipeline_user_scaled_v1` (VERIFIED; exploratory, not in the paper). Supersedes the earlier unscaled runs (25->58, 7->60, 41->60), which copied a path about 2.6x too large |
| Same clip, earlier unscaled runs | SUPERSEDED (RTMW3D coordinates are not metric) | `cluster_cam_user_rtmw3d_v1`, `cluster_pipeline_user_v1` |
| Internet clip (Pexels) | refused at the demo stage: hand path extent 5.87 m | `transfergap/results/cluster_pipeline_pexels_refused_v1` |

## KAIROS in MuJoCo (mobile base, no Isaac Sim)

`kairos_mobile` (`sim/scene.py`, `sim/kairos_model.py: mount_on_base`, `sim/kairos_mobile.py`): the Summit XLS chassis mesh from the lab's expanded URDF, a planar holonomic base
(slide x, slide y, hinge yaw; position servos on a velocity- and acceleration-limited setpoint), four visual omni wheels, and the UR10e + Robotiq 2F-140 on the top plate (arm base 0.5076 m above the floor,
0.38062 m above the base link as in the URDF). Demo: `python -m transfergap.sim.kairos_mobile demo --out DIR` drives the base from (-1.3, -0.9, yaw 0.9) to the table, picks and places the block with the unchanged controller,
then drives away. VERIFIED on the laptop and on the cluster (identical phase report): parked within 1 cm in 5.16 s, block placed, `results/kairos_mobile_demo_v1`; the pipeline gives 41 -> 60 of 60 for `kairos_mobile`,
the same as the fixed arm (`results/cluster_pipeline_kairos_mobile_v1`). Not modelled: wheel/floor contact and wheel motors (wheels spin for show); the real mount yaw is not checked. The lab mesh files stay
in the git-ignored `transfergap/transfergap/sim/assets/kairos/` (base meshes in `base/`, also on the cluster volume under `kairos_assets/base`); tests skip without them. The live viewer takes `--robot kairos_mobile`.

## Known limits (do not hide these)
- RTMW3D is trusted only for a **static camera with the person in view**. On internet clips it failed (`results/pose_estimator_bakeoff_v3`: 0/600). GEM-X and Fast SAM 3D Body did better there but are not installed on the cluster.
- Object pose is not detected: the object is assumed under the pinch point at grasp (`demo/gemx.py` docstring).
- Perception and calibration errors in the rollouts are the assumed ones of `sim/errors_demo.py`. Simulation only.
- The frozen fix stack was chosen on other demos; one clip and one person do not show it generalises.

## Live camera (webcam, arm only)

```
cd transfergap && bash live/run_live_cluster.sh --robot ur5e|ur10e|kairos [--source 0|file.mp4] [--seconds N]
```
Laptop webcam -> `live/push_cam.py` (JPEG POST over a persistent connection) -> `kubectl port-forward` -> pod `live/frame_relay.py` -> `live/hands_pub.py --estimator rtmw3d` -> `live/arm_live.py` -> viewer at `http://127.0.0.1:8091/`.
The pod cannot open a connection to the laptop, so frames are pushed. Pod side: `live/cluster_session.sh start|stop|status` (PID files, no pattern kills).
- VERIFIED (2026-10-06, a recorded video file standing in for the camera, KAIROS arm viewer): relay, RTMW3D hands channel and the arm viewer run through the port-forward; the hands channel ran at 17-21 fps with 4 parallel push connections (4.7 fps with one connection: each POST waits a full round trip through the port-forward). The port-forward restarts itself if it drops. Latency and tracking error of the arm are NOT measured (they need a calibrated live session).
- NOT yet run with the user's real webcam.
- G1 live is not ported (it needs the SONIC stack running next to the pose model); the earlier VM-based G1 live mode exists in `live/run_live_laptop.sh` and is out of scope now.

## Image
Recipe `transfergap/docker/Dockerfile.unified.flat` (adds the RTMW3D venv at `/opt/rtmw3d`, pinned by `docker/rtmw3d_pins.txt`; weights fetched on first use or mounted from `$TG_CACHE/rtmpose3d_ckpt`). Build and push: `docker/cluster/kaniko-full-r4.yaml`, `skopeo-push-ghcr-r4.yaml` (see `HANDOFF.md`). **r4 is built, pushed (`ghcr.io/sushruths04/transfergap:full-2026-10-06c`, digest sha256:947ee7e4c86a5db7b6bf0e61062f8cc6cf189ce75a256ed46f9f7b241e20b14e) and passes all 8 e2e stages on the cluster (VERIFIED, `transfergap/results/e2e_cluster_r4_v1`)**, including `perceive` and `pipeline`. The e2e Job used the newer `e2e.sh` from the volume; r5 should bake it in.

## Volume safety
Nothing on the cluster volume is deleted without a verified backup (user rule, 2026-10-06). New folders added by this work: `/ws/transfergap/envs/rtmw3d` (+ `rtmw3d_freeze.txt`), `cache/rtmpose3d_ckpt`, `ctx_cam` (code + pipeline outputs), `ctx_unified_r4`, `images/transfergap-full-2026-10-06c.tar` (when built).

## Metric scale (important)
RTMW3D's 3D output is not metric: on the author's clip the shoulder width came out 1.04 m and the upper arm 0.77 m (about 2.6x too large). The pipeline therefore rescales the pose so the median shoulder width equals `--shoulder-width-m` (default 0.40 m, an ASSUMED adult value: **measure the person's own and pass it**). One uniform factor fixes the size, not the depth: a monocular depth estimate stays weak (about 3 cm of depth range on this clip). `transfergap/human/analyze.py` reports the limb lengths, angles and hand aperture after the same scaling (upper arm 29.8 cm, forearm 25.7 cm, hand 17.3 cm, pinch 5.0 cm on this clip).

## Person measurements, G1 mimic, robot videos, the integrated video (2026-10-06; run on the cluster for the author's clip)
```
python -m transfergap.human.analyze --joints pose.npz --video clip.mp4 --out DIR [--shoulder-width-m 0.40]   # limb lengths, angles, hand aperture + overlay video
JOINTS=<scaled joints> OUT=DIR SONIC_WEIGHTS_SRC=... bash g1/image_g1_mimic.sh                                # G1 mimics the person (image Job: docker/cluster/g1-mimic-job.yaml; pauses tg-dev, one GPU)
python -m transfergap.human.mimic_fidelity --joints <scaled joints> --episode DIR/seed0_r0.episode.json        # how closely the G1 wrist follows the person's
python -m transfergap.human.robots_render --demo demo.npz --out DIR --robots ur5e ur10e kairos_mobile         # robots without / with the fix stack (one illustrative seed)
python -m transfergap.human.showcase --human overlay.mp4 --robots-dir DIR --counts repro_summary.json --g1 g1.mp4 --g1-fidelity mimic_fidelity.json --out demo.mp4
```
VERIFIED once on the author's clip (`transfergap/results/g1_mimic_user_v1`, video `deliverables/TransferGap_integrated_demo_2026-10-06.mp4`). Not yet in the image or in `tg-entrypoint`; the G1 step needs the single GPU (scale `deploy/tg-dev` to 0, run the Job, scale back, run `restore_tg_dev.sh`).

## Scene twin and marker (NEW 2026-10-06): your real task geometry
```
python -m transfergap.human.marker sheet --out marker_sheet.png --size-cm 12          # printable marker (also deliverables/TransferGap_marker_12cm.pdf)
python -m transfergap.human.marker detect --video clip.mp4 --size-cm 12               # marker found? camera distance, reprojection error
python -m transfergap.human.twin_from_video --video clip.mp4 --pose pose.npz --events G R --marker-size-cm 12 \
       --object-cm L W H --target-inner-cm L W --target-wall-cm H --tape-distance-cm D --out twin.json     # positions from the video, sizes from your tape
python -m transfergap.pipeline --video clip.mp4 --scene twin.json --scale-from scene ...                   # robots build YOUR scene; scale from your measured distance
TG_TWIN=twin.json python -m transfergap.sim.<any arm script>                                                # any arm Scene in the process uses the twin
```
`transfergap/configs/twin_template.json` is the form to fill (it refuses to load while any `FILL_ME` remains). Arms only (UR5e, UR10e, KAIROS, KAIROS mobile); the G1 scene (`g1/scene.py`) still uses its own fixed block and tray (NOT DONE). Not built: automatic detection of the objects and their sizes from the video.
VERIFIED: 10 unit tests (twin 6, marker 4 incl. a synthetic round trip with 1 cm accuracy and the height effect), the unchanged controller places a non-cubic measured box on UR5e, UR10e and KAIROS mobile (4/4 each on a generic test geometry), and two cluster runs on the author's clip with STAND-IN geometry (`results/cluster_pipeline_twin_standin_v1`, `..._twin_carry_only_v1`): object and container geometry, not carry distance, drive the outcome. NOT yet run with a real marker clip or measured sizes: that needs your recording (`RECORDING_PROTOCOL.md`).
