# 06: TransferGap as a product and as a hackathon winner

Research agent 6 of 6. Researched Sept 29, 2026.

How to read the labels:
- **VERIFIED** means I read the fact on the cited page this session. Some of those pages were read through a summarizing fetch tool, so for anything critical, open the URL directly.
- **UNVERIFIED** means a secondary source or my own inference.
- Market numbers come only from cited sources. Where I have no source, I say "unknown."

---

## 1. The hackathon, and what judges actually score

**Sources:** https://nebiusglobalaihackathon.devpost.com/ and https://nebiusglobalaihackathon.devpost.com/rules (VERIFIED)

### Deadline, prizes and judges
- **Deadline:** Oct 30, 2026, 10:00 AM PDT.
- **Prizes:**
  - Overall: $20k for 1st, $10k for 2nd, $6k for 3rd.
  - Track winners get an NVIDIA Jetson Orin Nano, one per track.
  - Best Use of Tavily: $3k.
  - 20 city winners get $500 each.
  - 10 feedback prizes of $100 plus swag, for "Most Valuable Feedback."
- **Judges:** 18 people from NVIDIA, Nebius and Tavily, working in ML engineering, developer relations and product management.

### Stage 1 is pass/fail
- The project must "reasonably fit the theme and reasonably apply the required APIs/SDKs."
- It must be "a genuine attempt… not a superficial rebrand."

### Required technology
- **Nebius:** Token Factory, or Nebius AI Cloud (Serverless Jobs, Endpoints or DevPods).
  - Managed Kubernetes is **not named** on the rules page. A Kubernetes deployment should be presented as running on Nebius AI Cloud, and the project should still make at least one Token Factory call and/or run a Serverless Job so it clearly matches the listed options. (Inference, UNVERIFIED.)
- **NVIDIA:** at least one NVIDIA open-source model. The rules list Nemotron, GR00T, Cosmos and Sonic.

### Required submission items
- Text description.
- Public repo under **Apache 2.0, MIT or MPL 2.0**. The repo's MIT license is compliant.
- README with setup instructions.
- Video **under 3 minutes**.
- Track identification.
- Feedback on the Nebius and NVIDIA tools used.
- An explanation of updates if the project existed before the hackathon.

### ⚠️ Correction for the vault
"Working demo / hosted application" is required **"except Physical AI."** Instead, Physical AI needs **≥1-minute clip** of the hardware operating, or, if there is no hardware, "the key application modules in action."

Implementation Status.md currently says a demo URL is required. That is wrong for this track. It is optional, though still helpful for the Design score.

### Stage 2: four criteria, equally weighted (VERIFIED quotes)

| Criterion | Judges' wording | What it means for TransferGap |
|---|---|---|
| Technological Implementation | "how effectively does it use Nebius Token Factory or AI Cloud… and NVIDIA Nemotron or other NVIDIA open source models" | Each of the 5 NVIDIA models must visibly do real work, with receipts. Nebius usage must also be visible: an L40S VM, Token Factory calls, a Serverless Job. |
| Design | "a complete, coherent product experience not just a technical proof of concept" | **The biggest current weakness.** Today the project is CLI plus markdown. It needs a report viewer, meaning one screen a user reads to get "where transfer failed and why." |
| Potential Impact | "credible, specific case for solving a real problem for a real audience" | Name the buyer: data vendors and robot teams (section 2). Cite the pain with sources. |
| Quality of the Idea | "creative, non-obvious use of… models" | Five models with separated roles: Cosmos judges video, Nemotron plans and repairs, GR00T acts, Sonic tracks, and GEM-X perceives. Model opinions never define success; simulator labels do. That separation is itself the non-obvious part. |

### Optional bonus: Tavily, $3k
Only worth it if the use is genuine. One plausible use is retrieving known failure modes and fixes from papers or docs when Nemotron proposes a correction. Do not bolt it on. The rules reward genuine use, and a forced integration reads as a rebrand. (Recommendation, UNVERIFIED value.)

### Free money
Submit thoughtful tool feedback: 10 × $100.

---

## 2. Market: who has the "will this transfer to my robot?" problem

### Evidence of pain and spend (VERIFIED from cited pages unless marked)

**Investor narrative is "cross-embodiment"**
- "The strongest investor signal is attached to cross-embodiment claims." The companies named are Physical Intelligence, FieldAI, Skild AI, Rhoda AI and Flexion.
- One line summarizes the dynamic: "A startup claiming general robot intelligence needs evidence of cross-embodiment learning."
- Year-to-date 2026 embodied-AI funding is about $5.6B.
- Source: https://newmarketpitch.com/blogs/news/embodied-ai-funding-trends. This is a secondary aggregator, so treat the numbers as UNVERIFIED-grade.

**Robotics startups overall**
- Nearly $14B raised in 2025, and $18.8B in H1 2026.
- The figures are Crunchbase data, quoted by TechCrunch: https://techcrunch.com/2026/05/26/human-archive-taps-into-indias-services-startups-to-collect-data-for-physical-ai/

**The human-video data glut is TransferGap's best wedge**
- Source: Jeff Allen, Flikforge CEO, July 7, 2026, https://flikforge.com/robot-data-glut-egocentric-video-physical-ai/. The author has a vendor interest, so treat this as UNVERIFIED-grade.
- Teams reportedly discard about 90% of bulk egocentric footage.
- A customer is quoted: "we are lucky to find 2 or 3 segments suitable for training."
- Commodity footage trades at $2–5 per hour. Purpose-built data sells for roughly 100× that.
- Implication: buyers cannot tell in advance which human data will transfer to their robot. **TransferGap measures exactly that.**

**Human-video vendors are raising money** (VERIFIED)
- Human Archive (YC W26): $8.2M seed, with more than 1,000 active headsets (TechCrunch link above).
- Luel: $27M seed, reported in the same search set; this detail is UNVERIFIED.
- These vendors must prove to buyers that their data transfers. That makes them natural first customers.

**The industry gap is named explicitly**
- The Robot Report says robotics development runs "open-loop": failures rarely feed back into what gets collected or simulated next.
- https://www.therobotreport.com/5-physical-ai-infrastructure-platforms-shaping-robotics-in-2026/ (VERIFIED)
- TransferGap's diagnose → correct → re-measure loop is a direct answer to that.

### Competitor and adjacent landscape

| Player | What it does | Funding / scale | Transfer-gap diagnosis? |
|---|---|---|---|
| Lightwheel (RoboFinals, EgoSuite, SimFoundry, RoboStack) | Real2Sim2Real loop; RoboFinals finds policy failure modes in sim before deployment | ~$100M in Q1 2026 orders; NVIDIA partner. [PR](https://www.prnewswire.com/news-releases/100m-in-q1-orders--lightwheel-marks-the-start-of-physical-ai-at-scale-302764687.html) VERIFIED | **Closest competitor.** The press release says nothing about measuring human→robot or cross-embodiment transfer. It is enterprise and closed. |
| Applied Intuition | Validation engineering, AV heritage, moving into humanoids | ~$15.5B valuation (Robot Report / aggregator) | General validation, not embodiment transfer. |
| Scale AI Physical AI | Data engine, plus fine-tune validation of datasets; UR partnership in Mar 2026 | Large. [scale.com/physical-ai](https://scale.com/physical-ai) VERIFIED | Validates data by downstream fine-tuning. Single embodiment, internal. |
| Encord | Data curation, annotation and model evaluation | $60M Series C, Feb 2026; 10× physical-AI revenue growth. [SiliconANGLE](https://siliconangle.com/2026/02/26/physical-ai-data-infrastructure-startup-encord-lands-60m-accelerate-intelligent-robot-drone-development/) VERIFIED | No |
| Foxglove | Robotics observability and visualization | $40M Series B, Nov 2025; users include NVIDIA, Amazon, Anduril and Dexterity. [Robot Report](https://www.therobotreport.com/foxglove-raises-40m-scale-data-platform-roboticists/) VERIFIED | No. It visualizes logs and does not score transfer. **It is a potential integration target** for exporting TransferGap reports. |
| Rerun | Multimodal physical-AI database and viewer | $17M seed, Mar 2025. [SiliconANGLE](https://siliconangle.com/2025/03/20/rerun-gets-17m-build-essential-data-infrastructure-ai-powered-robots-drones-cars/) VERIFIED | No. It is also a viewer integration candidate. |
| HF LeRobot v0.6 (`lerobot-eval`, 6 sim benchmarks, DAgger rollout) | Open eval and training loop | Open source; released Jul 7, 2026. [news](https://letsdatascience.com/news/hugging-face-releases-lerobot-06-robotics-toolkit-908e3ba5) VERIFIED | Benchmarks one policy on fixed tasks. Not paired cross-embodiment. **TransferGap should consume and emit LeRobot format.** |
| RoboArena | Crowd-sourced, double-blind pairwise real-robot evals (DROID) | Academic plus NVIDIA; live through Dec 2026. [arXiv 2506.18123](https://arxiv.org/abs/2506.18123) VERIFIED | Ranks policies on one platform, not across embodiments. |
| SIMPLER, PolaRiS, RobotArena∞, RoboDojo, X2Real | Real-to-sim evaluation correlation | Research | Sim-vs-real fidelity, not human→multi-robot. |
| H2RBench (CMU/UMich/TRI, CoRL 2026) | Real2Sim benchmark for human-to-robot transfer methods; 4 tasks; sim-real r=0.89 | Code: github.com/xiaochy/H2RBench. [site](https://h2rbench.github.io/) VERIFIED | **Closest research.** It is a benchmark of methods on one robot, not a tool that diagnoses your demo on your two embodiments. TransferGap must cite it and differentiate from it. |
| "No Free Checker" survey (arXiv 2609.09250, Sept 2026) | Survey of about 150 verifiers for robot policies; finds "credibility falls as availability rises" | [arXiv](https://arxiv.org/abs/2609.09250) VERIFIED | Supports TransferGap's design choice: simulator-state labels are the credible verifier, and model opinions such as Cosmos are cheap but less credible, so they are kept separate. |

### What's missing that TransferGap fills
Nobody found offers a **paired, same-demo, multi-embodiment report**. That report would say:
- where execution diverges (perception, retargeting, contact, balance or timing),
- with a simulator-defined label,
- plus a tested targeted correction and a confidence interval.

Existing tools do only part of this. They either store and visualize data (Foxglove, Rerun, Encord), benchmark one policy on fixed tasks (LeRobot, RoboArena, SIMPLER), or sell closed enterprise sim evaluation (Lightwheel, Applied Intuition). This conclusion rests on a web search, not an exhaustive review. **Say "we did not find", not "no one does."**

---

## 3. Positioning, pricing and pitch

### Options, ranked

1. **Recommended: "Transfer report / CI for human-demo → robot transfer."**
   - Input: a human demo or dataset plus a robot spec.
   - Output: a paired transfer report covering success per embodiment, the failure stage, the suggested correction and the measured delta.
   - This fits the existing starter (the episode contract, `paired_gap`, receipts) and the Robot Report's "open-loop" gap.
2. **Data-collection ROI estimator** for human-video vendors and buyers.
   - It scores which clips or segments transfer to a given robot before anyone pays to fine-tune.
   - This is the strongest commercial wedge given the data glut above, but it needs many demos. It is a roadmap slide, not the hackathon deliverable.
3. **Pre-deployment embodiment compatibility check.**
   - It answers "should we buy robot A or B for this task?"
   - It is interesting to integrators, but the claim is hard to defend with 2 simulated embodiments. It is also a roadmap item.

### First customer profile (hypothesis, UNVERIFIED)
- A human-video data vendor, such as Human Archive, Luel or the egocentric providers listed at https://truelabel.ai/blog/best-egocentric-video-data-providers, that must prove its data transfers to a buyer's robot.
- Or a small humanoid or mobile-manipulator team that is choosing which demos to collect.

### Pricing ideas (hypotheses only; no market-price data found, so the right price is unknown)
- Per-report pricing, with each report run as a Nebius Serverless Job, so cost scales with GPU minutes.
- A team subscription for CI on each new dataset or policy checkpoint.
- Open-source core (the scorer and report format) plus a hosted runner. This is the same open-core pattern as Foxglove and Rerun.

### Pitches
- **1-line:** "TransferGap tells you, before you fine-tune, where a human demonstration will break on each of your robots and whether a targeted fix repairs it."
- **3-sentence:** "Robot teams are buying millions of hours of human video, but most of it never transfers, and nobody can say why until after an expensive fine-tune. TransferGap replays one human demonstration on two different robot embodiments in simulation, scores every attempt with simulator ground truth, and uses NVIDIA Cosmos and Nemotron to localize the failure and propose a bounded correction. The output is a paired transfer report with confidence intervals, a CI check for human-to-robot data, running on Nebius."

---

## 4. Comparable winners and what they show

- **NVIDIA Cosmos Cookoff** (Feb–Apr 2026; sponsored by **Nebius** and Milestone; more than 1,600 participants).
  - Source: https://forums.developer.nvidia.com/t/the-results-are-in-meet-the-nvidia-cosmos-cookoff-winners-see-them-live-on-april-16/366130 (VERIFIED)
  - **Gold:** "See How It Thinks: Mixed Palletizing with Explainable Visual Reasoning" by Team Zenith. Repo: `doosan-robotics/explainable-palletizer`.
  - **Silver:** "ResQ-AI: Autonomous Disaster Response Drone." It uses a sim-to-real pipeline. Repo: `AdityaP9116/ResQ-AI`.
  - **Bronze:** "Voice Controlled AI Video Intelligence" by LiveKit. Repo: `livekit-examples/robotics-cosmos-live`.
  - The post does not state the judges' reasoning.
  - **Pattern (inference, UNVERIFIED):** the winners paired a concrete industrial or real-world task with *visible reasoning* (explainability) and a sim-to-real story. Gold was literally "see how it thinks."
  - **TransferGap should borrow this:** show Cosmos's reasoning trace and the failure localization on screen, next to the simulator's ground-truth label.
- **Action item:** clone or skim `doosan-robotics/explainable-palletizer` to see its README and demo structure. It is from a Nebius-sponsored event, so it may resemble what these judges like. (Not done here.)

---

## 5. Ideal demo video, under 3:00 (target 2:45)

Rule: every on-screen claim must correspond to a saved artifact. Label replay and autonomy explicitly, and label any sim footage as sim.

| Time | Shot | Purpose |
|---|---|---|
| 0:00–0:15 | Hook: "Robot teams buy millions of hours of human video. ~90% gets thrown away. Nobody can tell *which* demo will work on *which* robot, until after the fine-tune." Cite the source on screen. | Impact |
| 0:15–0:35 | One human RGB clip (reach, pick, place) → GEM-X reconstruction overlay | NVIDIA model #1, perception |
| 0:35–1:05 | **Split screen:** the same demo on the G1 (Sonic) and on the arm, running live in MuJoCo from an external camera view (a third-person camera is still a TODO). | Wow setup |
| 1:05–1:30 | **Wow moment:** one embodiment fails (for example, the grasp misses by X mm). The TransferGap report card appears: simulator label `not_released_and_settled_at_goal`, the failure stage, and Cosmos-Reason2's timestamped explanation shown *next to* the simulator's label, not replacing it. | Explainability, as in the Cookoff gold |
| 1:30–1:55 | Nemotron proposes a bounded correction (for example, a tool-frame or object-relative target adjustment). A re-run follows. | NVIDIA models #2 and #3 |
| 1:55–2:20 | Paired result: success delta in percentage points with a bootstrap CI, across N held-out trials. If the fix did not help, **show that honestly**. A measured null result still demonstrates the product. | Credibility |
| 2:20–2:35 | GR00T N1.7 pilot fine-tune checkpoint and rollout (only if done), plus a 2-second "running on Nebius" shot showing the L40S / Serverless Job / Token Factory receipts. | Required technology |
| 2:35–2:45 | Closing line plus the repo URL. | — |

Also produce a separate **≥1-minute uncut clip** of "key application modules in action" to satisfy the Physical AI rule. The uncut clip counters any suspicion of editing.

---

## 6. README and Devpost write-up structure

1. One-line pitch and the 3-sentence pitch.
2. A 30-second GIF of the split-screen failure → report card.
3. **"What's real" table:** each claim → evidence file or receipt → status (done / partial / not done). This is the anti-overclaim device, and judges from NVIDIA will check.
4. Architecture diagram, with each of the 5 NVIDIA models' roles and every Nebius service used.
5. Quickstart: local scorer in under 2 minutes, plus a GPU runbook.
6. Results: paired table, CIs, failure taxonomy counts, and deliberately failing examples scored correctly.
7. Related work and how TransferGap differs: H2RBench, RoboArena, LeRobot eval, Lightwheel RoboFinals, "No Free Checker."
8. Limitations: simulation only, a UR5e stand-in rather than the KAIROS UR10, small n, and a single source demo.
9. Feedback on Nebius and NVIDIA tools. This is required, and it is also a $100 prize.
10. Pre-hackathon work disclosure (required). The repo was initialized Sept 28, while the plan and research predate it, so state this plainly.

---

## 7. Risks that lose points, and how to preempt them

| Risk | Criterion hit | Preempt |
|---|---|---|
| Overclaiming ("guaranteed", "two-robot benchmark done", "fine-tuning deliverable") | Implementation / Impact credibility | "What's real" table; separate replay from autonomy; state n and CIs |
| No visible product (CLI plus markdown only) | **Design** | A single-page report viewer (static HTML from JSON reports). A hosted version is optional but good. |
| NVIDIA use looks decorative (a model called once, output unused) | Implementation / Idea | Show each model's output changing a decision or artifact, and keep receipts |
| Nebius use unclear | Stage 1 / Implementation | Show at least one Token Factory call and one Serverless Job or Endpoint in the video, with the IDs |
| Cosmos not provisioned by the deadline | Implementation | Provision early. The fallback is a Cosmos endpoint via Token Factory if it is listed; otherwise say so honestly. |
| Novelty challenged by H2RBench or Lightwheel | Idea | A related-work section with a precise delta: a paired multi-embodiment *diagnosis plus correction* tool, not a methods benchmark |
| Sim-only oracle inflating results (the RHO blog-post trap) | Credibility | Keep success labels in simulator state, and state that they are sim-only |
| Video over 3:00, or the key moment after 1:30 | All | Put the wow moment by 1:05–1:30 |
| License or repo not public by the deadline | Stage 1 fail | Push the public GitHub repo by Oct 20 |
| Misreading the rules (demo URL) | — | Fix the vault note: Physical AI is exempt from the working-demo URL |

---

## 8. Bottom line
- Position TransferGap as **"CI / transfer report for human-demo → robot transfer."** The wedge is human-video buyers and vendors, backed by the data-glut evidence.
- The score-maximizing gaps are:
  1. **Design:** a report-viewer UI.
  2. An **honest paired result**, even a null one.
  3. **Visible, receipted use** of each NVIDIA model and Nebius service.
  4. The **wow moment** by 1:30: split-screen failure → localized explanation → correction → measured delta.
