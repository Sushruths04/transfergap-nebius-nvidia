"""demo_budget_v1 error model and helpers (no rollouts)."""
import ast
import inspect
import tempfile
import unittest
from pathlib import Path

import numpy as np

from transfergap.demo.synthetic import make_demo
from transfergap.sim import errors_demo as E


class ErrorModel(unittest.TestCase):
    def setUp(self):
        self.spec = E.parse_demo_spec("synthetic:0")

    def test_components_depend_on_demo_kind(self):
        self.assertIn("retargeting", E.components_for(self.spec))
        with tempfile.TemporaryDirectory() as d:
            p = make_demo(seed=1)[0].save(Path(d) / "real.npz")
            spec = E.parse_demo_spec(str(p))
        self.assertEqual(spec["kind"], "file")
        self.assertNotIn("retargeting", E.components_for(spec))
        self.assertNotIn("oracle_retargeting", E.conditions_for(spec))

    def test_oracle_all_removes_every_error(self):
        pert, oracle, ref = E.build_perturbation(self.spec, 3, "oracle_all")
        self.assertEqual(oracle, "all")
        self.assertEqual(pert["perception_err_xy"], [0.0, 0.0])
        self.assertEqual(pert["tcp_offset_vec"], [0.0, 0.0, 0.0])
        self.assertEqual(pert["timing_scale"], 1.0)
        self.assertEqual(pert["demo_plan"], ref)

    def test_full_uses_noisy_estimate_and_human_pace(self):
        pert, _, ref = E.build_perturbation(self.spec, 3, "full")
        self.assertNotEqual(pert["demo_plan"]["style"], ref["style"])
        self.assertGreater(pert["timing_scale"], 1.0)
        again, _, _ = E.build_perturbation(self.spec, 3, "full")
        self.assertEqual(again["demo_plan"], pert["demo_plan"])            # deterministic per seed
        other, _, _ = E.build_perturbation(self.spec, 4, "full")
        self.assertNotEqual(other["demo_plan"]["style"], pert["demo_plan"]["style"])

    def test_single_oracles_touch_only_their_component(self):
        full, _, ref = E.build_perturbation(self.spec, 5, "full")
        t, _, _ = E.build_perturbation(self.spec, 5, "oracle_timing")
        self.assertEqual(t["timing_scale"], 1.0)
        self.assertEqual(t["demo_plan"], full["demo_plan"])
        r, _, _ = E.build_perturbation(self.spec, 5, "oracle_retargeting")
        self.assertEqual(r["demo_plan"], ref)
        self.assertEqual(r["perception_err_xy"], full["perception_err_xy"])

    def test_corrections(self):
        full, _, _ = E.build_perturbation(self.spec, 2, "full")
        sm, _, _ = E.build_perturbation(self.spec, 2, "full", "smooth_demo")
        self.assertNotEqual(sm["demo_plan"]["style"], full["demo_plan"]["style"])
        cap, _, _ = E.build_perturbation(self.spec, 2, "full", "speed_cap_3")
        self.assertLessEqual(cap["timing_scale"], E.SPEED_CAP)
        with self.assertRaises(ValueError):
            E.build_perturbation(self.spec, 2, "oracle_timing", "look_again")

    def test_smoothing_reduces_estimation_noise(self):
        clean = E.clean_demo(self.spec)
        noisy = E.estimated_demo(self.spec, 7)
        smooth = E._smooth_path(noisy, E.SMOOTH_WINDOW_S)
        err = lambda d: np.sqrt(np.mean(np.sum((d.pinch - clean.pinch) ** 2, axis=1)))
        self.assertLess(err(smooth), err(noisy))

    def test_error_model_reads_no_sim_state(self):
        tree = ast.parse(inspect.getsource(E))
        imported = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
                   {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertFalse([i for i in imported if any(k in i for k in ("mujoco", "scene", "rollout", "metrics"))])
        names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | \
                {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse([n for n in names if "success" in n.lower() or n in ("block_pos", "contact_flags")])


class Stacking(unittest.TestCase):
    def setUp(self):
        self.spec = E.parse_demo_spec("synthetic:0")

    def test_next_correction_ladder(self):
        self.assertEqual(E.next_correction("timing"), "speed_cap_3")
        self.assertEqual(E.next_correction("timing", ["speed_cap_3"]), "speed_cap_2")
        self.assertIsNone(E.next_correction("timing", list(E.SPEED_LADDER)))
        self.assertIsNone(E.next_correction("perception", ["look_again"]))

    def test_base_applies_under_every_condition_and_oracles_override(self):
        base = ("speed_cap_3", "look_again")
        full, _, _ = E.build_perturbation(self.spec, 1, "full", base=base)
        self.assertLessEqual(full["timing_scale"], 3.0)
        self.assertIn("look_again_err_xy", full)
        cal, _, _ = E.build_perturbation(self.spec, 1, "oracle_calibration", base=base)
        self.assertIn("look_again_err_xy", cal)
        self.assertEqual(cal["tcp_offset_vec"], [0.0, 0.0, 0.0])
        per, _, _ = E.build_perturbation(self.spec, 1, "oracle_perception", base=base)
        self.assertNotIn("look_again_err_xy", per)
        self.assertEqual(E.build_perturbation(self.spec, 1, "oracle_timing", base=base)[0]["timing_scale"], 1.0)
        two, _, _ = E.build_perturbation(self.spec, 1, "full", "speed_cap_2", base=base)
        self.assertLessEqual(two["timing_scale"], 2.0)

    def test_no_base_reproduces_frozen_v1_construction(self):
        for corr in (None, "look_again", "smooth_demo", "touch_probe_calibration", "speed_cap_3"):
            a, _, _ = E.build_perturbation(self.spec, 9, "full", corr)
            b, _, _ = E.build_perturbation(self.spec, 9, "full", corr, ())
            self.assertEqual(a, b)
        self.assertNotIn("SPEED_LADDER", E.constants())      # frozen v1 protocols must still match


class OracleKeepsPlanFixes(unittest.TestCase):
    def test_oracle_all_keeps_safe_path_projection(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            spec = E.parse_demo_spec(str(make_demo(seed=2)[0].save(Path(d) / "real.npz")))
            base = ("look_again", "safe_path_v2")
            full, _, _ = E.build_perturbation(spec, 1, "full", base=base)
            allo, _, _ = E.build_perturbation(spec, 1, "oracle_all", base=base)
        self.assertEqual(allo["demo_plan"], full["demo_plan"])          # real demo: no retargeting oracle
        syn = E.parse_demo_spec("synthetic:0")
        a, _, ref = E.build_perturbation(syn, 1, "oracle_all", base=base)
        self.assertEqual(a["demo_plan"].get("safe_projected"), "v2")      # clean plan, still projected


class StyleGap(unittest.TestCase):
    def test_sign_and_pairing(self):
        from transfergap.sim.demo_budget import style_gap
        a = [{"seed": s, "style": {"path_rmse_mean_m": 0.05}} for s in range(10)]
        b = [{"seed": s, "style": {"path_rmse_mean_m": 0.03}} for s in range(10)] + [{"seed": 99, "style": None}]
        g = style_gap(a, b)
        self.assertAlmostEqual(g["mean"], 0.02)
        self.assertEqual(g["n"], 10)


if __name__ == "__main__":
    unittest.main()
