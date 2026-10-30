# Research requests for Gemini (self-contained; paste one at a time)

Context to paste with every request (the project in one paragraph): TransferGap takes one human demonstration (a video of a person lowering a small box into a target box on a table, static camera) and (a) measures the person (body and hand pose, limb lengths, angles), (b) replays the demonstration style on several simulated robots in MuJoCo (Unitree G1 humanoid with the GEAR-SONIC whole-body controller; UR5e; UR10e; the lab's KAIROS mobile manipulator = UR10e + Robotiq 2F-140 on a Summit XLS base), and (c) diagnoses, per pipeline stage, why a transfer fails, using paired oracle substitution and pre-registered held-out seeds (the "Transfer Gap Budget"). Everything runs on one NVIDIA L40S (CUDA 12.x, Python 3.10, Linux) in a Kubernetes cluster with outbound internet; no cloud spending, no Isaac Sim, simulation only; research use is non-commercial. Current pose model: RTMW3D (monocular, per frame, 40 fps, coordinates are NOT metric: about 2.6x too large; depth weak). Known problems: the simulated scene (4 cm red cube, green tray) is not the real scene; scale comes from an assumed 0.40 m shoulder width; the G1 grasps only about 1 try in 3.

Ask for, in every answer: the date of each source, a link, the licence, the reported numbers (quote them), what you could not verify, and a ranked recommendation with a one-paragraph reason. No invented citations: say "not found" instead.

---

## R1. Metric hand and body pose from one static camera
**Question.** Which methods (2025-2026) give the best *metric* 3D hand and upper-body pose from a single static RGB camera, with or without a known-size marker (AprilTag/checkerboard) on the table? Compare at least: depth-model-based lifting (Depth Pro, UniDepth V2, MoGe-2, Metric3D v2), HaMeR/WiLoR for hands, SAM 3D Body, GEM-X, WHAM/TRAM/PromptHMR-style world-grounded methods, RTMW3D with a marker-based scale fix.
**Deliver.** A table (method, input, metric accuracy as reported with the benchmark, fps on an L40S, weights and licence, install effort on CUDA 12 / Python 3.10), then a recommendation for: (a) no marker, (b) marker on the table, (c) a RealSense D455 (RGB-D) next to the camera. Include how to fix scale and depth for our RTMW3D output cheaply.

## R2. Real objects to a simulation twin
**Question.** Best practice (2025-2026) to detect two tabletop objects (a small box, a larger black box) in a video frame, estimate their metric size and pose, and instantiate a matching MuJoCo scene: open-vocabulary detection/segmentation (Grounding DINO / OWLv2 / SAM 2 / SAM 3), 6D pose (FoundationPose, MegaPose, Gen6D) with and without depth, plane-from-marker metric recovery, and box dimension estimation from a single view.
**Deliver.** A minimal reliable pipeline (steps, models, licences, expected centimetre error), a failure-mode list, and what to measure by hand as a cross-check.

## R3. Real-time humanoid control from a monocular camera, and shared autonomy
**Question.** State of the art for controlling a humanoid like the Unitree G1 live from a webcam: GEAR-SONIC (VR 3-point input, planner), GMT, HOMIE, OmniH2O, TWIST/Twist2, ExBody2, H2O, and any 2025-2026 work using monocular video. What are the reported tracking errors, latencies and fall rates? Which add a way for the operator to *choose a target object* and let the robot execute the grasp (shared autonomy), and how do they hand over between teleoperation and autonomy?
**Deliver.** A comparison table and a recommended architecture for "I mimic the arms live; I click an object; the robot grasps it; I can take over", with the realistic grasp success numbers reported for G1/Dex3 or similar hands.

## R4. Novelty and related work (so we do not overclaim)
**Question.** Our claim: a per-stage failure budget for human-to-robot transfer (perception, retargeting, calibration, execution timing) measured by paired oracle substitution on simulator ground truth, with a correction rule frozen before held-out evaluation, applied across several embodiments from one demonstration. Search 2024-2026 work (arXiv, CoRL, RSS, ICRA, CVPR/ICCV workshops, the CoRL 2026 Scaling H2R workshop page) for anything that already does stage-wise attribution of transfer failures, oracle-substitution diagnostics, or "style" transfer metrics across embodiments (e.g. H2RBench, HumanEgo, Human-as-Humanoid, AHA, RoboFAC, Guardian, RHO, GaP, embodiment-gap surveys, DexMV/HumanPlus/OKAMI/ExBody lines).
**Deliver.** For each close paper: what it does, what it does not, and the one sentence we can safely say that is different. Flag any paper that makes our claim already.

## R5. A good operator UI for robot teleoperation and evaluation
**Question.** What do the best current robot teleoperation and evaluation consoles look like and what do they run on (Foxglove, Rerun, Viser, NVIDIA Isaac teleop UIs, Open-Teach, LeRobot tools, Gello/ACT dashboards)? Which parts are reusable in a browser served from a pod behind `kubectl port-forward`?
**Deliver.** A recommendation (build with FastAPI + WebSocket + hand-written SPA, or Rerun/Viser embed), a wireframe-level description (panels, controls, states, empty and error states), and the 8 UI details that separate a credible research console from a generated-looking one. Link three real examples with screenshots.

## R6. Datasets to test real-to-sim transfer honestly
**Question.** Which public datasets provide human pick-and-place or object-manipulation demonstrations with *real object geometry and accurate hand/body mocap*, so we can measure our pipeline's real-to-sim error against ground truth: HOI4D, GRAB, DexYCB, ARCTIC, OakInk(2), HO-3D, TACO, Ego-Exo4D-HM (already analysed), others? Include licence, size, camera setup, whether a table-top single-hand pick-and-place subset exists.
**Deliver.** A ranked shortlist with a concrete 1-day experiment on the top one: convert N demos into our demo format, run the pose-to-robot chain, report where the error comes from.

## R7. Evaluating "style" and success with small samples
**Question.** Recommended statistics and metrics for comparing robot executions of a human demonstration when n is small (6-60 seeds, 1-3 people): paired tests, bootstrap intervals, equivalence margins, multiple-comparison control; style metrics beyond path RMSE and speed correlation (DTW, Frechet distance, jerk, approach angle). Which have been used in the imitation/retargeting literature and how are they reported?
**Deliver.** A short protocol we can freeze in version control before the next held-out run, with the reasoning for each choice and the pitfalls.

## R8. NVIDIA stack: what is genuinely load-bearing here
**Question.** For this task, where can each of these add something measurable, and where would it be decoration: Cosmos-Reason / Cosmos-Predict (video critic, success checking), GR00T N1.x (a learned policy instead of scripted control), Isaac Lab or Newton physics, Warp / MuJoCo-Warp for fast sweeps, TensorRT, FoundationPose, NeMo/Nemotron for diagnosis? Constraints: no Isaac Sim (compute), one L40S, non-commercial.
**Deliver.** For each: a concrete 1-2 day experiment, the metric that would show it helps, and the risk. Be willing to say "cut it".
