# Deep analysis: what is real in the demo, what is assumed, real-time control, UI, data (2026-10-06 night)

Prompted by the author's remarks after watching the integrated demo: the distance between the box and the plate in the simulation is not the real one; no red cube or green tray was used in the real video; the result looks like an "AI slop" presentation; more data and a better UI are wanted; and the author wants to control the G1 in real time and decide when and what to pick.
Markers: **VERIFIED** (observed, with a committed result), **READ** (read in code or docs, not run today), **ASSUMED**, **NOT DONE**. This file is the audit; the roadmap and the research questions for Gemini are in `research/GEMINI_RESEARCH_REQUESTS.md`.

## 1. The honest answer to "is the box-to-plate distance transferable?": no

**What the simulation scene is (READ, `sim/scene.py`).** A 4 cm red cube at about (0.45, -0.12) m, a green tray 15 cm wide at (0.45, 0.22) m, a fixed table. These are our own task objects and positions, identical for every demo. They were never derived from the author's video.

**What the author's video contains (from the clip description and the pose).** A person lowering a small box into a black box on a wooden table; neither object has a measured size, position or shape anywhere in our data.

**What the pipeline carries over (READ and VERIFIED on the clip).**

| Aspect | Real source | What the sim does | Consequence |
|---|---|---|---|
| Hand path shape between grasp and release | the person's pinch point per frame | kept, but warped: the carry leg is mapped by a similarity (rotate and scale in the table plane) from the person's grasp-to-release vector onto the sim's block-to-tray vector (`demo/style.py: robot_path`) | **the real distance is not preserved.** On this clip the person's carry is 25.9 cm (after an assumed body scale) and mostly along -x; the sim's is 34.0 cm along +y: the path is stretched 1.31x and rotated about 90 degrees |
| Heights (lift, release height) | hand height above the table | kept in metres (style), clamped at the table | the lift of about 22 cm and a +7.6 cm higher release are the person's, but relative to an unmeasured table height |
| Where on the object the hand grasped | not observable | `grasp_offset` and `place_offset` are exactly 0 by construction (the object is assumed under the pinch point) | off-centre grasps, the object's size and shape play no role |
| Object size | unknown | 4 cm cube | the 5 cm pinch aperture measured on the person is not matched to anything |
| Scale | RTMW3D is not metric (about 2.6x too large) | rescaled from an ASSUMED 0.40 m shoulder width | every length and the carry distance inherit this assumption |
| Depth | monocular, weak (about 3 cm of depth range in this clip) | used as is | forward motion is poorly known (the G1 forward wrist r = -0.24) |
| Camera position and table alignment | not measured | `align_yaw` defaults to 0 | the rotation between the camera frame and the table is arbitrary |
| Timing | the person is about 2x faster than the robot's nominal speed | the corrections (`speed_cap_*`) replace the person's pace | speed is not copied, by design |
| Tool orientation, elbow posture | observed (angles measured) | not copied by the arms; the G1 gets wrists, neck and pinch | "style" means a tool-point path, not a body posture |
| Perception and calibration errors | none measured | injected, sizes ASSUMED (`sim/errors_demo.py`) | the diagnosis is valid under an assumed error model, not a measured one |

So the framing "transfer of your motion" holds for the **shape and timing of the hand path**, not for the **task geometry**, which is synthetic. That is the right criticism and it is why the demo can look like a staged simulation.

**Measured consequence (added the same night, after building the twin).** The distance mismatch is real but it is not what changes the result. With the real carry vector (26 cm, direction preserved) and the default cube and tray sizes, the counts equal the fixed-layout ones (UR5e 36 -> 60, UR10e 33 -> 60, KAIROS mobile 47 -> 60; `results/cluster_pipeline_twin_carry_only_v1`). With an ASSUMED larger box and a taller, narrower container they collapse (7, 9, 13 -> 52, 51, 60; `cluster_pipeline_twin_standin_v1`). So **object and container geometry drive the outcome**; the carry distance does not. Therefore measuring the box and the target container matters more than measuring the distance between them.

**Fixes, in order of effort and honesty.**
1. *Same afternoon, no new software.* For the next recording, measure with a tape: box size, target-box inner size, their centre distance, table height, and the camera's distance and height; put a printed AprilTag or checkerboard of known size on the table. Then (a) set the sim's object and target sizes and positions from these numbers and (b) replace the assumed shoulder width with the measured one.
2. *A scene twin from the video (BUILT 2026-10-06 for the arms, sizes still typed by the user; automatic object detection NOT built).* `sim/twin.py`, `pipeline --scene`, `human/marker.py`, `human/twin_from_video.py`, printable marker `deliverables/TransferGap_marker_12cm.pdf`, protocol `RECORDING_PROTOCOL.md`. Original plan: Detect the two objects (open-vocabulary detector + segmentation), get their metric position from the marker plane (and a depth model), build the sim scene with boxes of the measured size at the measured places, and drop the similarity warp: the robot then performs the *same* geometric task. For a robot that cannot reach it from its default base pose (the G1 on person 2 failed by 27-29 cm), position the base (KAIROS can drive; the G1 can step) or report infeasible, which the kinematic pre-check already does.
3. *A depth camera (best quality).* The lab owns D455 cameras: one RGB-D camera on the table gives metric 3D for hands and objects, removing the scale assumption and most of the depth weakness.

## 2. What was built, audited (counts and status)

See `STATUS_AND_OBJECTIVE.md` for the full table; the one-line summary: perception on the cluster (VERIFIED, static camera only), person measurements (VERIFIED once), arms UR5e, UR10e, KAIROS and KAIROS mobile (VERIFIED, 60 seeds), G1 mimicry of wrists (VERIFIED once, partial), G1 picking in your style (NOT WORKING), one image with 8 of 8 end-to-end stages (VERIFIED), live webcam through the cluster (PARTIAL, video stand-in at 17-21 fps).

Honest quality notes on what I built today:
- The integrated video is assembled from OpenCV cards and matplotlib-free views; it is informative and honest but it is a **script output**, not a designed product. It will read as "generated" to a technical audience.
- One clip, one person, hand-annotated grasp and release frames, one G1 replay. None of these is a statistic.
- The 0.40 m shoulder-width scale is an assumption that sits under every number in the person measurements.

## 3. Real-time control of the G1: is it possible, at what level?

Three levels, from most to least ready.

| Level | What the user does | State | Evidence and gap |
|---|---|---|---|
| **L1: live mimicry** | stand in front of the webcam; the G1 (and an arm) copy wrists, neck and pinch, in real time | **built on the old VM, VERIFIED there with a video stand-in; NOT run on the cluster or with your webcam** | GEM-X live 9.5-9.8 fps and frame-to-arm command 109-116 ms median (VM, `results/OVERVIEW_human_demo.md` section 6); RTMW3D now 40 fps on the cluster GPU; the cluster relay path runs at 17-21 fps (arm viewer, no G1). The G1 stayed up 150-205 s before a fall on stock videos; the G1 live chain (`live/g1_vr3pt.py`, SONIC VR-3-point, pinch closes the Dex3 hand) is READ and ran offline on the cluster today. **Needed:** a cluster Job that runs sim + SONIC + pose + relay together for a session, a port-forward to that pod (not `tg-dev`), a fall supervisor (exists in `run_live_vm.py`). Estimated 1-2 days, risk medium (stability of the G1 under live monocular input) |
| **L2: interactive commands** | click a button or an object: "pick that one", "place there", "slower"; keyboard or gamepad drives the G1 base and torso | **partly present, no UI** | SONIC deploy lists `keyboard` and `zmq_manager` inputs (READ in `deploy.sh`); a scripted pick-place controller with perception exists for UR5e, UR10e and KAIROS (at least 0.90 in the held-out perception cells; 56-60 of 60 on the demos with the fix stack). **Needed:** a command layer over `ScriptedPickPlace` and the G1 planner, an object list or click-to-select over the simulated camera view, and the UI. Arms: reliable, 1-2 days. G1: the closed-loop grasp succeeds only about one try in three (hybrid 10-17 of 40 per seed set; VR-3-point 3 of 40), so "pick that" on the G1 would usually fail today |
| **L3: shared autonomy ("what to pick" decided by you, "how" by the robot)** | point or click at the object; the robot plans and executes, you can abort or take over with your hand | **NOT DONE** | needs L2 plus object selection from a camera view and a handover between mimic and autonomous modes; the G1 grasp reliability is the limit, the arms are fine |

**Direct answer.** Yes, controlling the G1 live is possible: L1 (copy me now) is the nearest and is an engineering port of verified pieces; deciding *when* to pick is natural there, because your own pinch closes the hand. Deciding *what* to pick and having the G1 reliably succeed is not available yet (grasp success about 1 in 3). For a demo that reliably picks, show the **arms** in L2 and the **G1** in L1.

## 4. The UI

Current UI (READ): `live/viewer.html` (a plain page with three MJPEG panes and a few buttons, built in the first week for the VM), plus the OpenCV cards of the integrated video. Neither is designed.

What "not AI slop" needs here is an operator console for a real system, not decoration:
- left: your camera feed with the skeleton and the live numbers (limb lengths, angles, pinch, speed), with a "monocular estimate, scale assumed" badge until the scale is measured;
- centre: the robot views (G1, UR5e, UR10e, KAIROS) selectable, plus a top view of the scene twin;
- right: control and status: mode (mimic, command, replay), pinch and gripper state, latency and frame rate, a fall or reset indicator, record and replay;
- a second page for results: per-robot success counts with intervals, the transfer-gap budget, and a one-click "reproduce this row".
Technical options: a small FastAPI + WebSocket server in the pod serving a hand-written single-page app (fastest, fully ours), or an existing visualization tool (Rerun or Viser) for the 3D and time-series parts. Design rules: real data only on screen, one typeface, restrained colour, no gradients or filler icons, every number sourced. Estimated 3-4 days for a first good version. The Artifact tool cannot host it for the demo because the console must reach the pod through a port-forward; it can host a static results page for sharing.

## 5. More data: what to record and how

Goal: enough demonstrations to say something beyond one clip, and a real-to-sim check.
- **People:** at least 3 (the existing set has 3 including the author, with unequal quality). **Reps:** 10 per condition.
- **Conditions:** slow, normal, fast; start from the left and from the right; left and right hand; two or three objects (box, cup, tool); two target heights.
- **Camera:** static, full upper body and the table in view, 1080p at a fixed frame rate (the existing clip is 21.4 fps, an unusual rate: fix the camera at 30 fps), no zoom; ideally a second view or a RealSense D455 on the table for metric depth.
- **Scene:** a printed AprilTag or checkerboard of known size on the table; tape-measure numbers written in a metadata file (`objects`: sizes, centre distance, table height, camera distance).
- **Labels:** the grasp and release frame per demo (we have a hand-annotation helper only for the first clips); build a small annotation tool and test the automatic segmenter against the manual labels on at least 30 demos before trusting it.
- **Reference clips:** a few recordings of the same task with the arm or hand also tracked by the D455 depth to estimate our monocular error.

## 6. What is still open (scope)

| Item | Why it matters | Effort | Who |
|---|---|---|---|
| Real scene geometry in the simulation (scene twin) | removes the main "this is staged" objection | 2-4 days | agent, with the user's tape-measure data |
| Metric scale and depth (marker or D455) | every length and the G1 forward motion depend on it | 1-2 days with a marker; 2-3 with a D455 | agent + user recording |
| L1 live G1 on the cluster | the real-time claim | 1-2 days | agent, then a session with the user |
| L2 command layer and UI | choose what and when | 3-5 days | agent |
| Reliable G1 grasp | picking in the person's style, "pick that" | open research | agent + literature check (Gemini) |
| More people and clips; annotation tool; auto-segmenter validation | evidence beyond one clip | recording 2-3 hours + 2 days | user + agent |
| One-command integrated demo inside the image (r5) | robustness | 1 day | agent |
| Better pose model on the cluster for non-static video | not just a locked camera | 1-2 days | agent (candidate list in the research requests) |
| Paper: abstract, introduction, conclusion; reviews | deadline end of Oct 7 AoE | hours | **user** |

Out of scope by decision: Nebius, Isaac Sim, real-robot hardware.

## 7. A note on novelty claims

"Nobody has done this" should not be said until a literature check is done: the individual parts (video to pose, humanoid whole-body tracking, retargeting, oracle-style diagnosis) all exist in the literature. What the repository can defend today, with evidence, is the combination: a per-stage **Transfer Gap Budget** with paired oracle substitution and pre-registered held-out validation, run on several embodiments from one demonstration with the failures reported. The research request R4 asks Gemini to check this against recent work so the claim can be worded precisely.
