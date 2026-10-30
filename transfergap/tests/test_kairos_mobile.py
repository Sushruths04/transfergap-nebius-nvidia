import unittest

import numpy as np

from transfergap.sim import kairos_model as KM
from transfergap.sim import scene as S

READY = S.robot_ready("kairos_mobile") if "kairos_mobile" in S.ROBOTS else False


@unittest.skipUnless(READY, "KAIROS base/gripper lab assets not present (sim/assets/kairos)")
class KairosMobileTests(unittest.TestCase):
    def test_arm_names_and_actuator_order_unchanged(self):
        import mujoco
        sc = S.Scene(0, "kairos_mobile")
        m = sc.model
        names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, i) for i in range(m.nu)]
        self.assertEqual(names[:6], ["shoulder_pan", "shoulder_lift", "elbow", "wrist_1", "wrist_2", "wrist_3"])
        self.assertEqual(names[6], "g_fingers_actuator")
        self.assertEqual(names[7:], [f"{j}_servo" for j in KM.BASE_JOINTS])

    def test_arm_base_height_matches_lab_urdf(self):
        sc = S.Scene(0, "kairos_mobile")
        import mujoco
        bid = mujoco.mj_name2id(sc.model, mujoco.mjtObj.mjOBJ_BODY, "base")
        self.assertAlmostEqual(float(sc.data.xpos[bid][2]), 0.0, places=6)
        fl = sc.model.geom_pos[mujoco.mj_name2id(sc.model, mujoco.mjtObj.mjOBJ_GEOM, "floor")][2]
        self.assertAlmostEqual(float(fl), -(0.38062 + 0.127), places=5)

    def test_parked_pick_and_place_matches_fixed_arm(self):
        from transfergap.metrics import score_episode
        from transfergap.sim.rollout import run_episode
        for s in range(2):
            a = score_episode(run_episode(s, robot="kairos"))
            b = score_episode(run_episode(s, robot="kairos_mobile"))
            self.assertEqual(bool(a["success"]), bool(b["success"]))

    def test_base_drives_to_pose(self):
        from transfergap.sim.kairos_mobile import BaseDrive
        from transfergap.sim.rollout import CTRL_HZ
        import mujoco
        sc = S.Scene(0, "kairos_mobile")
        drv = BaseDrive(sc)
        drv.place(-0.8, -0.5, 0.6)
        sub = round(1 / (sc.model.opt.timestep * CTRL_HZ))
        n = 0
        while not drv.go_to((0.0, 0.0, 0.0), 1 / CTRL_HZ) and n < 40 * CTRL_HZ:
            sc.data.ctrl[:6] = sc.home_q
            for _ in range(sub):
                mujoco.mj_step(sc.model, sc.data)
            n += 1
        p = drv.pose()
        self.assertLess(np.hypot(p[0], p[1]), 0.03)
        self.assertLess(abs(p[2]), 0.03)

    def test_chassis_does_not_touch_table_when_parked(self):
        sc = S.Scene(0, "kairos_mobile")
        import mujoco
        mujoco.mj_forward(sc.model, sc.data)
        g = mujoco.mj_name2id(sc.model, mujoco.mjtObj.mjOBJ_GEOM, "kb_chassis_col")
        t = sc.table_geom
        pen = [c.dist for c in sc.data.contact[:sc.data.ncon] if {c.geom1, c.geom2} == {g, t}]
        self.assertFalse(pen)


if __name__ == "__main__":
    unittest.main()
