# TransferGap starter

> **Partly historical (marked 2026-10-06).** This is the original starter README (Sept 2026). For the current pipeline and results read `../PIPELINE.md`, `../STATUS_AND_OBJECTIVE.md` and `../DOC_INDEX.md`.

Episode scoring, paired comparisons, arm simulation, recorded Cosmos critique,
and a G1 SONIC contact pilot are implemented here. The pilot's reaching motion is
IK-authored; it is not human motion reconstruction. GR00T training and hardware
robot drivers are not implemented.
See [research review](../TransferGap%20Research%20Review.md) and
[KAIROS stack audit](../KAIROS%20Stack%20Audit.md).

## Run locally

The [static evidence report](static_report/README.md) runs locally without a GPU or
API key. The G1 and Cosmos result summaries are under `results/`.

Python 3.10+; evaluation uses the standard library. Run from this directory:

```bash
python3 -m transfergap doctor
python3 -m unittest discover -s tests -v
python3 -m transfergap evaluate examples/fixture_episodes.jsonl --allow-fixtures
```

The examples are hand-authored **fixtures**, not simulator or NVIDIA results.
Without `--allow-fixtures`, evaluation rejects them. The default report groups
simulation, hardware and fixtures separately, along with robot/method/sensor/protocol.

## Episode contract

One JSON object per line; see `examples/fixture_episodes.jsonl`. Required metadata:
`schema_version`, `source`, `trial_id`, `demo_id`, `scene_id`, `seed`, `robot`,
`method`, `sensor`, `protocol_id`, `frame_id`, and `units`. Use `method` to distinguish
replay, autonomous, planner/controller revisions and ablations. Freeze the task
definition under a protocol ID; never change success tolerances after inspecting tests.

Each state includes strictly increasing time in seconds, object position in metres,
object velocity in metres/second, release state, forbidden-collision state and fall
state. The scorer requires a lift and a contiguous released/settled suffix at the
goal. This is a **sampled-state** predicate: log at adequate frequency and latch
collision/fall events between samples in the simulator adapter. It does not prove
correct physics, object identity, or sensor calibration from an arbitrary JSON file.

Optional reference positions must use the same calibrated frame and sample times.
The metric is sample RMSE, not joint error, DTW, or a claim that every successful
robot must follow the same path. Orientation-sensitive tasks need another predicate.
Future simulator writers must persist asset/policy revisions, video, model-call
receipts and a manifest alongside the episode log; this first version does not
authenticate the origin of a submitted trace.

For a paired comparison:

```bash
python3 -m transfergap compare runs/condition_a.jsonl runs/condition_b.jsonl
```

Each file must contain one condition with identical trial keys and task settings.
The result is B minus A success in percentage points, with a paired bootstrap
interval. Use independent trial blocks; correlated retries or many seeds from one
demo do not create independent evidence. Small-n bootstrap intervals can be
degenerate. Summary success intervals use Wilson's binomial interval and have the
same independence caveat.

## Hosted NVIDIA models

Set the variables in `.env.example` in your shell. No automatic dotenv loading,
training submission, deployment or credential discovery occurs in the CLI.
Set exact model IDs available to your account. `GET /v1/models` is evidence of
inference availability, **not fine-tuning support**.

```bash
python3 -m transfergap plan --robot generic_wheeled_arm \
  --goal 'Pick up the block and place it in the tray' \
  --receipt runs/nemotron-plan.json

python3 -m transfergap review-video /path/to/rollout.mp4 \
  --goal 'Pick up the block and place it in the tray' \
  --receipt runs/cosmos-review.json
```

These commands make real billable API requests when configured. They never command
a robot. Receipts capture response/model identity, latency, usage and a request
hash; failures remain failures. Credentials and raw media are not stored in receipts.
The Cosmos adapter sends a short MP4 using the vLLM-style `video_url` data URI;
endpoint compatibility, video limits and structured responses must be tested with
the selected service. It is not a validated real-time monitor.

Nemotron JSON is checked against permitted skill names. This is only a proposal
contract, not a motion planner, grounding check or hardware interlock. Cosmos output
is retained for review and cannot override the independent benchmark label.

## Robot adapter work

`RobotAdapter` defines reset/observe/execute/ground_truth/stop. `RobotSpec` makes
the embodiment, action ordering, frame, control rate and revisions explicit.
The Sonic action contract checks the current 78D N1.7 representation; a 14D or
17D legacy action is rejected. This does not implement Sonic's transport/decoder.

`configs/kairos_legacy.template.json` is an inventory template informed by the
user's ROS 2 Humble/UR10 simulation notes. It is not a commissioned robot profile.
Private lab source and assets are deliberately absent from this public-style starter.

## Next executable milestone

1. On the GPU machine reproduce the official [Sonic MuJoCo quickstart](https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/quickstart.html).
2. Test the [GEM-X webcam/recording bridge](https://nvlabs.github.io/GR00T-WholeBodyControl/tutorials/live_camera_teleop.html).
3. Run one compatible [GR00T example](https://github.com/NVIDIA/Isaac-GR00T), then record exact code/weight revisions.
4. Produce the first simulator episode with real contact and score it here.
5. Verify Cosmos access and the [N1.7/Sonic training workflow](https://nvlabs.github.io/GR00T-WholeBodyControl/tutorials/vla_workflow.html) before launching fine-tuning.

Keep the lab's working Isaac Sim 4.2/ROS environment separate from newer GR00T and
Sonic dependencies. No upstream repository, checkpoint or lab controller has been
modified by this starter.

## Arm simulator (`transfergap/sim/`)

Local UR5e or UR10e + Robotiq 2F-85 block-to-tray scene (MuJoCo >= 3.2, CPU only). Scripted DLS-IK
pick-and-place with real contact grasping (no welds). Assets from mujoco_menagerie (Apache-2.0).

```bash
bash transfergap/sim/setup_sim.sh            # venv + menagerie sparse clone (UR5e, UR10e, 2F-85; pinned commit)
.venv/bin/python -m transfergap.sim.sweep --n 30 --out runs/sim/sweep.jsonl --video runs/sim/demo.mp4 [--robot ur10e]
.venv/bin/python -m unittest tests.test_sim
```

Gap budget (oracle substitution, paired seeds): `python -m transfergap.sim.gap_budget dev|heldout`
runs the frozen v1 protocol (UR5e; perception/calibration/timing). `--protocol v2 --robot ur5e|ur10e`
adds a kinematics/retargeting stage (constant joint-space error on the joint command, oracle = exact
IK) and per-component RNG streams; results go to `results/gap_budget_v2_<robot>/`. Held-out runs
refuse to start until the protocol (and, for v2, the dev results) are committed. All error
magnitudes are assumptions (see `sim/errors_v2.py`).

Perturbations (`sim/perturb.py`) model transfer-gap sources: `target_offset_m`, `tcp_offset_m`,
`grip_force_scale`, `timing_scale`; each is scored as its own `method` label
(`scripted_ik[<perturbation>]`). Extra fields `phase` (per state) and `perturbation` (episode)
are ignored by the scorer.
