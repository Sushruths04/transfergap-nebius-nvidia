"""Metric scale and table plane from a printed marker: the measurement that replaces the assumed shoulder width.

Put a printed ArUco marker of KNOWN size flat on the table in the video (print `python -m transfergap.human.marker sheet`; check the printed black square
with a ruler). From one frame this gives the table plane and the camera pose relative to it, so any image point that lies on (or at a known height above)
the table becomes a metric position in the TABLE FRAME (origin = marker centre, x along the marker's right edge, y along its up edge, z up).

    python -m transfergap.human.marker sheet --out marker_sheet.png [--size-cm 12]       # printable A4 page
    python -m transfergap.human.marker detect --video clip.mp4 [--frame 0] [--size-cm 12] [--hfov 70]

What it does NOT do: it does not know the camera lens. Without calibrated intrinsics (`--intrinsics K.json`, a 3x3 matrix) it assumes a horizontal field of view
(default 70 degrees, a typical webcam/phone value) and says so; the metric error then depends on how wrong that guess is (reported by `reprojection_px` and,
if you also tape-measure two marker-to-object distances, checkable). Positions of points above the table plane need their height: the ray is intersected with
the plane at that height, so a wrong height shifts the point along the viewing direction.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

DICT = "DICT_4X4_50"


def _cv():
    import cv2
    return cv2


def make_sheet(out, size_m=0.12, marker_id=0, dpi=300, paper_mm=(210.0, 297.0)):
    """Printable A4 page: one marker whose black square is exactly size_m on paper at 100% scale, a 10 cm check bar and instructions."""
    cv2 = _cv()
    W, H = (int(round(m / 25.4 * dpi)) for m in paper_mm)
    page = np.full((H, W), 255, np.uint8)
    side = int(round(size_m / 0.0254 * dpi))
    d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT))
    bits = cv2.aruco.generateImageMarker(d, marker_id, side)          # the black border is part of `side`
    x0, y0 = (W - side) // 2, int(0.18 * H)
    page[y0:y0 + side, x0:x0 + side] = bits
    bar = int(round(0.10 / 0.0254 * dpi))
    yb = y0 + side + int(0.06 * H)
    page[yb:yb + 12, (W - bar) // 2:(W - bar) // 2 + bar] = 0
    for xx in ((W - bar) // 2, (W - bar) // 2 + bar):
        page[yb - 20:yb + 32, xx - 3:xx + 3] = 0
    f = cv2.FONT_HERSHEY_SIMPLEX
    lines = [f"TransferGap scale marker  |  ArUco {DICT} id {marker_id}",
             f"Black square side = {size_m * 100:.1f} cm. Print at 100% / actual size (no 'fit to page').",
             "Check with a ruler: the bar below must measure exactly 10.0 cm and the black square the size above.",
             "Tape it FLAT on the table, in view of the camera, not under the objects. Keep it in the frame for the whole clip."]
    for i, s in enumerate(lines):
        cv2.putText(page, s, (int(0.07 * W), int(0.06 * H) + i * 70), f, 1.1, 0, 2, cv2.LINE_AA)
    cv2.putText(page, "10.0 cm", (W // 2 - 140, yb + 110), f, 1.3, 0, 3, cv2.LINE_AA)
    out = Path(out)
    cv2.imwrite(str(out), page)
    try:
        from PIL import Image
        Image.fromarray(page).save(str(out.with_suffix(".pdf")), resolution=dpi)
    except Exception:
        pass
    return {"png": str(out), "side_px": side, "dpi": dpi, "size_m": size_m}


def camera_matrix(w, h, hfov_deg=70.0, K=None):
    if K is not None:
        return np.asarray(K, float)
    f = (w / 2) / np.tan(np.radians(hfov_deg) / 2)
    return np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])


def detect(frame_bgr, marker_id=0):
    """4x2 corners (px, order: top-left, top-right, bottom-right, bottom-left of the marker) or None."""
    cv2 = _cv()
    d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT))
    det = cv2.aruco.ArucoDetector(d, cv2.aruco.DetectorParameters())
    corners, ids, _ = det.detectMarkers(frame_bgr)
    if ids is None:
        return None
    for c, i in zip(corners, ids.ravel()):
        if int(i) == marker_id:
            return c.reshape(4, 2).astype(float)
    return None


def pose(corners, size_m, K):
    """Camera pose of the marker plane: (rvec, tvec, reprojection error in px). Marker frame: origin at the centre, x right, y up (image), z toward the camera."""
    cv2 = _cv()
    h = size_m / 2
    obj = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], float)
    ok, rvec, tvec = cv2.solvePnP(obj, corners, K, None, flags=cv2.SOLVEPNP_IPPE_SQUARE)
    if not ok:
        raise RuntimeError("solvePnP failed")
    proj, _ = cv2.projectPoints(obj, rvec, tvec, K, None)
    return rvec, tvec, float(np.sqrt(np.mean(np.sum((proj.reshape(4, 2) - corners) ** 2, axis=1))))


def pixel_to_table(px, rvec, tvec, K, z=0.0):
    """Metric table-frame (x, y) of image points whose true height above the table plane is z (m). px: (N,2)."""
    cv2 = _cv()
    R, _ = cv2.Rodrigues(rvec)
    t = np.asarray(tvec, float).reshape(3)
    P = np.atleast_2d(np.asarray(px, float))
    rays = np.linalg.inv(K) @ np.vstack([P.T, np.ones(len(P))])            # camera-frame directions
    n = R[:, 2]                                                             # plane normal in the camera frame
    # points X = s * ray with n . (X - t) = z   (plane through the marker origin, raised by z)
    s = (n @ t + z) / (n @ rays)
    X = (rays * s).T                                                        # camera-frame points
    local = (R.T @ (X - t).T).T                                             # marker frame
    return local[:, :2]


def detect_in_video(video, frame=0, size_m=0.12, hfov=70.0, K=None, marker_id=0):
    cv2 = _cv()
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ok, f = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"cannot read frame {frame}")
    c = detect(f, marker_id)
    if c is None:
        return {"found": False, "frame": frame}
    Km = camera_matrix(f.shape[1], f.shape[0], hfov, K)
    rvec, tvec, err = pose(c, size_m, Km)
    return {"found": True, "frame": frame, "reprojection_px": round(err, 2), "camera_distance_m": round(float(np.linalg.norm(tvec)), 3),
            "marker_px_side": round(float(np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)])), 1),
            "intrinsics": "given" if K is not None else f"ASSUMED horizontal FOV {hfov} deg",
            "rvec": rvec.ravel().tolist(), "tvec": tvec.ravel().tolist(), "K": Km.tolist()}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("--out", required=True)
    s.add_argument("--size-cm", type=float, default=12.0)
    s.add_argument("--id", type=int, default=0)
    d = sub.add_parser("detect")
    d.add_argument("--video", required=True)
    d.add_argument("--frame", type=int, default=0)
    d.add_argument("--size-cm", type=float, default=12.0)
    d.add_argument("--hfov", type=float, default=70.0)
    d.add_argument("--intrinsics")
    a = ap.parse_args()
    if a.cmd == "sheet":
        print(json.dumps(make_sheet(a.out, a.size_cm / 100, a.id), indent=1))
    else:
        K = json.loads(Path(a.intrinsics).read_text()) if a.intrinsics else None
        print(json.dumps(detect_in_video(a.video, a.frame, a.size_cm / 100, a.hfov, K), indent=1))


if __name__ == "__main__":
    main()
