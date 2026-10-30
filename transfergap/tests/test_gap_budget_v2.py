"""gap_budget_v2: retargeting stage, per-seed random calibration direction, robot selection, v1 untouched."""
import json
import unittest
from pathlib import Path

import numpy as np

from transfergap.sim import errors, errors_v2 as E

try:
    import mujoco
    from transfergap.metrics import score_episode, summarize
    from transfergap.sim.gap_budget import Cfg
    from transfergap.sim.rollout import run_episode
    from transfergap.sim.scene import Scene, robot_ready
    READY = int(mujoco.__version__.split(".")[0]) >= 3 and robot_ready("ur5e")
    READY_10 = READY and robot_ready("ur10e")
except ImportError:
    READY = READY_10 = False

V1 = Path(__file__).resolve().parents[1] / "results" / "gap_budget_v1" / "protocol.json"


class ErrorModelV2(unittest.TestCase):
    def test_conditions_and_oracles(self):
        self.assertEqual(E.COMPONENTS, ("perception", "retargeting", "calibration", "timing"))
        self.assertEqual(E.CONDITIONS["oracle_retargeting"], "retargeting")
        self.assertEqual(set(E.CORRECTIONS), set(E.COMPONENTS))
        self.assertTrue(E.constants()["all_values_are_assumptions"])

    def test_deterministic_and_paired(self):
        for s in (0, 17, 1003):
            full, o = E.build_perturbation(s, "full")
            self.assertEqual(o, "none")
            self.assertEqual(full, E.build_perturbation(s, "full")[0])
            r, o = E.build_perturbation(s, "oracle_retargeting")
            self.assertEqual(o, "retargeting")
            self.assertEqual(r["retarget_q_err"], [0.0] * 6)
            for k in ("perception_err_xy", "tcp_offset_vec", "timing_scale"):
                self.assertEqual(r[k], full[k])           # only the retargeting stage is replaced
            a, _ = E.build_perturbation(s, "oracle_all")
            self.assertEqual((a["perception_err_xy"], a["retarget_q_err"], a["tcp_offset_vec"], a["timing_scale"]),
                             ([0.0] * 2, [0.0] * 6, [0.0] * 3, 1.0))
            self.assertNotEqual(full["retarget_q_err"], [0.0] * 6)

    def test_retarget_magnitude(self):
        q = np.array([E.sample_errors(s)["retarget_q_err"] for s in range(2000)])
        self.assertAlmostEqual(q.std(), E.RETARGET_JOINT_SIGMA_RAD, delta=0.05 * E.RETARGET_JOINT_SIGMA_RAD)

    def test_calibration_direction_random_per_seed(self):
        v = np.array([E.sample_errors(s)["tcp_offset_vec"] for s in range(400)])
        n = np.linalg.norm(v, axis=1)
        self.assertLessEqual(n.max(), E.CALIBRATION_MAX_M + 1e-12)
        d = v / n[:, None]
        self.assertTrue(np.all(np.abs(d.mean(axis=0)) < 0.15))                  # no preferred direction
        octants = {tuple(x) for x in (d > 0).astype(int)}
        self.assertEqual(len(octants), 8)                                       # every octant is hit
        self.assertLess(np.abs(d @ d[0]).min(), 0.2)                            # not one fixed axis

    def test_streams_are_independent_per_component(self):
        a = E.sample_errors(5)
        rng = np.random.default_rng([5, 424242, 3])
        u = rng.normal(size=3)
        u /= np.linalg.norm(u)
        self.assertTrue(np.allclose(a["tcp_offset_vec"] / np.linalg.norm(a["tcp_offset_vec"]), u))

    def test_corrections(self):
        f, _ = E.build_perturbation(7, "full")
        c, _ = E.build_perturbation(7, "full", "ik_resolve")
        self.assertEqual({k: v for k, v in c.items() if k != "retarget_q_err"}, {k: v for k, v in f.items() if k != "retarget_q_err"})
        self.assertLess(np.abs(c["retarget_q_err"]).max(), np.deg2rad(0.5))
        self.assertNotEqual(c["retarget_q_err"], f["retarget_q_err"])
        with self.assertRaises(ValueError):
            E.build_perturbation(7, "oracle_retargeting", "ik_resolve")

    def test_v1_model_and_frozen_protocol_unchanged(self):
        self.assertEqual(json.loads(V1.read_text())["constants"], errors.constants())
        self.assertEqual(errors.COMPONENTS, ("perception", "calibration", "timing"))


@unittest.skipUnless(READY, "needs mujoco>=3 and menagerie assets")
class RobotSelection(unittest.TestCase):
    def test_cfg_paths_and_v1_lock(self):
        self.assertEqual(Cfg().res.name, "gap_budget_v1")
        self.assertEqual(Cfg("v2", "ur10e").res.name, "gap_budget_v2_ur10e")
        self.assertEqual(Cfg("v2", "ur5e").singles, tuple(f"oracle_{c}" for c in E.COMPONENTS))
        with self.assertRaises(ValueError):
            Cfg("v1", "ur10e")

    def test_default_robot_is_ur5e(self):
        ep = run_episode(0)
        self.assertEqual(ep["robot"], "ur5e_2f85_fixed")

    def test_zero_retarget_error_is_the_exact_ik_oracle(self):
        a = run_episode(1)
        b = run_episode(1, {"retarget_q_err": [0.0] * 6})
        self.assertEqual(a["states"], b["states"])

    @unittest.skipUnless(READY_10, "needs UR10e menagerie assets")
    def test_ur10e_unperturbed_grasp_and_label(self):
        eps = [run_episode(s, robot="ur10e") for s in range(5)]
        self.assertEqual({e["robot"] for e in eps}, {"ur10e_2f85_fixed"})
        self.assertGreaterEqual(sum(score_episode(e)["success"] for e in eps), 4)
        sc = Scene(0, "ur10e")
        self.assertEqual(int((sc.model.eq_type == mujoco.mjtEq.mjEQ_WELD).sum()), 0)

    @unittest.skipUnless(READY_10, "needs UR10e menagerie assets")
    def test_robots_never_pooled(self):
        a, b = run_episode(0, robot="ur5e", oracle="none"), run_episode(0, robot="ur10e", oracle="none")
        self.assertEqual(len(summarize([a, b])["groups"]), 2)


if __name__ == "__main__":
    unittest.main()
