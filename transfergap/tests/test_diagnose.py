"""Diagnosis agent: strict menu validation, mocked Nemotron receipts, dev-only loop. No network, no credentials."""
import copy
import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from transfergap.diagnose import (DEFAULT_PARAMS, MENU, SUPER_MODEL, extract_json, nemotron_diagnosis,
                                  validate_correction)

try:
    import numpy  # noqa: F401
    import mujoco  # noqa: F401
    SIM = True
except ImportError:
    SIM = False

ROOT = Path(__file__).resolve().parents[1]
LOOK = {"target_stage": "perception", "operator": "look_again", "params": {"looks": 1}}


def proposal(op, **params):
    return {"target_stage": MENU[op]["target_stage"], "operator": op, "params": params or DEFAULT_PARAMS[op]}


class MenuValidation(unittest.TestCase):
    def test_every_default_is_on_menu(self):
        for op in MENU:
            self.assertEqual(validate_correction(proposal(op))["operator"], op)
        fixed = proposal("tool_frame_calibration", method="fixed_offset", offset_m=[0.01, 0, -0.02])
        self.assertEqual(validate_correction(fixed)["params"]["offset_m"], [0.01, 0.0, -0.02])

    def test_rejects_anything_off_menu(self):
        bad = [
            None, [], "look_again",
            {**LOOK, "operator": "retrain_policy"},
            {**LOOK, "target_stage": "timing"},                         # operator/stage mismatch
            {**LOOK, "confidence": 0.9},                                # unknown top-level key
            {"operator": "look_again", "params": {"looks": 1}},         # missing stage
            {**LOOK, "params": {"looks": 1, "sigma": 0.001}},           # unknown param
            {**LOOK, "params": {"looks": 4}},                           # out of bounds
            {**LOOK, "params": {"looks": True}},                        # bool is not int
            {**LOOK, "params": {"looks": 1.0}},                         # float is not int
            proposal("timing_scale", speed_cap=math.nan),
            proposal("timing_scale", speed_cap=0.5),
            proposal("timing_scale", speed_cap="2"),
            proposal("grip_force", scale=3.0),
            proposal("tool_frame_calibration", method="fixed_offset", offset_m=[0.1, 0, 0]),
            proposal("tool_frame_calibration", method="fixed_offset", offset_m=[0.01, 0]),
            proposal("tool_frame_calibration", method="touch_probe", probes=1, offset_m=[0, 0, 0]),
            proposal("tool_frame_calibration", method="laser_tracker"),
            {**LOOK, "rationale": "x" * 1001},
            {**LOOK, "params": [1]},
        ]
        for item in bad:
            with self.assertRaises(ValueError, msg=repr(item)[:80]):
                validate_correction(item)

    def test_validation_normalises_and_does_not_alias(self):
        raw = proposal("timing_scale", speed_cap=2)
        out = validate_correction(raw)
        self.assertEqual(out["params"], {"speed_cap": 2.0})
        out["params"]["speed_cap"] = 9
        self.assertEqual(raw["params"]["speed_cap"], 2)

    def test_extract_json_is_strict(self):
        self.assertEqual(extract_json('<think>hmm</think>\n```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json(' {"a": 1} '), {"a": 1})
        for bad in ('Here you go: {"a": 1}', '{"a": NaN}', '{"a": 1} {"b": 2}', ""):
            with self.assertRaises(ValueError):
                extract_json(bad)


def fake_response(content, rid="chatcmpl-test"):
    return io.StringIO(json.dumps({"id": rid, "model": SUPER_MODEL, "choices": [{"message": {"content": content},
                                   "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                                                                         "total_tokens": 15}}))


def toy_trace(seeds=(0, 1, 2)):
    return {"schema": "transfergap.failure_trace/v1", "split": "dev", "seeds": list(seeds),
            "budget_pp": {"perception": {"delta_pp": 11.7, "ci95_pp": [0, 23.3]},
                          "calibration": {"delta_pp": 11.7, "ci95_pp": [3.3, 21.7]},
                          "timing": {"delta_pp": 5.0, "ci95_pp": [0, 10]}}}


@unittest.skipUnless(SIM, "needs numpy + mujoco (sim seed constants)")
class NemotronReceipts(unittest.TestCase):
    env = {"NEBIUS_API_KEY": "test-secret"}

    def call(self, content=None, side_effect=None):
        sent = {}

        def opener(self_, request, timeout=None):
            sent["body"] = json.loads(request.data)
            sent["timeout"] = timeout
            if side_effect:
                raise side_effect
            return fake_response(content)
        d = tempfile.mkdtemp()
        path = Path(d) / "receipt.json"
        with patch.dict("os.environ", self.env, clear=True), patch("urllib.request.OpenerDirector.open", opener):
            prop, receipt = nemotron_diagnosis(toy_trace(), path)
        return prop, receipt, json.loads(path.read_text()), path, sent

    def test_valid_proposal_receipt(self):
        prop, _, stored, path, sent = self.call(json.dumps(proposal("look_again", looks=2)))
        self.assertEqual(sent["body"]["model"], SUPER_MODEL)
        self.assertIn("correction_menu", sent["body"]["messages"][1]["content"])
        self.assertEqual(prop["params"], {"looks": 2})
        self.assertTrue(stored["validated"])
        self.assertEqual(stored["response_id"], "chatcmpl-test")
        self.assertEqual(stored["usage"]["total_tokens"], 15)
        self.assertIn("latency_s", stored)
        self.assertEqual(stored["requested_model"], SUPER_MODEL)
        self.assertNotIn("test-secret", path.read_text())

    def test_off_menu_reply_is_recorded_as_not_validated(self):
        prop, _, stored, _, _ = self.call(json.dumps({"target_stage": "policy", "operator": "finetune", "params": {}}))
        self.assertIsNone(prop)
        self.assertEqual(stored["status"], "succeeded")
        self.assertFalse(stored["validated"])
        self.assertIn("not on the correction menu", stored["validation_error"])

    def test_prose_reply_is_not_validated(self):
        prop, _, stored, _, _ = self.call("I suggest looking again: " + json.dumps(LOOK))
        self.assertIsNone(prop)
        self.assertFalse(stored["validated"])

    def test_failed_request_still_closes_receipt(self):
        prop, _, stored, _, _ = self.call(side_effect=TimeoutError())
        self.assertIsNone(prop)
        self.assertEqual(stored["status"], "failed")
        self.assertFalse(stored["validated"])

    def test_no_key_no_call_no_receipt(self):
        with tempfile.TemporaryDirectory() as d, patch.dict("os.environ", {}, clear=True), \
                patch("urllib.request.OpenerDirector.open") as opener:
            with self.assertRaises(ValueError):
                nemotron_diagnosis(toy_trace(), Path(d) / "r.json")
            opener.assert_not_called()
            self.assertFalse((Path(d) / "r.json").exists())


def fake_episode(seed, cond, success):
    lift = 0.15 if success else 0.02
    goal = [0.3, 0, 0.02]
    pos = [[0, 0, .02], [0, 0, lift], goal if success else [0, 0, .02], goal if success else [0, 0, .02],
           goal if success else [0, 0, .02]]
    return {"schema_version": 1, "source": "simulation", "trial_id": f"seed{seed}", "demo_id": "d", "seed": seed,
            "scene_id": f"s{seed}", "robot": "toy", "method": f"toy[{cond}]", "sensor": "oracle",
            "protocol_id": "toy_v1", "frame_id": "world", "units": "m", "oracle": "none" if "+" in cond or
            cond == "full" else (cond.replace("oracle_", "")), "condition": cond,
            "perturbation": {"timing_scale": 1.0 + seed % 3},
            "task": {"goal_xyz": goal, "position_tolerance_m": .03, "min_lift_m": .05, "settle_duration_s": .5,
                     "max_settle_speed_m_s": .02},
            "states": [{"t_s": i * .25, "object_xyz": p, "object_velocity": [0, 0, 0], "released": i >= 2,
                        "forbidden_collision": False, "fallen": False} for i, p in enumerate(pos)]}


SEEN = []


def toy_trace_job(args):
    seed, cond, _ = args
    SEEN.append(seed)
    ok = {"full": seed % 2 == 0, "oracle_perception": seed % 4 != 1, "oracle_calibration": seed % 2 == 0,
          "oracle_timing": seed % 2 == 0, "oracle_all": True}[cond]
    return fake_episode(seed, cond, ok)


def toy_dev_job(args):
    seed, prop = args
    SEEN.append(seed)
    if prop is None:
        return fake_episode(seed, "full", seed % 2 == 0)
    from transfergap.diagnose import correction_tag
    return fake_episode(seed, "full+" + correction_tag(prop), seed % 4 != 1)


@unittest.skipUnless(SIM, "needs numpy + mujoco (sim seed constants)")
class DevOnlyLoop(unittest.TestCase):
    def setUp(self):
        SEEN.clear()

    def run_loop(self, env, **kw):
        from transfergap.diagnose import run_loop
        d = Path(tempfile.mkdtemp()) / "run"
        # Point ROOT at an empty dir so a real runs/gap_budget/dev.jsonl is never picked up by default.
        with patch.dict("os.environ", env, clear=True), patch("transfergap.diagnose.ROOT", d.parent):
            return run_loop(llm=kw.pop("llm", "auto"), seeds_limit=8, out_dir=d, procs=1, job=toy_dev_job,
                            trace_job=toy_trace_job, dev_episodes=kw.pop("dev_episodes", None), **kw), d

    def test_guards_reject_heldout(self):
        from transfergap.diagnose import assert_dev_only, validate_trace
        for seeds in ([1000], [0, 1059], [2000], []):
            with self.assertRaises(ValueError):
                assert_dev_only(seeds)
        with self.assertRaises(ValueError):
            validate_trace({**toy_trace(), "split": "heldout"})
        with self.assertRaises(ValueError):
            validate_trace(toy_trace(seeds=(0, 1000)))

    def test_rule_baseline_reproduces_frozen_choice(self):
        from transfergap.diagnose import rule_based_diagnosis
        dev = json.loads((ROOT / "results" / "gap_budget_v1" / "dev_results.json").read_text())
        trace = {**toy_trace(), "budget_pp": dev["budget"]}
        p = rule_based_diagnosis(trace)
        self.assertEqual(dev["chosen_correction"], "look_again")
        self.assertEqual(p["operator"], "look_again")
        with self.assertRaises(ValueError):
            rule_based_diagnosis({**toy_trace(), "budget_pp": {"timing": {"delta_pp": 0}}})

    def test_default_params_match_frozen_corrections(self):
        from transfergap.diagnose import corrected_perturbation
        from transfergap.sim import errors
        frozen = {"look_again": "look_again", "tool_frame_calibration": "touch_probe_calibration",
                  "timing_scale": "speed_cap_3"}
        for seed in (0, 7, 59):
            for op, name in frozen.items():
                self.assertEqual(corrected_perturbation(seed, proposal(op)),
                                 errors.build_perturbation(seed, "full", name)[0])
            more = corrected_perturbation(seed, proposal("look_again", looks=3))
            self.assertNotEqual(more["look_again_err_xy"], errors.build_perturbation(seed, "full", "look_again")[0]
                                ["look_again_err_xy"])

    def test_loop_without_key_runs_baseline_only_on_dev(self):
        with patch("urllib.request.OpenerDirector.open") as opener:
            report, d = self.run_loop({})
            opener.assert_not_called()
        self.assertEqual(report["nemotron_super"]["status"], "skipped")
        self.assertEqual(report["rule_based"]["proposal"]["operator"], "look_again")
        self.assertTrue(SEEN and max(SEEN) < 60)
        self.assertFalse(report["heldout_touched"])
        res = report["dev_evaluation"]["by_correction"]["look_again[looks=1]"]
        self.assertEqual(res["paired_gap_corrected_minus_full"]["n"], 8)
        for name in ("trace.json", "rule_based.json", "report.json"):
            self.assertTrue((d / name).exists())
        trace = json.loads((d / "trace.json").read_text())
        self.assertNotIn("perception_err_xy", json.dumps(trace))   # privileged error vectors stay out

    def test_loop_with_key_compares_llm_to_baseline(self):
        reply = json.dumps(proposal("timing_scale", speed_cap=2.0))
        with patch("urllib.request.OpenerDirector.open", return_value=fake_response(reply)):
            report, d = self.run_loop({"NEBIUS_API_KEY": "test-secret"})
        self.assertTrue(report["nemotron_super"]["validated"])
        self.assertEqual(report["agreement"], {"same_operator": False, "same_params": False})
        self.assertEqual(set(report["dev_evaluation"]["by_correction"]),
                         {"look_again[looks=1]", "timing_scale[speed_cap=2]"})
        self.assertTrue((d / "nemotron_super_receipt.json").exists())
        self.assertNotIn("test-secret", (d / "nemotron_super_receipt.json").read_text())
        self.assertTrue(max(SEEN) < 60)

    def test_heldout_episode_file_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "eps.jsonl"
            path.write_text(json.dumps(fake_episode(1000, "full", True)) + "\n")
            with self.assertRaises(ValueError):
                self.run_loop({}, dev_episodes=path)

    def test_cli_required_without_key_refuses(self):
        out = subprocess.run([sys.executable, "-m", "transfergap", "diagnose", "--llm", "required", "--no-apply",
                              "--out-dir", tempfile.mkdtemp() + "/x"], cwd=ROOT, capture_output=True, text=True,
                             env={"PATH": "/usr/bin:/bin"})
        self.assertEqual(out.returncode, 2)
        self.assertIn("NEBIUS_API_KEY", out.stderr)


if __name__ == "__main__":
    unittest.main()
