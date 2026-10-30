# User demo v1 — the author's own recorded pick and place (pre-registered, protocol.json)

- Recording: 50 s, Logitech Brio 100, 1280x720 at 21.4 fps (private, gitignored); GEM-X offline (static camera).
- Annotated right-hand cycle: grasp frame 862, release frame 926 (+/- 6 frames); carry 15 cm up into a box.
- Feasibility pre-check (before the run): G1 feasible; UR5e/UR10e infeasible as copied (approach dips 1.7 cm into
  the table) -> the frozen single stack includes safe_path_v2.
- Held-out (seeds 1000-1059), frozen v5 single stack, no re-tuning:
  UR5e 35/60 -> 59/60 (+40.0 pp [28.3, 51.7]); UR10e 30/60 -> 56/60 (+43.3 pp [31.7, 55.0]).
- G1 whole-body replay of the full take through SONIC (SMPL v3, live/g1_replay.py + live/pt_stream.py): no fall,
  arms track (shoulder roll reaches +/-1.1 rad in the T-pose); arm-spread correlation person vs G1 0.88 after a
  24.3 s alignment. Video (gitignored): runs/videos/take1_side_by_side.mp4.
- Bug found on the way: frames streamed before ENTER enabled SONIC's ZMQ mode are dropped; the first replay played
  out entirely before streaming was on (robot stood still). pt_stream.py holds the first pose until enabled.

## Per-demo diagnosis loop on the author's demo (`demo_budget_v1_demobf3218bb_*`, strict rule, held-out 1000-1059)

| step | stage found (dev) | fix | UR5e held-out | UR10e held-out |
|---|---|---|---|---|
| 0 | - | - | 35/60 | 30/60 |
| 1 | perception (both) | look_again | 52/60 | 39/60 |
| 2 | calibration (both) | touch_probe_calibration | **57/60** | **51/60** |
| 3 | stop: no positive budget left in the menu | - | - | - |

- oracle_all = 100% on dev for both arms: the copied style is feasible; the kinematic pre-check's 1.7 cm finger
  penetration flag was a false alarm (the table stops the fingers), as for person 2 on the UR5e.
- Slowing down HURTS this person (timing budget -10 / -15 pp at step 3): the author already moves at a pace the
  arms can follow (plan timing_scale 2.0 vs 5.9 for person 1).
- UR10e keeps a 21.7 pp perception budget after look_again (menu exhausted) -> a gap for a new correction.
- The single recipe from two other people (v5 stack, above) reached 59/60 and 56/60 — slightly better than the
  person's own 2-step diagnosis, because it also contains safe_path_v2 and the speed caps.

## Nemotron 3 Super as the diagnosing agent on this demo (`agent_choice.json` per step; 6 Token Factory calls)

Consulted after the rule's held-out runs (retrospective) but given only the dev gap budget, as in demo_agent.py.
- Steps 1-2: agrees with the rule on all 4 decisions (look_again, then touch_probe_calibration, both arms).
- Step 3, where the strict rule stops: the agent proposes speed_cap_3 (UR5e) and safe_path (UR10e). Held-out, paired
  by seed against the rule's stopping point: UR5e 57 -> 57/60 (+0.0 pp, the cap is a no-op at this person's pace);
  **UR10e 51 -> 56/60 (+8.3 pp [1.7, 15.0])** (`agent_step3_*/`). The agent recovered the gap the rule's menu logic
  left (the copied approach grazes the table on the longer arm; safe_path removes that).
