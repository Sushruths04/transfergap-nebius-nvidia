"""KAIROS arm (UR10e + Robotiq 2F-140): the gripper model builds, its linkage obeys the URDF mimic rules, the scene
classifies its fingers, and the existing controller completes nominal pick-and-place. Skipped when the lab's
gripper files have not been prepared on this machine (they are not part of the repository)."""
import unittest

import numpy as np

try:
    import mujoco
    from transfergap.sim import kairos_model
    from transfergap.sim.scene import Scene, robot_ready
    READY = int(mujoco.__version__.split(".")[0]) >= 3 and robot_ready("kairos")
except ImportError:
    READY = False


@unittest.skipUnless(READY, "KAIROS gripper model not prepared (python -m transfergap.sim.kairos_model prepare ...)")
class KairosModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = Scene(0, "kairos")

    def _joint(self, name):
        m = self.scene.model
        return m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "g_" + name)]

    def test_scene_names_the_controller_needs(self):
        s, m = self.scene, self.scene.model
        self.assertEqual(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, s.tool_body), "g_base")
        np.testing.assert_allclose(s.pinch_off, [0, 0, kairos_model.PINCH_Z])
        self.assertEqual(s.robot_label, "kairos_ur10e_2f140_fixed")
        self.assertEqual(len(s.finger_bodies), 10)             # 2 x (driver, spring, follower, coupler, pad)

    def test_mimic_constraints_match_the_urdf_exactly_once(self):
        m = self.scene.model
        eq = {}
        for i in range(m.neq):
            if m.eq_type[i] == mujoco.mjtEq.mjEQ_JOINT:
                n1 = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, m.eq_obj1id[i])
                eq.setdefault(n1, []).append((mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, m.eq_obj2id[i]),
                                              float(m.eq_data[i][0]), float(m.eq_data[i][1])))
        for name, sign in kairos_model.MIMIC:
            rows = eq.get("g_" + name, [])
            self.assertEqual(len(rows), 1, f"{name}: {rows}")               # once, not duplicated
            self.assertEqual(rows[0][0], "g_" + kairos_model.FINGER_JOINT)
            self.assertAlmostEqual(rows[0][1], 0.0)                         # offset
            self.assertAlmostEqual(rows[0][2], sign)                        # multiplier from the URDF

    def test_finger_command_is_tracked_and_mimics_hold(self):
        s, m, d = self.scene, self.scene.model, self.scene.data
        for c in (0, 128, 255):
            s.reset()
            d.ctrl[s.grip_act] = c
            for _ in range(600):
                mujoco.mj_step(m, d)
            q = d.qpos[self._joint(kairos_model.FINGER_JOINT)]
            self.assertAlmostEqual(q, c * kairos_model.FINGER_MAX / 255, delta=0.01)
            for name, sign in kairos_model.MIMIC:
                self.assertAlmostEqual(d.qpos[self._joint(name)], sign * q, delta=0.01, msg=name)

    def test_closing_pads_meet_at_the_pinch_axis(self):
        s, m, d = self.scene, self.scene.model, self.scene.data
        s.reset()
        d.ctrl[s.grip_act] = 255
        for _ in range(600):
            mujoco.mj_step(m, d)
        B = lambda n: d.xpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, n)]
        centre_dist = np.linalg.norm(B("g_left_pad") - B("g_right_pad"))
        self.assertLess(centre_dist, 0.012)                    # closed: pads about one pad thickness apart (7.5 mm)
        s.reset()
        for _ in range(100):
            mujoco.mj_step(m, d)
        self.assertGreater(np.linalg.norm(B("g_left_pad") - B("g_right_pad")), 0.12)   # open: about 13 cm

    def test_nominal_pick_and_place_succeeds(self):
        from transfergap import metrics
        from transfergap.sim.rollout import run_episode
        for seed in (0, 1, 2):
            ep = run_episode(seed, robot="kairos")
            self.assertTrue(metrics.score_episode(ep)["success"], f"seed {seed}")


if __name__ == "__main__":
    unittest.main()
