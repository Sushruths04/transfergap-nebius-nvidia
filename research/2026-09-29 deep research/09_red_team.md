# 09 — Red Team: TransferGap judged as-is (Sept 29, 2026)

Panel persona: NVIDIA robotics researcher, Nebius infra PM, VC. Blunt by design.
Sources read: `Physical AI/TransferGap.md`, `Implementation Status.md`, `Review and Next Plan 2026-09-28.md`, `transfergap/` code (in-session), devpost overview/rules/dates pages, license files of dependencies.

---

## 1. Official rules — what is actually required (VERIFIED)

Source: https://nebiusglobalaihackathon.devpost.com/rules , https://nebiusglobalaihackathon.devpost.com/ , https://nebiusglobalaihackathon.devpost.com/details/dates

- **Deadline:** Oct 30, 2026 10:00am PDT. Submission period opened Aug 26 9:00am PDT. Judging Nov 2 – Dec 15. Winners Jan 11.
- **Stage One (pass/fail):** must genuinely attempt the track goal and "reasonably apply required APIs/SDKs."
- **Stage Two — four criteria, EQUALLY weighted:**
  1. **Technological Implementation** — "How well is the project built, and how effectively does it use Nebius Token Factory or AI Cloud model(s), and NVIDIA Nemotron or other NVIDIA open source models as part of the solution?"
  2. **Design** — "Does the project deliver a complete, coherent product experience not just a technical proof of concept?"
  3. **Potential Impact** — "credible, specific case for solving a real problem for a real audience and does the solution actually address it based on what's demonstrated?"
  4. **Quality of the Idea** — "creative, non-obvious use of … and does the team show genuine understanding of the problem space?"
- **Required tech:** run on **Nebius Token Factory OR Nebius AI Cloud** — the rules text parenthesizes AI Cloud as "(Serverless Jobs, Serverless Endpoints, or DevPods)" and says the project "must make runtime calls to specified infrastructure"; plus **≥1 NVIDIA open-source model** (Nemotron emphasized).
- **Physical AI track:** ≥1 minute of hardware operating OR "key application modules in action"; video <3 min, public YouTube.
- **Repo:** public, license must be **Apache 2.0, MIT, or MPL 2.0** (our MIT is fine). Need README w/ setup, working demo URL or hosted app, text description.
- **Pre-existing work:** allowed if significantly updated during the period. TransferGap work started ~Sept 27, inside the period → fine, but keep the git history honest (repo only created Sept 28; earlier remote work is not in git — see risk R4).
- **Prizes:** Grand $20k, 2nd $10k, 3rd $6k; each track winner gets one Jetson Orin Nano; 20× $500 city awards. → **The money is in the overall ranking, not the track.** We compete against Nemotron agent apps on "complete product experience." That changes priorities (see §4).

### Does our current usage count?
| Requirement | Current state | Verdict |
|---|---|---|
| NVIDIA open model | Nemotron-3 Nano via Token Factory (1 smoke call, receipt exists); GEM-X, SONIC run on VM | **Counts**, but thin: one call is not "part of the solution" |
| Nebius Token Factory runtime calls | Only in the `plan` CLI; not in any product loop | **Weak** — must be in the live product path |
| Nebius AI Cloud | Raw Compute VM (L40S) | **UNVERIFIED whether a plain VM satisfies the rule**; rules text lists Serverless Jobs / Endpoints / DevPods. Treat as risk; add a Serverless Job and/or Endpoint so it unambiguously counts |
| Cosmos-Reason2 | Not provisioned | Zero credit until it runs |
| GR00T N1.7 | Not run at all | Zero credit until it runs |

---

## 2. Scorecard if submitted TODAY (as a judge would see it)

| Criterion | Score /10 | Why |
|---|---|---|
| Technological Implementation | **4** | Real engineering exists (SONIC sim2sim loop, GEM-X→SONIC, UR5e IK), but: none of it is in the repo (lives on a stopped VM), no scored episode, no GR00T, no Cosmos, one Nemotron call. The strongest work is invisible to a judge. |
| Design | **2** | No product surface at all — a Python CLI and markdown. The rule literally says "not just a technical proof of concept." This is the biggest gap. |
| Potential Impact | **4** | Real problem (does a demo/policy transfer to *my* robot?), but no named audience, no evidence a user wants it, and no demonstrated result that addresses it. |
| Quality of the Idea | **6** | Two-embodiment transfer-gap *diagnosis* is non-obvious and the team clearly understands the domain (the review discipline shows). Docked because Nemotron's role (text planner emitting reach/grasp/lift) is the most obvious possible LLM use, and H2RBench is close prior art. |
| **Total** | **16/40** | Not competitive for top 3. Very fixable — the gap is packaging + one real closed loop, not research. |

---

## 3. Failure modes, ranked by likelihood × impact

L = likelihood (1–5), I = impact (1–5).

| # | Risk | L | I | L×I | Mitigation |
|---|---|---|---|---|---|
| R1 | **No product experience** — judges see logs/markdown, score Design ≤3 | 5 | 5 | 25 | Build one web app (Gradio/Streamlit on a Nebius Serverless Endpoint or the VM behind a URL): upload clip → pick robots → run → "Transfer Gap Report" (per-robot success, failure stage, Cosmos/Nemotron explanation, suggested correction, before/after). This *is* the product. Freeze it by Oct 17. |
| R2 | **Scope explosion** — 5 NVIDIA models × 2 robots × fine-tuning × correction × HiPHI × K8s in 3 weeks, solo-ish | 5 | 5 | 25 | Adopt the MVWV below; everything else is stretch. Hard kill dates. |
| R3 | **No physically valid manipulation episode** on either robot (review P1: floor not demonstrated) | 4 | 5 | 20 | Scripted IK controller on fixed-base UR5e+2F85 picks a block in MuJoCo **first** (no human data, no learning). That gives a scorable baseline in days. Human-demo-conditioned version second. |
| R4 | **Remote work lost / not reproducible** — scripts only on the stopped VM disk; repo lacks them | 4 | 5 | 20 | First GPU action tomorrow: `rsync` all authored scripts/scene files/patches into the repo, commit, then snapshot. Never author code only on the VM again (edit locally, push). |
| R5 | **G1 cannot manipulate** — SONIC is a motion tracker; wrists/fingers streamed as zeros in the GEM-X path (live_camera_teleop.md "Limitations"); root translation not commanded | 4 | 4 | 16 | Reframe G1 honestly: G1 = whole-body *motion* transfer (tracking error, balance, falls), arm = *manipulation* transfer. The gap report compares on a common task-stage axis (reach/approach/contact/lift/place), not a fake matched grasp. Don't promise G1 grasping. |
| R6 | **GR00T fine-tune eats the schedule** — dataset format, modality config for NEW_EMBODIMENT, 1-GPU tuning, converges to nothing useful on 1 looped clip | 4 | 4 | 16 | Demote GR00T fine-tune from "never cut" to **stretch**. If it runs, show it as one extra "method" row in the report. Judges score the product, not the count of fine-tunes. (Current TransferGap.md says "Never cut … the GR00T fine-tune" — the red team disagrees.) |
| R7 | **AI Cloud VM may not count** as "Nebius AI Cloud (Serverless Jobs/Endpoints/DevPods)" | 3 | 5 | 15 | Run the evaluation sweep as a **Nebius Serverless Job** (containerized MuJoCo episodes → JSONL → our scorer) and host the app/Cosmos on a **Serverless Endpoint**. Explicitly name both in the write-up with job IDs. Ask in the devpost discussion to confirm a VM counts. |
| R8 | **Billing / compute burn** — on-demand L40S ~$1.55/h left running (already happened once); no working CLI | 3 | 4 | 12 | Restore CLI auth tomorrow; set a budget alert; scripts end with `shutdown`; prefer Serverless Jobs (bill per run) for sweeps; stop VM daily. |
| R9 | **Overclaiming** — "fine-tuning deliverable", "wheeled arm built" (no mobile base), "5 NVIDIA models" | 4 | 3 | 12 | Every claim in video/README links to an artifact. Call it "fixed-base arm (mobile base out of scope)" unless a base is actually added. Separate replay vs autonomy labels (already in the episode contract — keep). |
| R10 | **Demo video unreliable / ugly** — current sim frame shows only the floor; no third-person camera | 4 | 3 | 12 | Add a fixed third-person MuJoCo camera to both scenes early; record a canonical run; demo video uses pre-recorded runs + one live app click, not a live robot session. |
| R11 | **Cosmos-Reason2 never provisioned** or its judgement contradicts sim labels | 3 | 3 | 9 | Keep Cosmos as *explainer*, never the label (already the design). If not up by Oct 12, drop it — Nemotron VLM/text over structured sim logs covers the explanation role. |
| R12 | **HiPHI licensing / size** — ModalityNet Open Research License; commercial use needs separate license (HF card: "For commercial licensing… contact info@modalitynet.com"); 215 GB; gated approval; terms on redistribution/derived data not shown on the card (UNVERIFIED) | 3 | 3 | 9 | Do not ship HiPHI-derived data in the public repo or video until the actual license text is read. Use at most a handful of clips for internal eval, cite it, and do not build the product pitch on it. It also bypasses GEM-X (the video→motion step that *is* the product's input story). Stretch only. |
| R13 | **Placeholder video features an identifiable public official** (Wikimedia PD clip) — evidence MP4s of that person are committed | 2 | 3 | 6 | Replace with self-recorded footage before the video/repo goes public; remove or keep the PD clip only with source + license note. Rules disqualify privacy/IP violations. |
| R14 | **NVIDIA Open Model License attribution** — derivative weights need "Licensed by NVIDIA Corporation under the NVIDIA Open Model License" notice; Cosmos requires "Built on NVIDIA Cosmos" on product pages (https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/) | 3 | 2 | 6 | Add NOTICE file + "Built on NVIDIA Cosmos" in app footer if Cosmos is used. Don't commit GR00T/SONIC weights to the repo. |
| R15 | **Scoring/metric bugs undermine the headline number** | 2 | 3 | 6 | Mostly fixed Sept 28 (protocol freeze, 20 tests). Add a regression test for each new predicate; freeze protocol before looking at results. |
| R16 | **Menagerie/Unitree asset licenses** — UR5e (ROS-Industrial BSD), Robotiq 2F-85 (ROS-Industrial BSD), Unitree G1 (Unitree BSD-style) — VERIFIED permissive with notice retention | 1 | 2 | 2 | Keep their LICENSE files alongside any copied assets. |

---

## 4. What to CUT (to guarantee an honest, finished submission)

Cut now (move to "future work" slide):
1. **Kubernetes cluster.** mk8s adds ops overhead with zero judge-visible value for this scope. Use Serverless Jobs for sweeps + one Endpoint/VM for the app. (Agent 03 may recommend otherwise; red team says only if it's ≤½ day.)
2. **Mobile base.** Fixed-base UR5e+2F85, labelled honestly. The "wheeled" word goes away unless a base is actually simulated.
3. **G1 autonomy (GR00T→SONIC)**. G1 = replay/tracking only.
4. **RGB-D ablation, KAIROS/Isaac 4.2 lab stack, HiPHI at scale, RHO-style evolutionary search.**
5. **GR00T fine-tune → stretch**, not a core deliverable. Attempt only after MVWV is frozen (earliest Oct 13).

Keep (non-negotiable):
- One human clip → two robots → scored outcomes from simulator state → failure stage attribution → one targeted correction with before/after paired trials → a report a user can open.

---

## 5. Minimum Viable Winning Version (must exist Oct 30, 10am PT)

1. **Web app with a public URL** ("TransferGap Report"): input = a human demo clip (pre-loaded example + upload); output = per-robot panel with sim video (third-person), success/failure, *which stage failed* (reach/grasp/lift/place/balance), a natural-language diagnosis from Nemotron (Token Factory, live call, receipt shown), and a "Apply correction → re-run" before/after comparison.
2. **Two embodiments in MuJoCo:** G1 via GEM-X→SONIC (motion tracking metrics: joint/keypoint tracking error, falls) and fixed-base UR5e+2F-85 (pick/lift/place of a block, scored by the existing `metrics.py`).
3. **≥1 correction experiment** with paired trials (e.g., calibrated tool-frame/object-relative target correction on the arm; N independent trial blocks, Wilson/bootstrap from existing code) — a real measured delta, including failures.
4. **Nebius usage that unambiguously counts:** Token Factory Nemotron calls in the live app path + one **Serverless Job** that ran the evaluation sweep (job ID + output in repo). Cosmos-Reason2 on an Endpoint if it made it; otherwise omitted, not faked.
5. **Repo:** all authored code (incl. what's now only on the VM), README reproduction steps, MIT LICENSE, NOTICE for NVIDIA/menagerie assets, evidence artifacts linked from README.
6. **Video (<3 min, YouTube public):** 0:00–0:20 problem (a demo that works for one robot fails on another — why?); 0:20–1:40 app walkthrough on the real deployed URL (≥1 min of "key application modules in action"); 1:40–2:30 the correction result with numbers and one honest failure; 2:30–2:55 who pays for this + architecture slide naming each NVIDIA model / Nebius service.

### Hard dates
- Sept 30: VM code rescued into git; arm scripted pick scored ≥1 success in MuJoCo.
- Oct 4: G1 replay metrics + arm replay from human clip, both producing episode JSONL.
- Oct 8: Serverless Job runs the sweep; app skeleton live at a URL.
- Oct 12: correction experiment done; Nemotron diagnosis in app. Cosmos in or dropped.
- Oct 17: feature freeze. (Only then: GR00T fine-tune stretch.)
- Oct 20–28: video, write-up, review. Submit Oct 29.

---

## 6. What would move the score most (judge's view)

| Change | Criterion lifted | Est. gain |
|---|---|---|
| Working app at a URL with the report | Design +4, Impact +2 | biggest single lever |
| Nemotron doing something non-obvious: reading structured sim failure logs and proposing a *parameterized* correction that is then actually executed and measured (closed loop: diagnose → correct → verify) | Idea +2, Tech +2 | makes the LLM load-bearing |
| Serverless Job for the eval sweep, shown in video | Tech +1, removes R7 | cheap |
| Named user + quote (e.g., the user's own lab with the KAIROS robot: "we need to know before collecting 100 teleop demos whether they'll transfer") | Impact +2 | cheap, and it's true for this team |
| GR00T fine-tune | Tech +1 at most | expensive — stretch only |

Bottom line: the project's *research instincts* are strong and its *packaging* is near zero. Judges score four equal criteria, two of which (Design, Impact) the current plan barely addresses. Spend the next 3 weeks turning one honest closed loop into a product, not adding models.
