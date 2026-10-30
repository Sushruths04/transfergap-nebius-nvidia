"""Depth-based object estimation for the pick-and-place scene: the robot finds the object and the tray from a depth
image, so the controller no longer needs the block's true pose or size.

Pipeline: simulated depth camera (MuJoCo renderer; optional Gaussian depth noise) -> world point cloud ->
dominant horizontal plane = table -> points above it -> connected components -> per-object centre, size, yaw and
height from the top face -> rule-based selection (a graspable object that fits the gripper; a tray = a large
cluster) -> belief for the controller.

NOT READ HERE (enforced by tests/test_perception.py): the block pose, size or velocity, the goal, contacts, success.
The camera pose and intrinsics come from the model, i.e. they are a perfect calibration (stated, not hidden).
Only the renderer touches simulator state, as a real depth sensor would.

Limits: one fixed camera (overhead by default); objects assumed to rest on the table or on the tray floor; the target
is a cube (selection uses shape: squareness, fill, height ~ width), so a second cube would be ambiguous; the yaw is the
minimum-area-rectangle angle of the top face, wrapped to the cube's 90-degree symmetry.
"""
from __future__ import annotations

from collections import deque

import mujoco
import numpy as np

TOP_BAND_M = 0.006          # top-face points: within this distance of the highest points of an object
MIN_HEIGHT_M = 0.008        # points closer than this to the table plane are table (noise margin)
MAX_HEIGHT_M = 0.30


class DepthSensor:
    """Depth camera on a named model camera. depth in metres along the optical axis; NaN where nothing is hit."""

    def __init__(self, scene, camera="top", size=(480, 640), sigma_m=0.0, seed=0, max_range_m=3.0,
                 min_range_m=0.0, calib_rot_deg=0.0, calib_trans_mm=0.0, dropout=0.0, flying=0.0):
        self.m, self.camera, (self.H, self.W) = scene.model, camera, size
        self.cam_id = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_CAMERA, camera)
        if self.cam_id < 0:
            raise ValueError(f"camera {camera!r} not in the model")
        self.fy = 0.5 * self.H / np.tan(np.deg2rad(self.m.cam_fovy[self.cam_id]) / 2)
        self.fx, self.cx, self.cy = self.fy, (self.W - 1) / 2, (self.H - 1) / 2
        self.sigma, self.rng, self.max_range = sigma_m, np.random.default_rng(seed), max_range_m
        self.min_range = min_range_m
        self.dropout, self.flying = dropout, flying
        # calibration error: the pose the point cloud is built with differs from the pose the image was taken at
        # (rotation about a random axis in the camera frame, translation in a random direction), fixed per seed
        r = np.random.default_rng(seed + 50_000)
        ax, tv = r.normal(size=3), r.normal(size=3)
        ax, tv = ax / np.linalg.norm(ax), tv / np.linalg.norm(tv)
        a = np.deg2rad(calib_rot_deg)
        K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        self.R_err = np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K
        self.t_err = 1e-3 * calib_trans_mm * tv
        self.renderer = mujoco.Renderer(self.m, self.H, self.W)
        self.renderer.enable_depth_rendering()

    def capture(self, data):
        self.renderer.update_scene(data, camera=self.camera)
        depth = self.renderer.render().astype(np.float64).copy()
        if self.sigma > 0:
            depth += self.rng.normal(0.0, self.sigma, depth.shape)
        if self.flying > 0:                                       # flying pixels: random range along the ray
            f = self.rng.random(depth.shape) < self.flying
            depth[f] = self.rng.uniform(0.3, 2.0, int(f.sum()))
        depth[(depth <= self.min_range) | (depth > self.max_range)] = np.nan
        if self.dropout > 0:                                      # missing returns
            depth[self.rng.random(depth.shape) < self.dropout] = np.nan
        return depth

    def points(self, depth, data):
        """(H, W, 3) world coordinates of every pixel (NaN where invalid). MuJoCo cameras look along -z."""
        u, v = np.meshgrid(np.arange(self.W), np.arange(self.H))
        x = (u - self.cx) / self.fx * depth
        y = -(v - self.cy) / self.fy * depth
        pc = np.stack([x, y, -depth], axis=-1)
        R = data.cam_xmat[self.cam_id].reshape(3, 3) @ self.R_err
        return pc @ R.T + data.cam_xpos[self.cam_id] + self.t_err

    def close(self):
        self.renderer.close()


def fit_table_z(P, bin_m=0.005):
    """Height of the dominant horizontal plane (the table): the most populated 5 mm bin, refined by its median."""
    z = P[np.isfinite(P[:, 2]), 2]
    edges = np.arange(z.min(), z.max() + bin_m, bin_m)
    hist, edges = np.histogram(z, bins=edges)
    k = int(np.argmax(hist))
    near = z[(z >= edges[k] - bin_m) & (z <= edges[k + 1] + bin_m)]
    return float(np.median(near))


def fit_plane(pts, z0, band=0.03, iters=6, floor=0.003):
    """Robust (iteratively reweighted) least-squares plane z = a x + b y + c through the table points. Starts from the
    points within `band` of the coarse table height z0, then keeps points within 3 robust sigmas (>= `floor`).
    Returns (unit normal pointing up, a point on the plane)."""
    inl = np.abs(pts[:, 2] - z0) < band
    for _ in range(iters):
        q = pts[inl]
        A = np.c_[q[:, :2], np.ones(len(q))]
        coef = np.linalg.lstsq(A, q[:, 2], rcond=None)[0]
        r = pts[:, 2] - np.c_[pts[:, :2], np.ones(len(pts))] @ coef
        rin = r[inl]
        sig = 1.4826 * np.median(np.abs(rin - np.median(rin)))
        inl = np.abs(r) < max(3 * sig, floor)
    n = np.array([-coef[0], -coef[1], 1.0])
    return n / np.linalg.norm(n), pts[inl].mean(0)


def level_to_plane(P, n, c0):
    """Rotate the cloud about c0 so the plane normal n becomes +z (the real table is horizontal, so any tilt of the fitted
    plane is a calibration error); NaNs stay NaN."""
    zc = np.array([0.0, 0.0, 1.0])
    v, c = np.cross(n, zc), float(n @ zc)
    if np.linalg.norm(v) < 1e-12:
        return P
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    R = np.eye(3) + K + K @ K / (1 + c)
    return (P - c0) @ R.T + c0


def median_filter_depth(depth, k):
    """k x k median of a depth image ignoring NaN (edge-preserving denoise); pixels with no valid neighbour stay NaN."""
    pad = k // 2
    d = np.pad(depth, pad, constant_values=np.nan)
    win = np.lib.stride_tricks.sliding_window_view(d, (k, k)).reshape(*depth.shape, k * k)
    with np.errstate(all="ignore"):
        out = np.nanmedian(win, axis=-1)
    out[~np.isfinite(depth)] = np.nan                        # do not invent pixels where there was no return
    return out


def label_components(mask, z=None, max_step=None):
    """8-connected components of a boolean image -> (labels, count); numpy + a plain BFS (no scipy dependency).
    With z (an image of heights) and max_step, neighbours join only if their heights differ by at most max_step
    (surface continuity: an object does not merge with something far above or below it)."""
    labels = np.zeros(mask.shape, dtype=np.int32)
    H, W = mask.shape
    n = 0
    for r0, c0 in zip(*np.nonzero(mask)):
        if labels[r0, c0]:
            continue
        n += 1
        labels[r0, c0] = n
        q = deque([(r0, c0)])
        while q:
            r, c = q.popleft()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and mask[rr, cc] and not labels[rr, cc] and (
                            max_step is None or abs(z[rr, cc] - z[r, c]) <= max_step):
                        labels[rr, cc] = n
                        q.append((rr, cc))
    return labels, n


def _hull_area(xy):
    """Area of the convex hull of 2D points (monotone chain + shoelace)."""
    p = np.unique(np.round(xy, 6), axis=0)
    if len(p) < 3:
        return 0.0
    p = p[np.lexsort((p[:, 1], p[:, 0]))]
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    h = []
    for chain in (p, p[::-1]):
        part = []
        for q in chain:
            while len(part) >= 2 and cross(part[-2], part[-1], q) <= 0:
                part.pop()
            part.append(q)
        h += part[:-1]
    h = np.array(h)
    return float(0.5 * abs(np.dot(h[:, 0], np.roll(h[:, 1], -1)) - np.dot(h[:, 1], np.roll(h[:, 0], -1))))


def _min_area_rect(xy, step_deg=1.0):
    """Minimum-area bounding rectangle (1st-99th percentile extents, robust to speckle): (centre, extents, angle)."""
    best = None
    for a in np.deg2rad(np.arange(0.0, 90.0, step_deg)):
        ax = np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])
        proj = xy @ ax.T
        lo, hi = np.percentile(proj, 1, axis=0), np.percentile(proj, 99, axis=0)
        area = float(np.prod(hi - lo))
        if best is None or area < best[0]:
            best = (area, a, ax, lo, hi)
    area, a, ax, lo, hi = best
    return ((lo + hi) / 2) @ ax, hi - lo, float(a)


def _measure(pts, table_z):
    """Centre, size, yaw, squareness and fill of a cluster, from its top face (perspective-robust). Axis 0 of the
    minimum-area rectangle is at `yaw` (rad, in [0, 90 deg)); extents are along its two axes."""
    z = pts[:, 2]
    top = float(np.median(z[z >= np.median(z)]))        # median of the upper half: the top face, unbiased by noise
    face = pts[z >= top - TOP_BAND_M]
    xy = face[:, :2]
    centre_xy, ext, yaw = _min_area_rect(xy)
    ax = np.array([[np.cos(yaw), np.sin(yaw)], [-np.sin(yaw), np.cos(yaw)]])
    proj = xy @ ax.T                                     # fill needs near-untrimmed extents: the 1-99 % trim
    lo, hi = np.percentile(proj, 0.25, axis=0), np.percentile(proj, 99.75, axis=0)   # would flatter a disc to ~0.9
    inside = np.all((proj >= lo) & (proj <= hi), axis=1)
    fill = _hull_area(xy[inside]) / max(float(np.prod(hi - lo)), 1e-12)
    return dict(centre_xy=centre_xy, extent=ext, yaw=yaw, top_z=float(top), height=float(top - table_z),
                aspect=float(ext.max() / max(ext.min(), 1e-9)), fill=float(min(fill, 1.0)),
                extent_x=float(np.percentile(xy[:, 0], 99) - np.percentile(xy[:, 0], 1)),
                extent_y=float(np.percentile(xy[:, 1], 99) - np.percentile(xy[:, 1], 1)))


def table_noise(P, depth_valid, table_z):
    """Depth noise sigma measured on the table plane (robust: 1.4826 x MAD of the heights of near-table points)."""
    r = P[..., 2][depth_valid]
    r = r[np.abs(r - table_z) < 0.03] - table_z
    return float(1.4826 * np.median(np.abs(r - np.median(r)))) if len(r) else 0.0


def estimate_objects(P, depth_valid, table_z, min_points=25, min_height=MIN_HEIGHT_M, max_step=0.025):
    """All object-like clusters above the table. P: (H, W, 3) world points; depth_valid: (H, W) bool."""
    H, W = depth_valid.shape
    z = P[..., 2]
    mask = depth_valid & (z > table_z + min_height) & (z < table_z + MAX_HEIGHT_M)
    labels, n = label_components(mask, np.nan_to_num(z), max_step)
    out = []
    for k in range(1, n + 1):
        rows, cols = np.nonzero(labels == k)
        if len(rows) < min_points:
            continue
        pts = P[rows, cols]
        o = _measure(pts, table_z)
        o.update(n_points=int(len(rows)),
                 touches_border=bool(rows.min() == 0 or cols.min() == 0 or rows.max() == H - 1 or cols.max() == W - 1))
        out.append(o)
    return out


def reject_reason(o, max_width_m, max_height_m=0.10, min_extent_m=0.015, min_points=80,
                  max_aspect=1.3, min_fill=0.9, height_ratio=(0.6, 1.5)):
    """Why a cluster is not the graspable cube (None = it is a candidate): solid (not a noise speckle), fits between the
    fingers, not clipped by the image border, cube-shaped from depth alone (top face about square and filled, height
    about the width) so cylinders, bars and plates are rejected."""
    if o["touches_border"]:
        return "touches image border"
    if o["n_points"] < min_points:
        return "too few points"
    if min(o["extent"]) < min_extent_m:
        return "too small"
    if max(o["extent"]) > max_width_m:
        return "wider than the gripper opening"
    if o["height"] > max_height_m:
        return "too tall"
    if o["aspect"] > max_aspect:
        return f"not square (aspect {o['aspect']:.2f})"
    if o["fill"] < min_fill:
        return f"top face not filled (fill {o['fill']:.2f})"
    if not height_ratio[0] <= o["height"] / o["extent"].mean() <= height_ratio[1]:
        return "height does not match width"
    return None


def select_graspable(objs, max_width_m, **kw):
    """The cube the gripper can take: among the clusters that pass reject_reason, the largest by point count."""
    c = [o for o in objs if reject_reason(o, max_width_m, **kw) is None]
    return max(c, key=lambda o: o["n_points"]) if c else None


def select_tray(objs, min_size_m=0.10):
    c = [o for o in objs if not o["touches_border"] and max(o["extent"]) >= min_size_m]
    return max(c, key=lambda o: o["extent"].prod()) if c else None


def tray_floor_z(P, depth_valid, tray, table_z, max_above_table=0.045):
    """Height of the tray floor: median of the points inside the tray walls that are low enough to be floor (below
    `max_above_table`; the walls are 29 mm, so anything higher is the block being carried or an arm, not floor)."""
    half = 0.5 * np.array([tray["extent_x"], tray["extent_y"]]) - 0.035
    d = np.abs(P[..., :2] - tray["centre_xy"])
    inside = depth_valid & (d[..., 0] <= half[0]) & (d[..., 1] <= half[1]) & (P[..., 2] < table_z + max_above_table)
    return float(np.median(P[..., 2][inside])) if inside.sum() >= 20 else float(table_z)


class Perceiver:
    """Callable for rollout.run_episode(perceiver=...): scene -> {"block_xyz", "goal_xyz", "info"} from one depth frame."""

    def __init__(self, max_width_m, camera="top", sigma_m=0.002, seed=0, size=(480, 640), need_tray=True, need_block=True, keep_cloud=False, **sensor_kw):
        self.keep_cloud = keep_cloud      # keep the levelled cloud and all clusters in .last (for figures)
        self.need_block = need_block      # False: tray only (look-again at the place pose)
        self.need_tray = need_tray        # False: block only (a wrist view at hover does not see the tray)
        self.max_width, self.camera, self.sigma, self.seed, self.size = max_width_m, camera, sigma_m, seed, size
        self.sensor_kw = sensor_kw        # calib_rot_deg, calib_trans_mm, dropout, flying (see DepthSensor)
        self.last = None

    @staticmethod
    def _level(P, valid):
        """Level the cloud to the fitted table plane; returns (cloud, table height, measured depth noise)."""
        pts = P[valid]
        z0 = fit_table_z(pts, bin_m=0.01)
        n, c0 = fit_plane(pts, z0)
        P = level_to_plane(P, n, c0)
        table_z = float(c0[2])
        return P, table_z, table_noise(P, valid, table_z)

    def __call__(self, scene):
        sensor = DepthSensor(scene, self.camera, self.size, self.sigma, seed=self.seed + scene.seed, **self.sensor_kw)
        try:
            depth = sensor.capture(scene.data)
            P, table_z, sigma_est = self._level(sensor.points(depth, scene.data), np.isfinite(depth))
            if sigma_est > 0.003:                              # noisy sensor: median-filter the depth, then redo the fit
                depth = median_filter_depth(depth, 7 if sigma_est > 0.015 else 5 if sigma_est > 0.007 else 3)
                P, table_z, sigma_est = self._level(sensor.points(depth, scene.data), np.isfinite(depth))
        finally:
            sensor.close()
        valid = np.isfinite(depth)
        objs = estimate_objects(P, valid, table_z, min_height=max(MIN_HEIGHT_M, 4.0 * sigma_est))
        blk = select_graspable(objs, self.max_width) if self.need_block else None
        tray = select_tray(objs) if self.need_tray else None
        floor = tray_floor_z(P, valid, tray, table_z) if tray is not None else None
        self.last = dict(block=blk, tray=tray, table_z=table_z, floor_z=floor, n_clusters=len(objs), sigma_est=sigma_est,
                         tray_xy=None if tray is None else tray["centre_xy"])
        if self.keep_cloud:                                           # also on failure: shows what was seen
            self.last.update(objs=objs, cloud=P, valid=valid)
        if (self.need_block and blk is None) or (self.need_tray and tray is None):
            raise RuntimeError(f"perception failed: block {'found' if blk else 'missing'}, "
                               f"tray {'found' if tray else 'missing'} ({len(objs)} clusters)")
        block_xyz = goal_xyz = yaw = width = None
        if blk is not None:
            width = float(blk["extent"].mean())                       # cube side (top face, minimum-area rectangle)
            block_half = 0.5 * blk["height"]                          # resting on the table
            block_xyz, yaw = np.array([*blk["centre_xy"], table_z + block_half]), blk["yaw"]
            if tray is not None:                                      # block centre when resting on the tray floor
                goal_xyz = np.array([*tray["centre_xy"], floor + block_half])
        return {"block_xyz": block_xyz, "goal_xyz": goal_xyz, "yaw": yaw, "width_m": width, "info": self.last}
