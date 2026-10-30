"""VR 3-point streamer (g1/stream_vr3.py): hand closure mapping, privacy of its inputs, key-frame conversion."""
import ast
import os
import sys
import unittest
from pathlib import Path

import numpy as np

G1 = Path(__file__).resolve().parents[1] / "g1"
sys.path.insert(0, str(G1))

SONIC = Path(os.environ.get("SONIC_ROOT", "~/GR00T-WholeBodyControl")).expanduser()
try:
    sys.path.insert(0, str(SONIC))
    import gear_sonic.data.robot_model.instantiation.g1  # noqa: F401
    HAVE_SONIC = True
except Exception:
    HAVE_SONIC = False

try:
    import stream_vr3  # noqa: E402
except ModuleNotFoundError as e:                      # pyzmq lives in the SONIC sim venv, not in every environment
    raise unittest.SkipTest(f"needs {e.name} (present in the SONIC sim environment)")


class Closure(unittest.TestCase):
    def test_open_closed_and_pregrasp(self):
        closed = np.array([-0.0, -0.7, -0.7, 1.0, 1.5, 1.0, 1.5])
        self.assertAlmostEqual(float(stream_vr3.closure(np.zeros(7))), 0.0)
        self.assertAlmostEqual(float(stream_vr3.closure(closed)), 1.0)
        pregrasp = np.array([0.0, 0.6, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.assertLess(float(stream_vr3.closure(pregrasp)), 0.3)

    def test_clipped_to_unit_interval(self):
        self.assertEqual(float(stream_vr3.closure(np.full(7, 5.0))), 1.0)
        self.assertEqual(float(stream_vr3.closure(np.full(7, -5.0))), 0.0)


class Inputs(unittest.TestCase):
    def test_reads_only_the_plan_and_signal_files(self):
        src = (G1 / "stream_vr3.py").read_text()
        tree = ast.parse(src)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
                {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
               {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        for bad in ("object_xyz", "block", "episode", "contact", "success", "score", "qpos", "xpos"):
            self.assertFalse([n for n in names if bad in n.lower()], bad)
        self.assertFalse({m for m in mods if m in {"sim_runner", "score", "metrics", "mujoco"}})


@unittest.skipUnless(HAVE_SONIC, "needs the upstream GR00T-WholeBodyControl checkout (SONIC_ROOT)")
class KeyFrames(unittest.TestCase):
    def test_shapes_unit_quaternions_and_fixed_left_arm(self):
        n = 5
        jp = np.zeros((n, 29), np.float32)
        jp[:, 22 - 11 + 0] = np.linspace(0, 0.3, n)            # move some right-arm joint a little
        pos, ori = stream_vr3.key_frames({"joint_pos": jp}, SONIC)
        self.assertEqual(pos.shape, (n, 3, 3))
        self.assertEqual(ori.shape, (n, 3, 4))
        self.assertTrue(np.allclose(np.linalg.norm(ori, axis=2), 1.0, atol=1e-6))
        self.assertTrue(np.allclose(pos[:, 0], pos[0, 0]))       # left arm held
        self.assertTrue(np.allclose(pos[:, 2], [0.0, 0.0, 0.40]))  # neck upright


if __name__ == "__main__":
    unittest.main()
