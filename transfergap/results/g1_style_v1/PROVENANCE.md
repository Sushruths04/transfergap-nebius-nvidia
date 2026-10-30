# G1 copying a real human demo's style (g1_style_v1)

- Demo: Pexels clip 8135753 (notebook into a box) → GEM-X → `demo/gemx.py` → style plan
  (`runs/demos/pexels_8135753_notebook.plan.json`, gitignored; regenerate with `demo.style.style_plan_from_demo`).
- Motion: `g1/plan_reach.py --demo-plan` (commit `c8dfbf8`): the G1 right hand follows the retargeted human path
  (reach, carry, retreat legs); grasp calibration = the frozen `g1_contact_v1` plan args (stance offset
  (-0.075, 0.005), grasp_dz 0.03, pitch -0.2, roll -0.4); per-seed true block target (perception oracle).
- Conditions (defined in `g1/run_style.sh`, committed at `d33f075` before the run): execution speed only —
  human pace (timing_scale 5.92), speed cap 3x, robot nominal. Seeds 100–109 × 3 rollouts (SONIC+MuJoCo is
  nondeterministic). No tuning between conditions; no held-out/dev split (one pass, all reported).
- Scoring: `g1/score.py` tiers (touch / grasp / place = metrics.score_episode) and `g1/style_score.py` (wrist
  path vs planned human-derived wrist path, one time shift per rollout, median shift 4.2–4.6 s).
- Raw logs: gitignored `runs/g1_style/` (laptop) and the VM disk.
