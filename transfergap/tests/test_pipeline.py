import tempfile
import unittest
from pathlib import Path

import numpy as np

from transfergap import pipeline
from transfergap.demo import synthetic


def _demo():
    d = synthetic.make_demo(0)
    return d[0] if isinstance(d, tuple) else d


class PipelineTests(unittest.TestCase):
    def test_plausible_demo_passes(self):
        self.assertEqual(pipeline.plausibility(_demo()), [])

    def test_garbage_pose_is_flagged(self):
        d = _demo()
        d.pinch = d.pinch * 20.0               # metres-wide path, as RTMW3D gives on internet clips
        self.assertTrue(pipeline.plausibility(d))

    def test_nan_is_flagged(self):
        d = _demo()
        d.pinch = d.pinch.copy()
        d.pinch[3, 0] = np.nan
        self.assertIn("non-finite pinch/aperture", pipeline.plausibility(d))

    def test_missing_pose_interpreter_reports_failed_stage(self):
        with tempfile.TemporaryDirectory() as t:
            a = pipeline.argparse.Namespace(video="x.mp4", joints=None, out=t, robots=["ur5e"], side="Right",
                                            window=None, events=None, object_height="hand_at_grasp",
                                            fixes=pipeline.DEFAULT_FIXES, pose_python=None, shoulder_width_m=0.40, scene=None, scale_from="shoulder")
            import os
            os.environ.pop("TG_POSE_PY", None)
            rep = pipeline.run(a)
            self.assertFalse(rep["ok"])
            self.assertEqual(rep["stages"]["perceive"]["status"], "FAILED")
            self.assertTrue(rep["stages"]["demo"]["status"].startswith("skipped"))
            self.assertTrue((Path(t) / "REPORT.md").exists())


if __name__ == "__main__":
    unittest.main()
