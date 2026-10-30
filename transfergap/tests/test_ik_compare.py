"""IK comparison harness: evaluator correctness, fidelity of the DLS copy to the controller, solver sanity,
and the rule that no IK code reads the block or scene state."""
import ast
import inspect
import unittest

import numpy as np

try:
    import mujoco
    from transfergap.sim import ik_compare
    from transfergap.sim.controller import R_DOWN, ScriptedPickPlace
    from transfergap.sim.scene import ASSETS, Scene, robot_ready
    READY = int(mujoco.__version__.split(".")[0]) >= 3 and robot_ready("ur10e")
except ImportError:
    READY = False
try:
    import mink  # noqa: F401
    HAS_MINK = True
except ImportError:
    HAS_MINK = False

PRIVILEGED = {"block_pos", "block_vel", "contact_flags", "block_body", "block_geom", "block_qadr",
              "table_geom", "link_bodies", "finger_bodies"}


@unittest.skipUnless(READY, "needs mujoco >= 3 and the menagerie UR10e assets")
class IkCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arm = ik_compare.ArmKin("ur10e")

    def test_evaluator_round_trip(self):
        rng = np.random.default_rng(0)
        for _ in range(5):
            q = rng.uniform(self.arm.jlo, self.arm.jhi)
            p, R = self.arm.fk(q)
            e = self.arm.evaluate(q, p, R)
            self.assertLess(e["pos"], 1e-12)
            self.assertLess(e["ori"], 1e-6)
            self.assertEqual(e["viol"], 0.0)

    def test_evaluator_flags_limit_violation_and_nan(self):
        q = self.arm.jhi + 0.1
        p, R = self.arm.fk(self.arm.q_home)
        self.assertGreater(self.arm.evaluate(q, p, R)["viol"], 0.05)
        e = self.arm.evaluate(np.full(6, np.nan), p, R)
        self.assertFalse(e["finite"])

    def test_dls_copy_matches_the_controller_ik_step(self):
        """arm.dls with the tool-down target must equal ScriptedPickPlace.ik_step (same maths, general rotation)."""
        scene = Scene(0, "ur10e")
        ctl = ScriptedPickPlace(scene)
        target = ctl.tool_point() + np.array([0.08, -0.05, -0.1])
        ctl.ik_step(target, iters=4)
        R_site = self.arm.body_rot_to_site(R_DOWN)
        q = self.arm.dls(self.arm.q_home, target, R_site, iters=4)
        np.testing.assert_allclose(q, ctl.q, atol=1e-9)

    def test_dls_converges_with_more_iterations(self):
        rng = np.random.default_rng(1)
        p, R = self.arm.fk(rng.uniform(-1.0, 1.0, 6) * np.array([1, .5, .5, 1, 1, 1]) + self.arm.q_home * 0.2)
        e4 = self.arm.evaluate(self.arm.dls(self.arm.q_home, p, R, iters=4), p, R)
        e200 = self.arm.evaluate(self.arm.dls(self.arm.q_home, p, R, iters=200), p, R)
        self.assertLessEqual(e200["pos"], e4["pos"] + 1e-9)

    @unittest.skipUnless(HAS_MINK, "mink not installed")
    def test_mink_reaches_a_reachable_pose_inside_limits(self):
        rng = np.random.default_rng(2)
        p, R = self.arm.fk(rng.uniform(self.arm.jlo, self.arm.jhi))
        q, _ = self.arm.mink_solve(self.arm.q_home, p, R)
        e = self.arm.evaluate(q, p, R)
        self.assertLessEqual(e["pos"], ik_compare.POS_TOL)
        self.assertLessEqual(e["ori"], ik_compare.ORI_TOL)
        self.assertEqual(e["viol"], 0.0)

    @unittest.skipUnless(HAS_MINK, "mink not installed")
    def test_unreachable_target_is_finite_inside_limits_and_respects_the_bound(self):
        R = self.arm.body_rot_to_site(R_DOWN)
        p = self.arm.shoulder + np.array([0.0, 0.0, 1.0]) * 2.0 * self.arm.reach
        lower = float(np.linalg.norm(p - self.arm.shoulder) - self.arm.reach)
        for name, e in ik_compare.run_methods(self.arm, self.arm.q_home, p, R).items():
            self.assertTrue(e["finite"], name)
            self.assertEqual(e["viol"] <= 1e-9, True, name)
            self.assertGreaterEqual(e["pos"], lower - 1e-6, name)


class NoPrivilegedStateTest(unittest.TestCase):
    def test_ik_compare_never_reads_block_or_scene_state(self):
        src = inspect.getsource(ik_compare) if READY else open(
            __file__.replace("tests/test_ik_compare.py", "transfergap/sim/ik_compare.py")).read()
        tree = ast.parse(src)
        used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse(used & PRIVILEGED, used & PRIVILEGED)


if __name__ == "__main__":
    unittest.main()
