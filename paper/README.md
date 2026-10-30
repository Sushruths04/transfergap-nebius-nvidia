# Workshop paper

The 2026-10-07 final limited revision is complete in `main.tex`; upload `main_submission.pdf`: four body pages, one references page, and one anonymous appendix page (six total), in the official double-blind submission style. `main_draft.pdf` is an identical copy for existing links. The conditional transfer bottleneck is central throughout. `DRAFT_ABSTRACT_INTRO_CONCLUSION.tex` contains synchronised editorial extracts; `SUBMISSION_ABSTRACT.txt` is the current abstract for submission-form copying.

`PRE_SUBMISSION_AUDIT_2026-10-07.md` records the latest limited changes, reviewer verdict, manual checks and submission readiness. `FINAL_REVIEW_2026-10-07.md` records the earlier positioning revision and optional future experiments; its manuscript-disclosure wording is superseded by the final pass. All references are checked in `REFERENCE_AUDIT_2026-10-07.md`; number provenance and reconstruction limits are in `NUMERICAL_AUDIT_2026-10-07.md`. The additional read-only audit `audit_supplementary.py` recounts saved depth/version rows and compares all 100 real-number macros. `submission_verification_2026-10-07.json` records the final PDF hash, page structure, anonymous metadata and macro hashes.

`REVIEW_2026-10-06.md` records the detailed review, verification, remaining research limitations, and a finding-by-finding cross-check of the additional review supplied by the user. `REVIEW_FINDINGS.md` is the historical October 5 review. `review_recount_20261006.json` records the new saved-episode recount; every requested arm/table/G1 count and paired arm bootstrap interval matches.

The current number generators are `make_fig_v3.py` and `make_numbers_real.py`; setup constants remain in `figures/numbers.tex`. The latter now also generates the style-depth stress counts (88/120, 88/120, 91/120) from saved results. Every previously generated number macro is unchanged. `figures/number_sources.txt` records the B–D number sources.

Build from the repository root with an installed TeX compiler:

```bash
cd paper
tectonic main.tex
```

Alternatively use `latexmk -pdf main.tex`. The verified rebuild used an existing Tectonic 0.15.0 binary and cached TeX resources in an isolated local build directory. The final PDF has no undefined references/citations/macros or overfull boxes. The cached `lineno.sty` warning, template `xcolor` colour-definition warnings, two underfull bibliography lines, and Tectonic rerun-consistency warning are nonblocking; all six final pages were rendered and checked. PDF author metadata remains `Anonymous Submission`.

The existing cluster code passed 222 tests, seven skipped. Its 101 Python source/test files match this checkout. The cluster does not have the local `tests/test_record_clip.py` (two unrelated recorder tests), so that file is not covered by the run. No application/experiment code or result files were changed, and no experiments were rerun.

The fresh 500-seed arm study is confirmatory within its assumed error model. Revised-seed video results are exploratory; the separate unused-seed results condition on the same six demonstrations. Stage budgets are signed gains, not additive failure shares. The nominal and demonstration-derived timing models yield different dominant components. G1 runtime differences remain unexplained and are confined to the appendix; the small version comparison also changed `filelock`. Fresh-demo bootstrap intervals and measured depth-error RMS cannot be independently reconstructed from individual observations, which were not saved. These are evidence limits, not outstanding writing fixes.

The author still needs to read the final PDF, check the submission form, and personally submit. Keep submission mode; real author information belongs only in a later camera-ready version. See `SUBMISSION_CHECKLIST.md`. No public release or submission was performed.
