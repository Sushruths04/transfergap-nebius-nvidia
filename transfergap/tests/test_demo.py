"""Human-demo input path: schema, segmentation, object-relative + style retargeting, style metrics, purity,
and (with menagerie assets) a demo-driven rollout."""
import ast
import inspect
import tempfile
import unittest
from pathlib import Path

import numpy as np

from transfergap.demo import gemx, retarget, schema, segment, style, synthetic
from transfergap.demo.retarget import ROBOT_NOMINAL_S, exact_plan, plan_from_demo
from transfergap.demo.schema import HumanDemo
from transfergap.demo.segment import segment as seg_fn
from transfergap.demo.style import carry_map, robot_path, style_metrics, style_plan_from_demo
from transfergap.demo.synthetic import make_demo

try:
    import mujoco  # noqa: F401
    from transfergap.sim.scene import ASSETS
    READY = (ASSETS / "universal_robots_ur5e").exists()
except ImportError:
    READY = False


class Schema(unittest.TestCase):
    def test_roundtrip_and_validation(self):
        demo, _ = make_demo(seed=1)
        with tempfile.TemporaryDirectory() as d:
            back = HumanDemo.load(demo.save(Path(d) / "demo.npz"))
        np.testing.assert_allclose(back.pinch, demo.pinch)
        self.assertEqual(back.meta, demo.meta)
        with self.assertRaises(ValueError):
            HumanDemo(demo.t[::-1], demo.pinch, demo.aperture, demo.object_xyz, demo.goal_xyz, "x")
        with self.assertRaises(ValueError):
            HumanDemo(demo.t, demo.pinch[:, :2], demo.aperture, demo.object_xyz, demo.goal_xyz, "x")
        bad = demo.pinch.copy()
        bad[3, 1] = np.nan
        with self.assertRaises(ValueError):
            HumanDemo(demo.t, bad, demo.aperture, demo.object_xyz, demo.goal_xyz, "x")


class Segmentation(unittest.TestCase):
    def test_recovers_grasp_and_release(self):
        for seed in range(5):
            demo, truth = make_demo(seed=seed)
            s = seg_fn(demo)
            self.assertLessEqual(abs(s.grasp - truth["grasp_index"]), 2)
            self.assertLessEqual(abs(s.release - truth["release_index"]), 2)
            self.assertTrue(s.reach_start < s.grasp < s.lift_end <= s.place_start < s.release <= s.end)

    def test_robust_to_estimator_jitter(self):
        for seed in range(5):
            demo, truth = make_demo(seed=seed, jitter_sigma_m=0.005)
            s = seg_fn(demo)
            self.assertLessEqual(abs(s.grasp - truth["grasp_index"]), 4)
            self.assertLessEqual(abs(s.release - truth["release_index"]), 4)

    def test_rejects_demo_without_grasp(self):
        demo, _ = make_demo()
        flat = HumanDemo(demo.t, demo.pinch, np.full_like(demo.aperture, 0.09), demo.object_xyz, demo.goal_xyz,
                         "synthetic")
        with self.assertRaises(ValueError):
            seg_fn(flat)


class Retargeting(unittest.TestCase):
    def test_object_relative_offsets_and_timing(self):
        demo, truth = make_demo(seed=4)
        plan = plan_from_demo(demo)
        np.testing.assert_allclose(plan["grasp_offset"], truth["grasp_offset"], atol=1e-3)
        np.testing.assert_allclose(plan["place_offset"], truth["release_offset"], atol=3e-3)
        human = sum(plan["human_durations_s"].values())
        self.assertAlmostEqual(plan["timing_scale"], sum(ROBOT_NOMINAL_S.values()) / human)
        self.assertGreater(plan["timing_scale"], 1.0)          # a human-paced demo is faster than the robot
        fast = plan_from_demo(make_demo(seed=4, speed=2.0)[0])
        self.assertAlmostEqual(fast["timing_scale"] / plan["timing_scale"], 2.0, delta=0.15)

    def test_yaw_alignment_rotates_offsets(self):
        demo, _ = make_demo(seed=2)
        a, b = plan_from_demo(demo), plan_from_demo(demo, align_yaw=np.pi / 2)
        np.testing.assert_allclose(b["grasp_offset"][:2], [-a["grasp_offset"][1], a["grasp_offset"][0]], atol=1e-9)

    def test_z_floor_clamp(self):
        demo, _ = make_demo(seed=0, grasp_bias_sigma_m=0.0)
        low = HumanDemo(demo.t, demo.pinch - [0, 0, 0.05], demo.aperture, demo.object_xyz, demo.goal_xyz,
                        "synthetic")
        self.assertGreaterEqual(plan_from_demo(low)["grasp_offset"][2], retarget.Z_FLOOR_M)


class Style(unittest.TestCase):
    def setUp(self):
        self.demo, _ = make_demo(seed=5)
        self.plan = style_plan_from_demo(self.demo)

    def test_legs_anchor_exactly(self):
        g, r = np.array([0.45, -0.1, 0.02]), np.array([0.45, 0.22, 0.03])
        path = robot_path(self.plan, g, r)
        np.testing.assert_allclose(path["reach"][1][-1], g, atol=1e-9)
        np.testing.assert_allclose(path["carry"][1][0], g, atol=1e-9)
        np.testing.assert_allclose(path["carry"][1][-1], r, atol=1e-9)
        np.testing.assert_allclose(path["retreat"][1][0], r, atol=1e-9)
        sg = seg_fn(self.demo)
        lift_h = self.demo.pinch[sg.grasp:sg.release + 1, 2].max() - self.demo.pinch[sg.grasp, 2]
        self.assertAlmostEqual(path["carry"][1][:, 2].max() - g[2], lift_h, delta=0.02)   # lift height is kept

    def test_safe_project_clamps_only_below_contact_height(self):
        from transfergap.demo.style import safe_project
        p = self.plan
        low = {k: dict(v) for k, v in p["style"]["legs"].items()}
        rel = np.array(low["reach"]["rel"])
        rel[5, 2] = -0.05
        q = dict(p, style=dict(p["style"], legs=dict(low, reach=dict(low["reach"], rel=rel.tolist()))))
        s = safe_project(q)
        r = np.array(s["style"]["legs"]["reach"]["rel"])
        self.assertGreaterEqual(r[:, 2].min(), 0.0)
        np.testing.assert_allclose(r[:, :2], rel[:, :2])                 # xy (style) untouched
        self.assertNotIn("safe_projected", q)                              # input not mutated

    def test_carry_map(self):
        M = carry_map([0.2, 0.0, 0.0], [0.0, 0.4, 0.1])
        np.testing.assert_allclose(M @ [0.2, 0.0, 0.0], [0.0, 0.4, 0.0], atol=1e-12)
        np.testing.assert_allclose(M @ [0.0, 0.0, 0.3], [0.0, 0.0, 0.3], atol=1e-12)

    def test_metrics_zero_for_identical_paths_and_grow_with_offset(self):
        path = robot_path(self.plan, [0.4, 0.0, 0.02], [0.4, 0.3, 0.02])
        m = style_metrics(path, path)
        self.assertAlmostEqual(m["path_rmse_mean_m"], 0.0, places=9)
        self.assertAlmostEqual(m["approach_angle_deg"], 0.0, places=3)
        self.assertAlmostEqual(m["speed_profile_corr"], 1.0, places=6)
        shifted = {k: (t, x + [0.02, 0, 0]) for k, (t, x) in path.items()}
        self.assertAlmostEqual(style_metrics(path, shifted)["path_rmse_mean_m"], 0.02, places=6)


class GemxConversion(unittest.TestCase):
    """Fake SOMA joints built from a synthetic demo (y-up frame, table 0.7 m up) convert back to the same path."""
    def test_joints_to_demo(self):
        demo, _ = make_demo(seed=6, grasp_bias_sigma_m=0.0)
        names = ["Hips"] + [f"{s}Hand{f}End" for s in ("Left", "Right") for f in ("Thumb", "Index")]
        J = np.zeros((len(demo.t), len(names), 3))
        half = np.c_[demo.aperture / 2, np.zeros((len(demo.t), 2))]
        lift = np.array([0.0, 0.0, 0.70])
        for k, sign in ((names.index("RightHandThumbEnd"), -1), (names.index("RightHandIndexEnd"), 1)):
            d = demo.pinch + lift + sign * half
            J[:, k] = np.stack([d[:, 0], d[:, 2], -d[:, 1]], axis=1)      # demo frame -> SOMA y-up
        out = gemx.demo_from_joints(J, names, demo.fps)
        np.testing.assert_allclose(out.aperture, demo.aperture, atol=1e-9)
        shift = out.pinch - demo.pinch
        np.testing.assert_allclose(shift, np.broadcast_to(shift[0], shift.shape), atol=1e-9)   # rigid shift only
        sg = seg_fn(out)
        self.assertAlmostEqual(out.pinch[sg.grasp:sg.release + 1, 2].min(), gemx.OBJECT_HALF_M, places=9)
        np.testing.assert_allclose(plan_from_demo(out)["grasp_offset"], [0, 0, 0], atol=1e-9)  # unobservable here


class DemoModulesArePure(unittest.TestCase):
    """The demo path reads no simulator state and never references success/scoring."""
    def test_no_sim_imports_or_success(self):
        for mod in (schema, segment, retarget, style, synthetic, gemx):
            tree = ast.parse(inspect.getsource(mod))
            imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
                       {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
            self.assertFalse([i for i in imported if any(k in i for k in ("mujoco", "sim", "metrics"))],
                             mod.__name__)
            names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
                    {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            self.assertFalse([n for n in names if "success" in n.lower() or "block_pos" in n], mod.__name__)


@unittest.skipUnless(READY, "menagerie assets / mujoco not available")
class DemoDrivenRollout(unittest.TestCase):
    def test_style_plan_at_nominal_speed_succeeds_and_logs_tool_path(self):
        from transfergap.metrics import score_episode
        from transfergap.sim.rollout import run_episode
        plan = style_plan_from_demo(make_demo(seed=3)[0])
        ep = run_episode(0, {"demo_plan": plan, "timing_scale": 1.0}, label="demo_style")
        self.assertTrue(score_episode(ep)["success"], score_episode(ep)["failure_reasons"])
        phases = {s["phase"] for s in ep["states"]}
        self.assertTrue({"align", "reach", "close", "carry", "open", "retreat"} <= phases)
        self.assertTrue(all("tool_xyz" in s for s in ep["states"]))

    def test_exact_plan_matches_scripted_baseline_outcome(self):
        from transfergap.metrics import score_episode
        from transfergap.sim.rollout import run_episode
        self.assertTrue(score_episode(run_episode(1, {"demo_plan": exact_plan()}))["success"])
        self.assertNotIn("tool_xyz", run_episode(1, {})["states"][0])   # legacy episodes unchanged


if __name__ == "__main__":
    unittest.main()


class HiphiBvh(unittest.TestCase):
    """Forward kinematics of a two-joint BVH: Z-X-Y Euler order, offsets in cm, End Site positions."""
    BVH = """HIERARCHY
ROOT Hips
{
  OFFSET 0 0 0
  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
  JOINT Arm
  {
    OFFSET 10 0 0
    CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
    End Site
    {
      OFFSET 5 0 0
    }
  }
}
MOTION
Frames: 2
Frame Time: 0.011111
0 100 0 0 0 0 10 0 0 0 0 0
0 100 0 90 0 0 10 0 0 0 0 0
"""

    def test_fk(self):
        from transfergap.demo.hiphi import forward_kinematics, parse_bvh, y_up_to_z_up
        joints, dt, motion = parse_bvh(self.BVH)
        self.assertEqual([j.name for j in joints], ["Hips", "Arm"])
        self.assertAlmostEqual(dt, 0.011111)
        P = forward_kinematics(joints, motion)
        np.testing.assert_allclose(P["Arm_End"][0], [15, 100, 0], atol=1e-9)
        np.testing.assert_allclose(P["Arm_End"][1], [0, 115, 0], atol=1e-9)     # 90 deg about Z at the root
        np.testing.assert_allclose(y_up_to_z_up([1.0, 2.0, 3.0]), [1.0, -3.0, 2.0])

    def test_first_cycle_and_quat(self):
        from transfergap.demo.hiphi import first_cycle, quat_rotate
        t = np.arange(300) / 90.0
        obj = np.zeros((300, 3))
        obj[90:150, 2] = np.linspace(0, 0.3, 60)
        obj[150:, 2] = 0.3
        g, r = first_cycle(obj, t)
        self.assertLessEqual(abs(g - 90), 2)
        self.assertLessEqual(abs(r - 150), 2)
        q = np.array([[0, 0, np.sin(np.pi / 4), np.cos(np.pi / 4)]])
        np.testing.assert_allclose(quat_rotate(q, np.array([1.0, 0, 0]))[0], [0, 1, 0], atol=1e-12)
