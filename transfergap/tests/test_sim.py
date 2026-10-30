import unittest

try:
    import mujoco
    from transfergap.sim.scene import ASSETS, Scene
    from transfergap.sim.rollout import run_episode
    READY = int(mujoco.__version__.split(".")[0]) >= 3 and (ASSETS / "universal_robots_ur5e").exists()
except ImportError:
    READY = False

from transfergap.metrics import score_episode, summarize, validate_episode


@unittest.skipUnless(READY, "needs mujoco>=3 and menagerie assets (run transfergap/sim/setup_sim.sh)")
class SimTests(unittest.TestCase):
    def test_unperturbed_grasp_succeeds(self):
        wins = sum(score_episode(run_episode(seed))["success"] for seed in range(10))
        self.assertGreaterEqual(wins, 9)

    def test_large_target_offset_mostly_fails(self):
        wins = sum(score_episode(run_episode(s, {"target_offset_m": 0.05}))["success"] for s in range(5))
        self.assertLessEqual(wins, 1)

    def test_no_attachment_constraints(self):
        sc = Scene(0)
        m = sc.model
        self.assertEqual(int((m.eq_type == mujoco.mjtEq.mjEQ_WELD).sum()), 0)
        block_joint = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "block_free")
        for i in range(m.neq):  # only the gripper's own linkage constraints may exist
            ids = {int(m.eq_obj1id[i]), int(m.eq_obj2id[i])}
            self.assertNotIn(block_joint if m.eq_type[i] == mujoco.mjtEq.mjEQ_JOINT else sc.block_body, ids)

    def test_scene_deterministic_and_goal_exposed(self):
        a, b = Scene(3), Scene(3)
        self.assertEqual(a.block_pos().tolist(), b.block_pos().tolist())
        self.assertNotEqual(a.block_pos().tolist(), Scene(4).block_pos().tolist())
        self.assertEqual(len(a.goal_xyz), 3)

    def test_episode_validates_with_extra_fields(self):
        ep = run_episode(0, {"timing_scale": 1.0})
        validate_episode(ep)
        self.assertIn("phase", ep["states"][0])
        self.assertIsInstance(ep["perturbation"], dict)
        self.assertEqual(ep["source"], "simulation")
        rate = 1 / (ep["states"][1]["t_s"] - ep["states"][0]["t_s"])
        self.assertGreaterEqual(rate, 50 - 1e-6)
        self.assertEqual(summarize([ep])["groups"][0]["episodes"], 1)


if __name__ == "__main__":
    unittest.main()
