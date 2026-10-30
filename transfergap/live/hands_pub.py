"""Real-time mode, GPU-VM side: camera -> GEM-X live (upstream webcam_stream.GemWebcamStreamer) -> per-frame SOMA
joints -> hub channels for the robot listeners (and optionally the upstream SMPL v3 stream to SONIC for the G1).

    # on the VM, from the GEM-X root (relative inputs/soma_assets, see OVERVIEW §6), GEM-X venv:
    python ~/transfergap_g1/live/hands_pub.py --source http://127.0.0.1:8090/stream.mjpg \
        --upstream ~/GR00T-WholeBodyControl/gear_sonic/examples/live_camera_teleop --port 8092 [--stream-sonic]
    # CPU test without GEM-X: replay exported joints at their own fps
    python live/hands_pub.py --replay runs/demos/pexels_8135753_joints.npz --port 8092

Channels (live/hub.py): hands.jsonl / hands.json = {"seq", "t_cap" (wall time the frame was read), "t_pub",
"frame": "soma_world_y_up", "joints": {name: [x, y, z]} for JOINTS}; cam.mjpg = camera frame with the 2D keypoints.
SOMA forward pass on live params: live params carry no translation, so a zero translation is passed (the layer
requires one; found in the first VM rehearsal 2026-10-02).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub import Hub  # noqa: E402

JOINTS = ["Hips", "Chest", "Neck1", "Head", "LeftLeg", "RightLeg", "LeftShoulder", "RightShoulder", "LeftArm",
          "RightArm", "LeftForeArm", "RightForeArm", "LeftHand", "RightHand",
          "LeftHandThumbEnd", "LeftHandIndexEnd", "RightHandThumbEnd", "RightHandIndexEnd",
          "LeftHandIndex1", "LeftHandMiddle1", "LeftHandPinky1", "RightHandIndex1", "RightHandMiddle1",
          "RightHandPinky1"]                      # wrist/neck frames for the G1 3-point bridge (live/g1_vr3pt.py)


def replay(path, hub, fps=None, loop=True):
    z = np.load(path, allow_pickle=False)
    names = [str(n) for n in z["joint_names"]]
    J, dt = z["joints"], 1.0 / float(fps or z["fps"])
    if all(n in names for n in JOINTS):
        idx = [names.index(n) for n in JOINTS]
        pick = lambda f: {n: J[f, i].tolist() for n, i in zip(JOINTS, idx)}
    else:            # an RTMW3D export (133 COCO-WholeBody points): build the same 24 joints as live_rtmw3d does
        pick = lambda f: {n: J[f][ix].mean(0).tolist() for n, ix in WB.items()}
    seq = 0
    while True:
        for f in range(len(J)):
            t0 = time.time()
            hub.put_json("hands", {"seq": seq, "t_cap": t0, "t_pub": time.time(), "frame": "soma_world_y_up",
                                   "source": f"replay:{Path(path).name}:{f}", "joints": pick(f)})
            seq += 1
            time.sleep(max(0.0, dt - (time.time() - t0)))
        if not loop:
            return


class LatestFrame:
    """Reads the camera stream in a background thread and keeps ONLY the newest frame. GEM-X runs at ~10 fps, slower
    than the camera, so reading frames in order lets a queue build up inside the video reader and the pose (and the
    robots) fall further and further behind the person (seen in the 2026-10-02 live session). t_cap = arrival time."""

    def __init__(self, opener, source):
        import threading
        self.opener, self.source = opener, source
        self.cap = opener(source)
        self.size = (int(self.cap.get(3)) or 640, int(self.cap.get(4)) or 480)
        self.frame, self.t, self.seen, self.ended = None, 0.0, 0, False
        self.lock = threading.Lock()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        n = 0
        while True:
            ok, f = self.cap.read()
            if not ok:
                if not self.source.startswith("http"):
                    self.ended = True
                    return
                time.sleep(0.5)                    # camera server restarted / tunnel hiccup: reconnect
                self.cap.release()
                self.cap = self.opener(self.source) if _reachable(self.source) else self.cap
                continue
            n += 1
            with self.lock:
                self.frame, self.t, self.n = f, time.time(), n

    def latest(self):
        with self.lock:
            if self.frame is None or getattr(self, "n", 0) == self.seen:
                return False, None, 0.0
            self.seen = self.n
            return True, self.frame, self.t


def _reachable(url):
    import urllib.request
    try:
        urllib.request.urlopen(url, timeout=1).close()
        return True
    except Exception:
        return False


def draw_skeleton(bgr, kp2d, tracking, width=480, conf=0.4):
    """GEM-X's 77-joint 2D skeleton (bones + joints, part colours as gem/utils/kp2d_utils.py), downscaled."""
    import cv2
    from gem.utils.kp2d_utils import _JOINT_GROUP_77, _PART_COLORS_77, PARENTS_77
    sc = width / bgr.shape[1]
    vis = cv2.resize(bgr, (width, int(bgr.shape[0] * sc)))
    k = kp2d.numpy() if hasattr(kp2d, "numpy") else np.asarray(kp2d)
    pts = [(int(x * sc), int(y * sc), c) for x, y, c in k]
    for j, par in enumerate(PARENTS_77):
        if par >= 0 and pts[j][2] > conf and pts[par][2] > conf:
            hand = "hand" in _JOINT_GROUP_77[j]
            cv2.line(vis, pts[j][:2], pts[par][:2], _PART_COLORS_77[_JOINT_GROUP_77[j]], 1 if hand else 2, cv2.LINE_AA)
    for j, (x, y, c) in enumerate(pts):
        if c > conf:
            cv2.circle(vis, (x, y), 1 if "hand" in _JOINT_GROUP_77[j] else 3, _PART_COLORS_77[_JOINT_GROUP_77[j]], -1)
    cv2.putText(vis, "tracking" if tracking else "warming up / no person", (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (255, 255, 255), 1, cv2.LINE_AA)
    return vis


# COCO-WholeBody (133) indices -> the joint names used by the live retargeting (arm_live, g1_vr3pt)
WB = {"Head": [0], "LeftShoulder": [5], "RightShoulder": [6], "LeftArm": [5], "RightArm": [6], "LeftForeArm": [7],
      "RightForeArm": [8], "LeftHand": [9], "RightHand": [10], "LeftLeg": [11], "RightLeg": [12], "Hips": [11, 12],
      "Chest": [5, 6], "Neck1": [5, 6], "LeftHandThumbEnd": [95], "LeftHandIndexEnd": [99], "LeftHandIndex1": [96],
      "LeftHandMiddle1": [100], "LeftHandPinky1": [108], "RightHandThumbEnd": [116], "RightHandIndexEnd": [120],
      "RightHandIndex1": [117], "RightHandMiddle1": [121], "RightHandPinky1": [129]}
WB_BONES = [(5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)] + \
    [(b, b + k) for b in (91, 112) for k in (1, 5, 9, 13, 17)] + \
    [(b + k, b + k + 1) for b in (91, 112) for f in (1, 5, 9, 13, 17) for k in range(f, f + 3)]

FINGERS = ("thumb", "index", "middle", "ring", "pinky")


def hand_detail(soma, base):
    """All 21 hand keypoints of one hand (COCO-WholeBody: wrist then 4 per finger) and per-finger bend angles in degrees
    (180 = straight finger, smaller = more curled), from the joint angles at the two interior joints of each finger."""
    P = soma[base:base + 21]
    out = {}
    for f, name in enumerate(FINGERS):
        def ang(u, v, w):
            x, y = u - v, w - v
            return float(np.degrees(np.arccos(np.clip(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-9), -1, 1))))
        out[name] = [round(ang(P[1 + 4 * f], P[2 + 4 * f], P[3 + 4 * f]), 1), round(ang(P[2 + 4 * f], P[3 + 4 * f], P[4 + 4 * f]), 1)]
    return {"kp": np.round(P, 4).tolist(), "bend": out}


def live_rtmw3d(a, hub):
    """Real-time variant with RTMW3D (OpenMMLab, ~27 fps on the L40S; see results/pose_estimator_bakeoff_v3: as
    good as GEM-X on a static full-body camera, unusable on occluded in-the-wild video). Per-frame, no SMPL stream."""
    import cv2
    from rtmpose3d import RTMPose3D
    model = RTMPose3D.from_pretrained("rbarac/rtmpose3d", device="cuda:0")
    grab = LatestFrame(lambda s: cv2.VideoCapture(s), a.source)
    seq, t_last, fps, prev = 0, time.time(), 0.0, None
    while True:
        ok, bgr, t_cap = grab.latest()
        if not ok:
            if grab.ended:
                break
            time.sleep(0.003)
            continue
        r = model(bgr, return_tensors="np")
        k3, k2, bb = (np.asarray(r.get(k, [])) for k in ("keypoints_3d", "keypoints_2d", "bboxes"))
        vis = cv2.resize(bgr, (480, int(bgr.shape[0] * 480 / bgr.shape[1])))
        sc = 480 / bgr.shape[1]
        if k3.size:
            cen = (bb[:, :2] + bb[:, 2:4]) / 2
            i = int(np.argmax((bb[:, 2] - bb[:, 0]) * (bb[:, 3] - bb[:, 1]))) if prev is None else \
                int(np.argmin(np.linalg.norm(cen - prev, axis=1)))
            prev = cen[i]
            K = k3[i]
            soma = np.stack([K[:, 0], K[:, 2], -K[:, 1]], -1)          # camera z-up -> SOMA y-up convention
            now = time.time()
            fps = 0.9 * fps + 0.1 / max(now - t_last, 1e-6)
            t_last = now
            hub.put_json("hands", {"seq": seq, "t_cap": t_cap, "t_pub": now, "frame": "soma_world_y_up",
                                   "fps": round(fps, 2), "estimator": "rtmw3d",
                                   "joints": {n: soma[idx].mean(0).tolist() for n, idx in WB.items()},
                                   "hands_detail": {"Left": hand_detail(soma, 91), "Right": hand_detail(soma, 112)}})
            seq += 1
            for u, v in WB_BONES:
                cv2.line(vis, tuple(int(c * sc) for c in k2[i][u]), tuple(int(c * sc) for c in k2[i][v]),
                         (0, 200, 255) if u < 91 else (130, 255, 130), 2, cv2.LINE_AA)
        cv2.putText(vis, f"RTMW3D {fps:4.1f} fps", (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        hub.put_jpeg("cam", vis[..., ::-1])
        print(f"\r[hands_pub/rtmw3d] {seq} poses | {fps:4.1f} fps", end="", flush=True)


def soma_names(assets):
    for npz in Path(assets).rglob("SOMA_neutral.npz"):
        z = np.load(npz)
        key = next((k for k in z.files if k.endswith("joint_names")), None)
        if key is not None:
            names = [str(n) for n in z[key]]
            return names[1:] if names[0] == "Root" else names
    raise SystemExit(f"no SOMA joint names under {assets}")


def live(a, hub):
    import torch
    sys.path.insert(0, str(Path(a.upstream).expanduser()))
    import webcam_stream as ws                    # upstream module; adds GEM-X to sys.path via --gemx-root/$GEMX_ROOT
    from gem.utils.soma_utils.soma_layer import SomaLayer
    assets = str(Path(a.gemx_root).expanduser() / "inputs" / "soma_assets")
    soma = SomaLayer(data_root=assets, low_lod=True, device="cuda", identity_model_type="mhr", mode="warp")
    names = soma_names(assets)
    idx = [names.index(n) for n in JOINTS]
    conv = pub = None
    if a.stream_sonic:
        from soma_to_smpl import SomaToSmpl, SonicV3Publisher
        conv = SomaToSmpl(soma, device="cuda", smooth=a.smooth, sonic_root=a.sonic_root)
        pub = SonicV3Publisher(port=a.sonic_port, sonic_root=a.sonic_root)
    grab = LatestFrame(ws._open_source, a.source)
    W, H = grab.size
    streamer = ws.GemWebcamStreamer(str(Path(a.gemx_root).expanduser()), window=a.window, no_imgfeat=True)
    seq, t_last, fps = 0, time.time(), 0.0
    while True:
        ok, bgr, t_cap = grab.latest()             # newest frame only: never process a queued, stale frame
        if not ok:
            if grab.ended:
                break
            time.sleep(0.005)
            continue
        kp2d, params = streamer.process_frame(bgr[..., ::-1].copy(), W, H, decode=True)
        if params is not None:
            p = {k: v[None].float().cuda() for k, v in params.items()}
            with torch.no_grad():                # live params carry no translation; the layer needs one
                out = soma(**p, transl=torch.zeros(1, 3, device="cuda"))
            j = out["joints"][0].cpu().numpy()
            if pub is not None:
                pub.publish(conv.convert(params))
            now = time.time()
            fps = 0.9 * fps + 0.1 / max(now - t_last, 1e-6)
            t_last = now
            hub.put_json("hands", {"seq": seq, "t_cap": t_cap, "t_pub": now, "frame": "soma_world_y_up",
                                   "fps": round(fps, 2), "joints": {n: j[i].tolist() for n, i in zip(JOINTS, idx)}})
            seq += 1
        hub.put_jpeg("cam", draw_skeleton(bgr, kp2d, params is not None)[..., ::-1])
        print(f"\r[hands_pub] {seq} poses | {fps:4.1f} fps", end="", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8092)
    ap.add_argument("--estimator", default="gemx", choices=["gemx", "rtmw3d"])
    ap.add_argument("--replay", help="exported joints .npz (CPU test, no GEM-X)")
    ap.add_argument("--replay-once", action="store_true", help="play the replay once and exit (default: loop)")
    ap.add_argument("--replay-fps", type=float, default=None)
    ap.add_argument("--source", default="http://127.0.0.1:8090/stream.mjpg")
    ap.add_argument("--gemx-root", default=".", help="GEM-X repo root (run from it)")
    ap.add_argument("--upstream", default="~/GR00T-WholeBodyControl/gear_sonic/examples/live_camera_teleop")
    ap.add_argument("--window", type=int, default=30)
    ap.add_argument("--stream-sonic", action="store_true", help="also publish SMPL v3 to SONIC (G1)")
    ap.add_argument("--sonic-port", type=int, default=5556)
    ap.add_argument("--sonic-root", default=None)
    ap.add_argument("--smooth", type=float, default=0.75)
    a = ap.parse_args()
    if not a.replay and a.estimator == "gemx":     # upstream module reads --gemx-root from argv at import
        sys.argv += ["--gemx-root", str(Path(a.gemx_root).expanduser())] if "--gemx-root" not in sys.argv else []
    hub = Hub(a.port)
    print(f"[hands_pub] hub on http://127.0.0.1:{a.port}/hands.jsonl", flush=True)
    if a.replay:
        replay(a.replay, hub, a.replay_fps, loop=not a.replay_once)
    elif a.estimator == "rtmw3d":
        live_rtmw3d(a, hub)
    else:
        live(a, hub)


if __name__ == "__main__":
    main()
