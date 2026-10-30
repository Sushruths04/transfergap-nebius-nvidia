"""Cosmos critic: request format, receipts, parsing and scoring with mocked HTTP. No network, no GPU."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from transfergap import critic
from transfergap.critic import (FPS, STAGES, USER_PROMPT, check_base_url, critique_clip, parse_answer,
                                score, select_balanced, stage_label)


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def response(content, finish="stop"):
    body = {"id": "chatcmpl-cosmos", "model": "nvidia/Cosmos-Reason2-8B",
            "choices": [{"message": {"content": content, "reasoning_content": "thinking"}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 4000, "completion_tokens": 300, "total_tokens": 4300}}
    return FakeResp(json.dumps(body).encode())


GOOD = json.dumps({"success": "no", "failing_stage": "grasp", "rationale": "The gripper closes beside the block."})


class Parsing(unittest.TestCase):
    def test_plain_json(self):
        a, err = parse_answer(GOOD)
        self.assertIsNone(err)
        self.assertEqual(a, {"success": False, "failing_stage": "grasp",
                             "rationale": "The gripper closes beside the block."})

    def test_think_block_and_fence(self):
        a, _ = parse_answer("<think>\nhmm\n</think>\n\n```json\n" + GOOD + "\n```")
        self.assertEqual(a["failing_stage"], "grasp")
        a, _ = parse_answer("reasoning without opening tag\n</think>\n" + GOOD)
        self.assertEqual(a["failing_stage"], "grasp")

    def test_rejects_prose_and_off_list(self):
        for bad in ("It failed at grasp.", "[1]", None,
                    json.dumps({"success": "maybe", "failing_stage": "none", "rationale": ""}),
                    json.dumps({"success": "no", "failing_stage": "transport", "rationale": ""})):
            a, err = parse_answer(bad)
            self.assertIsNone(a)
            self.assertTrue(err)


class Labels(unittest.TestCase):
    def test_scoring_requires_exact_unique_clip_coverage(self):
        labels = [{"clip_id": "a", "condition": "full", "success": True, "stage": "none"},
                  {"clip_id": "b", "condition": "full", "success": False, "stage": "grasp"}]
        predictions = [{"clip_id": "a", "parsed": True,
                        "answer": {"success": True, "failing_stage": "none"}}]
        with self.assertRaisesRegex(ValueError, "missing=1"):
            score(labels, predictions)
        with self.assertRaisesRegex(ValueError, "duplicate clip IDs"):
            score(labels, predictions + predictions)

    def test_stage_label(self):
        self.assertEqual(stage_label({"success": True, "failure_reasons": []}), "none")
        self.assertEqual(stage_label({"success": False, "failure_reasons": ["no_lift",
                                     "not_released_and_settled_at_goal"]}), "grasp")
        self.assertEqual(stage_label({"success": False, "failure_reasons": ["not_released_and_settled_at_goal"]}),
                         "place")

    def test_select_balanced_one_per_seed_per_class(self):
        outs = [{"seed": s, "condition": c, "stage": STAGES[(s + i) % 3]}
                for s in range(30) for i, c in enumerate(["full", "oracle_all", "oracle_timing"])]
        picked = select_balanced(outs, 5)
        self.assertEqual(len(picked), 15)
        for st in STAGES:
            seeds = [p["seed"] for p in picked if p["stage"] == st]
            self.assertEqual(len(seeds), len(set(seeds)))
        self.assertEqual(picked, select_balanced(outs, 5))      # deterministic

    def test_heldout_seeds_refused(self):
        with self.assertRaises(ValueError):
            critic._assert_dev([3, 1001])


class Request(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.clip = self.d / "clip000.mp4"
        self.clip.write_bytes(b"\x00\x00\x00\x18ftypmp42fake")

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, content=GOOD, side_effect=None, **kw):
        sent = {}

        def opener(self_, request, timeout=None):
            sent["url"] = request.full_url
            sent["headers"] = dict(request.header_items())
            sent["body"] = json.loads(request.data)
            if side_effect:
                raise side_effect
            return response(content)
        with patch("urllib.request.OpenerDirector.open", opener):
            rec = critique_clip(self.clip, self.d / "r.json", "http://127.0.0.1:8000/v1", **kw)
        return rec, json.loads((self.d / "r.json").read_text()), sent

    def test_request_follows_model_card(self):
        rec, stored, sent = self.call()
        b = sent["body"]
        self.assertEqual(sent["url"], "http://127.0.0.1:8000/v1/chat/completions")
        self.assertEqual(b["model"], "nvidia/Cosmos-Reason2-8B")
        self.assertEqual(b["mm_processor_kwargs"]["fps"], 4)
        self.assertEqual(b["media_io_kwargs"]["video"]["fps"], 4)
        self.assertEqual(FPS, 4)
        self.assertGreaterEqual(b["max_tokens"], 4096)
        user = b["messages"][1]["content"]
        self.assertTrue(user[0]["video_url"]["url"].startswith("data:video/mp4;base64,"))
        self.assertEqual(user[1]["text"], USER_PROMPT)
        self.assertTrue(USER_PROMPT.endswith("Write your final answer immediately after the </think> tag."))
        self.assertEqual(b["response_format"]["json_schema"]["schema"]["properties"]["failing_stage"]["enum"],
                         list(STAGES))
        self.assertNotIn("Authorization", sent["headers"])
        self.assertNotIn("clip000", json.dumps(b))               # the clip name never reaches the model

    def test_receipt_contents(self):
        rec, stored, _ = self.call(extra={"clip_id": "clip000"})
        self.assertEqual(stored["status"], "succeeded")
        self.assertTrue(stored["parsed"])
        self.assertEqual(stored["answer"]["failing_stage"], "grasp")
        self.assertEqual(stored["response_id"], "chatcmpl-cosmos")
        self.assertEqual(stored["usage"]["completion_tokens"], 300)
        self.assertEqual(stored["reasoning_content"], "thinking")
        self.assertIn("latency_s", stored)
        self.assertEqual(stored["prompt_sha256"], critic.prompt_sha256())
        self.assertEqual(stored["clip_id"], "clip000")

    def test_unparseable_and_failed_are_recorded(self):
        _, stored, _ = self.call(content="The robot failed.")
        self.assertEqual(stored["status"], "succeeded")
        self.assertFalse(stored["parsed"])
        (self.d / "r.json").unlink()
        _, stored, _ = self.call(side_effect=TimeoutError())
        self.assertEqual(stored["status"], "failed")
        self.assertFalse(stored["parsed"])

    def test_receipt_never_overwritten(self):
        self.call()
        with self.assertRaises(FileExistsError):
            self.call()

    def test_api_key_header_but_not_in_receipt(self):
        _, stored, sent = self.call(api_key="test-secret")
        self.assertEqual(sent["headers"]["Authorization"], "Bearer test-secret")
        self.assertNotIn("test-secret", json.dumps(stored))

    def test_base_url_rules(self):
        check_base_url("http://127.0.0.1:8000/v1")
        check_base_url("https://example.com/v1")
        for bad in ("http://89.169.112.223:8000/v1", "https://u:p@example.com/v1", "ftp://x/v1"):
            with self.assertRaises(ValueError):
                check_base_url(bad)


class Scoring(unittest.TestCase):
    def setUp(self):
        self.labels = [{"clip_id": f"c{i}", "success": st == "none", "stage": st}
                       for i, st in enumerate(["none"] * 4 + ["grasp"] * 4 + ["place"] * 4)]

    def pred(self, i, stage):
        if stage is None:
            return {"clip_id": f"c{i}", "parsed": False, "answer": None, "latency_s": 1.0}
        return {"clip_id": f"c{i}", "parsed": True, "latency_s": 2.0, "finish_reason": "stop",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                "answer": {"success": stage == "none", "failing_stage": stage, "rationale": ""}}

    def test_perfect(self):
        r = score(self.labels, [self.pred(i, l["stage"]) for i, l in enumerate(self.labels)])
        self.assertEqual(r["stage"]["accuracy"]["accuracy"], 1.0)
        self.assertEqual(r["success"]["accuracy"]["accuracy"], 1.0)
        self.assertEqual(r["success"]["majority_baseline"]["class"], "no")
        self.assertAlmostEqual(r["success"]["majority_baseline"]["accuracy"], 8 / 12)
        self.assertAlmostEqual(r["stage"]["majority_baseline"]["accuracy"], 4 / 12)
        self.assertEqual(r["stage"]["per_class"]["grasp"]["precision"], 1.0)

    def test_constant_answer_and_unparsed(self):
        preds = [self.pred(i, "grasp") for i in range(11)] + [self.pred(11, None)]
        r = score(self.labels, preds)
        self.assertEqual(r["stage"]["accuracy"]["correct"], 4)
        self.assertEqual(r["stage"]["confusion"]["place"]["unparsed"], 1)
        self.assertEqual(r["stage"]["per_class"]["grasp"]["recall"], 1.0)
        self.assertAlmostEqual(r["stage"]["per_class"]["grasp"]["precision"], 4 / 11)
        self.assertIsNone(r["stage"]["per_class"]["none"]["precision"])
        self.assertEqual(r["success"]["accuracy"]["correct"], 7)     # 'no' right on 7 of the 8 failures
        self.assertEqual(r["parsed"], 11)
        lo, hi = r["stage"]["accuracy"]["wilson_95"]
        self.assertTrue(lo < 4 / 12 < hi)

    def test_unlabelled_prediction_refused(self):
        with self.assertRaises(ValueError):
            score(self.labels, [self.pred(99, "none")])

    def test_write_results(self):
        with tempfile.TemporaryDirectory() as t:
            run, res = Path(t) / "run", Path(t) / "res"
            run.mkdir()
            (run / "labels.jsonl").write_text("".join(json.dumps(l) + "\n" for l in self.labels))
            preds = [self.pred(i, l["stage"] if i % 3 else "place") for i, l in enumerate(self.labels)]
            (run / "predictions_scored.jsonl").write_text("".join(json.dumps(p) + "\n" for p in preds))
            (run / "manifest_scored.json").write_text(json.dumps(
                {"model": "m", "prompt_sha256": "a" * 64, "git_commit": "b" * 40, "workers": 2}))
            critic.write_results(run, res)
            for f in ("summary.json", "summary.md", "confusion_matrix.png", "labels.jsonl", "predictions.jsonl"):
                self.assertTrue((res / f).exists(), f)
            self.assertIn("majority-class baseline", (res / "summary.md").read_text())


class V2(unittest.TestCase):
    def test_v1_prompt_hash_is_unchanged(self):
        # the hash recorded in the committed v1 receipts
        self.assertTrue(critic.prompt_sha256().startswith("309d056cd99e17d4"))
        self.assertNotEqual(critic.prompt_sha256("obs", "close"), critic.prompt_sha256("obs", "close_top"))

    def test_observational_prompt_does_not_narrate_the_task(self):
        for cam in critic.CAMERAS:
            text = critic.user_prompt("obs", cam).lower()
            for word in ("task", "pick up", "carry", "success", "place it", "release"):
                self.assertNotIn(word, text)
            self.assertTrue(text.endswith("write your final answer immediately after the </think> tag."))
        self.assertIn("side by side", critic.user_prompt("obs", "close_top"))
        self.assertNotIn("side by side", critic.user_prompt("obs", "close"))

    def test_observational_parsing_and_derivation(self):
        def ans(last, left):
            return json.dumps({"cube_last_frame": last, "cube_left_table": left, "observations": "x"})
        cases = {("tray", "yes"): (True, "none"), ("tray", "no"): (True, "none"),
                 ("table", "no"): (False, "grasp"), ("table", "yes"): (False, "place"),
                 ("gripper", "yes"): (False, "place"), ("gripper", "no"): (False, "grasp")}
        for (last, left), (succ, stage) in cases.items():
            a, err = parse_answer(ans(last, left), "obs")
            self.assertIsNone(err)
            self.assertEqual((a["success"], a["failing_stage"]), (succ, stage))
            self.assertEqual(a["observed"], {"cube_last_frame": last, "cube_left_table": left})
        for bad in (ans("floor", "no"), ans("tray", "maybe"), GOOD):
            self.assertIsNone(parse_answer(bad, "obs")[0])

    def test_obs_request_uses_obs_schema(self):
        body = critic.request_body("m", [], prompt="obs")
        self.assertEqual(body["response_format"]["json_schema"]["schema"], critic.OBS_SCHEMA)

    def test_seed_splits(self):
        self.assertFalse(set(critic.SPLITS["tuning"]) & set(critic.SPLITS["v2"]))
        self.assertFalse(set(critic.SPLITS["dev"]) & (set(critic.SPLITS["tuning"]) | set(critic.SPLITS["v2"])))
        self.assertEqual(critic.assert_split([2000, 2019], "tuning"), [2000, 2019])
        for seeds, split in (([2020], "tuning"), ([5], "tuning"), ([1003], "v2"), ([2019], "v2"), ([1001], "dev")):
            with self.assertRaises(ValueError):
                critic.assert_split(seeds, split)

    def test_v2_split_requires_frozen_config(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "labels.jsonl").write_text(json.dumps({"clip_id": "c0", "seed": 2030, "split": "v2",
                                                        "condition": "full", "stage": "none"}) + "\n")
            with patch("urllib.request.OpenerDirector.open") as opener:
                with self.assertRaises(ValueError):
                    critic.run("http://127.0.0.1:8000/v1", out_dir=d, require_frozen=False, prompt="obs",
                               camera="close")
                with patch.dict(critic.FROZEN_V2, {"prompt": None, "camera": None}), self.assertRaises(ValueError):
                    critic.run("http://127.0.0.1:8000/v1", out_dir=d, frozen_v2=True)
                opener.assert_not_called()

    def test_static_controls_scored_separately(self):
        labels = [{"clip_id": "a", "condition": "full", "success": True, "stage": "none"},
                  {"clip_id": "b", "condition": "full", "success": False, "stage": "grasp"},
                  {"clip_id": "s", "condition": "static_control", "success": False, "stage": "grasp"}]
        yes = {"success": True, "failing_stage": "none", "rationale": ""}
        preds = [{"clip_id": i, "parsed": True, "answer": yes, "latency_s": 1.0} for i in "abs"]
        r = score(labels, preds)
        self.assertEqual(r["n"], 2)
        self.assertEqual(r["static_controls"], {"n": 1, "said_success": 1, "said_grasp": 0, "unparsed": 0})

    def test_rel_paths(self):
        self.assertFalse(critic.rel(critic.ROOT / "runs" / "x.jsonl").startswith("/"))
        self.assertEqual(critic.rel(critic.ROOT / "runs" / "x.jsonl"), "transfergap/runs/x.jsonl")


class Cli(unittest.TestCase):
    def test_critic_subcommand_registered(self):
        import subprocess
        import sys
        out = subprocess.run([sys.executable, "-m", "transfergap", "critic", "--help"], capture_output=True,
                             text=True, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(out.returncode, 0)
        self.assertIn("render", out.stdout)


if __name__ == "__main__":
    unittest.main()
