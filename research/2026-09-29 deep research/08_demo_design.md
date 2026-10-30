# 08 — TransferGap hackathon demo design (video + hosted demo + build plan)

Research agent 8, 2026-09-29. Scope: exactly what gets shown and how to build it. Market/pitch is agent 6's file.
Tags: **VERIFIED** = I read the primary source or ran the code myself. **UNVERIFIED** = secondary source, or not executed.

---

## 1. Hard constraints from the actual hackathon pages (these shape everything)

Source: https://nebiusglobalaihackathon.devpost.com/ and /rules (VERIFIED via fetch, 2026-09-29, summarizing tool; re-read the page by hand before submitting)

- **Four judging criteria, equally weighted.** Two of them name **Nemotron** and **Nebius Token Factory / AI Cloud** explicitly:
  1. Technological Implementation: "…how effectively does it use Nebius Token Factory or AI Cloud model(s), and NVIDIA Nemotron?"
  2. Design: "Does the project deliver a complete, coherent product experience not just a technical proof of concept?"
  3. Potential Impact: "…a credible, specific case for solving a real problem for a real audience?"
  4. Quality of the Idea: "Is this a creative, non-obvious use of Nebius Token Factory or AI Cloud model(s), and NVIDIA Nemotron?"
  → **Implication:** in the current plan Nemotron is a side planner smoke test. For the demo it has to sit visibly *inside the product loop*, e.g. the diagnosis explainer and correction proposer, with a receipt shown on screen. Otherwise two of the four criteria score weakly no matter how good the robotics is.
- **Physical AI track:** "leverage Nemotron, GROOT, Cosmos, and Sonic… with Nebius Serverless Jobs to run simulations, generate synthetic data, evaluate robot policies…" The demo must include "at least a 1-minute clip showing the physical hardware/robot actually operating" **or** "key application modules in action". → A continuous ≥60 s screen recording of the working pipeline satisfies this. Plan it as one unbroken segment.
- **Video:** public YouTube, **≤3 min**, **with audio explaining use of Nebius Token Factory and the NVIDIA models**. Silent footage with captions does not satisfy "audio".
- **Demo URL:** required for other tracks, but the page says Physical AI submissions are exempt (UNVERIFIED nuance; re-read). **Build one anyway.** The Design criterion ("complete, coherent product experience") is scored on product feel, and a hosted demo is the cheapest proof.
- Prizes: Grand $20k, 2nd $10k, 3rd $6k; the track winner gets 4× Jetson Orin Nano.

## 2. What makes 2025–2026 robotics demos land in under 30 seconds

| Observation | Source | Status |
|---|---|---|
| GEAR-SONIC's page opens with a trailer and then a skill montage showing breadth; demos are grouped under headings; it links an interactive demo instead of embedding one | https://nvlabs.github.io/GEAR-SONIC/ | VERIFIED (fetched) |
| π0.5 openly shows **failed episodes** next to successes and states that no evaluation scene came from training data. That transparency is the credibility signal | https://www.physicalintelligence.company/blog/pi05 | UNVERIFIED (search snippet) |
| LeRobot Worldwide Hackathon (June 2025): winners had one concrete everyday task (shirt folding, medicine sorting), real robot footage and a public video gallery | https://huggingface.co/spaces/LeRobot-worldwide-hackathon/all-winners ; https://medium.com/@sarohapranav/folding-shirts-sorting-medicines-and-winning-at-the-lerobot-worldwide-hackathon-98ad4e21c972 | UNVERIFIED (snippets; the Lightning.ai write-up did not load) |

Principles I take from these (my synthesis):
1. **Result in the first 10 seconds.** Open on the punchline image, not the architecture.
2. **One task, instantly legible.** Block → tray. Anyone understands success or failure without narration.
3. **Show failure on purpose.** For TransferGap the failure *is* the product output, so this is the strongest possible fit with the π0.5 credibility pattern.
4. **Put every number next to its evidence.** Seed, commit, episode ID and receipt must be on screen or one click away.
5. **Always watermark "SIMULATION".** Judges punish overclaiming more than they punish sim-only work.

## 3. The single "wow moment"

> **The same 8-second human clip drives two different robots. One succeeds, one fails. TransferGap names the exact stage and physical cause of the failure from simulator state, Nemotron proposes a bounded fix, and the fix is re-tested on held-out paired trials, with before/after success rates and confidence intervals, all in one flow.**

How to keep it verifiable rather than staged:
- Stage labels (reach/grasp/lift/place/release) come **only** from simulator state: contacts, object pose, gripper state. Nemotron and Cosmos **explain**; they never grade. This matches the existing `metrics.py` rule "Model opinions never define benchmark success".
- The correction must be **chosen on dev trials and reported on held-out trials** (review finding: don't select the fix on the advertised set).
- Every result card links to: episode JSONL, rendered MP4, `.rrd` trajectory file, Nemotron receipt JSON (response ID, model, latency, tokens), git commit and seed.
- **Fallback that keeps the moment honest:** if the G1 cannot grasp at all, that is itself a measured embodiment-gap result ("G1 + SONIC: motion tracked, grasp stage never reached, 0/N"). The demo still works because TransferGap's output is the diagnosis, not a success. Never present G1 tracking as manipulation.
- Before/after numbers in this doc are placeholders. **Only measured numbers go into the video.**

## 4. Video storyboard (target 2:55, 1920×1080, 30 fps)

A continuous ≥60 s "modules in action" segment is marked ★ (satisfies the track rule).

| Time | Shot | Visual elements | Voice-over (gist) |
|---|---|---|---|
| 0:00–0:10 | **Cold open.** Three panels: human clip, G1 rollout, wheeled-arm rollout, all playing in sync | Top row 3×(640×360). A red stamp slams onto one robot panel: "FAILED @ GRASP — 2.1 cm tool-frame offset" (placeholder). A green "SUCCESS" on the other. "SIMULATION" watermark bottom-right | "Same human demonstration. Two robots. One fails, and today nobody can tell you why." |
| 0:10–0:28 | **Problem** | 3–4 fast cuts: teams collecting human video, embodiment variety (G1, arm, KAIROS photo if allowed), a text card: "Will this demo transfer to *my* robot?" | Human-video data is cheap, but transfer is unpredictable and each failed robot test costs hours. |
| 0:28–1:35 ★ | **Product walkthrough, one continuous screen recording** of the hosted app | (1) Upload/select clip. (2) GEM-X keypoint and mesh overlay, labelled "GEM-X (NVIDIA)". (3) "Retarget → G1 (SONIC)" and "→ UR5e+2F-85 (GR00T N1.7)" status chips. (4) Side-by-side third-person rollouts. (5) **Stage timeline strip** under each rollout: five segments reach/grasp/lift/place/release, green/red/grey, with a playhead synced to the video. (6) Failure card: the stage, the simulator evidence (e.g. min gripper-object distance, contact never registered) and a link to the episode JSONL | Narrate each NVIDIA component as it appears: GEM-X reconstruction, SONIC whole-body control, GR00T N1.7 action head. |
| 1:35–2:00 | **Diagnosis: Nemotron via Nebius Token Factory** | A panel shows the live request: model ID `nvidia/NVIDIA-Nemotron-3-…`, the structured input (the stage table, not raw video), the output hypothesis restricted to allowed correction types, and a receipt footer (response ID, latency, tokens). Optional smaller Cosmos-Reason2 panel with a video-event assessment tagged "advisory — simulator decides" | Nemotron reads the structured failure trace and proposes a bounded correction. It cannot invent coordinates or declare success. |
| 2:00–2:30 | **Correction test at scale: Nebius Serverless Job** | Job-submission card with job ID; a time-lapse grid of N held-out paired episodes (for example 4×5 thumbnails) turning green or red; then a bar chart of before vs after with 95% CI whiskers (Wilson per arm, paired bootstrap for the gap) and the text "n = X paired held-out trials" | The job runs paired trials on Nebius AI Cloud. The fix was chosen on development trials and is reported here on held-out ones. |
| 2:30–2:48 | **Product framing** | A "TransferGap Report" PDF/HTML mock with per-robot stage success, top failure causes and the recommended fix. Then a stack strip with model and platform names only (no logo misuse): Nemotron · GR00T N1.7 · SONIC · GEM-X · Cosmos-Reason2 · Nebius Token Factory · AI Cloud · Serverless Jobs | CI for robot-policy transfer: know before you ship to a new embodiment. |
| 2:48–2:55 | **Close** | Repo URL, demo URL, "all numbers traceable to artifacts" | — |

Production notes:
- Screen-record with OBS at 1080p30. Record the narration separately, lay it under the footage, and normalize loudness (`ffmpeg -af loudnorm=I=-16:TP=-1.5:LRA=11`).
- Burn captions into the video as well; judges often watch muted.
- Ensure every on-screen number comes from a real artifact produced in the recording session.

## 5. Hosted demo: what is live vs precomputed (and how to label it)

| Component | Live or precomputed | Why | On-screen label |
|---|---|---|---|
| Episode scoring, stage attribution, paired stats (`transfergap` package, pure Python) | **Live** (CPU) | Seconds of compute; judges can upload their own JSONL | none needed |
| Nemotron diagnosis via Token Factory | **Live**, rate-limited, with receipt shown | Cheap (~500 tokens/call; see agent 3 for pricing) and directly scores criteria 1 and 4 | "Live call · model · response ID" |
| Cosmos-Reason2 video assessment | Live only if the endpoint exists; otherwise a precomputed receipt | Endpoint not provisioned (status as of Sept 28) | "Recorded call · date · response ID" |
| GEM-X reconstruction, MuJoCo rollouts, GR00T inference | **Precomputed** | GPU minutes each; a public page must not spin up GPUs per visitor | "Recorded run · date · commit · seed" |
| "Re-run N trials" button → Nebius Serverless Job | Optional live (owner-only or token-gated) | Shows the real Nebius compute path; must be cost-capped | "Job ID … · status" |

This split is honest provided the labels are always visible. Never let a precomputed rollout look live.

Hosting recommendation:
- **Primary: Gradio app on a free HF Space.** Free "CPU Basic: 2 vCPU, 16 GB memory" (VERIFIED, https://huggingface.co/pricing). It runs the scorer, report and a live Nemotron call (`NEBIUS_API_KEY` stored as a Space secret). Precomputed MP4 and `.rrd` artifacts live in an HF dataset repo.
  - Put a per-session call cap and a global daily cap on Nemotron calls.
  - Free Spaces sleep when idle (sleep behavior UNVERIFIED on the pricing page). Wake it before judging.
- **Alternative that scores Nebius usage more directly:** serve the same container from Nebius (mk8s or the VM). It costs GPU-free CPU hours only if deployed on a CPU node; see agent 3 for CPU node pricing. Reasonable compromise: HF Space for the UI, Nebius for every model call and job, and say so in the README.
- **Trajectory viewer: rerun.io.** Log per episode: object pose (`Transforms3D`), gripper/EE pose, stage labels (`TextLog`), video frames. Save as `.rrd` and embed with an iframe: `https://app.rerun.io/version/{RERUN_VERSION}/?url={RRD_URL}`. The viewer version **must match** the SDK version that wrote the file (VERIFIED, https://rerun.io/docs/howto/integrations/embed-web). CORS on the HF `resolve/` URL is UNVERIFIED; test early, and fall back to `@rerun-io/web-viewer` or plain MP4 if it fails.

## 6. Engineering recipes

### 6.1 Third-person rendering, headless

**Renderer API (VERIFIED by running it locally, mujoco 2.3.3; the box has a newer version with the same API):**
```python
import mujoco
# the model XML must allow the size: <visual><global offwidth="1280" offheight="720"/></visual>
r = mujoco.Renderer(m, 720, 1280)            # (model, height, width)
r.update_scene(d, camera="third_person")      # camera: int id | str name | MjvCamera
frame = r.render()                            # (720, 1280, 3) uint8

cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
cam.trackbodyid = m.body("pelvis").id; cam.distance = 3.0; cam.azimuth = 135; cam.elevation = -20
r.update_scene(d, camera=cam)                 # tracking camera, no XML edit needed
```
- Test script: `scratchpad/research/render_test.py`. With `MUJOCO_GL=glfw` it rendered both a named camera and a tracking camera at 1280×720.
- On this laptop `egl` and `osmesa` failed (broken local driver/OSMesa). On the L40S box `MUJOCO_GL=egl` is already recorded as working (Implementation Status, Sept 27). → **Use `MUJOCO_GL=egl` on the box.**

**Recommended architecture: log state, re-render offline.**
- SONIC's `run_sim_loop.py` owns its `MjData` in its own process; the only existing view is the robot's `ego_view` camera (which is why the evidence frame shows only the floor).
- Rather than patching the sim loop to render, log `qpos` (plus the object pose) every control tick to `.npz`. Afterwards reload the same MJCF, set `d.qpos`, call `mujoco.mj_forward(m, d)` and render from any camera.
- Benefits: deterministic, decoupled from real-time control, several angles per episode, and the same log feeds the scorer JSONL and the rerun `.rrd`. One source of truth for video, score and viewer is itself a credibility feature.
- Caveat (UNVERIFIED): confirm the SONIC scene's MJCF and the rendering MJCF are identical, including hand models. Otherwise the rendered pose diverges from the simulated one.

Camera placement:
- **G1:** tracking camera on `pelvis` (distance about 3 m, azimuth 135°, elevation −20°) plus a fixed side camera aimed at the table.
- **Arm:** a fixed camera at about 45° above the table corner, `xyaxes` pointed at the tray. Render at 30 fps; physics runs faster, so render every k-th logged step.

### 6.2 Compositing (ffmpeg; standard filters)

UNVERIFIED here because this laptop has no ffmpeg; the box used ffmpeg on Sept 27.
```bash
# 3-up with labels
ffmpeg -i human.mp4 -i g1.mp4 -i arm.mp4 -filter_complex "\
[0:v]scale=640:360,drawtext=text='HUMAN':x=12:y=12:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.6[a];\
[1:v]scale=640:360,drawtext=text='G1 · SONIC':x=12:y=12:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.6[b];\
[2:v]scale=640:360,drawtext=text='UR5e+2F85 · GR00T N1.7':x=12:y=12:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.6[c];\
[a][b][c]hstack=inputs=3[top]" -map "[top]" -c:v libx264 -crf 20 -pix_fmt yuv420p top.mp4

# stage timeline strip (static PNG from matplotlib, 1920x80) + moving playhead
ffmpeg -i top.mp4 -loop 1 -i strip.png -f lavfi -i color=white:s=3x80 -filter_complex "\
[0:v]pad=1920:1080:0:0[bg];[bg][1:v]overlay=0:360[s];\
[s][2:v]overlay=x='(W-3)*t/DUR':y=360:shortest=1" -c:v libx264 -crf 20 out.mp4
# (replace DUR with the clip duration in seconds)

# SIMULATION watermark
... ,drawtext=text='SIMULATION':x=w-tw-20:y=h-th-20:fontsize=28:fontcolor=white@0.7
```
- Draw the stage strip from the episode's stage labels with matplotlib: one horizontal bar per robot, colored segments, labelled.
- One static PNG plus an ffmpeg-animated playhead is far cheaper than rendering matplotlib per frame.

### 6.3 Web app (Gradio) layout

Top to bottom:
1. Clip selector (three curated clips) plus optional JSONL upload.
2. The three-panel video.
3. Two stage-timeline strips.
4. Failure card(s).
5. "Diagnose with Nemotron" button → structured prompt → rendered answer plus receipt.
6. Before/after chart with CI.
7. Rerun iframe tab.
8. "Reproduce" tab showing the exact commands, commit and seed.

Keep the Nemotron input structured (the stage table plus simulator evidence) and the output constrained to a small enum of correction types (tool-frame offset, object-relative target shift, approach height, grasp width, timing). Reuse the existing `validate_plan` pattern: reject anything outside the enum and show the rejection. A visible validation step is itself a design point.

## 7. Build order and time estimates (one engineer; hours are focused work)

| # | Item | Depends on | Est. |
|---|---|---|---|
| 1 | Per-tick state logger (qpos, object pose, gripper, contacts) → `.npz` + scorer JSONL, for both sims | adapters (agents 2 and 5) | 4 h |
| 2 | Stage labeler from simulator state (reach/grasp/lift/place/release + failure reason) + unit tests | 1 | 4 h |
| 3 | Offline re-renderer: log → third-person MP4 (EGL on the box) | 1 | 3 h |
| 4 | Compositor script (3-up, strip, watermark) | 2, 3 | 3 h |
| 5 | Rerun `.rrd` exporter + iframe CORS test | 1 | 2 h |
| 6 | Nemotron diagnosis prompt, enum-validated, with receipt | 2 | 3 h |
| 7 | Gradio app wiring precomputed artifacts + live scorer + live Nemotron | 4, 5, 6 | 6 h |
| 8 | Nebius Serverless Job for the paired sweep + job-ID display | agent 3 runbook | 4–6 h |
| 9 | HF Space deploy, secrets, rate/cost caps, wake-before-judging check | 7 | 2 h |
| 10 | Video: script, OBS capture of the ★ segment, narration, captions, edit | all | 6 h |
| | **Total** | | **≈37–40 h** |

- Start items 1–3 as soon as the box is back. They de-risk everything else, and a correct third-person render alone upgrades the evidence the review flagged as weak ("JPEG shows the floor").
- Freeze demo features by Oct 19, matching the review's schedule. Record the video Oct 20–25 and submit early.

## 8. Risks specific to the demo

- **Overclaiming:** keep the "SIMULATION" watermark, "recorded run" labels, and CI plus n on every rate. Don't show one looped clip as "generalization".
- **The G1 can't grasp:** present that as a measured gap (see §3). Don't cut to G1 walking and imply manipulation.
- **Nemotron looks decorative:** it must change something measurable (the proposed correction is the one tested). If it proposes nothing useful, say so and show the rejection; that is still honest.
- **Live demo breaks during judging:** precomputed artifacts mean the page still works with the API key revoked. The Nemotron button shows the last recorded receipt with a "recorded" label as a fallback.
- **Rerun version mismatch or CORS:** pin the rerun SDK version, and fall back to MP4.

## Sources
- https://nebiusglobalaihackathon.devpost.com/ (criteria, track, prizes)
- https://nebiusglobalaihackathon.devpost.com/rules
- https://nvlabs.github.io/GEAR-SONIC/
- https://www.physicalintelligence.company/blog/pi05
- https://huggingface.co/spaces/LeRobot-worldwide-hackathon/all-winners
- https://medium.com/@sarohapranav/folding-shirts-sorting-medicines-and-winning-at-the-lerobot-worldwide-hackathon-98ad4e21c972
- https://rerun.io/docs/howto/integrations/embed-web
- https://huggingface.co/pricing
- MuJoCo Renderer: verified locally via `inspect` and by running `render_test.py` (mujoco 2.3.3)
