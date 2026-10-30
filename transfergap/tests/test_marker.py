import unittest

import numpy as np

try:
    import cv2
    HAVE = hasattr(cv2, "aruco")
except Exception:
    HAVE = False


@unittest.skipUnless(HAVE, "OpenCV with aruco not installed in this environment")
class MarkerTests(unittest.TestCase):
    def _render(self, size_m=0.12, w=1280, h=720):
        """Synthetic camera looking down at a table with a marker: returns (frame, K, rvec, tvec) with ground truth."""
        from transfergap.human import marker as M
        K = M.camera_matrix(w, h, 70.0)
        rvec = np.array([np.radians(150.0), 0.0, 0.0])               # looking down-forward at the table
        R, _ = cv2.Rodrigues(rvec)
        tvec = np.array([0.05, -0.04, 0.9])
        d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        side = 400
        img = cv2.aruco.generateImageMarker(d, 0, side)
        img = cv2.copyMakeBorder(img, 60, 60, 60, 60, cv2.BORDER_CONSTANT, value=255)
        hh = size_m / 2
        obj = np.array([[-hh, hh, 0], [hh, hh, 0], [hh, -hh, 0], [-hh, -hh, 0]], float)
        px, _ = cv2.projectPoints(obj, rvec, tvec, K, None)
        src = np.array([[60, 60], [60 + side, 60], [60 + side, 60 + side], [60, 60 + side]], np.float32)
        H = cv2.getPerspectiveTransform(src, px.reshape(4, 2).astype(np.float32))
        frame = cv2.warpPerspective(img, H, (w, h), borderValue=200)
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR), K, rvec, tvec

    def test_pose_and_metric_positions_are_recovered(self):
        from transfergap.human import marker as M
        frame, K, rvec, tvec = self._render()
        c = M.detect(frame)
        self.assertIsNotNone(c)
        r, t, err = M.pose(c, 0.12, K)
        self.assertLess(err, 1.0)
        np.testing.assert_allclose(t.ravel(), tvec, atol=0.01)
        # a table point 20 cm right and 10 cm up the marker's axes, projected and recovered
        pts = np.array([[0.20, 0.10, 0.0], [-0.15, 0.05, 0.0]])
        px, _ = cv2.projectPoints(pts, rvec, tvec, K, None)
        got = M.pixel_to_table(px.reshape(-1, 2), r, t, K, z=0.0)
        np.testing.assert_allclose(got, pts[:, :2], atol=0.01)                 # within 1 cm on a synthetic frame

    def test_height_matters_and_is_modelled(self):
        from transfergap.human import marker as M
        frame, K, rvec, tvec = self._render()
        r, t, _ = M.pose(M.detect(frame), 0.12, K)
        p3 = np.array([[0.10, 0.10, 0.05]])                                     # a point 5 cm above the table
        px, _ = cv2.projectPoints(p3, rvec, tvec, K, None)
        right = M.pixel_to_table(px.reshape(-1, 2), r, t, K, z=0.05)
        wrong = M.pixel_to_table(px.reshape(-1, 2), r, t, K, z=0.0)
        self.assertLess(np.linalg.norm(right - p3[:, :2]), 0.01)
        self.assertGreater(np.linalg.norm(wrong - p3[:, :2]), 0.02)             # ignoring the height gives a visibly wrong place

    def test_sheet_has_the_requested_physical_size(self):
        import tempfile
        from pathlib import Path
        from transfergap.human import marker as M
        with tempfile.TemporaryDirectory() as t:
            info = M.make_sheet(Path(t) / "s.png", 0.12, dpi=300)
            self.assertAlmostEqual(info["side_px"] / 300 * 25.4, 120.0, delta=0.1)       # 12.0 cm at 300 dpi
            page = cv2.imread(str(Path(t) / "s.png"), 0)
            self.assertIsNotNone(M.detect(cv2.cvtColor(page, cv2.COLOR_GRAY2BGR)))

    def test_twin_from_video_recovers_positions_and_checks_against_tape(self):
        import tempfile
        from pathlib import Path
        from transfergap.human import marker as M
        from transfergap.human import twin_from_video as TV
        from transfergap.human.analyze import hand_idx
        frame, K, rvec, tvec = self._render()
        obj_h = 0.03
        o3 = np.array([0.20, 0.10, obj_h / 2])                     # grasp point: object middle
        t3 = np.array([-0.12, 0.05, 0.004 + obj_h / 2])            # release point: resting on the target floor
        T = 40
        kp = np.zeros((T, 133, 2))
        h = hand_idx("Right")
        for frame_i, p3 in ((10, o3), (30, t3)):
            px, _ = cv2.projectPoints(p3[None], rvec, tvec, K, None)
            kp[frame_i, h["thumb_tip"]] = px.reshape(2)
            kp[frame_i, h["index_tip"]] = px.reshape(2)
        with tempfile.TemporaryDirectory() as d:
            vid = str(Path(d) / "v.mp4")
            w = cv2.VideoWriter(vid, cv2.VideoWriter_fourcc(*"mp4v"), 25, (frame.shape[1], frame.shape[0]))
            for _ in range(3):
                w.write(frame)
            w.release()
            np.savez(Path(d) / "p.npz", kp2d=kp, fps=25.0)
            dist = float(np.linalg.norm(o3[:2] - t3[:2]))
            twin, chk = TV.build_twin(vid, Path(d) / "p.npz", (10, 30), 0, 0.12, [0.06, 0.04, obj_h], [0.12, 0.10], 0.06, tape_distance_m=dist)
        np.testing.assert_allclose(twin["object"]["xy_m"], o3[:2], atol=0.015)
        np.testing.assert_allclose(twin["target"]["xy_m"], t3[:2], atol=0.015)
        self.assertLess(abs(chk["video_vs_tape_pct"]), 5.0)


if __name__ == "__main__":
    unittest.main()
