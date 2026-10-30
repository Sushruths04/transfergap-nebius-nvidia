"""Tests for the 2026-10-29 additions: wrist-yaw retargeting, online fingertip IK, LeRobot export. Skipped parts need runs/allegro (not in git)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "live"))
sys.path.insert(0, str(ROOT))


def _hand(yaw, ap=0.05):
    j = {k: np.zeros(3) for k in ("LeftLeg", "RightLeg", "RightHandIndexEnd", "RightHandThumbEnd")}
    j["LeftLeg"], j["RightLeg"] = np.array([0, 0.1, 0.0]), np.array([0, -0.1, 0.0])
    j["RightHandIndexEnd"] = np.array([np.cos(yaw), np.sin(yaw), 0.0]) * ap
    return j


def test_pinch_yaw_recovers_angle_and_wraps():
    import arm_live as A
    for deg in (0, 30, 60, -45):
        assert np.degrees(A.pinch_yaw(_hand(np.radians(deg)), "Right")) == pytest.approx(deg, abs=1e-6)
    assert np.degrees(A.pinch_yaw(_hand(np.radians(120)), "Right")) == pytest.approx(-60, abs=1e-6)   # half-turn symmetry of the gripper
    assert A.pinch_yaw(_hand(0.3, ap=0.01), "Right") is None                                          # too close: direction unreliable


def test_ik_closing_axis_follows_yaw():
    import arm_live as A
    sim = A.ArmSim("ur5e")
    for deg in (0, 40, -40):
        sim.q = np.array(sim.s.home_q, float)
        for _ in range(25):
            sim.ik_step(np.array([0.45, 0.0, 0.15]), yaw=np.radians(deg))
        p, R = sim.tool(sim.ik)
        assert np.degrees(np.arctan2(R[1, 1], R[0, 1])) == pytest.approx(deg, abs=0.5)
        assert np.linalg.norm(p - [0.45, 0, 0.15]) < 0.005


ALLEGRO = ROOT / "runs" / "allegro" / "scene_right.xml"


@pytest.mark.skipif(not ALLEGRO.exists(), reason="Allegro model not fetched")
def test_hand_ik_rigid_frame_invariance_and_limits():
    from hand_ik import HandIK
    rng = np.random.default_rng(0)
    # a plausible straight hand: wrist at 0, finger bases along +y, fingers along +x
    P = np.zeros((21, 3))
    for f, b in enumerate((1, 5, 9, 13, 17)):
        base = np.array([0.08, 0.03 * (f - 2), 0.0])
        for k in range(4):
            P[b + k] = base + np.array([0.03 * k, 0, 0])
    q, e = HandIK(str(ALLEGRO)).step(P)
    A = rng.normal(size=(3, 3))
    Q, _ = np.linalg.qr(A)
    Q *= np.sign(np.linalg.det(Q))
    q2, e2 = HandIK(str(ALLEGRO)).step(P @ Q.T + 0.3)
    assert np.allclose(q, q2, atol=1e-6)                      # any rigid motion of the input gives the same finger shape
    ik = HandIK(str(ALLEGRO))
    assert q.shape == (16,) and np.all(np.abs(q) < 3.2)


def test_to_lerobot_writes_only_successes(tmp_path):
    pa = pytest.importorskip("pyarrow")
    sys.path.insert(0, str(ROOT / "scripts"))
    import to_lerobot
    src = tmp_path / "src"
    src.mkdir()
    tr = [{"t": i * 0.01, "q": [0.0] * 6, "ctrl": [0.0] * 7, "phase": "reach"} for i in range(100)]
    eps = []
    for n, ok in (("a", True), ("b", False)):
        (src / f"ur5e_{n}.json").write_text(json.dumps({"trace": tr}))
        eps.append({"name": f"ur5e_{n}", "robot": "ur5e", "seed": 1, "success": ok})
    (src / "index.json").write_text(json.dumps({"demo": "d", "episodes": eps}))
    to_lerobot.main(str(src), str(tmp_path / "out"), 25)
    info = json.loads((tmp_path / "out" / "meta" / "info.json").read_text())
    assert info["total_episodes"] == 1 and info["fps"] == 25 and info["total_frames"] == 25
