import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from transfergap.adapters import RobotSpec, sonic_action_names, validate_action_chunk, validate_plan
from transfergap.hosted import call_model, video_messages
from transfergap.metrics import paired_gap, score_episode, summarize, wilson_interval


def episode():
    positions = [[0, 0, .02], [0, 0, .15], [.3, 0, .02], [.3, 0, .02], [.3, 0, .02]]
    return {"schema_version": 1, "source": "fixture", "trial_id": "trial-1", "demo_id": "demo-1",
            "scene_id": "scene-1", "seed": 1, "robot": "fixture_robot_a", "method": "fixture_replay",
            "sensor": "rgb", "protocol_id": "pnp-v1", "frame_id": "table", "units": "m",
            "task": {"goal_xyz": [.3, 0, .02], "position_tolerance_m": .03,
                     "min_lift_m": .05, "settle_duration_s": .5, "max_settle_speed_m_s": .02},
            "states": [{"t_s": i * .25, "object_xyz": p, "object_velocity": [0, 0, 0],
                        "released": i >= 2, "forbidden_collision": False, "fallen": False}
                       for i, p in enumerate(positions)]}


class ScoringTests(unittest.TestCase):
    def test_pick_release_and_dwell(self):
        self.assertTrue(score_episode(episode())["success"])

    def test_no_lift_is_not_pick_and_place(self):
        ep = episode()
        ep["states"][1]["object_xyz"][2] = .02
        self.assertIn("no_lift", score_episode(ep)["failure_reasons"])

    def test_endpoint_alone_is_not_success(self):
        ep = episode()
        ep["states"][-2]["released"] = False
        self.assertFalse(score_episode(ep)["success"])

    def test_collision_or_fall_fails_even_if_object_arrives(self):
        for flag in ("fallen", "forbidden_collision"):
            ep = episode()
            ep["states"][1][flag] = True
            self.assertFalse(score_episode(ep)["success"])

    def test_speed_at_target_fails(self):
        ep = episode()
        ep["states"][-1]["object_velocity"] = [1, 0, 0]
        self.assertFalse(score_episode(ep)["success"])

    def test_reject_bad_timestamps_and_nan(self):
        ep = episode()
        ep["states"][1]["t_s"] = 0
        with self.assertRaises(ValueError):
            score_episode(ep)
        ep = episode()
        ep["states"][1]["object_xyz"][0] = math.nan
        with self.assertRaises(ValueError):
            score_episode(ep)

    def test_trajectory_frame_and_time_are_explicit(self):
        ep = episode()
        ep["reference"] = copy.deepcopy(ep["states"])
        self.assertEqual(score_episode(ep)["object_position_sample_rmse_m"], 0)
        ep["reference"][1]["t_s"] += .1
        with self.assertRaises(ValueError):
            score_episode(ep)

    def test_fixtures_require_explicit_opt_in(self):
        with self.assertRaises(ValueError):
            summarize([episode()])
        self.assertTrue(summarize([episode()], True)["contains_fixtures"])

    def test_duplicates_do_not_inflate_sample_size(self):
        with self.assertRaises(ValueError):
            summarize([episode(), episode()], True)

    def test_wilson_does_not_claim_certainty(self):
        lower, upper = wilson_interval(10, 10)
        self.assertLess(lower, .8)
        self.assertAlmostEqual(upper, 1)

    def test_paired_gap_and_missing_trials(self):
        a, b = episode(), episode()
        b["robot"] = "fixture_robot_b"
        b["states"][-1]["released"] = False
        self.assertEqual(paired_gap([a], [b])["success_gap_b_minus_a_pp"], -100)
        b["seed"] = 2
        with self.assertRaises(ValueError):
            paired_gap([a], [b])

    def test_mismatched_task_rejected(self):
        a, b = episode(), episode()
        b["task"]["position_tolerance_m"] *= 2
        with self.assertRaises(ValueError):
            paired_gap([a], [b])

    def test_summarize_rejects_drifting_tolerance_within_one_protocol(self):
        # Same protocol_id, same (source, robot, method, sensor) group even — but a second
        # trial silently loosened its tolerance. Pooling these into one success_rate would
        # mix two different success definitions under one reported number.
        a, b = episode(), episode()
        b["trial_id"], b["demo_id"], b["seed"] = "trial-2", "demo-2", 2
        b["task"]["position_tolerance_m"] *= 10
        with self.assertRaises(ValueError):
            summarize([a, b], True)

    def test_paired_gap_rejects_tolerance_drift_across_pairs_in_one_protocol(self):
        # Pair 1 (a1/b1) and pair 2 (a2/b2) are each internally consistent (paired_gap's
        # per-pair task-equality check passes both), but pair 2 uses a looser tolerance
        # than pair 1 under the same protocol_id — exactly the gap the per-pair check misses.
        a1, b1 = episode(), episode()
        b1["robot"] = "fixture_robot_b"
        a2, b2 = episode(), episode()
        a2["trial_id"], a2["demo_id"], a2["seed"] = "trial-2", "demo-2", 2
        b2["trial_id"], b2["demo_id"], b2["seed"] = "trial-2", "demo-2", 2
        b2["robot"] = "fixture_robot_b"
        for ep in (a2, b2):
            ep["task"]["position_tolerance_m"] *= 10
        with self.assertRaises(ValueError):
            paired_gap([a1, a2], [b1, b2])

    def test_summarize_never_pools_different_oracles(self):
        a, b = episode(), episode()
        a["oracle"], b["oracle"] = "none", "perception"
        b["trial_id"], b["demo_id"], b["seed"] = "trial-2", "demo-2", 2   # same method/group otherwise
        groups = summarize([a, b], True)["groups"]
        self.assertEqual(sorted(g["oracle"] for g in groups), ["none", "perception"])
        self.assertTrue(all(g["episodes"] == 1 for g in groups))

    def test_oracle_and_condition_must_be_nonempty_strings(self):
        for key in ("oracle", "condition"):
            for bad in ("", 3, None):
                ep = episode()
                ep[key] = bad
                with self.assertRaises(ValueError):
                    summarize([ep], True)

    def test_paired_gap_compares_oracles_but_refuses_mixed_side(self):
        def ep(seed, oracle, ok):
            e = episode()
            e["trial_id"], e["demo_id"], e["seed"], e["oracle"] = f"t{seed}", f"d{seed}", seed, oracle
            if not ok:
                e["states"][1]["object_xyz"] = [0, 0, .02]   # never lifted
            return e
        full = [ep(i, "none", i % 2) for i in range(4)]
        orc = [ep(i, "perception", True) for i in range(4)]
        self.assertAlmostEqual(paired_gap(full, orc)["success_gap_b_minus_a_pp"], 50.0)
        with self.assertRaises(ValueError):   # one side pools two oracle values
            paired_gap(full[:2] + [ep(2, "timing", True), ep(3, "timing", True)], orc)

    def test_plan_rejects_non_object_json(self):
        for bad in ([], None, "not a plan"):
            with self.assertRaises(ValueError):
                validate_plan(bad, ["reach"])


class InterfaceTests(unittest.TestCase):
    def test_legacy_actions_cannot_enter_sonic_contract(self):
        spec = RobotSpec("g1", "UNITREE_G1_SONIC", sonic_action_names(), "sonic_native", 50, "asset-test", "policy-test")
        validate_action_chunk(spec, [[0.] * 78])
        for dim in (14, 17, 64):
            with self.assertRaises(ValueError):
                validate_action_chunk(spec, [[0.] * dim])

    def test_planner_cannot_invent_robot_skills(self):
        with self.assertRaises(ValueError):
            validate_plan({"steps": [{"skill": "walk", "target": "table"}]}, ["reach"])

    def test_no_credentials_no_receipt_or_mock(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {}, clear=True):
            path = Path(directory) / "receipt.json"
            with self.assertRaises(ValueError):
                call_model("nemotron", [], path)
            self.assertFalse(path.exists())

    def test_hosted_response_receipt(self):
        response = {"id": "test-response", "model": "test-model", "choices": [{"message": {"content": "test"}}]}
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {
            "NEMOTRON_MODEL": "test-model", "NEBIUS_API_KEY": "test-secret"}, clear=True):
            import io
            with patch("urllib.request.OpenerDirector.open", return_value=io.StringIO(json.dumps(response))):
                path = Path(directory) / "receipt.json"
                call_model("nemotron", [], path)
            stored = json.loads(path.read_text())
            self.assertEqual(stored["status"], "succeeded")
            self.assertEqual(stored["response_id"], "test-response")
            self.assertNotIn("test-secret", path.read_text())
            with self.assertRaises(FileExistsError):
                call_model("nemotron", [], path)

    def test_failed_call_is_recorded_as_failed(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {
            "NEMOTRON_MODEL": "test-model", "NEBIUS_API_KEY": "test-secret"}, clear=True):
            path = Path(directory) / "receipt.json"
            with patch("urllib.request.OpenerDirector.open", side_effect=TimeoutError):
                with self.assertRaises(RuntimeError):
                    call_model("nemotron", [], path)
            self.assertEqual(json.loads(path.read_text())["status"], "failed")


if __name__ == "__main__":
    unittest.main()
