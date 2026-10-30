import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import record_clip as R  # noqa: E402


class RecordClipTests(unittest.TestCase):
    def test_a_21fps_camera_becomes_constant_30fps(self):
        t = np.arange(0, 2.0, 1 / 21.4)                       # the first clip's rate
        pick = R.resample_to_cfr(t, 30.0)
        self.assertAlmostEqual(len(pick) / 30.0, t[-1], delta=0.05)         # same duration
        self.assertTrue((np.diff(pick) >= 0).all())                          # never goes back in time
        self.assertTrue((np.diff(pick) <= 1).all())                          # no skipped source frame at a lower source rate
        self.assertAlmostEqual(R.achieved_fps(t), 21.4, delta=0.1)

    def test_a_30fps_camera_is_passed_through(self):
        t = np.arange(0, 1.0, 1 / 30)
        np.testing.assert_array_equal(R.resample_to_cfr(t, 30.0), np.arange(len(t)))


if __name__ == "__main__":
    unittest.main()
