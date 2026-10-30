import json
import os
import tempfile
import unittest

import numpy as np

from transfergap.sim import scene as S
from transfergap.sim import twin as T


def spec(**kw):
    d = {"schema": T.SCHEMA, "name": "synthetic test geometry (not a real scene)", "source": "test",
         "object": {"size_m": [0.06, 0.04, 0.03], "xy_m": [0.0, 0.0]},
         "target": {"inner_size_m": [0.12, 0.10], "wall_height_m": 0.06, "xy_m": [0.26, 0.0]},
         "placement": {"yaw_deg": 90, "anchor_xy_m": [0.45, 0.0]}}
    d.update(kw)
    return d


class TwinTests(unittest.TestCase):
    def test_distance_and_sizes_are_preserved(self):
        tw = T.load(spec())
        self.assertAlmostEqual(float(np.linalg.norm(T.carry_vector(tw))), 0.26, places=9)
        np.testing.assert_allclose(T.box_half_extents(tw), [0.03, 0.02, 0.015])      # long side along x, closing across the short side

    def test_bad_input_is_rejected_with_the_field_name(self):
        with self.assertRaises(ValueError):
            T.load(spec(object={"size_m": [0.06, 0.04], "xy_m": [0, 0]}))
        with self.assertRaises(ValueError):
            T.load(spec(target={"inner_size_m": [0.03, 0.03], "xy_m": [0.2, 0]}))       # smaller than the object
        with self.assertRaises(ValueError):
            T.load({**spec(), "schema": "other"})

    def test_validate_flags_a_box_the_gripper_cannot_close_on(self):
        tw = T.load(spec(object={"size_m": [0.12, 0.10, 0.03], "xy_m": [0.0, 0.0]},
                         target={"inner_size_m": [0.25, 0.22], "wall_height_m": 0.06, "xy_m": [0.30, 0.0]}))
        self.assertTrue(any("gripper opening" in w for w in T.validate(tw, "ur5e")))
        self.assertEqual(T.validate(T.load(spec()), "ur5e"), [])

    def test_scene_builds_the_measured_geometry(self):
        tw = T.load(spec())
        sc = S.Scene(0, "ur5e", twin=tw)
        self.assertAlmostEqual(sc.block_half, 0.015)
        self.assertAlmostEqual(float(np.linalg.norm(sc.goal_xyz[:2] - np.array([0.45, -0.13]))), 0.26, delta=0.011)

    def test_env_twin_applies_and_default_scene_is_unchanged(self):
        base = S.Scene(0, "ur5e")
        self.assertAlmostEqual(float(np.linalg.norm(base.goal_xyz[:2] - S.BLOCK_CENTER)), 0.34, delta=0.045)   # the fixed sim layout
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(spec(), f)
        os.environ["TG_TWIN"] = f.name
        try:
            self.assertAlmostEqual(S.Scene(0, "ur5e").block_half, 0.015)
        finally:
            os.environ.pop("TG_TWIN")
            os.unlink(f.name)
        self.assertAlmostEqual(S.Scene(0, "ur5e").block_half, S.BLOCK_HALF)

    def test_unchanged_controller_places_the_measured_box(self):
        from transfergap.metrics import score_episode
        from transfergap.sim.rollout import run_episode
        tw = T.load(spec())
        import transfergap.sim.rollout as R
        from transfergap.sim import scene
        orig = scene.Scene.__init__
        def patched(self, *a, **k):
            k.setdefault("twin", tw)
            orig(self, *a, **k)
        scene.Scene.__init__ = patched
        try:
            ok = [bool(score_episode(run_episode(s, robot="ur5e"))["success"]) for s in range(2)]
        finally:
            scene.Scene.__init__ = orig
        self.assertEqual(ok, [True, True])


if __name__ == "__main__":
    unittest.main()
