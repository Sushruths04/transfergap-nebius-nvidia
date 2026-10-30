"""Depth perception: the estimator never reads ground truth, its pieces are correct on synthetic data, it localises
the block and tray in real renders (also under depth noise), and the new scene/controller hooks keep old behaviour."""
import ast
import inspect
import unittest

import numpy as np

try:
    import mujoco
    from transfergap.sim import perception
    from transfergap.sim.controller import ScriptedPickPlace
    from transfergap.sim.perception import (Perceiver, _hull_area, _min_area_rect, fit_plane, fit_table_z,
                                            label_components, level_to_plane, median_filter_depth)
    from transfergap.sim.scene import BLOCK_HALF, BLOCK_MASS, TRAY_FLOOR, Scene
    READY = int(mujoco.__version__.split(".")[0]) >= 3
    try:
        _s = Scene(0, "ur5e")
        _r = mujoco.Renderer(_s.model, 32, 32)
        _r.close()
        RENDER = True
    except Exception:
        RENDER = False
except ImportError:
    READY = RENDER = False
    KAIROS = False

# attributes the estimator must never touch: the block, the goal, contacts, anything that scores
FORBIDDEN_ATTRS = {"block_pos", "block_vel", "contact_flags", "block_body", "block_geom", "block_qadr", "table_geom",
                   "link_bodies", "finger_bodies", "goal_xyz", "block_half", "xpos", "qpos"}
FORBIDDEN_WORDS = ("success", "score", "metrics")

try:
    from transfergap.sim.scene import robot_ready as _robot_ready
    KAIROS = _robot_ready("kairos")      # the lab gripper description is not distributed: mount it (docker/entrypoint.sh) or these tests skip
except Exception:  # noqa: BLE001
    KAIROS = False


@unittest.skipUnless(READY, "needs mujoco >= 3")
class PerceptionPartsTests(unittest.TestCase):
    def test_estimator_reads_no_ground_truth(self):
        tree = ast.parse(inspect.getsource(perception))
        used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse(used & FORBIDDEN_ATTRS, used & FORBIDDEN_ATTRS)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | used
        for w in FORBIDDEN_WORDS:
            self.assertFalse([n for n in names if w in n.lower()], w)

    def test_label_components_diagonal_connectivity_and_separation(self):
        m = np.zeros((6, 8), bool)
        m[0, 0] = m[1, 1] = m[2, 2] = True            # diagonal chain: one 8-connected component
        m[4, 5:8] = True                              # a second, separate component
        labels, n = label_components(m)
        self.assertEqual(n, 2)
        self.assertEqual(labels[0, 0], labels[2, 2])
        self.assertNotEqual(labels[0, 0], labels[4, 6])
        self.assertTrue((labels[~m] == 0).all())

    def test_fit_table_z_finds_the_dominant_plane(self):
        rng = np.random.default_rng(0)
        table = np.c_[rng.uniform(0, 1, (4000, 2)), rng.normal(0.0, 0.002, 4000)]
        floor = np.c_[rng.uniform(0, 1, (1500, 2)), rng.normal(-0.75, 0.002, 1500)]
        box = np.c_[rng.uniform(0.4, 0.44, (200, 2)), rng.normal(0.04, 0.002, 200)]
        self.assertAlmostEqual(fit_table_z(np.vstack([table, floor, box])), 0.0, delta=0.002)


@unittest.skipUnless(READY, "needs mujoco >= 3")
class HardTestPartsTests(unittest.TestCase):
    def test_min_area_rect_recovers_yaw_centre_and_size_of_a_rotated_square(self):
        rng = np.random.default_rng(1)
        u = rng.uniform(-0.03, 0.03, (3000, 2))
        a = np.deg2rad(33.0)
        R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        xy = u @ R.T + [0.4, -0.1]
        c, ext, yaw = _min_area_rect(xy)
        np.testing.assert_allclose(c, [0.4, -0.1], atol=0.002)
        np.testing.assert_allclose(sorted(ext), [0.06, 0.06], atol=0.002)
        self.assertAlmostEqual(np.rad2deg(yaw) % 90, 33.0, delta=1.5)
        self.assertGreater(_hull_area(xy) / np.prod(ext), 0.97)                 # a square is filled

    def test_fill_separates_a_cube_top_from_a_cylinder_top(self):
        from transfergap.sim.perception import _measure
        rng = np.random.default_rng(3)
        t = rng.uniform(0, 2 * np.pi, 4000)
        disc = 0.025 * np.sqrt(rng.uniform(0, 1, 4000))[:, None] * np.c_[np.cos(t), np.sin(t)] + [0.4, 0.0]
        sq = rng.uniform(-0.025, 0.025, (4000, 2)) + [0.4, 0.0]
        mk = lambda xy: np.c_[xy, np.full(len(xy), 0.05)]
        self.assertGreater(_measure(mk(sq), 0.0)["fill"], 0.95)
        self.assertLess(_measure(mk(disc), 0.0)["fill"], 0.85)

    def test_tray_floor_ignores_a_carried_block_above_it(self):
        """regression: with the block held above the tray the floor estimate came out 0.216 m too high."""
        from transfergap.sim.perception import tray_floor_z
        rng = np.random.default_rng(4)
        floor = np.c_[rng.uniform(0.40, 0.50, (3000, 2)), rng.normal(0.004, 0.0005, 3000)]
        held = np.c_[rng.uniform(0.44, 0.46, (4000, 2)), np.full(4000, 0.25)]    # more points than the floor has
        P = np.vstack([floor, held]).reshape(1, -1, 3)
        tray = dict(centre_xy=np.array([0.45, 0.45]), extent_x=0.16, extent_y=0.16)
        self.assertAlmostEqual(tray_floor_z(P, np.ones(P.shape[:2], bool), tray, 0.0), 0.004, delta=0.001)

    def test_plane_fit_levels_a_tilted_table_and_ignores_objects(self):
        rng = np.random.default_rng(2)
        xy = rng.uniform(0, 1, (6000, 2))
        z = 0.012 * xy[:, 0] - 0.008 * xy[:, 1] + rng.normal(0, 0.001, 6000)     # tilted table
        box = np.c_[rng.uniform(0.4, 0.46, (300, 2)), rng.uniform(0.04, 0.05, 300)]
        pts = np.vstack([np.c_[xy, z], box])
        n, c0 = fit_plane(pts, fit_table_z(pts, bin_m=0.01))
        lev = level_to_plane(pts, n, c0)
        self.assertLess(np.abs(lev[:6000, 2] - c0[2]).max(), 0.005)             # table is flat again
        self.assertGreater(lev[6000:, 2].min() - c0[2], 0.03)                   # the box stays on top of it

    def test_median_filter_removes_speckle_keeps_edges_and_holes(self):
        d = np.full((20, 20), 1.0)
        d[:, 10:] = 0.6
        d[5, 5] = 2.0
        d[8, 15] = np.nan
        f = median_filter_depth(d, 3)
        self.assertAlmostEqual(f[5, 5], 1.0)
        self.assertAlmostEqual(f[3, 9], 1.0)
        self.assertAlmostEqual(f[3, 10], 0.6)                                   # step edge preserved
        self.assertTrue(np.isnan(f[8, 15]))                                     # holes are not invented

    def test_depth_step_splits_components_that_overlap_in_the_image(self):
        z = np.zeros((6, 8))
        z[:, 4:] = 0.2                                                          # a high surface next to a low one
        m = np.ones((6, 8), bool)
        self.assertEqual(label_components(m)[1], 1)
        self.assertEqual(label_components(m, z, 0.025)[1], 2)

    def test_controller_wraps_grasp_yaw_to_the_cube_symmetry(self):
        from transfergap.sim.controller import R_DOWN
        s = Scene(0, "ur5e")
        ctl = ScriptedPickPlace(s)
        np.testing.assert_allclose(ctl.R_goal, R_DOWN)                          # default unchanged
        ctl.set_grasp_yaw(np.deg2rad(100))                                      # = 10 deg for a cube
        self.assertAlmostEqual(np.rad2deg(ctl.grasp_yaw), 10.0, places=6)
        ctl.set_grasp_yaw(np.deg2rad(-50))                                      # = +40
        self.assertAlmostEqual(np.rad2deg(ctl.grasp_yaw), 40.0, places=6)

    @unittest.skipUnless(KAIROS, "needs the KAIROS gripper assets (not distributed)")
    def test_grasp_yaw_rotates_only_when_the_cube_would_not_clear_the_opening(self):
        w = 0.06
        kai = ScriptedPickPlace(Scene(0, "kairos"))
        kai.set_grasp_yaw(np.deg2rad(35), w)                                    # 128 mm opening: 83 mm needed -> stay
        self.assertEqual(kai.grasp_yaw, 0.0)
        ur = ScriptedPickPlace(Scene(0, "ur5e"))
        ur.set_grasp_yaw(np.deg2rad(35), w)                                     # 85 mm opening: 83 > 60 -> rotate
        self.assertAlmostEqual(np.rad2deg(ur.grasp_yaw), 35.0, places=6)
        ur.set_grasp_yaw(np.deg2rad(5), 0.05)                                   # 50 x 1.08 = 54 <= 60 -> stay
        self.assertEqual(ur.grasp_yaw, 0.0)
        ur.set_grasp_yaw(np.deg2rad(5), w)                                      # 60 x 1.08 = 65 > 60 -> rotate
        self.assertAlmostEqual(np.rad2deg(ur.grasp_yaw), 5.0, places=6)
        ur.set_grasp_yaw(np.deg2rad(35), None)                                  # no width given: always rotate
        self.assertAlmostEqual(np.rad2deg(ur.grasp_yaw), 35.0, places=6)

    def test_scene_options_default_to_the_old_scene(self):
        a, b = Scene(3, "ur5e", 0.02), Scene(3, "ur5e", 0.02, 0.0, ())
        np.testing.assert_allclose(a.block_pos(), b.block_pos())
        np.testing.assert_allclose(a.model.body_quat[a.block_body], [1, 0, 0, 0])
        from transfergap.sim.scene import sample_block_yaw, sample_distractors
        c = Scene(3, "ur5e", 0.03, 0.5, sample_distractors(3, 3, a.block_pos()[:2], 0.03))
        self.assertAlmostEqual(c.model.body_quat[c.block_body][3], np.sin(0.25), places=6)
        self.assertEqual(sum(1 for i in range(c.model.ngeom) if (c.model.geom(i).name or "").startswith("distractor")), 3)
        self.assertLessEqual(abs(sample_block_yaw(7)), np.deg2rad(45))
        dist = [np.linalg.norm(np.array(d["xy"]) - a.block_pos()[:2]) for d in sample_distractors(3, 3, a.block_pos()[:2], 0.03)]
        self.assertGreater(min(dist), 0.1)                                      # clear of the fingers


@unittest.skipUnless(READY, "needs mujoco >= 3")
class HeldoutGuardTests(unittest.TestCase):
    def test_heldout_refuses_without_a_committed_protocol_and_with_partial_protocols(self):
        import tempfile
        from transfergap.sim import perception_hard_eval as H
        seeds = H.parse_range(H.SPLITS["heldout"])
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                H.check_frozen(d, list(H.CONDITIONS), H.SIZES, seeds)           # no protocol.json at all
        import json
        from pathlib import Path
        proto = Path(__file__).resolve().parents[1] / "results" / "perception_hard_v1" / "protocol.json"
        if proto.exists():                                                       # the frozen protocol matches the code
            p = json.loads(proto.read_text())
            self.assertEqual(p["conditions"], json.loads(json.dumps(H.CONDITIONS)))
            self.assertEqual(p["heldout_seeds"], H.SPLITS["heldout"])
        self.assertTrue(set(H.parse_range(H.SPLITS["dev"])).isdisjoint(seeds))   # dev and held-out seeds never overlap


@unittest.skipUnless(READY and RENDER, "needs mujoco >= 3 and a working GL backend (EGL)")
class PerceptionInTheSceneTests(unittest.TestCase):
    def _err(self, robot, seed, half, sigma):
        s = Scene(seed, robot, half)
        est = Perceiver(0.128 if robot == "kairos" else 0.085, sigma_m=sigma)(s)
        return (np.linalg.norm(est["block_xyz"] - s.block_pos()), np.linalg.norm(est["goal_xyz"] - s.goal_xyz),
                est["info"]["block"]["height"] - 2 * half)

    @unittest.skipUnless(KAIROS, "needs the KAIROS gripper assets (not distributed)")
    def test_block_and_tray_are_localised_within_a_few_millimetres(self):
        for robot, seed, half in (("ur5e", 0, 0.02), ("kairos", 3, 0.03), ("ur10e", 7, 0.015)):
            eb, eg, eh = self._err(robot, seed, half, 0.002)
            self.assertLess(eb, 0.004, (robot, eb))
            self.assertLess(eg, 0.004, (robot, eg))
            self.assertLess(abs(eh), 0.004, (robot, eh))

    @unittest.skipUnless(KAIROS, "needs the KAIROS gripper assets (not distributed)")
    def test_large_depth_noise_does_not_pick_a_speckle(self):
        """regression: at 5 mm noise the smallest-cluster rule selected noise 31 cm away from the block."""
        eb, eg, _ = self._err("kairos", 0, 0.02, 0.005)
        self.assertLess(eb, 0.006)
        self.assertLess(eg, 0.006)

    def test_block_size_parameter_and_default_goal_belief(self):
        s = Scene(0, "ur5e", 0.03)
        self.assertAlmostEqual(s.model.geom_size[s.block_geom][0], 0.03)
        self.assertAlmostEqual(s.model.body_mass[s.block_body], BLOCK_MASS * (0.03 / BLOCK_HALF) ** 3, places=6)
        self.assertAlmostEqual(s.goal_xyz[2], TRAY_FLOOR + 0.03)
        d = Scene(0, "ur5e")
        np.testing.assert_allclose(ScriptedPickPlace(d).goal_b, d.goal_xyz)          # default unchanged
        np.testing.assert_allclose(ScriptedPickPlace(d, goal_belief_xyz=[0.1, 0.2, 0.3]).goal_b, [0.1, 0.2, 0.3])

    def test_yawed_block_with_distractors_is_found_with_its_yaw(self):
        from transfergap.sim.scene import sample_distractors
        yaw = np.deg2rad(31.0)
        s = Scene(2, "ur5e", 0.03, yaw, sample_distractors(2, 4, Scene(2, "ur5e", 0.03).block_pos()[:2], 0.03))
        est = Perceiver(0.085, sigma_m=0.002)(s)
        self.assertLess(np.linalg.norm(est["block_xyz"] - s.block_pos()), 0.004)
        dy = (est["yaw"] - yaw + np.pi / 4) % (np.pi / 2) - np.pi / 4
        self.assertLess(abs(np.rad2deg(dy)), 3.0)

    def test_calibration_error_moves_the_estimate_but_leveling_keeps_height_sane(self):
        s = Scene(1, "ur5e", 0.03)
        est = Perceiver(0.085, sigma_m=0.002, calib_rot_deg=1.0, calib_trans_mm=10.0)(s)
        xy = np.linalg.norm(est["block_xyz"][:2] - s.block_pos()[:2])
        self.assertGreater(xy, 0.010)                                           # an uncalibrated camera is wrong ...
        self.assertLess(xy, 0.05)                                               # ... by about range x angle
        self.assertLess(abs(est["block_xyz"][2] - s.block_pos()[2]), 0.012)

    @unittest.skipUnless(KAIROS, "needs the KAIROS gripper assets (not distributed)")
    def test_pick_and_place_with_depth_belief_succeeds(self):
        from transfergap import metrics
        from transfergap.sim.rollout import run_episode
        ep = run_episode(2, robot="kairos", block_half=0.03, perceiver=Perceiver(0.128, sigma_m=0.002))
        self.assertTrue(metrics.score_episode(ep)["success"])


if __name__ == "__main__":
    unittest.main()
