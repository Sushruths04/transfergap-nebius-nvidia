"""Closed-loop G1 streamer (g1/stream_cl.py): privacy of its inputs and the behaviour of the correction.

The correction may use only the robot's own state (joint angles + pelvis pose) and the plan. Physics-dependent
tests need the upstream G1 model (GR00T-WholeBodyControl checkout, mujoco); they skip when it is not available.
"""
import ast
import os
import sys
import unittest
from pathlib import Path

import numpy as np

G1 = Path(__file__).resolve().parents[1] / "g1"
sys.path.insert(0, str(G1))

SONIC = Path(os.environ.get("SONIC_ROOT", "~/GR00T-WholeBodyControl")).expanduser()
HAVE_MODEL = (SONIC / "gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml").exists()
try:
    import mujoco  # noqa: F401
except ImportError:
    HAVE_MODEL = False


class StreamClInputs(unittest.TestCase):
    def test_hybrid_tail_is_blended_not_switched(self):
        src = (G1 / "stream_cl.py").read_text()
        self.assertIn("--tail-traj", src)
        self.assertIn("10 * s**3 - 15 * s**4 + 6 * s**5", src)       # min-jerk cross-fade, no step in the joint targets

    def test_reads_no_scene_state(self):
        src = (G1 / "stream_cl.py").read_text()
        tree = ast.parse(src)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        for bad in ("object_xyz", "block", "episode", "contact", "success", "score"):
            self.assertFalse([n for n in names if bad in n.lower() and n != "NOBLOCK"], bad)   # zmq.NOBLOCK is a flag
        self.assertFalse({m for m in mods if m in {"sim_runner", "score", "metrics", "track_error"}})
        self.assertNotIn("diag.npz", src)          # never reads the rollout logs
        # build_spec(..., with_block=False): the streamer's kinematic model has no block body at all
        self.assertIn("G1Kin(", src)

    def test_state_message_is_exactly_one_flat_float64_qpos(self):
        src = (G1 / "sim_runner.py").read_text()
        self.assertIn("np.ascontiguousarray(d.qpos[:block_qadr], dtype=np.float64).tobytes()", src)


@unittest.skipUnless(HAVE_MODEL, "needs mujoco and the upstream G1 model (set SONIC_ROOT)")
class CorrectorBehaviour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from plan_reach import plan
        import stream_cl
        cls.stream_cl = stream_cl
        cls.traj, cls.meta = plan(str(SONIC), pitch_down=-0.2, roll=-0.4, grasp_dz=0.03)
        cls.phase = cls.traj["phase"]
        cls.k = int(np.where(cls.phase == "approach")[0][40])

    def corrector(self):
        return self.stream_cl.Corrector(str(SONIC), self.traj, {"pitch_down": -0.2, "roll": -0.4})

    def test_perfect_tracking_leaves_the_plan_unchanged(self):
        c = self.corrector()
        q = self.traj["qpos"][self.k].astype(float)
        for _ in range(20):
            out, info = c.step_rr(self.k, q.copy(), 0.02, True)
        self.assertLess(np.abs(out - q).max(), 5e-3)
        self.assertLess(info[3], 5e-3)

    def test_inactive_or_missing_state_passes_plan_through(self):
        c = self.corrector()
        q = self.traj["qpos"][self.k].astype(float)
        out, info = c.step_rr(self.k, None, 0.02, True)
        self.assertTrue(np.array_equal(out, q) and info is None)
        out, info = c.step_rr(self.k, q.copy(), 0.02, False)
        self.assertTrue(np.array_equal(out, q) and info is None)

    def test_displaced_hand_is_pulled_back_to_the_plan(self):
        c = self.corrector()
        plan_q = self.traj["qpos"][self.k].astype(float)
        meas = plan_q.copy()
        meas[0] -= 0.06                                   # pelvis slid back 6 cm: the hand is 6 cm short
        errs = []
        for _ in range(60):
            out, info = c.step_rr(self.k, meas, 0.02, True, kr=3.0)
            errs.append(info[3])
            for n in self.stream_cl.IK_JOINTS:             # ideal plant: the arm reaches what is commanded
                a = c.kin.qadr[n]
                meas[a] = out[a]
        self.assertGreater(errs[0], 0.05)
        self.assertLess(errs[-1], 0.5 * errs[0])
        self.assertTrue(all(b <= a + 1e-6 for a, b in zip(errs, errs[1:])))

    def test_carry_offset_shifts_only_the_carry_and_place_targets(self):
        from plan_reach import plan
        base, mb = plan(str(SONIC), pitch_down=-0.2, roll=-0.4, grasp_dz=0.03)
        shifted, ms = plan(str(SONIC), pitch_down=-0.2, roll=-0.4, grasp_dz=0.03, carry_offset=(0.065, -0.11, 0.0))
        self.assertEqual(mb["waypoints"]["grasp"], ms["waypoints"]["grasp"])
        self.assertEqual(mb["waypoints"]["pre"], ms["waypoints"]["pre"])
        for k in ("over", "place"):
            d = np.array(ms["waypoints"][k]) - np.array(mb["waypoints"][k])
            self.assertTrue(np.allclose(d, [0.065, -0.11, 0.0]), k)
        self.assertEqual(ms["carry_offset"], [0.065, -0.11, 0.0])

    def test_settle_lengthens_only_the_descent(self):
        from plan_reach import plan
        base, _ = plan(str(SONIC), pitch_down=-0.2, roll=-0.4, grasp_dz=0.03)
        slow, ms = plan(str(SONIC), pitch_down=-0.2, roll=-0.4, grasp_dz=0.03, settle=1.5)
        self.assertEqual(len(slow["phase"]) - len(base["phase"]), 75)
        for ph in ("hold", "approach", "close", "lift", "transport", "lower", "release"):
            self.assertEqual(int((slow["phase"] == ph).sum()), int((base["phase"] == ph).sum()), ph)
        self.assertEqual(int((slow["phase"] == "descend").sum()) - int((base["phase"] == "descend").sum()), 75)
        self.assertEqual(ms["settle_s"], 1.5)

    def test_offsets_and_joint_limits_are_bounded(self):
        c = self.corrector()
        plan_q = self.traj["qpos"][self.k].astype(float)
        meas = plan_q.copy()
        meas[0] -= 2.0                                    # unreachable error
        for _ in range(400):
            out, _ = c.step_rr(self.k, meas, 0.02, True, kr=5.0, lim=0.4)
        self.assertLessEqual(np.abs(c.delta).max(), 0.4 + 1e-9)
        for n in self.stream_cl.IK_JOINTS:
            a = c.kin.qadr[n]
            self.assertGreaterEqual(out[a], c.kin.lo[n] - 1e-9)
            self.assertLessEqual(out[a], c.kin.hi[n] + 1e-9)


if __name__ == "__main__":
    unittest.main()
