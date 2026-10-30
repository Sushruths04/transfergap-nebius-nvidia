"""G1 contact attempt: open-loop separation and tier scoring.

The motion streamer and the motion planner must not read simulator state or scores; the sim runner
may read state but only writes it to the log. Scoring is checked on synthetic episodes.
"""
import ast
import sys
import unittest
from pathlib import Path

G1 = Path(__file__).resolve().parents[1] / "g1"
sys.path.insert(0, str(G1))

import score  # noqa: E402


def _names(path):
    tree = ast.parse(path.read_text())
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    strings = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return names, mods, strings


class OpenLoopSeparation(unittest.TestCase):
    def test_streamer_reads_no_sim_state(self):
        names, mods, strings = _names(G1 / "stream_motion.py")
        self.assertFalse({m for m in mods if "mujoco" in m or m in {"sim_runner", "scene", "score", "metrics"}})
        for bad in ("episode", "object_xyz", "block", "qpos", "xpos", "success", "score"):
            self.assertFalse([n for n in names | strings if bad in n.lower()], bad)

    def test_planner_targets_come_from_task_constants(self):
        names, mods, strings = _names(G1 / "plan_reach.py")
        self.assertFalse({m for m in mods if m in {"sim_runner", "score", "metrics", "track_error"}})
        # the planner's kinematic model is built without the block body; no reads of block state or logs
        for bad in ("episode", "object_xyz", "block_free", "diag.npz", "success"):
            self.assertFalse([n for n in names | strings if bad in n.lower()], bad)
        self.assertIn("build_spec(sonic_root, with_block=False)", (G1 / "plan_reach.py").read_text())

    def test_runner_sends_nothing_to_controller(self):
        names, mods, strings = _names(G1 / "sim_runner.py")
        self.assertNotIn("stream_motion", mods)
        self.assertNotIn("stream_cl", mods)
        # the only outgoing message is the optional proprioception channel (--state-port): the robot's own qpos
        # (joints + pelvis pose, sliced before the block joint), never object, table or tray state
        src = (G1 / "sim_runner.py").read_text()
        tree = ast.parse(src)
        sends = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "send"]
        self.assertEqual(len(sends), 1)
        payload = ast.get_source_segment(src, sends[0].args[0])
        self.assertIn("d.qpos[:block_qadr]", payload)
        for bad in ("xpos", "object", "bpos", "block)", "contact", "states"):
            self.assertNotIn(bad, payload)


def _ep(zs, contact, released, goal=(0.34, 0.0, 0.744)):
    states = []
    for i, (z, c, r) in enumerate(zip(zs, contact, released)):
        xy = (0.33, -0.2) if i < len(zs) // 2 else goal[:2]
        states.append({"t_s": round(0.1 * i, 3), "object_xyz": [*xy, z], "object_velocity": [0, 0, 0],
                       "released": r, "forbidden_collision": False, "fallen": False, "hand_block_contact": c,
                       "pelvis_xyz": [0, 0, 0.76]})
    return {"schema_version": 1, "source": "simulation", "trial_id": "seed0_r0", "demo_id": score.DEMO,
            "scene_id": "x", "seed": 0, "rollout": 0, "robot": score.ROBOT, "method": "m", "sensor": "oracle",
            "oracle": "none", "protocol_id": score.PROTOCOL, "frame_id": "world", "units": "m",
            "task": {"goal_xyz": list(goal), **score.TASK}, "robot_fell": False, "states": states}


class Tiers(unittest.TestCase):
    def test_touch_only(self):
        t = score.tiers(_ep([0.74] * 20, [False] * 5 + [True] * 3 + [False] * 12, [True] * 20,
                            goal=(0.9, 0.9, 0.744)))
        self.assertEqual((t["touch"], t["grasp"], t["place"]), (True, False, False))

    def test_lift_without_contact_is_not_a_grasp(self):
        t = score.tiers(_ep([0.74] * 5 + [0.80] * 5 + [0.74] * 10, [False] * 20, [True] * 20,
                            goal=(0.9, 0.9, 0.744)))
        self.assertFalse(t["grasp"])

    def test_full_place(self):
        zs = [0.74] * 4 + [0.80] * 6 + [0.744] * 10
        contact = [False] * 2 + [True] * 9 + [False] * 9
        t = score.tiers(_ep(zs, contact, [not c for c in contact]))
        self.assertEqual((t["touch"], t["grasp"], t["place"]), (True, True, True))

    def test_reduce_states_ors_contacts_and_ands_released(self):
        raw = [{"t_s": 0.02 * i, "object_xyz": [0, 0, 0], "object_velocity": [0, 0, 0], "released": i != 3,
                "forbidden_collision": False, "fallen": False, "hand_block_contact": i == 3,
                "pelvis_xyz": [0, 0, 0]} for i in range(10)]
        red = score.reduce_states(raw)
        self.assertEqual(len(red), 2)
        self.assertTrue(red[0]["hand_block_contact"])
        self.assertFalse(red[0]["released"])
        self.assertFalse(red[1]["hand_block_contact"])


if __name__ == "__main__":
    unittest.main()
