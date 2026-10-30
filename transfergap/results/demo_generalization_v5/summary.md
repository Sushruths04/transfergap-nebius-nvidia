# Demo generalization v5 (pre-registered)

safe_path_v2 selected on dev seeds 0-19 (dev_selection_safe_path.jsonl). Held-out seeds 1000-1059, n=60 per cell. P1 = speed_cap_3, look_again, touch_probe_calibration, speed_cap_2; P2 = look_again, touch_probe_calibration.

| demo | stack | robot | no fix | stack | gain pp [95% CI] | path RMSE cm |
|---|---|---|---|---|---|---|
| person 1 notebook | P1+v2 | ur5e | 0/60 | **57/60** | +95.0 [+88.3, +100.0] | 13.9 -> 4.9 |
| person 1 notebook | P1+v2 | ur10e | 0/60 | **60/60** | +100.0 [+100.0, +100.0] | 9.1 -> 2.9 |
| person 1 markers | P1+v2 | ur5e | 0/60 | **51/60** | +85.0 [+75.0, +93.3] | 13.2 -> 7.1 |
| person 1 markers | P1+v2 | ur10e | 0/60 | **25/60** | +41.7 [+28.3, +55.0] | 7.8 -> 5.5 |
| person 1 orange marker | P1+v2 | ur5e | 0/60 | **46/60** | +76.7 [+65.0, +86.7] | 15.6 -> 7.5 |
| person 1 orange marker | P1+v2 | ur10e | 0/60 | **58/60** | +96.7 [+91.7, +100.0] | 10.4 -> 6.2 |
| person 1 notepad | P1+v2 | ur5e | 0/60 | **58/60** | +96.7 [+91.7, +100.0] | 14.5 -> 7.5 |
| person 1 notepad | P1+v2 | ur10e | 0/60 | **58/60** | +96.7 [+91.7, +100.0] | 9.5 -> 6.4 |
| person 2 box (own stack) | P2+v2 | ur5e | 11/60 | **60/60** | +81.7 [+71.7, +91.7] | 11.8 -> 12.8 |
| person 2 box (own stack) | P2+v2 | ur10e | 4/60 | **55/60** | +85.0 [+75.0, +93.3] | 8.4 -> 9.6 |
| person 2 box (single stack) | P1+v2 | ur5e | 11/60 | **60/60** | +81.7 [+71.7, +91.7] | 11.8 -> 12.4 |
| person 2 box (single stack) | P1+v2 | ur10e | 4/60 | **50/60** | +76.7 [+66.7, +86.7] | 8.4 -> 9.3 |

Simulation; assumed perception/calibration magnitudes; grasp/release frames annotated by inspection; person 2 uses object_height='hand_at_grasp'.

Person-2 result (v5 own stack: look_again, touch_probe_calibration, safe_path_v2) reproduced in Nebius Serverless Job `aijob-e00fzswzrgy0snz3ty` (image 7266371): UR5e 11 -> 60/60, UR10e 4 -> 55/60, identical to the local held-out run.
