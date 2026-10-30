# 05 — Embodiments, retargeting and simulation engineering

Research agent 5 of 6. Compiled 2026-09-29. All repositories were cloned (shallow, blob-filtered) and files read
with `git show` unless marked otherwise. **VERIFIED** = read in source at the listed commit. **UNVERIFIED** =
inferred, from a search-result summary, or not executed. Nothing here has been run on the GPU box.

## Pinned sources

| Repo | Commit / tag read | License |
|---|---|---|
| NVlabs/GR00T-WholeBodyControl (SONIC) | `b042411fae38ee4d1af9aac82a37a1f8d14d6dd0` | Code Apache-2.0, weights NVIDIA Open Model License |
| google-deepmind/mujoco_menagerie | `4d038b3feae26ec82b46a4d586379114012a8ac7` | Per model (below) |
| YanjieZe/GMR | `bb1bbe40774794fceb2a7c579a3464a28e68c844` | MIT |
| dexsuite/dex-retargeting | `3f56141bc8bd2760d5e452e382937269554ebb21` | (not checked) |
| RobotnikAutomation/robotnik_description | `jazzy-devel` @ `4bc73425d090ead4591a7091e7ef7e7dc4fe862a`; `humble-devel` @ `1a7aff1310dbc4427e0b2ae5ef83e0ffd2094504` | BSD-3-Clause (© 2025 Robotnik) |
| kevinzakka/mink | tag `v1.3.0`, HEAD `2b9a26337e22` | Apache-2.0 |
| google-deepmind/mujoco / mujoco_warp | tags `3.14.0` / `v3.14.0` | Apache-2.0 |
| NVlabs/GEM-X | (license only) | Apache-2.0 |
| rolpotamias/WiLoR | (license only) | **CC BY-NC-ND 4.0** |
| geopavlakos/hamer | (license only) | MIT code (MANO model itself is non-commercial) |

---

## 1. G1 manipulation with SONIC

### 1.1 What the SONIC MuJoCo sim actually loads — VERIFIED

- `gear_sonic/scripts/run_sim_loop.py` → `SimulatorFactory` → `gear_sonic/utils/mujoco_sim/base_sim.py`.
- Scene comes from the YAML key `ROBOT_SCENE` in `gear_sonic/utils/mujoco_sim/wbc_configs/g1_29dof_sonic_model12.yaml`:
  `gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml`, which `<include>`s `g1_29dof_with_hand.xml` and adds only
  a floor, light and a `com_marker` site. **There is no table, object or task in the SONIC sim.**
- `base_sim.py` rejects every `env_name` other than `"default"`:
  `"Invalid environment name ... Only 'default' is supported in this minimal build."`
  The RoboCasa loco-manipulation tasks (below) are **not** reachable from the SONIC sim path.
- The YAML also contains a commented alternative `scene_29dof_activated3dex.xml` under `gear_sonic/...`; that file does
  **not** exist in the `gear_sonic` tree (it exists only under `decoupled_wbc/control/robot_model/model_data/g1/`).
- `scene_43dof.xml` carries NVIDIA's own warning: *"Note that the hand model in g1_29dof_with_hand.xml is not stable
  for simulation."* Treat this as the primary G1-grasp risk.

### 1.2 Hands — VERIFIED

- G1 in this model = 29 body DoF + 2×7 **Unitree Dex3** hand DoF (43 motors). YAML: `NUM_HAND_JOINTS: 7`.
- Per hand: `thumb_0/1/2`, `middle_0/1`, `index_0/1` (3-finger). Right-hand ranges (rad):
  thumb_0 [-1.047, 1.047], thumb_1 [-1.047, 0.724], thumb_2 [-1.745, 0], middle_0 [0, 1.571], middle_1 [0, 1.745],
  index_0 [0, 1.571], index_1 [0, 1.745]. Left hand is mirrored.
- Hand link geoms are mesh + a small box on thumb_1, default `contype/conaffinity` (i.e. they **do** collide).
  Global default `friction="1.0"`. Sim step = `1/sim_frequency` = 1/200 s = **5 ms**.
- The 78-D VLA action = 64 SONIC latent tokens + 7 left-hand + 7 right-hand joint targets
  (`docs/source/tutorials/vla_workflow.md`). The hand dims are **absolute Dex3 joint positions**, not tokens.
- **Hands can be commanded from any ZMQ stream**, including our GEM-X/replay path: `docs/source/tutorials/zmq.md`,
  "Optional Stream Fields": `left_hand_joints` / `right_hand_joints`, shape `[7]` or `[1,7]`, "7-DOF Dex3 joint
  positions", allowed in protocol v1–v4 and "applied to the robot directly". The live-camera example currently streams
  wrists/fingers as zeros — adding these two fields is the missing link for G1 grasping.
- Ready-made close poses exist: `gear_sonic/utils/teleop/solver/hand/g1_gripper_ik_solver.py`
  (`_get_index_close_q_desired`, `_get_middle_close_q_desired`, …). Open = zeros; closed = preset vector; the solver
  linearly interpolates by a 0–1 grip value, with right hand = negated left. Reuse that logic (copy it; the methods are
  private) with our pinch value as the grip scalar.
- Protocol v3 note (VERIFIED, zmq.md): only wrist joints `joint_pos[23:29]` (IsaacLab order) need real values; SMPL
  carries the rest. For manipulation, feed real wrist angles, not zeros.

### 1.3 Can SONIC-G1 actually pick and lift a block in MuJoCo?

- **UNVERIFIED — nobody (in the repo or in our logs) has shown a simulated SONIC-G1 grasp.** NVIDIA's manipulation
  evidence is real-robot VLA video (GEAR-SONIC page) and the sim data-collection mode; no sim grasp success metric is
  published in the repo.
- Structural reasons it may be hard: SONIC is a motion-tracking policy (it tracks the reference; it does not reason
  about the object), the hand model is flagged unstable, 5 ms contact steps with mesh fingers, and monocular
  lower-body noise makes the robot step forward during reaches (live_camera_teleop.md "Limitations").
- Useful precedent in the same repo (different controller): `decoupled_wbc/dexmg/gr00trobocasa/robocasa/environments/
  locomanipulation/locomanip_basic.py` / `locomanip_pnp.py` define G1 tasks `LMPickBottle`, `LMPnPBottle`,
  `LMPnPAppleToPlate`, `LMBoxPnP` with checkers such as `AllCriteria(IsInContact(obj, table_target), IsUpright(obj))`.
  These run under **Decoupled WBC (N1.5/N1.6 era)**, not SONIC. They are a good source of object MJCFs and success
  predicates to copy, not a runnable SONIC task.
- **Recommendation:** make the G1 gate honest and tiered — (a) reach-and-touch (hand–object contact), (b) grasp
  (object z-lift ≥ 5 cm for ≥ 1 s with ≥ 2 finger contacts), (c) place. Report each separately. If (b) fails, the G1
  line is reported as motion transfer + contact, and the manipulation claim rests on the arm (matches the review's
  fallback).

### 1.4 How to add a table + block + tray to the SONIC scene — recipe (code-level VERIFIED, run UNVERIFIED)

Constraints read from `base_sim.py`:
- Robot joint indices are discovered by **name substring**: any joint whose name contains `hip, knee, ankle, waist,
  shoulder, elbow, wrist` is a body joint; `left_hand`/`right_hand` are hand joints; then
  `assert len(body)==29`, `len(hand)==7`. qpos addressing assumes the robot's joints come first
  (`qpos[body_joint_index + 7 - 1]`).
- ⇒ Object free joints must (1) be declared **after** the `<include>` of the robot, and (2) have names that contain
  **none** of those substrings (e.g. `block_free`, `tray_*` are fine; avoid "hand", "wrist", …).

Create `gear_sonic/data/robot_model/model_data/g1/scene_43dof_tabletop.xml` (our file, keep in our repo as a patch):

```xml
<mujoco model="g1_43dof tabletop">
  <include file="g1_29dof_with_hand.xml"/>
  <!-- copy visual/asset/floor/light blocks from scene_43dof.xml unchanged -->
  <worldbody>
    <!-- … floor + light as in scene_43dof.xml … -->
    <body name="table" pos="0.55 0 0">
      <geom name="table_top" type="box" size="0.30 0.45 0.02" pos="0 0 0.70" rgba="0.55 0.4 0.3 1"/>
      <geom name="table_leg" type="box" size="0.05 0.05 0.34" pos="0 0 0.34" rgba="0.3 0.3 0.3 1"/>
    </body>
    <body name="block" pos="0.42 -0.15 0.745">
      <freejoint name="block_free"/>
      <geom name="block_geom" type="box" size="0.025 0.025 0.025" mass="0.08"
            friction="1.5 0.02 0.001" condim="4" rgba="0.9 0.2 0.2 1"/>
    </body>
    <body name="tray" pos="0.45 0.15 0.72">
      <geom name="tray_floor" type="box" size="0.10 0.08 0.005"/>
      <geom name="tray_wall_px" type="box" size="0.005 0.08 0.02" pos=" 0.10 0 0.02"/>
      <geom name="tray_wall_nx" type="box" size="0.005 0.08 0.02" pos="-0.10 0 0.02"/>
      <geom name="tray_wall_py" type="box" size="0.10 0.005 0.02" pos="0  0.08 0.02"/>
      <geom name="tray_wall_ny" type="box" size="0.10 0.005 0.02" pos="0 -0.08 0.02"/>
    </body>
    <camera name="third_person" mode="targetbody" target="pelvis" pos="1.8 -1.8 1.4"/>
  </worldbody>
</mujoco>
```

Then point `ROBOT_SCENE` at it (edit a copy of the YAML, or pass whatever config override the tyro CLI exposes —
check `SimLoopConfig` for a wbc-yaml path flag on the box). Positions are placeholders: tune table height to G1 reach
(pelvis ≈ 0.78 m standing — UNVERIFIED). Prefer per-geom contact settings (`condim`, `friction`) over editing the global
`<option>` — the SONIC policy was validated with the stock option block; changing cone/impratio/timestep globally
changes robot dynamics. `--sim-frequency 500` (tyro field `sim_frequency`, default 200) is a candidate fix for jittery
finger contacts — **UNVERIFIED** effect on the sim2sim loop.

Ground truth for our scorer: read `data.body("block").xpos` / `cvel`, finger–block contacts from `data.contact`, and
`fallen` from pelvis height. The SONIC sim runs in its own process; the cleanest capture point is a small subclass or
patch of `DefaultEnv.sim_step` that appends these to a JSONL in our episode schema (keep it a patch file in our repo).

### 1.5 Third-person video (fixes "evidence frame shows only the floor") — VERIFIED mechanism

`DefaultEnv.__init__` only auto-creates `{"ego_view": {"mjcf_name": "head_camera", 640×480}}` when `camera_configs` is
empty; `update_render_caches()` already supports extra entries via `mjcf_name` or free-camera `params`. So: add the
`third_person` camera to the scene (above) and patch the default dict to also include
`"third_person": {"height": 720, "width": 1280, "mjcf_name": "third_person"}`. Keep `ego_view`/`head_camera`
unchanged — it is what the data exporter records as `observation.images.ego_view` for GR00T. Keep
`MUJOCO_GL=egl` and `--camera-port 5560` (5555 is taken by `nv-hostengine` on the Nebius image — Sept 27 finding).

---

## 2. Wheeled single-arm embodiment

### 2.1 Candidates in mujoco_menagerie @ `4d038b3` — VERIFIED

| Model dir | What | License |
|---|---|---|
| `universal_robots_ur10e/ur10e.xml` | **UR10e**, has `attachment_site` on `wrist_3_link` | BSD-3 (ROS-Industrial) |
| `universal_robots_ur5e/ur5e.xml` | UR5e (what was used Sept 27) | BSD-3 |
| `robotiq_2f85/2f85.xml`, `robotiq_2f85_v4/` (has `mjx_2f85.xml`) | 2F-85, `pinch` site | BSD (ROS-Industrial) |
| `stanford_tidybot/` (`tidybot.xml`, `base.xml`, `scene_base.xml`) | holonomic base (`joint_x`,`joint_y` slide + `joint_th` hinge, position actuators kp 1e6/5e4) + Kinova Gen3 + 2F-85 | base MIT; arm/gripper keep their licenses |
| `hello_robot_stretch_3/` | Stretch 3 | Apache-2.0 |
| `pal_tiago/` | TIAGo | Apache-2.0 |
| `kinova_gen3/` | Gen3 | Kinova BSD-style |

There is **no Robotnik model in menagerie** (VERIFIED by directory listing).

### 2.2 The user's real robot: public RB-KAIROS description — VERIFIED exists, conversion UNVERIFIED

`RobotnikAutomation/robotnik_description` (BSD-3, ROS 2; branches `humble-devel`, `jazzy-devel`) contains
`robots/rbkairos/rbkairos.urdf.xacro`, `rbkairos_plus.urdf.xacro`, `urdf/bases/rbkairos/rbkairos_base.urdf.xacro`,
mecanum wheel xacro and meshes. README: `ros2 launch robotnik_description robot_description.launch.py robot:=rbkairos
robot_model:=rbkairos_plus arm_type:=ur10e` ("RB-Kairos with a UR arm"; `arm_type` default `ur10e`). Also
`simulators/isaac/README.md`. This is a **public, redistributable** KAIROS twin — it resolves the "private lab USD must
not be copied" constraint. Old ROS 1 sim repos (`rbkairos_sim`, `rbkairos_common`, kinetic/melodic/noetic) also exist.
Converting xacro → URDF → MJCF needs `xacro`, `ur_description`, `robotnik_sensors`; mecanum rollers do not simulate
well in MuJoCo — replace the wheel joints with TidyBot-style planar `x/y/θ` joints for the benchmark (and say so).

### 2.3 Recommendation

- **Arm model: UR10e + Robotiq 2F-85 from menagerie** (closest public match to KAIROS UR10 + Robotiq; UR5e was an
  unnecessary mismatch). Note: `ur10e.xml` `base` has `quat="0 0 0 -1"` (180° about Z), identical to UR5e — this is
  exactly the Sept 27 X/Y sign flip.
- **Milestone 1: fixed-base** UR10e+2F85 on a stand (per the review). **Milestone 2: mobile** — attach to the TidyBot
  base (`scene_base.xml`) with `MjSpec.attach()`, labelled honestly as "holonomic base abstraction". Optional polish:
  RB-KAIROS chassis mesh as visual-only geometry on that base.
- **IK: use `mink`** (Apache-2.0, `examples/arm_ur5e.py`, `examples/mobile_tidybot.py` — whole-body base+arm IK) solving
  directly on the MJCF. This removes the URDF↔MJCF frame mismatch that produced the 7.2 mm residual (review P1 #2): the
  target frame becomes the 2F-85 `pinch` site in the same model that is simulated.
- Gripper: 2F-85 actuator range; keep the pinch heuristic (thumb-tip↔index-tip distance → 0–1 → gripper ctrl).

---

## 3. Retargeting pipelines

### 3.1 GMR (General Motion Retargeting) — VERIFIED from README @ `bb1bbe4`

- Robots: 17 humanoids incl. `unitree_g1` (29) and `unitree_g1_with_hands` (43); one wheeled humanoid
  (`galaxea_r1pro`). **No single-arm / UR support** (it is a humanoid retargeter).
- Inputs: SMPL-X (AMASS, OMOMO), BVH `--format lafan1|nokov`, Xsens BVH (`scripts/xsens_bvh_to_robot.py`), OptiTrack
  FBX, PICO/XRoboToolkit streaming, GVHMR monocular-video output.
- Commands: `python scripts/bvh_to_robot.py --bvh_file X --robot unitree_g1 --save_path out.pkl --format nokov`;
  batch: `scripts/bvh_to_robot_dataset.py`.
- IK configs are JSON (`general_motion_retargeting/ik_configs/bvh_nokov_to_g1.json`: root `Hips`→`pelvis`, per-bone
  scale table, two IK match tables).
- **HiPHI** (55-joint Y-up BVH, 90 Hz, Noitom) is **not a listed format**. Expected work: a new
  `bvh_hiphi_to_g1.json` cloned from the Nokov config + loader tweaks for joint names. UNVERIFIED until one HiPHI BVH
  header is inspected (access is gated).
- SMPL-X body models are **non-commercial research license** — matters for the product story; BVH routes avoid SMPL-X.

### 3.2 SONIC's own motion tooling — VERIFIED (files exist, not run)

- `gear_sonic/data_process/extract_soma_joints_from_bvh.py` — BVH (NOVA 78-joint skeleton) → 26 SOMA joints.
- `gear_sonic/data_process/convert_soma_csv_to_motion_lib.py` — G1 29-DoF `joint_pos/body_pos/body_quat` CSV or PKL →
  motion_lib PKL (includes IsaacLab↔MuJoCo reordering).
- `gear_sonic/data_process/export_motion_to_deploy.py` — motion_lib → `gear_sonic_deploy` reference CSVs
  (`joint_pos.csv, joint_vel.csv, body_pos.csv, body_quat.csv, body_lin_vel.csv, body_ang_vel.csv, info.txt,
  metadata.txt`, 50 Hz), same layout as `gear_sonic_deploy/reference/example/*`.
- G1 order tables `G1_ISAACLAB_TO_MUJOCO_DOF` etc. live in `gear_sonic/envs/manager_env/robots/g1.py`.

### 3.3 Recommended HiPHI → G1 route (deterministic, benchmark-friendly)

`HiPHI BVH → GMR (new hiphi config) → G1 qpos (MuJoCo order) → FK for body_pos/quat → convert_soma_csv_to_motion_lib
→ export_motion_to_deploy → reference/hiphi/<clip>/ → ./deploy.sh --motion-data reference/hiphi/ sim → press T`.
This plays HiPHI as a **SONIC reference motion** — no ZMQ timing, exactly repeatable, ideal for scored trials. Streaming
the same qpos over **Protocol v1** (`joint_pos`/`joint_vel`, 29, IsaacLab order) is the live alternative. Add
`left/right_hand_joints` from HiPHI finger channels or a contact-time grasp schedule. End-to-end UNVERIFIED.

### 3.4 Hands → gripper

- **Drop WiLoR for anything product-facing: its license is CC BY-NC-ND 4.0** (VERIFIED, `license.txt`). HaMeR code is
  MIT but depends on MANO (non-commercial).
- GEM-X (Apache-2.0) already estimates the full SOMA body incl. hands (77 joints; tutorial: "GEM-X estimates hands, so
  wiring them through is a natural extension"). Using GEM-X hand keypoints for the pinch signal = one model, one frame,
  permissive license. Finger accuracy is UNVERIFIED.
- `dex-retargeting`'s pattern for parallel grippers (`configs/teleop/panda_gripper.yml`, thumb-tip/index-tip vector) is
  still the right scope for the 2F-85.

### 3.5 Object-relative (interaction-preserving) retargeting — why kinematic mimicry is not enough

Kinematic mimicry copies the hand path; a different body size/arm means the gripper misses the object. The field has
moved to preserving the human↔object relation:
- **OmniRetarget** (arXiv 2509.26633; interaction mesh + Laplacian deformation; G1 loco-manipulation; code +
  `huggingface.co/datasets/omniretarget/OmniRetarget_Dataset`). Repo location UNVERIFIED.
- **HDMI** (arXiv 2509.16757, `github.com/LeCAR-Lab/HDMI`, HEAD `32282f6dcf26`): monocular video → human+object
  trajectories → RL co-tracking of robot and object on G1; 14 sim tasks, 6 real.
- Search leads not read (UNVERIFIED): HOI-Retarget (arXiv 2609.34674), TopoRetarget (2606.16272), Weave (2609.16683),
  Unified retargeting with learned point-cloud correspondence (2609.02134), Direct Dynamic Retargeting (2605.23762).
- **Practical adoption for us (cheap):** express the demo in the **object frame** — grasp pose = T_obj→hand at contact,
  place pose = T_tray→obj at release — and re-solve IK per embodiment from the simulated object pose. This is exactly
  the "object-relative target adjustment" correction the review proposed as the paired experiment:
  condition A = raw kinematic replay, condition B = object-relative retarget, same trials.

---

## 4. Fast parallel evaluation and rendering

| Tool | Status (tag) | Fit for us |
|---|---|---|
| MuJoCo (CPU) | 3.14.0 — same version SONIC's `.venv_sim` installed | Arm episodes with a scripted/mink controller are cheap on CPU; run N processes. **Default choice.** |
| MuJoCo Warp | `v3.14.0` (matches MuJoCo 3.14) | GPU-batched physics; worth it only for thousands of rollouts or RL. Not needed for a few hundred scored episodes. |
| MuJoCo Playground / Madrona | `v0.2.0` | JAX/Warp + batch rendering (pick-cube vision example). Overkill now; relevant if we train an RL residual. |
| ManiSkill3 | `v3.0.1` | GPU-parallel; would mean porting scenes. Skip. |
| Isaac Lab | `v3.0.0-beta2` | SONIC's training/eval uses Isaac Lab (`gear_sonic/eval_agent_trl.py`, `num_envs=128`) for motion-tracking metrics. Good for "does SONIC track this HiPHI clip" batch metrics; no objects. |

- The **SONIC G1 loop cannot be batched in one process**: it is `run_sim_loop.py` + C++/TensorRT `deploy.sh` talking over
  DDS + ZMQ (ports 5555/5556/5557). Parallelism = many isolated sim+deploy pairs. **One Kubernetes pod per worker**
  gives each pair its own network namespace, so ports/DDS never collide — a clean use of Nebius Managed Kubernetes /
  Serverless Jobs (deployment specifics belong to the infra agent). CPU-heavy, light GPU (TensorRT inference is small).
- Headless render: `MUJOCO_GL=egl`; `mujoco.Renderer(model, 720, 1280)` with a named camera for the arm; for G1 use the
  `third_person` camera patch in §1.5.

---

## 5. Block-to-tray task — concrete recipe for both robots

Shared protocol (freeze as `protocol_id=block_tray_v1` so `validate_protocol_consistency` holds):
block 5 cm cube, 0.08 kg, friction 1.5; tray 20×16 cm, 4 cm walls; table top z = 0.72 m (arm) — G1 table height tuned
once and frozen; goal_xyz = tray centre + block half-height; `min_lift_m 0.05`, `position_tolerance_m 0.05`,
`settle_duration_s 0.5`, `max_settle_speed_m_s 0.02`; log at ≥ 50 Hz; `forbidden_collision` = robot–table hard hit
(latched); `fallen` = G1 pelvis z < 0.5 m (latched).

**Arm (UR10e + 2F-85):**
1. `MjSpec` load `universal_robots_ur10e/ur10e.xml`; attach `robotiq_2f85/2f85.xml` at `attachment_site`; add stand,
   table, block (freejoint), tray, `third_person` camera; merge mesh assets (Sept 27 gotcha); save + reload + step 200.
2. Controller: mink IK to the `pinch` site; waypoints pre-grasp (+10 cm) → grasp → close → lift 15 cm → move over tray →
   release. First scripted (oracle object pose), then human-derived (object-relative targets from the demo).
3. Milestone 2: attach to TidyBot base, use `mobile_tidybot.py`-style whole-body IK.

**G1 (SONIC):**
1. `scene_43dof_tabletop.xml` per §1.4; start sim with image publish on 5560 and deploy with
   `--input-type zmq --zmq-host localhost sim`.
2. Motion: GEM-X replay (`soma_pt_to_sonic_v3.py`) or HiPHI reference (§3.3), plus `right_hand_joints` from the
   index-close preset scaled by pinch; real wrist angles in `joint_pos[23:29]`.
3. Score tiers (touch / grasp / place) separately; retain failures.

Both robots write the same JSONL episode schema consumed by `transfergap evaluate/compare`.

---

## 6. Risks and open items (ranked)

1. **G1 grasp in sim may not work at all** (unstable hand model warning, 5 ms step, tracking policy ignores the object).
   Budget one day; fall back to arm-only manipulation + G1 motion/contact result.
2. HiPHI access is gated and its skeleton needs a new GMR config.
3. Licensing for a product: WiLoR (NC-ND), MANO, SMPL/SMPL-X are non-commercial; GEM-X, mink, menagerie UR/Robotiq/
   TidyBot, robotnik_description are permissive. SONIC/GR00T weights are under the NVIDIA Open Model License (read its
   terms before claiming commercial use — not checked here).
4. SONIC sim's `env_name` restriction means every scene change is a local patch to NVIDIA files — keep patches in our
   repo and re-apply by script; pin the commit above.
5. `deploy.sh` treats unknown flags as the positional `sim/real` argument (tutorial warning) — never add
   `--zmq-port/--zmq-topic`.
