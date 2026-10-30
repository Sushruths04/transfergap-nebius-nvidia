---
type: backlog
updated: 2026-09-30
tags: [ideas, backlog, stretch]
---

# Ideas Backlog

Stretch ideas, not committed. Do them only after the core result exists (feature freeze Oct 17). Sources: [[Research Synthesis 2026-09-30]] §3, §6, §10; reports [[10_nvidia_stack]], [[11_cosmos_worldmodel]], [[13_synthetic_data]], [[05_embodiments_sim]], [[06_product_hackathon]]. Back to [[Home]] · [[Knowledge/README|Knowledge]].

| Idea | What | Gate / risk | Note |
|---|---|---|---|
| **GR00T arm pilot** | MimicGen-lite episodes -> GR00T N1.7 fine-tune on the UR arm | User-approved stretch (Sept 30); needs at least 100 episodes; gated Cosmos-Reason2-2B access | [[GR00T N1.7]] |
| **Cosmos-Predict2.5 world model (tier 2)** | Action-conditioned 2B arm world model fit to our sim runs; predict success before execution | High risk; L40S training cost unknown; no G1 checkpoint | [[Cosmos-Predict2.5 and Transfer2.5]] |
| **Cosmos early-frame prediction (tier 1)** | Predict success from first frames; test readout transfer arm -> G1 | After Tier 0 critic exists | [[Cosmos 3]] |
| **Cosmos 3 forward dynamics preview** | Preview a proposed correction before running it in sim (UR 10D listed) | Needs H100 spot Job; unproven | [[Cosmos 3]] |
| **Cosmos-Transfer2.5 photoreal shots** | Ablation: does critic accuracy hold on photoreal video | 65 GB, H100 only; decorative if only for visuals | [[Cosmos-Predict2.5 and Transfer2.5]] |
| **HiPHI mocap-vs-monocular ablation** | Optical mocap vs monocular GEM-X on matched motion classes | Research licence, 215 GB (download selectively by Frame/LU), needs GMR joint map; conversion script only, never redistribute | [[Related Work]] |
| **TidyBot mobile base** | Mount the MIT TidyBot holonomic base under the arm | Label the arm fixed-base until then | [[05_embodiments_sim]] |
| **UR10e KAIROS twin** | UR10e + 2F-85 (closest public match to KAIROS); milestone 1 fixed base | Planned Oct 1-3 variant; the KAIROS stack itself is cut | [[05_embodiments_sim]] |
| **Nemotron Omni second critic** | Independent video critic scored against the same labels | Not on Token Factory; FP8 self-host | [[Nemotron]] |
| **HF dataset release** | LeRobot v2.1 stage-labelled paired episodes, scorer, frozen protocol | Licence chain (menagerie, NVIDIA Open Model License, HiPHI) | [[12_paper_recognition]] |
| **Upstream `deploy.sh` docs PR** | Fix the README vs tutorial flag contradiction; document the `[Y/n]` prompt | Cheap, shows competence | [[People and Labs]], [[Lessons Learned]] |
| **Sim-vs-real rank agreement** | Pearson/Spearman/MMRV as in H2RBench, if any KAIROS trials happen | Needs hardware | [[Related Work]] |
| **Isaac Lab-Arena / RoboLab metric alignment** | Graded score + SPARC in `metrics.py`; GR00T client-server contract | About 4 h; recommended, not stretch | [[MuJoCo Warp]] |
| **Static leaderboard** | README or HF Space table (embodiment x correction) | Live leaderboard not worth it | [[12_paper_recognition]] |
| **Product: "CI for human-to-robot transfer"** | Tell teams where a demo will break on each robot and whether a fix repairs it; first customers human-video data vendors and cross-embodiment robot teams (UNVERIFIED hypothesis). Commercial use of HiPHI-derived data needs a separate licence | Product surface is the biggest Design lever; NVIDIA Inception only if it becomes a startup | [[06_product_hackathon]] |
| **GTC poster / RSS full study** | Reuse the hackathon output | Deadlines in [[Deadlines]] | [[Deadlines]] |
