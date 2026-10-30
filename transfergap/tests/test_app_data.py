"""Data-loading layer of the Gradio app (app/backend.py). Does not import gradio."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "app"))

import backend as B  # noqa: E402

from test_core import episode  # noqa: E402


def write_run(results, name, summary):
    d = Path(results) / name
    d.mkdir(parents=True)
    (d / "summary.json").write_text(json.dumps(summary))
    return d


def minimal_summary(**extra):
    cond = {"oracle": "none", "n": 10, "successes": 4, "success_rate": .4, "wilson_95": [.17, .69],
            "failure_reasons": {"no_lift": 6}}
    s = {"git_commit": "abcdef1234567", "dev": {"seeds": [0, 9], "conditions": {"full": cond},
         "budget": {"retargeting": {"delta_pp": 20.0, "ci95_pp": [5.0, 35.0], "n": 10}}}}
    s.update(extra)
    return s


class RecordedRunTests(unittest.TestCase):
    def test_discovers_recorded_gap_budget_v1(self):
        runs, problems = B.discover_runs()
        self.assertEqual(problems, [])
        run = {r.name: r for r in runs}["gap_budget_v1"]
        self.assertEqual(run.robot, "UR5e + Robotiq 2F-85")
        self.assertTrue(run.robot_inferred)
        self.assertTrue(run.has_heldout)
        self.assertEqual(run.commit, "f8dd798")

    def test_provenance_label_has_run_date_commit_seeds(self):
        run = B.load_run(B.RESULTS_DIR / "gap_budget_v1")
        dev, held = B.provenance(run, "dev"), B.provenance(run, "heldout")
        for label in (dev, held):
            self.assertIn("Recorded run `gap_budget_v1`", label)
            self.assertIn("commit `f8dd798`", label)
            self.assertIn(run.recorded, label)
        self.assertIn("dev seeds 0-59", dev)
        self.assertIn("held-out seeds 1000-1059", held)

    def test_budget_rows_match_summary(self):
        run = B.load_run(B.RESULTS_DIR / "gap_budget_v1")
        rows = {r["stage"]: r for r in B.budget_rows([run])}
        self.assertEqual(set(rows), {"perception", "calibration", "timing", "all"})
        self.assertAlmostEqual(rows["perception"]["delta_pp"], 11.6667, places=3)
        self.assertEqual((rows["calibration"]["ci_low"], rows["calibration"]["n"]), (run.summary["dev"]["budget"]["calibration"]["ci95_pp"][0], 60))
        self.assertEqual(rows["all"]["kind"], "all")
        self.assertAlmostEqual(rows["all"]["delta_pp"], 43.333, places=2)

    def test_success_rows_carry_wilson_ci(self):
        run = B.load_run(B.RESULTS_DIR / "gap_budget_v1")
        rows = {r["Condition"]: r for r in B.success_rows([run], "dev")}
        self.assertEqual(rows["full"]["Success"], "34/60")
        self.assertEqual(rows["full"]["Wilson 95% CI"], "[44%, 68%]")
        self.assertEqual(rows["oracle_all"]["Failure reasons"], "-")
        held = B.success_rows([run], "heldout")
        self.assertEqual([r["Condition"] for r in held], ["full", "full+look_again"])

    def test_correction_view_recomputes_verdict(self):
        run = B.load_run(B.RESULTS_DIR / "gap_budget_v1")
        v = B.correction_view(run)
        self.assertEqual(v["correction"], "look_again")
        self.assertEqual(v["before"]["successes"], 32)
        self.assertEqual(v["after"]["successes"], 45)
        self.assertTrue(v["excludes_zero"])
        self.assertTrue(v["improved"])
        self.assertEqual(v["excludes_zero"], v["recorded_flag"])
        self.assertTrue(v["verdict"].startswith("Yes"))


class DiscoveryTests(unittest.TestCase):
    def test_future_run_with_robot_field_and_no_heldout(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_run(tmp, "gap_budget_g1", minimal_summary(robot="Unitree G1 (SONIC)", recorded_at="2026-10-09T12:00:00Z"))
            write_run(tmp, "broken", {"not": "a budget"})
            (Path(tmp) / "no_summary").mkdir()
            runs, problems = B.discover_runs(tmp)
        self.assertEqual([r.name for r in runs], ["gap_budget_g1"])
        self.assertEqual(len(problems), 1)
        self.assertIn("broken", problems[0])
        run = runs[0]
        self.assertEqual(run.robot, "Unitree G1 (SONIC)")
        self.assertFalse(run.robot_inferred)
        self.assertEqual(run.recorded, "2026-10-09")
        self.assertFalse(run.has_heldout)
        self.assertIsNone(B.correction_view(run))
        self.assertEqual([r["stage"] for r in B.budget_rows([run])], ["retargeting"])   # no oracle_all -> no row
        self.assertIn("dev seeds 0-9", B.provenance(run))
        self.assertEqual(B.success_rows([run], "heldout"), [])

    def test_missing_results_dir_is_reported(self):
        runs, problems = B.discover_runs("/nonexistent/transfergap/results")
        self.assertEqual(runs, [])
        self.assertEqual(len(problems), 1)

    def test_ci_excludes_zero(self):
        self.assertTrue(B.ci_excludes_zero([0.1, 5]))
        self.assertTrue(B.ci_excludes_zero([-5, -0.1]))
        self.assertFalse(B.ci_excludes_zero([0.0, 23.3]))   # touching zero does not exclude it
        self.assertFalse(B.ci_excludes_zero([-3, 3]))

    def test_correction_view_ci_including_zero_says_no(self):
        s = minimal_summary(heldout={"seeds": [100, 109], "correction": "look_again", "conditions": {
            "full": minimal_summary()["dev"]["conditions"]["full"],
            "full+look_again": minimal_summary()["dev"]["conditions"]["full"]},
            "paired_gap_corrected_minus_full": {"delta_pp": 0.0, "ci95_pp": [-10.0, 10.0], "n": 10}})
        with tempfile.TemporaryDirectory() as tmp:
            run = B.load_run(write_run(tmp, "r", s))
        v = B.correction_view(run)
        self.assertFalse(v["excludes_zero"])
        self.assertTrue(v["verdict"].startswith("No"))


class UploadTests(unittest.TestCase):
    def test_parse_jsonl_reports_line(self):
        with self.assertRaisesRegex(ValueError, "line 2"):
            B.parse_jsonl('{"a": 1}\n{oops\n')
        with self.assertRaisesRegex(ValueError, "no episodes"):
            B.parse_jsonl("\n\n")
        with self.assertRaisesRegex(ValueError, "one JSON object"):
            B.parse_jsonl("[1, 2]\n")

    def test_scores_example_fixture_with_metrics(self):
        eps = B.parse_jsonl(B.EXAMPLE_EPISODES.read_text())
        with self.assertRaisesRegex(ValueError, "Fixture"):
            B.score_upload(eps)
        res = B.score_upload(eps, allow_fixtures=True)
        self.assertEqual(len(res["report"]["groups"]), 1)
        self.assertEqual(len(res["episodes"]), len(eps))
        self.assertIsNone(res["paired"])

    def test_two_conditions_get_paired_gap(self):
        a, b = [], []
        for i in range(4):
            x = episode()
            x.update(trial_id=f"t{i}", seed=i)
            y = copy.deepcopy(x)
            y["method"] = "corrected"
            if i < 2:   # baseline fails on two trials (no lift)
                x["states"][1]["object_xyz"][2] = .02
            a.append(x)
            b.append(y)
        res = B.score_upload(a + b, allow_fixtures=True)
        p = res["paired"]
        self.assertEqual((p["a"], p["b"]), ("corrected", "fixture_replay"))
        self.assertEqual(p["paired_trials"], 4)
        self.assertEqual(p["success_gap_b_minus_a_pp"], -50.0)
        self.assertEqual(sum(r["success"] == "yes" for r in res["episodes"]), 6)

    def test_mismatched_trials_report_error_not_crash(self):
        x, y = episode(), episode()
        y["method"], y["trial_id"] = "other", "different"
        p = B.score_upload([x, y], allow_fixtures=True)["paired"]
        self.assertIn("error", p)


class DiagnoseTests(unittest.TestCase):
    def setUp(self):
        self.run = B.load_run(B.RESULTS_DIR / "gap_budget_v1")

    def test_disabled_without_key(self):
        enabled, msg = B.diagnose_status({})
        self.assertFalse(enabled)
        self.assertIn("NEBIUS_API_KEY", msg)
        self.assertFalse(B.diagnose_status({"NEBIUS_API_KEY": "x"})[0])
        with patch.dict("os.environ", {}, clear=True):
            res = B.run_diagnosis(self.run, caller=lambda *a: self.fail("must not call the model"))
        self.assertFalse(res["ok"])

    def test_status_never_reveals_key(self):
        secret = "sk-very-secret-value"
        enabled, msg = B.diagnose_status({"NEBIUS_API_KEY": secret, "NEMOTRON_MODEL": "nvidia/nemotron-x"})
        self.assertTrue(enabled)
        self.assertNotIn(secret, msg)

    def test_messages_contain_trace_and_menu_only(self):
        msgs = B.diagnosis_messages(self.run)
        payload = json.loads(msgs[1]["content"])
        self.assertEqual(set(payload), {"failure_trace", "correction_menu"})
        self.assertEqual(payload["failure_trace"]["gap_budget_pp"]["perception"]["recovery_pp"], 11.7)
        self.assertEqual(payload["correction_menu"]["perception"]["correction"], "look_again")

    def test_parse_proposal_checks_menu(self):
        good = 'Sure:\n```json\n{"stage": "perception", "correction": "look_again", "rationale": "r"}\n```'
        self.assertEqual(B.parse_proposal(good)[1], None)
        self.assertIn("not in the menu", B.parse_proposal('{"stage": "vibes", "correction": "x"}')[1])
        self.assertIn("does not match", B.parse_proposal('{"stage": "timing", "correction": "look_again"}')[1])
        self.assertEqual(B.parse_proposal("no json here"), (None, "response is not a JSON object"))

    def test_run_diagnosis_uses_hosted_adapter_and_hides_key(self):
        secret = "sk-very-secret-value"
        seen = {}

        def fake_call(role, messages, path):
            seen.update(role=role, path=path)
            return {"status": "succeeded", "requested_model": "m", "returned_model": "m", "latency_s": 1.2,
                    "request_sha256": "ab" * 32, "content": '{"stage": "perception", "correction": "look_again", '
                    '"rationale": "largest budget item", "expected_effect": "fewer no_lift"}'}
        with tempfile.TemporaryDirectory() as tmp, \
                patch.dict("os.environ", {"NEBIUS_API_KEY": secret, "NEMOTRON_MODEL": "m"}):
            res = B.run_diagnosis(self.run, out_dir=tmp, caller=fake_call)
        self.assertEqual(seen["role"], "nemotron")
        self.assertTrue(res["ok"])
        self.assertTrue(res["agrees_with_rule"])
        self.assertNotIn(secret, json.dumps(res))

    def test_run_diagnosis_failure_is_reported(self):
        def boom(*a):
            raise RuntimeError("nemotron request failed (HTTPError); see receipt")
        with tempfile.TemporaryDirectory() as tmp, \
                patch.dict("os.environ", {"NEBIUS_API_KEY": "k", "NEMOTRON_MODEL": "m"}):
            res = B.run_diagnosis(self.run, out_dir=tmp, caller=boom)
        self.assertFalse(res["ok"])
        self.assertIn("HTTPError", res["message"])


if __name__ == "__main__":
    unittest.main()
