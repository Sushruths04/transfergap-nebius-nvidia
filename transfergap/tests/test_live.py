import json
import sys
import time
import unittest
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "live"))


def soma(p):            # demo-frame point -> SOMA y-up (inverse of demo.gemx.soma_to_demo_frame)
    x, y, z = p
    return [x, z, -y]


def frame(hand_fwd=0.3, hand_up=0.0, aperture=0.08):
    J = {"Hips": [0, 0, 1.0], "Chest": [0, 0, 1.3], "Head": [0, 0, 1.7], "LeftLeg": [0, 0.1, 0.95],
         "RightLeg": [0, -0.1, 0.95], "LeftArm": [0, 0.2, 1.45], "RightArm": [0, -0.2, 1.45], "LeftHand": [0, 0.25, 0.9]}
    pinch = np.array([hand_fwd, -0.2, 1.2 + hand_up])
    J["RightHand"] = pinch.tolist()
    J["RightHandThumbEnd"] = (pinch + [0, aperture / 2, 0]).tolist()
    J["RightHandIndexEnd"] = (pinch - [0, aperture / 2, 0]).tolist()
    return {"joints": {k: soma(v) for k, v in J.items()}, "t_cap": time.time()}


class LiveTest(unittest.TestCase):
    def test_calibrated_neutral_maps_to_ready_and_moves_with_the_hand(self):
        from arm_live import READY, LiveHand
        h = LiveHand(gain=1.0, calib_s=0.0, alpha=1.0)
        for _ in range(5):
            h.update(frame())
        self.assertIsNotNone(h.neutral)
        h.update(frame())
        np.testing.assert_allclose(h.target, READY, atol=1e-9)
        h.update(frame(hand_fwd=0.4, hand_up=0.1))          # hand 10 cm forward and 10 cm up
        np.testing.assert_allclose(h.target, READY + [0.1, 0.0, 0.1], atol=1e-9)
        self.assertFalse(h.closed)
        h.update(frame(aperture=0.02))
        self.assertTrue(h.closed)
        h.update(frame(aperture=0.05))                        # hysteresis: stays closed until > 6 cm
        self.assertTrue(h.closed)

    def test_guided_calibration_maps_the_touch_point_to_the_block(self):
        import arm_live
        arm_live.COUNTDOWN_S, arm_live.CAPTURE_S = 0.0, 0.0
        h = arm_live.LiveHand(gain=0.8, alpha=1.0, auto=False)
        h.update(frame())
        self.assertIsNone(h.neutral)                               # no auto-calibration
        h.request("neutral")
        h.update(frame(hand_fwd=0.0, hand_up=-0.45))               # hand 20 cm forward of... arms hanging
        h.update(frame(hand_fwd=0.0, hand_up=-0.45))
        self.assertIsNotNone(h.neutral, h.msg)
        h.request("table")
        h.update(frame(hand_fwd=0.4, hand_up=-0.2))                # touching the object
        h.update(frame(hand_fwd=0.4, hand_up=-0.2))
        self.assertIsNotNone(h.anchor, h.msg)
        h.update(frame(hand_fwd=0.4, hand_up=-0.2))
        np.testing.assert_allclose(h.target, arm_live.BLOCK, atol=0.03)   # soft clip only bends near the limits
        bad = arm_live.LiveHand(auto=False)
        bad.update(frame())
        bad.request("neutral")
        bad.update(frame(hand_fwd=0.4, hand_up=0.0))               # arm held forward: rejected
        bad.update(frame(hand_fwd=0.4, hand_up=0.0))
        self.assertIsNone(bad.neutral)

    def test_hub_serves_latest_json(self):
        from hub import Hub
        hub = Hub(0)
        port = hub.server.server_address[1]
        hub.put_json("status", {"a": 1})
        hub.put_json("status", {"a": 2})
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/status.json", timeout=5) as r:
            self.assertEqual(json.loads(r.read()), {"a": 2})
        hub.server.shutdown()


if __name__ == "__main__":
    unittest.main()
