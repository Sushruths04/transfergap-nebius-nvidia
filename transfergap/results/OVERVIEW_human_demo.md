# Human-demo transfer results — overview (lane B, 2026-10-02)

What the system does: one human demonstration → the robot follows the human's retargeted hand path (style), on
several robots; each failure is attributed to a pipeline stage by oracle substitution, for **task success and
style fidelity**; the largest stage selects a fix (rule, cross-checked by Nemotron 3 Super), which is frozen in
git and verified on held-out seeds (1000–1059, n = 60 paired). Every number below links to its folder.

## 1. Real human demo → two arms (Pexels clip 8135753, via GEM-X)

Free-licence video of a man picking a notebook off a desk and dropping it into a box; GEM-X 3D pose →
`demo/gemx.py`; grasp/release frames hand-annotated (`demo/clips.py`). His style: reach from ~35 cm above, lift
~20 cm over the rim, drop from ~22 cm, whole cycle 1.5 s (≈ 6× robot pace).

| step | stage found (dev) | fix (rule; Nemotron) | UR5e held-out | UR10e held-out | folder |
|---|---|---|---|---|---|
| 0 | — | — | 0/60 | 0/60 | `demo_budget_v1_demo1bc4be60_{robot}` |
| 1 | timing (human pace) | speed_cap_3 (rule only) | 10/60, +16.7 pp [8.3, 26.7] | 15/60, +25.0 pp [15.0, 36.7] | same |
| 2 | perception | look_again (agent agreed) | 35/60, +41.7 pp [28.3, 55.0] | 35/60, +33.3 pp [16.7, 50.0] | `..._{robot}__after-speed_cap_3` |
| 3 | calibration | touch_probe_calibration (agent agreed) | 50/60, +25.0 pp [8.3, 41.7] | 51/60, +26.7 pp [11.7, 41.7] | `..._{robot}__after-speed_cap_3+look_again` |
| 4 | timing (remaining) | speed_cap_2 (agent agreed; only option left) | **57/60**, +11.7 pp [5.0, 20.0] | **60/60**, +15.0 pp [6.7, 23.3] | `..._{robot}__after-speed_cap_3+look_again+touch_probe_calibration` |

Cumulative vs no fix: UR5e +95.0 pp [88.3, 100.0], UR10e +100.0 pp. Style: path RMSE to the human path
13.9 → 5.0 cm (UR5e), 9.2 → 2.9 cm (UR10e) — slowing down lets the arm trace the human's arc more closely; the
human's absolute pace is what is given up (speed-profile correlation stays near 0). The step-3 stack (83/85%) was
reproduced exactly in a Nebius Serverless Job.
Reproduced exactly in a Nebius Serverless Job: `receipts/aijob-e00a6zskrtabq957zz.*`.
Figure: `demo_style_figures/style_paths_demo1bc4be60_seed1001.png`.

## 1b. Generalization to more demos (same clip, other objects and motions)

Three more pick-and-place cycles of the same Pexels clip (markers, one orange marker, a notepad), annotated by
frame inspection; pre-registered tests (`demo_generalization_v1/`, `demo_generalization_v2/`):
- **v1 (negative):** the notebook's 4-fix stack applied unchanged → 0/60 on every demo and arm, although the
  robots followed the human path within 2–4 cm. Diagnosis: in quick flicks the human hand follows the object
  down into the box after release (11–18 cm), and for the flat notepad it sweeps 4.7 cm below grasp height;
  copying that collides even with every stage oracled ("the style itself is infeasible").
- **v2:** adding one style-safety projection (`safe_path`: copied legs never go below the contact height,
  everything else kept) → one fixed stack transfers: notebook 57/60 and 60/60 (unchanged), markers 51/60 and
  25/60, orange marker 46/60 and 58/60, notepad 58/60 and 58/60 (UR5e, UR10e; all gains' CIs exclude zero).
  Style cost of the projection: path RMSE +1.5–2.5 cm vs the same stack without it.

## 1c. A different person (Pexels 7205253, woman, two-handed box move)

- `demo_generalization_v3` (negative): 0/60 both arms — the video-only "object rests under the lowest hand point"
  rule mislocated the object for a pick-from-stack (grasp ~4 cm too high). Fixed with an explicit
  `object_height="hand_at_grasp"` option for this clip only (notebook demo verified unchanged).
- `demo_generalization_v4`: person 1's fixed stack HURTS her: UR5e 11/60 → 0/60 (−18.3 pp), UR10e 4/60 → 0/60.
  No universal recipe.
- Per-demo diagnosis loop on her demo (`demo_budget_v1_demo5f8bdc01_*`): her budget is different (perception
  first; slowing down HURTS her, −15 pp on UR5e dev; UR10e oracle_all 0% = style infeasible for that arm).
  Step 1 look_again: UR5e 11→41/60 (+50.0 pp), UR10e 4→17/60 (+21.7 pp). Step 2 touch probe: UR5e 41→57/60
  (+26.7 pp; **95%**, no speed change needed), UR10e 17→14/60 (n.s.). Step 3: rule and Nemotron disagreed on
  both arms; head-to-head on held-out: UR5e rule (speed_cap_3, a no-op for her 2× pace) 57/60 vs agent
  (safe_path) 0/60; UR10e agent (speed_cap_3, no-op) 14/60 vs rule (safe_path, via the new style-feasibility
  check) 0/60. safe_path — derived from person 1's flicks — is harmful for her style. Score: 1–1.
- Lessons: the diagnosis must be per demo/person; corrections that are no-ops for a demo (speed cap above
  the human pace) should be filtered; the style-feasibility → safe_path rule is not safe as a default.

## 1d. Final: safe_path_v2 — two people, five real demos, both arms (`demo_generalization_v5/`)

Diagnosing why safe_path broke person 2 (the clamped retreat dragged the block sideways with open fingers) led
to `safe_path_v2` (lift clear first after the release, then follow the human). Selected on dev seeds 0–19
(v2 ≥ v1 everywhere; person-2 UR10e 0/20 → 19/20), then pre-registered held-out:

| demo | UR5e (no fix → stack) | UR10e (no fix → stack) |
|---|---|---|
| person 1 notebook | 0 → 57/60 | 0 → 60/60 |
| person 1 markers | 0 → 51/60 | 0 → 25/60 |
| person 1 orange marker | 0 → 46/60 | 0 → 58/60 |
| person 1 notepad | 0 → 58/60 | 0 → 58/60 |
| person 2 box, own diagnosed stack | 11 → **60/60** | 4 → **55/60** |
| person 2 box, person 1's stack (single recipe) | 11 → 60/60 | 4 → 50/60 |

All gains' 95% CIs exclude zero. Style cost of the lift-first retreat for person 2: path RMSE +1.0–1.2 cm.
Remaining weak cell: person-1 markers on UR10e (25/60).

## 2. Synthetic demo (controlled noise) → two arms

`demo_budget_v1_syn0_{robot}`: the stage that breaks the task (perception, calibration) is not the stage that
breaks style (timing for path error; hand-estimation noise for speed profile). Held-out look_again: UR5e
29→47/60 (+30.0 pp), UR10e 25→45/60 (+33.3 pp), style unchanged. Synthetic, NOT human data.

## 3. Second real demo, HiPHI motion capture (exploratory, dev only)

`demo_budget_v1_demofbc7ecf3_{robot}` + `EXPLORATORY.md`: two-handed box lift; needed object-normalised offsets
(box ~58 cm vs 4 cm block). Even with every stage oracled, copying the "push the box down" carry collides →
a separate failure class: the style itself is infeasible for this robot. HiPHI is non-commercial; raw data is
never committed.

## 4. G1 humanoid copying the same real demo

`g1_style_v1/` (+ PROVENANCE.md): G1 right hand follows the same retargeted human path (`g1/plan_reach.py
--demo-plan`), frozen v1 grasp calibration, per-seed true target; 10 seeds × 3 rollouts per condition.

| G1 condition | touch | grasp | place |
|---|---|---|---|
| human pace (5.9×) | 30/30 | 0/30 | **0/30** |
| speed cap 3× | 30/30 | 18/30 | **8/30** |
| robot pace | 30/30 | 24/30 | **20/30** |

Same diagnosis as the arms: human pace is the dominant failure; slowing down restores the task. At robot pace
G1 places 20/30 while copying the human's ~24 cm lift (its earlier straight-line IK baseline: 19/30 and 17/30).
Wrist path RMSE to the human-derived path: median 5.5 cm (robot pace) – 6.4 cm (human pace).

## 5. G1 copying person 2 (`g1_style_person2_v1/`)

0/30 grasps in every condition (touch 13–17/30); wrist path RMSE 16–19 cm. Cause visible before execution: the
plan's IK cannot reach her path (max error 28–31 cm) because she walks ~0.8 m while reaching and the G1 stands
still — an embodiment (reachability) gap, flaggable by a cheap kinematic pre-check.

## 6. Real-time mode (B8) — camera → GEM-X live → UR arm + G1, in a browser

`live/` (VM side `run_live_vm.py`, laptop side `run_live_laptop.sh <vm-ip>`): laptop webcam → SSH tunnel → GEM-X
live on the L40S → per-frame hand/body keypoints → (a) a UR arm following the right hand in MuJoCo (live IK, pinch =
gripper) and (b) the G1 under SONIC, both rendered on the VM and streamed back as MJPEG next to the camera view with
live latency and path-lag readouts; the session is saved and converts into a HumanDemo (`live/session_to_demo.py`).
Measured in VM rehearsals with a video stand-in (2026-10-02): GEM-X live 9.5–9.8 fps; frame-on-VM → arm command
109–116 ms median. G1: the full-body SMPL stream (upstream live-camera path) fell after 3–100 s with the legs hidden
behind a desk; our "virtual VR headset" bridge (`live/g1_vr3pt.py`: wrist and neck frames from monocular keypoints
→ SONIC's VR 3-point mode, the locomotion planner balances the legs, pinch closes the Dex3 hand) kept the G1 standing
for 150 s (pelvis 0.75–0.79 m, arms following the replayed person, hand touched the block) before one fall; the
supervisor restarts it automatically. With GEM-X live on a stock video the G1 copied the person pressing both hands
into the desk and tipped over (3 falls in 90 s); the live version of the safe-path rule (wrists never below the
block's top, torso kept upright, wrist targets ≤ 1 m/s) kept it standing for 205 s before its first fall on the same
input (0 falls during the 120 s recording
`runs/videos/live_demo_120s.mp4`, gitignored). Not yet run with the user's own webcam.

## 7. Kinematic feasibility pre-check — "is this style possible for this robot?" (`feasibility_precheck_v1/`)

CPU only, no rollout, ~1 s per demo and arm: walk the copied human path with converged IK on the robot model and
check robot/table/tray overlap at each pose (`sim/feasibility.py`; G1 via the frozen G1 planner's IK). Thresholds
frozen before the run (IK error 2 cm, penetration 5 mm). Against the earlier simulated outcomes: **24/26 cases
agree; all 11 infeasible styles flagged** (G1 person 2 unreachable by 27–29 cm; HiPHI box pushed into the table;
person-1 markers/orange/notepad sweeps and dips into the table) and every working safe_path_v2 variant passes.
One false alarm (person 2 on UR5e: her approach from below the table top is stopped by the table and still works);
the other miss is a real per-layout G1 planner failure — over all 180 G1 rollouts, pre-check-flagged plans grasped
**0/99**, unflagged robot-pace plans 24/27 (seed 106 was the only robot-pace seed with 0/3, and its plan had a
49 cm IK error). Use per trial layout, before spending GPU time.

## 8. Which human pose estimator? (`pose_estimator_bakeoff_v1/`, `_v2/`)

Same clips, annotations, demo builder, fix stacks and held-out seeds; only the estimator differs. GEM-X (NVIDIA,
temporal) vs Fast SAM 3D Body (ECCV 2026, per-frame, SAM 3D Body weights; 6.2 fps on the L40S, 6.7 fps with
TensorRT engines). v1: GEM-X 528/600 vs Fast SAM 459/600 held-out — newer is not better on average (its pinch path is
1.5–13x jumpier), but it fixes the weakest cell. v2 (pre-registered): choose the estimator per demo x arm on dev seeds
(candidates incl. Fast SAM + the pipeline's existing 0.2 s smoothing) → **576/600 held-out (96%) vs 528/600 (88%)**;
markers/UR10e 25 → 60/60 (+58.3 pp [45.0, 71.7]), markers/UR5e 51 → 60, person 2/UR10e 55 → 60, one cell −1.
The pose estimator is one more stage of the transfer gap, chosen per demo like the fixes.

## 9. The author's own demonstration (`user_demo_v1/`, own camera)

A 50 s recording (Logitech Brio 100, 1280x720 at 21.4 fps; private, never committed) → GEM-X offline. The annotated
right-hand pick-and-place (grasp f862, release f926 into a box 15 cm up) was pre-checked (G1 feasible; arms: approach
dips 1.7 cm into the table) and run with the frozen single stack of §1d, no re-tuning: **UR5e 35/60 → 59/60
(+40.0 pp [28.3, 51.7]), UR10e 30/60 → 56/60 (+43.3 pp [31.7, 55.0])**; with the fixes the robot traces the author's
S-shaped carry and 18 cm lift (`user_demo_v1/style_figure/`). Whole take replayed to the G1 through SONIC (SMPL v3,
`live/g1_replay.py` + `live/pt_stream.py`): no fall, T-pose/reach/carry copied, arm-spread correlation 0.88; and to two
UR arms (`live/arm_replay.py`, left/right hand): the arms follow but direct copying does not grasp the block — the
planned, corrected pipeline does. Videos (gitignored): `runs/videos/take1_final.mp4`, `user_ur5e_fixes_seed1001.mp4`.

## 10. Overnight additions (2026-10-02 night)

- **Nemotron 3 Super on the author's demo** (`user_demo_v1/summary.md`): agrees with the rule on 4/4 decisions;
  where the strict rule stops, its extra fix (safe_path on UR10e) gives 51 → 56/60 (+8.3 pp [1.7, 15.0]).
- **Cosmos-Reason2-2B fine-tuned as a success critic** (`cosmos_critic_ft_v1/`): LoRA on 640 labelled rollout clips
  on the Nebius L40S. Test accuracy 63.6% → **94.1%** (+30.5 pp [24.5, 36.8]); failures caught 17.5% → 86.6%; on an
  unseen person's demo 76.7% → 93.3%. Simulator renders only.
- **Three pose estimators** (`pose_estimator_bakeoff_v3/`): GEM-X 528, Fast SAM 3D Body 459, RTMW3D 0 of 600 on
  internet clips; on the author's static full-body recording 115 / 120 / 118 of 120. RTMW3D runs at 27 fps → live
  option `--estimator rtmw3d` for proper camera setups.
- **G1 on the author's demo** (`g1_style_user_v1/`): 0/30 grasps at both paces — the copied reach approaches from
  3 cm below the block (IK fine, so the kinematic pre-check cannot see it); pre-registered safe_path_v2 follow-up.

## Caveats (apply throughout)

Simulation only (MuJoCo; G1 under GEAR-SONIC); scripted IK controllers for the arms; perception, calibration and
hand-estimation magnitudes are assumptions (frozen in each protocol.json); GEM-X has no object detector, so the
Pexels demo's object/goal positions come from the hand at grasp/release; grasp/release frames were annotated by
inspecting the video; style is measured on the tool/wrist point only (no orientation).
