# Outcome against the pre-registered hypotheses (protocol.json, committed before the run)

- H1 supported on both arms: look_again gain +26.8 pp [22.6, 31.2] (UR5e), +25.8 pp [21.6, 30.2] (UR10e).
- H2 supported: look_again, the correction chosen on dev seeds, is the largest of the four on both arms.
- H3 NOT supported: with 500 seeds the interaction term (sum of singles minus oracle_all) is +13.4 pp [6.2, 20.8] on the UR5e
  and +3.8 pp [-2.6, 10.4] on the UR10e. Both are non-negative; the sign flip seen with 60 seeds in gap_budget_v2 did not replicate (a between-arm contrast was not tested, so its cause is not established; sampling variation is the likely reading, not a demonstrated one).
- H4 NOT supported: retargeting recovers +8.8 pp [5.6, 12.0] (UR5e) and +6.4 pp [3.0, 9.8] (UR10e), both excluding zero;
  the 60-seed result (-5.0 pp, interval spanning zero) was too small a sample to see it.
- Budget ranking with 500 seeds, both arms: perception > calibration > timing ~ retargeting (UR5e 30.0 / 17.0 / 11.2 / 8.8).
Note: the first launch scored episodes quadratically and was killed after the UR5e episodes were written; the analysis was fixed
(cached scoring, no change to any definition) and the run resumed from the saved UR5e episodes.
