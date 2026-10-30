# G1 contact attempt (GEAR-SONIC + MuJoCo)

The Unitree G1 humanoid half of the TransferGap pick-and-place task: a 4 cm / 50 g block on a table
is picked up with the right Dex3 hand and put in a tray. The robot is the GEAR-SONIC whole-body
tracking policy running in the upstream sim2sim loop (MuJoCo sim + C++ TensorRT deploy binary). The
reference motion is streamed to it over ZMQ, open loop. Simulator state is used only to label and
score rollouts. Results: `../results/g1_contact_v1/`.

## What drives the robot (read this before citing the result)

- The **contact motion is not a human demonstration.** The only human-video motion we have (GEM-X on
  a public-domain walking clip) contains no reach and no hand pose; GEM-X streams wrists and fingers
  as zeros. The reach-grasp-place motion is a set of **IK keyframes** (`plan_reach.py`): straight
  Cartesian segments for a grasp point between the thumb and fingers, solved on the static G1 model,
  then streamed as SONIC **protocol v1** (29 joint targets, IsaacLab order) plus Dex3 hand targets on
  the same `pose` topic the GEM-X bridge uses. The closed-hand target is the upstream teleop preset
  (`g1_gripper_ik_solver.py`, middle close).
- **Kimodo-G1 was not used.** Its text encoder is LLM2Vec on the gated `meta-llama/Meta-Llama-3-8B-Instruct`;
  the HF token on the VM gets 403 for that repo. Kimodo zeroes the text features of an empty prompt
  (`kimodo/model/kimodo_model.py`, `empty_text_mask`) and `load_model(text_encoder=...)` accepts a
  pre-built encoder, so a constraint-only run with a stub encoder looks possible, but it was not tried.
- The human-video loop itself (GEM-X `hpe_results.pt` -> `soma_pt_to_sonic_v3.py` -> SONIC -> G1) was
  re-run on 2026-10-01 with the commands below; it drives the G1 (protocol v3) but does no task.
- The motion is aimed using parameters tuned on two dev seeds (0, 1) and frozen in
  `../results/g1_contact_v1/protocol.json` before the trial seeds (100-109) were run: table height,
  IK waist cost, a **stance offset** (the robot stands about 7.5 cm behind the origin once released
  from the elastic band; measured in dev rollouts, applied as a constant) and the hand orientation
  chosen by `grasp_search.py` (kinematic check only, no rollouts).

## Files

| file | runs where | role |
|---|---|---|
| `scene.py` | VM, `.venv_sim` | loads upstream `scene_43dof.xml` unmodified with `MjSpec`, adds table, block, tray, cameras, writes our own XML |
| `plan_reach.py` | VM, `.venv_sim` | IK keyframes -> 50 Hz joint trajectory (`.npz` + `.json` metadata) |
| `grasp_search.py` | VM, `.venv_sim` | kinematic grid search for a hand pose that clears the table and squeezes the block |
| `preview.py` | VM, `.venv_sim` | kinematic playback of a plan to mp4 |
| `sim_runner.py` | VM, `.venv_sim`, from the WBC repo root | upstream `BaseSimulator` with `ROBOT_SCENE` pointed at our XML; logs state, renders video |
| `stream_motion.py` | VM, `.venv_sim` | open-loop ZMQ publisher, upstream `pack_pose_message`, protocol v1 + hands |
| `run_trials.py`, `run_v1.sh` | VM | one fresh sim + deploy + streamer per rollout in tmux `g1-sim`/`g1-deploy`/`g1-stream` |
| `track_error.py` | VM | diagnostics: tracking lag, wrist error per phase |
| `score.py` | laptop | raw logs -> repo-schema JSONL (10 Hz) -> touch/grasp/place tiers, `summary.json` |
| `video.py` | VM | mp4 via system ffmpeg (no imageio in `.venv_sim`) |

Harness changes relative to the upstream entry point (`gear_sonic/scripts/run_sim_loop.py`), all
simulator-side: the elastic band is lowered to standing height and released by timer 1-4 s after the
controller first sends commands (upstream: keys `7`/`9` in the viewer); `check_fall` no longer resets
the scene (that would teleport the block); a fall ends the rollout and is logged. Nothing upstream is
edited (`git status` in the WBC checkout is clean).

The 60 recovered raw trial logs and plan metadata are stored locally as
`../runs/g1_recovered_2026-10-01.tar.gz` (gitignored, about 9 MB). Before rescoring,
extract it from the `transfergap/` directory with
`tar -xzf runs/g1_recovered_2026-10-01.tar.gz -C runs` and use
`runs/g1_recovered_2026-10-01/` as the input root. The uncompressed files were
removed from the laptop after scoring to save disk space; the VM's original logs
remain on its stopped, retained disk.

## Upstream pins (VM, 2026-10-01)

```
GR00T-WholeBodyControl  b042411fae38ee4d1af9aac82a37a1f8d14d6dd0   (clean)
  weights nvidia/GEAR-SONIC snapshot 6733128a3d8a523b1418b06bca3cdf61c8b0987f
  policy/release/model_decoder.onnx md5 1d4391ad404d0ff36281abec349b23fd
  policy/release/model_encoder.onnx md5 a21244b1cdceac9dc8625442a55d42e0
  .venv_sim: mujoco 3.14.0, numpy 1.26.4, pyzmq 27.2.0
TensorRT 10.13.3.9 (x86_64, CUDA 13.0); driver 580.173.02; NVIDIA L40S
GEM-X  32992550dba114c62243fb55e361311972dce8f9
kimodo 58e781898b3d7e328a676a75d3e338c45dce3ad9 (cloned, not used)
```

## Reproduce

Step 1, the human-video loop (verified 2026-10-01; `--input-type zmq` replaces the old `#` keypress):

```bash
# tmux g1-sim
cd ~/GR00T-WholeBodyControl && source .venv_sim/bin/activate
MUJOCO_GL=egl python gear_sonic/scripts/run_sim_loop.py --enable-offscreen --no-enable-onscreen
# tmux g1-deploy (needs a tty: answer y, wait for "Init Done", then press ] and later ENTER)
cd ~/GR00T-WholeBodyControl/gear_sonic_deploy && export TensorRT_ROOT=$HOME/TensorRT-10.13.3.9
bash deploy.sh --input-type zmq --zmq-host localhost sim
# tmux g1-stream
cd ~/GR00T-WholeBodyControl && source ~/GEM-X/.venv/bin/activate
python gear_sonic/examples/live_camera_teleop/soma_pt_to_sonic_v3.py --gemx-root ~/GEM-X \
  --pt ~/GEM-X/outputs/demo_soma/test_walk/hpe_results.pt --fps 30 --loop
# then ENTER in g1-deploy: log shows "ZMQ STREAMING MODE: ENABLED" and "Protocol v3: Received SMPL action"
```

Do not add `--zmq-port`/`--zmq-topic` to `deploy.sh`: it forwards only `--input-type` and
`--zmq-host`; the binary subscribes to `localhost:5556`, topic `pose`.

Steps 2-5, the scored contact trials:

```bash
# laptop: copy the code to the VM
rsync -az -e "ssh -i ~/.ssh/transfergap_gpu" transfergap/g1/ ubuntu@<vm>:transfergap_g1/g1/
# VM: plans + 2 conditions x 10 seeds x 3 rollouts (~70 min; ~68 s per rollout, mostly deploy start-up)
tmux new-session -d -s g1-orch "bash ~/transfergap_g1/g1/run_v1.sh 2>&1 | tee /tmp/g1-orch-v1.log"
# laptop: fetch raw logs (episode.json only), then score
rsync -az --include='*/' --include='*.episode.json' --include='status.jsonl' --include='plans/*.json' --exclude='*' \
  -e "ssh -i ~/.ssh/transfergap_gpu" ubuntu@<vm>:transfergap_g1/runs/ runs/g1_v1/
cd transfergap && .venv/bin/python g1/score.py \
  --run runs/g1_v1/g1_v1_nominal:nominal_target:none:runs/g1_v1/plans/reach_nominal.json \
  --run 'runs/g1_v1/g1_v1_true:true_target:perception:runs/g1_v1/plans/reach_true_seed{seed}.json' \
  --out results/g1_contact_v1
```

Ports: the deploy binary binds 5557 (debug) and subscribes to 5556; 5555 is taken on the Nebius
image; the camera publisher is not used. GPU: the deploy binary holds ~1.3 GB of TensorRT engines;
the sim's EGL renderer is small.
