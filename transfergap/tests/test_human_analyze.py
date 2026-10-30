import tempfile
import unittest
from pathlib import Path

import numpy as np

from transfergap.human import analyze as A


def skeleton(T=40, upper=0.30, fore=0.26, elbow_deg=90.0):
    """Synthetic person (SOMA y-up, metres): right arm with a known upper arm, forearm and elbow angle."""
    J = np.zeros((T, 133, 3))
    J[:, A.L_SH], J[:, A.R_SH] = [-0.2, 1.4, 0], [0.2, 1.4, 0]
    J[:, A.L_HIP], J[:, A.R_HIP] = [-0.1, 0.9, 0], [0.1, 0.9, 0]
    J[:, A.R_EL] = J[:, A.R_SH] + [0, -upper, 0]                       # upper arm hangs down
    th = np.radians(elbow_deg)
    # forearm direction making angle elbow_deg with the (elbow -> shoulder) direction (up)
    up = np.array([0, 1.0, 0]); side = np.array([0, 0, 1.0])
    fdir = np.cos(th) * up + np.sin(th) * side
    J[:, A.R_WR] = J[:, A.R_EL] + fore * fdir
    h = A.hand_idx("Right")
    J[:, h["wrist"]] = J[:, A.R_WR]
    J[:, h["middle_mcp"]] = J[:, A.R_WR] + 0.08 * fdir
    J[:, h["middle_tip"]] = J[:, A.R_WR] + 0.18 * fdir
    J[:, h["thumb_tip"]] = J[:, A.R_WR] + [0.0, 0.0, 0.0] + 0.02 * side
    J[:, h["index_tip"]] = J[:, h["thumb_tip"]] + [0.06, 0, 0]
    return J


class HumanAnalyzeTests(unittest.TestCase):
    def test_known_lengths_angle_and_aperture(self):
        M = A.metrics(skeleton(elbow_deg=90.0), 25.0)
        np.testing.assert_allclose(M["upper_arm_m"], 0.30, atol=1e-9)
        np.testing.assert_allclose(M["forearm_m"], 0.26, atol=1e-9)
        np.testing.assert_allclose(M["hand_m"], 0.18, atol=1e-9)
        np.testing.assert_allclose(M["elbow_deg"], 90.0, atol=1e-6)
        np.testing.assert_allclose(M["aperture_m"], 0.06, atol=1e-9)
        np.testing.assert_allclose(M["shoulder_width_m"], 0.4, atol=1e-9)

    def test_elbow_angle_tracks_flexion(self):
        a = A.metrics(skeleton(elbow_deg=60.0), 25.0)["elbow_deg"][0]
        b = A.metrics(skeleton(elbow_deg=120.0), 25.0)["elbow_deg"][0]
        self.assertAlmostEqual(a, 60.0, places=4)
        self.assertAlmostEqual(b, 120.0, places=4)

    def test_hanging_arm_has_zero_shoulder_angle(self):
        M = A.metrics(skeleton(), 25.0)
        np.testing.assert_allclose(M["shoulder_deg"], 0.0, atol=1e-6)

    def test_metric_scale_fixes_an_oversized_skeleton(self):
        J = skeleton() * 2.6                                    # a skeleton that is 2.6x too large, as RTMW3D gives
        s = A.metric_scale(J, 0.40)
        self.assertAlmostEqual(s, 1 / 2.6, places=6)
        M = A.metrics(J * s, 25.0)
        np.testing.assert_allclose(M["upper_arm_m"], 0.30, atol=1e-6)
        np.testing.assert_allclose(M["aperture_m"], 0.06, atol=1e-6)

    def test_summary_and_run_without_video(self):
        with tempfile.TemporaryDirectory() as t:
            J = skeleton()
            np.savez(Path(t) / "p.npz", joints=J, kp2d=np.zeros((40, 133, 2)), fps=25.0)
            s = A.run(Path(t) / "p.npz", Path(t) / "o")
            self.assertAlmostEqual(s["lengths_m"]["upper_arm_m"]["median"], 0.30, places=3)
            self.assertTrue((Path(t) / "o" / "human_analysis.json").exists())


if __name__ == "__main__":
    unittest.main()
