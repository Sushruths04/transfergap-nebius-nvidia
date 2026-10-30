# 02 — GR00T N1.7 fine-tuning for TransferGap on one L40S, both embodiments, sim-generated data

Research agent 2 of 6. Date: 2026-09-29.

**Method.** I shallow-cloned the upstream repositories again. The earlier scratchpad copies were gone. I read the files verbatim with `git show`, not through a summarizer. I read GitHub issues with `gh`, and used web search only for MimicGen and DreamGen.

**Pinned commits:**

| Repo | Commit |
|---|---|
| `NVIDIA/Isaac-GR00T` | `51d4c89f72fda44cbf77285c6a8114b52676b8a1` |
| `NVlabs/GR00T-WholeBodyControl` | `b042411fae38ee4d1af9aac82a37a1f8d14d6dd0` |
| `NVlabs/mimicgen` | `72bd767c255545f462e7ccfb2731f2e5d4c1d9bb` |

**Citation keys used below:**
- `IG:<path>` means Isaac-GR00T at the pinned commit.
- `WBC:<path>` means GR00T-WholeBodyControl at the pinned commit.

**Labels:**
- **VERIFIED** means the claim was read in source or docs at the pinned commit.
- **UNVERIFIED** means it is inference or a plan, and needs a check on the GPU box.

---

## 0. Headline findings (read these first)

1. **Blocking prerequisite: the GR00T backbone is gated.** N1.7's VLM backbone is `nvidia/Cosmos-Reason2-2B`. The README says it is a **gated** model that "every GR00T checkpoint (including the base `nvidia/GR00T-N1.7-3B`) loads on first use". Without access, loading fails with `GatedRepoError`/401.
   - VERIFIED: `IG:README.md` L181-185, and `IG:gr00t/experiment/launch_finetune.py` sets `config.model.model_name = "nvidia/Cosmos-Reason2-2B"`.
   - **Action:** the user must request access on HF before the GPU session, then run `huggingface-cli login` or set `HF_TOKEN` on the box. The same HF account also needs any HiPHI access.
   - This also means GR00T literally contains Cosmos-Reason2. It is a legitimate "Cosmos inside the loop" talking point.
2. **Single-GPU fine-tuning is the documented default, with an exact command.** `IG:getting_started/finetune_new_embodiment.md` L95-112 uses `NUM_GPUS=1`, `--global-batch-size 32` and `--max-steps 2000` on the 5-episode `cube_to_bowl_5` demo set. By default only the projector and diffusion head train (`tune_llm=False`, `tune_visual=False`, from `IG:gr00t/configs/finetune_config.py`). VERIFIED.
3. **The data-volume guidance is concrete.** From `IG:FAQ.md` ("How much data..."), VERIFIED:
   - Simple fixed-location pick-and-place: about 100 trajectories.
   - Complex scenes: 500 or more.
   - High-DoF humanoid: 2,000 or more.

   The one published G1+SONIC single-task policy (soda can) used about 150 episodes, 20k iterations and batch 32. It reached 8/12 = 66.7% on a real robot (`IG:examples/GR00TWholeBodyControl/README.md`, VERIFIED). **One human clip is a demo case, not a dataset.** Episodes must be multiplied by physics-validated generation (§3.4).
4. **G1 embodiment: the GEM-X route cannot produce a G1 grasp as-is.** The UNITREE_G1_SONIC action is `motion_token`(64) + `left_hand_joints`(7) + `right_hand_joints`(7) (`IG:gr00t/configs/data/embodiment_configs.py` L67-114, VERIFIED).
   - The exporter fills `action.motion_token` from the C++ controller's `token_state`. It fills hand joints from the teleop pose message and writes **zeros** when those are absent (`WBC:gear_sonic/scripts/run_data_exporter.py` L662-665 and L756-767, VERIFIED).
   - The GEM-X tutorial says wrists and fingers are **not tracked** and are streamed as zeros (`WBC:docs/source/tutorials/live_camera_teleop.md`, Limitations, VERIFIED).
   - **So G1 data collected via GEM-X has hands that never close.** A fix is needed: inject `left/right_hand_joints` computed from WiLoR pinch into the pose stream. This is UNVERIFIED design (§4.3).
5. **The G1 MuJoCo sim has no table or object.** `run_sim_loop` loads `ROBOT_SCENE: gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml` from `WBC:gear_sonic/utils/mujoco_sim/wbc_configs/g1_29dof_sonic_model12.yaml` (VERIFIED). The only camera is `head_camera` "ego_view" at 640×480 (`WBC:gear_sonic/utils/mujoco_sim/base_sim.py` L55-58, VERIFIED). A G1 manipulation task needs:
   - a copied scene XML with table and block,
   - the yaml `ROBOT_SCENE` edited,
   - object-state logging added for our scorer. **All UNVERIFIED engineering.**
6. **Port collision on the Nebius image (from our own Sept 27 finding).** `nv-hostengine` occupies **5555**. The following all default to 5555 (VERIFIED):
   - the camera publisher (`--camera-port`),
   - the data exporter (`--camera-port`),
   - `run_gr00t_server.py` (`IG:getting_started/policy.md` L295-309, "default: 5555"),
   - `open_loop_eval.py` in server mode.

   **Always pass `--camera-port 5560` and `--port 5550`.**
7. **Sim-only G1 data collection is supported, but the stock recording path assumes PICO.**
   - `launch_data_collection.py --sim` starts the sim with `--enable-image-publish --enable-offscreen --camera-port <p>` (`WBC:gear_sonic/scripts/launch_data_collection.py` L316-334, VERIFIED).
   - It does **not** set `MUJOCO_GL=egl`. Our Sept 27 box crashed without it, so export it before launching tmux (UNVERIFIED that tmux inherits it; set it inside the pane command if needed).
   - `stream_mode` comes from the PICO manager (`manager_state` topic). With plain `--input-type zmq` and no manager, `current_stream_mode` stays 0 and the `teleop.smpl_*` features record zeros. `action.motion_token` is still recorded from the C++ proprio. VERIFIED from code (L248, L362-363, L662-665, L675). Whether C++ publishes `token_state` in `zmq` input mode is UNVERIFIED; check the parquet after the first episode.
   - Recording is toggled with key `c` (discard with `x`) over a **ZMQ keyboard publisher on port 5580** (`WBC:docs/source/tutorials/data_collection.md`, Recording Controls, VERIFIED). Without the PICO pane, something must publish `c` on 5580. `launch_inference.py` contains an inline keyboard publisher script (L342-366) that can be reused.
8. **LeRobot version trap.**
   - GR00T at the pinned commit loads **LeRobot v2.1** and says to convert v3→v2 (`IG:getting_started/data_preparation.md` L13-15, VERIFIED).
   - Upstream issue #774 "Add native LeRobot v3 dataset loading" was closed on 2026-09-12. It is not reflected in the pinned docs; treat v2.1 as required.
   - Current `pip install lerobot` writes v3. **Don't use it.** Reuse `gear_sonic.data.exporter.Gr00tDataExporter`, which pins lerobot `a445d9c9…` (`lerobot.common.*` namespace, v2.1 writer) and writes `meta/modality.json` (`WBC:gear_sonic/pyproject.toml` L54-65; `WBC:gear_sonic/data/exporter.py` L145-320, VERIFIED). The alternative is to write parquet and MP4 directly, mirroring `IG:demo_data/cube_to_bowl_5`.
9. **DreamGen/Cosmos synthetic data: skip it.** `IG:FAQ.md` says a Cosmos synthetic-data pipeline "is currently in development and not yet part of the standard release" (VERIFIED). GR00T-Dreams requires fine-tuning Cosmos-Predict2 and training an IDM per embodiment ([github.com/nvidia/gr00t-dreams](https://github.com/nvidia/gr00t-dreams)). That does not fit one L40S and four weeks. Use MimicGen-style physics replay instead (§3.4).
10. **Nondeterminism.** SONIC+MuJoCo rollouts are not bit-reproducible run to run, even after a fresh restart (`NVlabs/GR00T-WholeBodyControl#274`, open). Paired G1 comparisons must use multiple rollouts per trial key and report variance. Do not treat one seed as one fixed outcome.

---

## 1. Environment setup on the L40S (Isaac-GR00T)

All VERIFIED from `IG:README.md` L128-201 unless marked otherwise.

```bash
sudo apt-get install -y git-lfs ffmpeg && git lfs install    # ffmpeg 4–7 only (Ubuntu 24.04 ships 6.x: OK)
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/NVIDIA/Isaac-GR00T.git && cd Isaac-GR00T
git checkout 51d4c89f72fda44cbf77285c6a8114b52676b8a1           # pin
uv sync --python 3.12                                           # torch 2.9.0 cu128, flash-attn 2.8.3 wheel
uv run python -c "import gr00t; print('GR00T installed successfully')"
export HF_TOKEN=...            # account with access to nvidia/Cosmos-Reason2-2B (gated)
export CUDA_HOME=/usr/local/cuda   # README: fixes "CUDA_HOME is unset" during finetune
export USE_WANDB=0             # examples/finetune.sh defaults USE_WANDB=1 (VERIFIED L~8); avoid wandb login dependency
```

**CUDA 13 note.** Our image is `ubuntu24.04-cuda13.0`. Isaac-GR00T targets "dGPU on CUDA 12.8" and pins `torch==2.9.0` from the `pytorch-cu128` index (`IG:pyproject.toml` L23, L88-95; VERIFIED). cu128 wheels run on a newer driver (UNVERIFIED on this box; check `nvidia-smi` driver ≥ 570).

`IG:scripts/patch_triton_cuda13.sh` exists for "Triton 3.3.1 / PyTorch 2.7 does not handle CUDA 13.x" (VERIFIED). The pinned torch is 2.9, so it is probably not needed. Run it only if `ptx_get_version` errors appear (UNVERIFIED).

**First sanity run.** Reproduce the as-shipped SO-100 example first. The docs insist on this baseline (`IG:getting_started/finetune_new_embodiment.md` L192, VERIFIED):

```bash
export NUM_GPUS=1
CUDA_VISIBLE_DEVICES=0 uv run python gr00t/experiment/launch_finetune.py \
  --base-model-path nvidia/GR00T-N1.7-3B --dataset-path ./demo_data/cube_to_bowl_5 \
  --embodiment-tag NEW_EMBODIMENT --modality-config-path examples/SO100/so100_config.py \
  --num-gpus $NUM_GPUS --output-dir /data/ckpt/so100_smoke \
  --save-total-limit 5 --save-steps 500 --max-steps 2000 \
  --global-batch-size 32 \
  --color-jitter-params brightness 0.3 contrast 0.4 saturation 0.5 hue 0.08 \
  --dataloader-num-workers 4
uv run python gr00t/eval/open_loop_eval.py --dataset-path ./demo_data/cube_to_bowl_5 \
  --embodiment-tag NEW_EMBODIMENT --model-path /data/ckpt/so100_smoke/checkpoint-2000 \
  --traj-ids 0 --execution-horizon 16 --steps 400 --modality-keys single_arm gripper \
  --save-plot-path /data/eval/so100_smoke
```

Expected shape: `Average MSE` on traj 0 falls with steps. Reference points on 1×H100 were 87.5 → 25.4 → 13.2 → 10.0 at checkpoints 500/1000/1500/2000. These are not targets (same doc L172-181, VERIFIED). **Record our own L40S numbers and time as the baseline receipt.**

**Flag spelling.** Both `--base-model-path` (docs) and `--base_model_path` (`IG:examples/finetune.sh`) appear in official files. The CLI is `tyro.cli(FinetuneConfig)` (`launch_finetune.py`, VERIFIED). Use the hyphen form as in the docs.

**Wall-clock estimate (UNVERIFIED).** No official L40S training throughput exists.
- Issue #304 reports about 2.65 s/it on 8×L40 at batch 32 per GPU (N1.5 era). A maintainer says training is "more IO bound than GPU bound".
- Issue #162 reports about 1.3 it/s on A100s at batch 16.
- For 1×L40S at global batch 32, budget **1–3 s/it**. That gives about **0.6–1.7 h per 2,000 steps** and **3–8 h per 10,000 steps**. Measure on the smoke run and re-plan.

**VRAM.** Default tuning (projector + DiT) peaks at about 35 GB per GPU (`IG:getting_started/hardware_recommendation.md`, read last night). The L40S has 48 GB. Do not enable `--tune-visual`/`--tune-llm`. These need 80 GB or more per the same doc. Issue #298 suggests `tune_visual=True` for real-robot transfer, but that is not affordable here.

**Host RAM.** Issue #375 reports an OOM-killer at checkpoint save from dataloader workers. The fix there was to reduce `--dataloader-num-workers` (4) and batch. Also keep the 8 GB swapfile added on Sept 27. If host RAM is tight, lower `--num-shards-per-epoch` (hardware doc and `finetune_config.py` docstring, VERIFIED).

---

## 2. Dataset format GR00T expects (both embodiments)

VERIFIED from `IG:getting_started/data_preparation.md` and `IG:demo_data/cube_to_bowl_5/meta/*`.

```
<dataset>/
  meta/info.json         codebase_version "v2.1", fps, features, data_path, video_path templates
  meta/episodes.jsonl    {"episode_index": 0, "tasks": ["..."], "length": 568}
  meta/tasks.jsonl       {"task_index": 0, "task": "pick up the block and place it in the tray"}
  meta/modality.json     GR00T-specific slicing of observation.state / action + video key renames
  data/chunk-000/episode_000000.parquet
  videos/chunk-000/observation.images.<cam>/episode_000000.mp4
```

**Parquet columns.** Each parquet row holds:
- `observation.state` and `action` (float32 1-D concatenations),
- `timestamp`, `frame_index`, `episode_index`, `index`, `task_index`,
- the annotation column (for example `annotation.human.task_description` = index into `tasks.jsonl`),
- optionally `next.reward` and `next.done`.

**`cube_to_bowl_5/meta/info.json`** (VERIFIED): `"codebase_version":"v2.1"`, `"fps":30`, `"chunks_size":1000`. Features are `action[6]`, `observation.state[6]`, two videos (480×640×3, av1), `timestamp`, `frame_index`, `episode_index`, `index`, `task_index`.

**Stats** (`meta/stats.json`, `meta/relative_stats.json`) are generated automatically at training start by rank 0 (`IG:gr00t/data/dataset/factory.py` L56-60, VERIFIED). **If the action `delta_indices` length changes, the stats must be regenerated.** Otherwise an `IndexError` shape mismatch occurs (`IG:getting_started/data_config.md` L58-90, VERIFIED):

```bash
uv run python gr00t/data/stats.py --dataset-path <ds> --embodiment-tag NEW_EMBODIMENT --modality-config-path <cfg.py>
```

**Constraints and warnings:**
- The action horizon must be **≤ 40**. N1.7's `max_action_horizon` is 40, and a larger horizon errors (issue #644, VERIFIED report).
- Issue #742 (open) reports that padded action dimensions leak into valid predictions, because noise enters the DiT before the loss mask. The fix is behind `strict_action_padding_mask`, which defaults to False. It is unmerged as of the thread. This is **a real accuracy caveat for low-DoF embodiments** like our 7-D arm. Note it; there is no action for us.
- Issue #663 warns about action–state step jumps in sim-collected data. **Record the commanded target as `action` and the measured joint position as `state` at the same tick. Keep the controller smooth** (no teleporting between waypoints).

---

## 3. Line B — UR5e + Robotiq 2F-85 (NEW_EMBODIMENT)

### 3.1 Embodiment choice

**Recommendation: fixed-base arm for the GR00T pilot.** The independent review already flagged that the scene has no mobile base, so "wheeled" is not established (`Review and Next Plan 2026-09-28.md`, finding 6). A wheeled base adds 2–3 base-velocity action dimensions and a navigation phase, and nothing in the docs requires it for pick-and-place. Add a base later only as an explicit, separate milestone.

**State/action: joint space**, mirroring the SO-100 pattern that is VERIFIED to work:
- `single_arm`: 6 UR5e joints, action RELATIVE / NON_EEF / DEFAULT
- `gripper`: 1 value (`gripper_right_driver_joint` target in [0, 0.8] rad, the range read from our compiled model on Sept 27), action ABSOLUTE

Rationale: `IG:getting_started/data_config.md` L193-203 says relative is smoother, and the gripper should be absolute. It also says to store **absolute** state and action in the dataset, because the processor converts them to relative.

**Cameras.** Add two MuJoCo cameras to `ur5e_2f85_scene.xml` with `MjSpec`:
- `front`: fixed third-person view. This doubles as the demo-video camera the project still lacks.
- `wrist`: attached to `wrist_3_link`.

Render both with `mujoco.Renderer` at 480×640. UNVERIFIED engineering, but standard MuJoCo API.

**FPS: 30.** This matches `cube_to_bowl_5` and the SO-100 config. Control at 30 Hz with actuator position targets, and step physics at the model timestep in between.

### 3.2 `meta/modality.json` (Line B)

The shape is VERIFIED against `IG:examples/SO100/modality.json`; our dimensions differ.

```json
{
  "state":  {"single_arm": {"start": 0, "end": 6}, "gripper": {"start": 6, "end": 7}},
  "action": {"single_arm": {"start": 0, "end": 6}, "gripper": {"start": 6, "end": 7}},
  "video":  {"front": {"original_key": "observation.images.front"},
             "wrist": {"original_key": "observation.images.wrist"}},
  "annotation": {"human.task_description": {"original_key": "task_index"}}
}
```

### 3.3 Modality config `transfergap/configs/ur5e_2f85_config.py`

This is a direct adaptation of `IG:examples/SO100/so100_config.py` (VERIFIED structure). Only one `NEW_EMBODIMENT` config may be registered per process (`IG:getting_started/policy.md` L44-45, VERIFIED).

```python
from gr00t.configs.data.embodiment_configs import register_modality_config
from gr00t.data.embodiment_tags import EmbodimentTag
from gr00t.data.types import ActionConfig, ActionFormat, ActionRepresentation, ActionType, ModalityConfig

ur5e_2f85_config = {
    "video": ModalityConfig(delta_indices=[0], modality_keys=["front", "wrist"]),
    "state": ModalityConfig(delta_indices=[0], modality_keys=["single_arm", "gripper"]),
    "action": ModalityConfig(
        delta_indices=list(range(0, 16)),               # ≤ 40 (issue #644)
        modality_keys=["single_arm", "gripper"],
        action_configs=[
            ActionConfig(rep=ActionRepresentation.RELATIVE, type=ActionType.NON_EEF, format=ActionFormat.DEFAULT),
            ActionConfig(rep=ActionRepresentation.ABSOLUTE, type=ActionType.NON_EEF, format=ActionFormat.DEFAULT),
        ],
    ),
    "language": ModalityConfig(delta_indices=[0], modality_keys=["annotation.human.task_description"]),
}
register_modality_config(ur5e_2f85_config, embodiment_tag=EmbodimentTag.NEW_EMBODIMENT)
```

Optional: `sin_cos_embedding_keys=["single_arm"]` on state for radian joints (`data_config.md` L107-117, VERIFIED option). Leave it off for the first run, so the smoke comparison changes only one thing.

### 3.4 Generating 100–200 episodes from one human demo ("MimicGen-lite")

**Why not the MimicGen library directly.** `NVlabs/mimicgen` requires implementing an env interface: `get_robot_eef_pose`, `target_pose_to_action`, `action_to_target_pose`, `action_to_gripper_action`, `get_object_poses`, `get_subtask_term_signals`, `get_datagen_info` (`mimicgen/env_interfaces/base.py` @72bd767, VERIFIED). Its datagen loop is built around robosuite/robomimic environments and hdf5 source demos. Porting our raw MjSpec scene into that is more work than re-implementing its core idea.

**The core idea** (arXiv [2310.17596](https://arxiv.org/pdf/2310.17596)):
- Split the source demo into object-centric segments.
- For a new scene, transform each segment by the SE(3) pose of its reference object.
- Interpolate between segments.
- Execute with the robot controller in physics.
- Keep only the successes.

MimicGen reports more than 50K demonstrations from about 200 source demos. DexMimicGen ([2410.24185](https://arxiv.org/html/2410.24185v1)) reports 21K from 60. DemoGen ([2502.16932](https://arxiv.org/html/2502.16932)) is a one-demo variant.

**TransferGap-specific pipeline** (UNVERIFIED plan). The human demo is the *source*, which is what makes this the project's story rather than generic data generation.

1. **Source.** WiLoR hand trajectory from the human clip, expressed in the calibrated table frame. Mark segments: approach→grasp (relative to the block) and carry→release (relative to the tray). Use pinch distance → gripper (existing `gripper_heuristic.py`).
2. **Per episode.** Sample block and tray poses from a frozen distribution, with a seed per trial. Transform each segment by `T_obj_new · T_obj_src⁻¹`. Add a joining interpolation segment.
3. **Execute** with `ur5e_ik.py` (damped least squares, with the 180°-Z base fix from Sept 27) → position actuators at 30 Hz. Real contact only: no weld or teleport of the object.
4. **Score each episode with `transfergap.metrics.score_episode`** (lift + release + settle at goal). **Keep only successes for training.** Log the failures separately; they are benchmark data, not garbage.
5. **Write** with `Gr00tDataExporter`: `create(save_root, fps=30, features, modality_config, task=..., robot_type="ur5e_2f85", vcodec="h264")`, then `add_frame({...})` per tick, then `save_episode()`.
   - API VERIFIED at `WBC:gear_sonic/data/exporter.py` L178-320.
   - Run it inside `.venv_data_collection` (`bash install_scripts/install_data_collection.sh`, VERIFIED to exist).
   - The feature dicts follow `WBC:gear_sonic/data/features_sonic_vla.py` (`{"dtype":"video","shape":[480,640,3],"names":[...]}`).
6. **Hold out.** Freeze a separate seed set (for example 30 scenes) before training, per the review's leakage warning. Never generate training episodes on those seeds.

Target **about 150 successful training episodes**, which is at or above the FAQ's "~100 for simple pick & place". At 30 Hz with about 8 s episodes, that is roughly 36k frames. This is CPU work, not GPU work: MuJoCo plus rendering, parallelizable across 16 vCPUs. Expect minutes to an hour (UNVERIFIED).

**Nebius Kubernetes / Serverless Jobs angle** (UNVERIFIED; for agent-level planning). Episode generation and scoring are embarrassingly parallel CPU work. Running them as a Nebius Serverless Job, or a k8s Job array with seed shards, is a natural "meaningful Serverless Job" deliverable. The review and the official rules call for one. Fine-tuning stays on the single L40S.

### 3.5 Fine-tune, evaluate, and serve (Line B)

```bash
cd ~/Isaac-GR00T
export NUM_GPUS=1 USE_WANDB=0
CUDA_VISIBLE_DEVICES=0 uv run python gr00t/experiment/launch_finetune.py \
  --base-model-path nvidia/GR00T-N1.7-3B \
  --dataset-path /data/ds/ur5e_block_tray_v1 \
  --embodiment-tag NEW_EMBODIMENT \
  --modality-config-path ~/transfergap/configs/ur5e_2f85_config.py \
  --num-gpus 1 --output-dir /data/ckpt/ur5e_v1 \
  --save-total-limit 5 --save-steps 1000 --max-steps 6000 \
  --global-batch-size 32 --dataloader-num-workers 4 \
  --color-jitter-params brightness 0.3 contrast 0.4 saturation 0.5 hue 0.08
```

`--max-steps 6000` is a judgment call (UNVERIFIED). The SO-100 run used 2k steps on 5 episodes; the G1 soda-can run used 20k steps at batch 32 on about 150 episodes. Start at 6k with checkpoints every 1k, and pick by open-loop trend plus closed-loop success on *development* seeds. Test seeds are kept frozen.

**Open-loop check:** same `open_loop_eval.py` command as §1, with `--modality-keys single_arm gripper`, `--traj-ids 0 1 2` and `--save-plot-path`.

**Closed-loop in our MuJoCo scene.** Start the server on a free port, not 5555:

```bash
uv run python gr00t/eval/run_gr00t_server.py --embodiment-tag NEW_EMBODIMENT \
  --model-path /data/ckpt/ur5e_v1/checkpoint-6000 --device cuda:0 --host 127.0.0.1 --port 5550
```

Client, in our sim process (API VERIFIED in `IG:getting_started/policy.md` L114-176 and L326-346):

```python
from gr00t.policy.server_client import PolicyClient
policy = PolicyClient(host="127.0.0.1", port=5550, timeout_ms=15000, strict=False)
obs = {"video": {"front": front[None, None], "wrist": wrist[None, None]},     # uint8 (B=1,T=1,H,W,3)
       "state": {"single_arm": q[None, None].astype("float32"), "gripper": g[None, None].astype("float32")},
       "language": {"task": [["pick up the block and place it in the tray"]]}}
action, _ = policy.get_action(obs)   # action["single_arm"]: (1,16,6) physical units, NOT normalized
# execute first N (e.g. 8 of 16) steps, re-query — execution horizon is a free parameter; record it in the protocol
```

Log the same state/object trace our scorer needs. The result is a closed-loop success rate on frozen seeds, which is directly comparable with the scripted/replay baseline in `transfergap compare`.

Inference speed on L40-class hardware: 7.8 Hz eager, 26 Hz with TensorRT (`hardware_recommendation.md`, VERIFIED). Eager is enough for a 30 Hz sim with action chunking.

---

## 4. Line A — Unitree G1 + SONIC (UNITREE_G1_SONIC)

### 4.1 What the tag expects

VERIFIED from `IG:gr00t/configs/data/embodiment_configs.py` L67-114 and `IG:gr00t/data/embodiment_tags.py`.

- `UNITREE_G1_SONIC = "unitree_g1_sonic"` is a **POSTTRAIN** tag. The config is pre-registered, so **no `--modality-config-path`** is passed. It also cannot be used zero-shot with the base model (`policy.md` L76).
- Video: `ego_view`.
- State: `left_leg`, `right_leg`, `waist`, `left_arm`, `right_arm`, `left_hand`, `right_hand`, `projected_gravity`.
- Action horizon: **40** steps.
- Action keys: `motion_token` (64), `left_hand_joints` (7), `right_hand_joints` (7). All ABSOLUTE and NON_EEF.

The WBC data exporter writes exactly this layout (`WBC:gear_sonic/data/features_sonic_vla.py`, modality with `original_key: action.motion_token`, `teleop.left_hand_joints`, …; VERIFIED). The recording rate is 50 Hz (`FPS = 50`).

A maintainer confirmed in `NVlabs/GR00T-WholeBodyControl#158` that N1.7 predicts the 64-D whole-body token plus hand joints, with no separate navigation command.

### 4.2 Sim collection command (UNVERIFIED combination; each flag VERIFIED to exist)

```bash
cd ~/GR00T-WholeBodyControl
export MUJOCO_GL=egl
python gear_sonic/scripts/launch_data_collection.py --sim \
  --deploy-input-type zmq --no-pico-manager --no-camera-viewer \
  --camera-port 5560 --task-prompt "walk to the table and pick up the block" \
  --dataset-name g1_block_v1 --no-text-to-speech
# separately: GEM-X/replay bridge publishing SMPL on tcp://*:5556 (proven Sept 27)
# separately: something publishing key 'c' / 'x' on ZMQ port 5580 to start/stop episodes
```

Then post-process (`WBC:docs/source/tutorials/vla_workflow.md`, VERIFIED):

```bash
source .venv_data_collection/bin/activate
python gear_sonic/scripts/process_dataset.py --dataset-path outputs/g1_block_v1 --output-path outputs/g1_block_v1_clean
```

**Check after the first episode:**
- `action.motion_token` is non-zero (C++ publishes `token_state` in `zmq` mode).
- `observation.images.ego_view` shows the scene.
- Episode length matches.

If motion tokens are all zeros, the whole G1 VLA line is blocked until fixed.

### 4.3 What is missing for G1 *manipulation* (all UNVERIFIED engineering)

1. **Scene.**
   - Copy `scene_43dof.xml` and add a table (about 0.7 m) and a block with a free joint.
   - Point `ROBOT_SCENE` in a copied wbc yaml at it. `run_sim_loop` reads `config.load_wbc_yaml()` (`WBC:gear_sonic/scripts/run_sim_loop.py` L37).
   - Add a third-person camera for the demo video.
2. **Object-state logging** for `transfergap` scoring. `base_sim` publishes robot state only. Read `mj_data.xpos` of the block body and write our episode JSONL.
3. **Hands.** Protocol v3 carries `left/right_hand_joints` (exporter L405-406 reads them from the pose message).
   - Extend our bridge to fill 7-D Dex3 hand targets, for example open/closed presets blended by WiLoR pinch distance.
   - Without this, recorded hand actions are zeros and the G1 cannot grasp. This is the most important G1 gap.
4. **Balance-induced walking.** Reaching forward makes the robot step (live_camera_teleop.md Limitations). Keep the table close and the reaches small. There is no commanded root translation on this path.
5. **Honest scope.** The published real-robot G1 result needed about 150 teleop episodes for a single task. Producing 100 or more *successful* sim G1 grasp episodes from GEM-X replay plus perturbation is uncertain.

**Recommended priority** (matches the independent review: "if G1 cannot manipulate, motion tracking stays a separate result"):
- Do Line B (arm) GR00T first.
- Attempt the G1 fine-tune only after at least 20 successful sim grasp episodes exist.

### 4.4 G1 fine-tune and sim inference

Fine-tune (VERIFIED command form, `IG:examples/GR00TWholeBodyControl/README.md`):

```bash
cd ~/Isaac-GR00T
NUM_GPUS=1 USE_WANDB=0 GLOBAL_BATCH_SIZE=32 MAX_STEPS=10000 SAVE_STEPS=2000 \
bash examples/finetune.sh --base-model-path nvidia/GR00T-N1.7-3B \
  --dataset-path ~/GR00T-WholeBodyControl/outputs/g1_block_v1_clean \
  --embodiment-tag UNITREE_G1_SONIC --output-dir /data/ckpt/g1_v1 --experiment-name g1-block
```

Serve:

```bash
uv run python gr00t/eval/run_gr00t_server.py --model-path /data/ckpt/g1_v1/checkpoint-10000 \
  --embodiment-tag UNITREE_G1_SONIC --device cuda:0 --host 127.0.0.1 --port 5550
```

Closed loop in sim (VERIFIED flag, `WBC:docs/source/tutorials/vla_inference.md`):

```bash
python gear_sonic/scripts/launch_inference.py --sim --camera-port 5560 \
  --prompt "walk to the table and pick up the block"
```

The launcher's policy-port flag default was not read. Check `--help` and pass 5550. It also uses `--deploy-input-type zmq_manager` by default, which is correct for VLA inference.

---

## 5. Consolidated pitfalls (checklist)

| # | Pitfall | Source | Mitigation |
|---|---|---|---|
| 1 | Cosmos-Reason2-2B gated → GatedRepoError | IG README L181 | Request HF access now; `HF_TOKEN` on box |
| 2 | Port 5555 taken by `nv-hostengine` | our Sept 27 log; defaults in policy.md / data_collection.md | `--camera-port 5560`, server `--port 5550` |
| 3 | `MUJOCO_GL` unset → GLFW crash headless | our Sept 27 log | `export MUJOCO_GL=egl` before tmux launchers |
| 4 | LeRobot v3 writer (current pip) incompatible | data_preparation.md L13; issues #369/#408 | Use `Gr00tDataExporter` (lerobot a445d9c9) |
| 5 | Action horizon > 40 errors | issue #644 | Keep 16 (arm), 40 (SONIC) |
| 6 | Changed `delta_indices` without regenerating stats → IndexError | data_config.md L58-90 | Rerun `gr00t/data/stats.py` |
| 7 | `action_configs` order silently mismatched | data_config.md L125 | Same order as `modality_keys` |
| 8 | wandb default on in finetune.sh | examples/finetune.sh | `USE_WANDB=0` |
| 9 | Host-RAM OOM at checkpoint save | issue #375 | workers=4, swap, lower num_shards_per_epoch |
| 10 | Padded action dims leak (low-DoF) | issue #742 (open) | Note as caveat; no action |
| 11 | Action/state step jumps in sim data | issue #663 | Smooth controller; record target + measured same tick |
| 12 | Open-loop good ≠ closed-loop good | issue #298 | Always run closed-loop on frozen seeds |
| 13 | SONIC+MuJoCo nondeterministic | WBC #274 | Multiple rollouts per trial; report variance |
| 14 | GEM-X path streams zero hands | live_camera_teleop.md; exporter L756-767 | Inject hand joints from WiLoR pinch |
| 15 | G1 sim scene empty | wbc yaml ROBOT_SCENE | Custom scene XML + yaml |
| 16 | Only one NEW_EMBODIMENT config per process | policy.md L44 | One config file per run |
| 17 | `stream_mode`=0 without PICO manager → `teleop.smpl_*` zeros | exporter L248/L675 | Harmless for training keys; verify `motion_token` |

---

## 6. Runbook order for the GPU sessions

Durations are UNVERIFIED estimates.

1. **(Before the box) User:** request access to `nvidia/Cosmos-Reason2-2B` (and HiPHI if wanted) on Hugging Face.
2. **Box, about 1 h:**
   - Install Isaac-GR00T at the pinned commit.
   - Run the SO-100 smoke fine-tune and open-loop eval.
   - Record s/it, peak VRAM (`nvidia-smi`) and MSE trend as a receipt.
   - Decides all later step budgets.
3. **Box or CPU, 0.5–1 day:**
   - Build the UR5e scene cameras.
   - Build the scripted IK expert and the MimicGen-lite generator.
   - Write about 10 episodes with `Gr00tDataExporter`.
   - Validate by loading them through GR00T's loader: a 50-step fine-tune with `--max-steps 50`.
4. **CPU, parallel:** generate about 150 successful training episodes plus a frozen held-out seed list. This is the Serverless/k8s Job candidate.
5. **GPU, 3–8 h:** fine-tune the UR5e model for 6k steps. Checkpoint each 1k. Run open-loop eval on each checkpoint.
6. **GPU+CPU:** closed-loop eval via PolicyServer on held-out seeds. Compare against the scripted/replay baseline with `transfergap compare`.
7. **G1 track (parallel, gated):**
   - Scene + object logging + hand injection.
   - Sim collection with `--sim --deploy-input-type zmq --no-pico-manager`.
   - Verify that `motion_token` is non-zero.
   - Fine-tune `UNITREE_G1_SONIC` only once there are at least 20 successful episodes.

---

## 7. Open items (UNVERIFIED, check on the box)

- The C++ deploy publishes `token_state` (motion token) in `--input-type zmq` mode, not only `zmq_manager`.
- The actual L40S s/it and peak VRAM at batch 32.
- Whether `launch_inference.py` exposes a policy-port flag (default unknown).
- Whether the tmux panes inherit `MUJOCO_GL`.
- Whether `Gr00tDataExporter` runs outside the WBC robot-model context. `create()` only needs features, modality_config and fps, but `validate_frame` imports come from the lerobot pin.
- Whether Triton needs `patch_triton_cuda13.sh` with torch 2.9 on the CUDA 13 image.
- Whether upstream #774 (native LeRobot v3) has landed after our pin. If so, it removes the v2.1 constraint, but only re-pin deliberately.
