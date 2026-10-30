# gap_budget_v3: 500 fresh seeds per arm, all corrections held-out

Protocol and hypotheses: `protocol.json` (committed before the run). Seeds 3000-3499, paired by seed.

## ur5e

full: 232/500

| stage | budget pp | 95% CI |
|---|---|---|
| perception | +30.0 | [+25.8, +34.4] |
| retargeting | +8.8 | [+5.6, +12.0] |
| calibration | +17.0 | [+13.2, +20.8] |
| timing | +11.2 | [+8.0, +14.6] |
| oracle_all | +53.6 | [+49.2, +58.0] |

Interaction (sum of singles minus oracle_all): +13.4 pp, 95% CI [+6.2, +20.8]

| correction (held-out) | successes | gain pp | 95% CI |
|---|---|---|---|
| look_again (perception) | 366/500 | +26.8 | [+22.6, +31.2] |
| ik_resolve (retargeting) | 272/500 | +8.0 | [+5.0, +11.4] |
| touch_probe_calibration (calibration) | 320/500 | +17.6 | [+13.6, +21.6] |
| speed_cap_3 (timing) | 264/500 | +6.4 | [+4.0, +8.8] |

Largest gain: look_again

## ur10e

full: 240/500

| stage | budget pp | 95% CI |
|---|---|---|
| perception | +29.4 | [+25.0, +33.8] |
| retargeting | +6.4 | [+3.0, +9.8] |
| calibration | +12.0 | [+8.2, +15.6] |
| timing | +8.0 | [+5.4, +10.8] |
| oracle_all | +52.0 | [+47.6, +56.4] |

Interaction (sum of singles minus oracle_all): +3.8 pp, 95% CI [-2.6, +10.4]

| correction (held-out) | successes | gain pp | 95% CI |
|---|---|---|---|
| look_again (perception) | 369/500 | +25.8 | [+21.6, +30.2] |
| ik_resolve (retargeting) | 277/500 | +7.4 | [+4.2, +10.8] |
| touch_probe_calibration (calibration) | 307/500 | +13.4 | [+9.6, +17.0] |
| speed_cap_3 (timing) | 276/500 | +7.2 | [+4.8, +9.6] |

Largest gain: look_again
