import copy
import unittest

import numpy as np

from transfergap.sim.scene import robot_ready


@unittest.skipUnless(robot_ready("ur5e"), "menagerie assets missing")
class FeasibilityPrecheckTest(unittest.TestCase):
    def setUp(self):
        from transfergap.demo.style import style_plan_from_demo
        from transfergap.demo.synthetic import make_demo
        self.plan = style_plan_from_demo(make_demo(seed=7)[0])

    def test_synthetic_demo_is_feasible(self):
        from transfergap.sim.feasibility import check_arm
        r = check_arm(self.plan, "ur5e", jitter=False)
        self.assertTrue(r["feasible"], r["reasons"])

    def test_retreat_into_the_table_is_flagged(self):
        from transfergap.sim.feasibility import check_arm
        p = copy.deepcopy(self.plan)
        rel = np.array(p["style"]["legs"]["retreat"]["rel"])
        rel[10:30, 2] -= 0.10                       # follow the object 10 cm down after the release
        p["style"]["legs"]["retreat"]["rel"] = rel.tolist()
        r = check_arm(p, "ur5e", jitter=False)
        self.assertFalse(r["feasible"])
        self.assertTrue(any(x.startswith("collides") for x in r["reasons"]), r["reasons"])

    def test_out_of_workspace_is_flagged(self):
        from transfergap.sim.feasibility import check_arm
        p = copy.deepcopy(self.plan)
        rel = np.array(p["style"]["legs"]["reach"]["rel"])
        rel[:20, 0] += 1.5                           # reach starts 1.5 m further away than the arm's span
        p["style"]["legs"]["reach"]["rel"] = rel.tolist()
        r = check_arm(p, "ur5e", jitter=False)
        self.assertFalse(r["feasible"])
        self.assertTrue(any(x.startswith("unreachable") for x in r["reasons"]), r["reasons"])


if __name__ == "__main__":
    unittest.main()
