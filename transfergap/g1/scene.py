"""Task overlay for the GEAR-SONIC MuJoCo G1 scene: table, 4 cm block, tray, third-person camera.

The upstream scene (GR00T-WholeBodyControl, gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml)
is loaded unmodified with MjSpec; the task objects are added on top and the result is written to an
XML file that we own. The upstream sim reads its scene path from the ROBOT_SCENE config key, which
sim_runner.py points at this generated file. Nothing in the upstream checkout is edited.

Run with the upstream sim venv (mujoco 3.14), e.g.
    python transfergap/g1/scene.py --sonic-root ~/GR00T-WholeBodyControl --seed 0 --out /tmp/g1_task_seed0.xml
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

UPSTREAM_SCENE = "gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml"

# Robot stands at the origin facing +x. All task geometry in metres, world frame.
TABLE_TOP_Z = 0.72
TABLE_CENTER_XY = (0.48, 0.0)
TABLE_HALF = (0.26, 0.40, 0.02)          # near edge at x = 0.22
BLOCK_HALF, BLOCK_MASS = 0.02, 0.05      # 4 cm cube, 50 g (same block as the arm slice)
BLOCK_NOMINAL_XY = np.array([0.33, -0.20])
BLOCK_JITTER = 0.02                      # +/- uniform per axis, metres, seeded
TRAY_XY = (0.34, 0.0)
TRAY_FLOOR, TRAY_WALL, TRAY_HALF, TRAY_T = 0.004, 0.025, 0.075, 0.005


def sample_block_xy(seed):
    """Block placement for a trial. Pure function of the seed (scene config, not simulator state)."""
    return BLOCK_NOMINAL_XY + np.random.default_rng(seed).uniform(-BLOCK_JITTER, BLOCK_JITTER, 2)


def goal_xyz():
    return np.array([*TRAY_XY, TABLE_TOP_Z + TRAY_FLOOR + BLOCK_HALF])


def look_at(pos, target, up=(0, 0, 1)):
    f = np.asarray(target, float) - np.asarray(pos, float)
    f /= np.linalg.norm(f)
    x = np.cross(f, up)
    x /= np.linalg.norm(x)
    return [*x, *np.cross(x, f)]


def build_spec(sonic_root, seed=0, with_block=True):
    import mujoco

    G = mujoco.mjtGeom
    scene = Path(sonic_root).expanduser() / UPSTREAM_SCENE
    spec = mujoco.MjSpec.from_file(str(scene))
    # mesh paths in the included robot file are relative to the upstream folder; make them absolute
    spec.meshdir = str(scene.parent / "meshes")
    spec.visual.global_.offwidth, spec.visual.global_.offheight = 1280, 720
    w = spec.worldbody
    tx, ty = TABLE_CENTER_XY
    hx, hy, hz = TABLE_HALF
    wood, green = [.62, .5, .38, 1], [.2, .55, .3, 1]
    w.add_geom(name="table", type=G.mjGEOM_BOX, size=[hx, hy, hz], pos=[tx, ty, TABLE_TOP_Z - hz],
               rgba=wood, friction=[.8, .005, .0001], condim=4)
    for i, (sx, sy) in enumerate([(1, 1), (1, -1), (-1, 1), (-1, -1)]):   # visual-only legs
        w.add_geom(name=f"table_leg{i}", type=G.mjGEOM_BOX, size=[.02, .02, (TABLE_TOP_Z - 2 * hz) / 2],
                   pos=[tx + sx * (hx - .03), ty + sy * (hy - .03), (TABLE_TOP_Z - 2 * hz) / 2],
                   rgba=wood, contype=0, conaffinity=0)
    px, py = TRAY_XY
    z0 = TABLE_TOP_Z
    h, t, wz = TRAY_HALF, TRAY_T, TRAY_WALL / 2
    w.add_geom(name="tray_floor", type=G.mjGEOM_BOX, size=[h, h, TRAY_FLOOR / 2], pos=[px, py, z0 + TRAY_FLOOR / 2],
               rgba=green, friction=[.8, .005, .0001], condim=4)
    for i, (dx, dy, sx, sy) in enumerate([(h, 0, t, h), (-h, 0, t, h), (0, h, h, t), (0, -h, h, t)]):
        w.add_geom(name=f"tray_wall{i}", type=G.mjGEOM_BOX, size=[sx, sy, wz],
                   pos=[px + dx, py + dy, z0 + TRAY_FLOOR + wz], rgba=green, friction=[.8, .005, .0001], condim=4)
    if with_block:
        bx, by = sample_block_xy(seed)
        blk = w.add_body(name="block", pos=[bx, by, z0 + BLOCK_HALF + 1e-4])
        blk.add_freejoint(name="block_free")
        blk.add_geom(name="block_geom", type=G.mjGEOM_BOX, size=[BLOCK_HALF] * 3, mass=BLOCK_MASS,
                     friction=[1.0, .01, .001], condim=4, rgba=[.85, .15, .1, 1],
                     solref=[.004, 1], solimp=[.95, .99, .001, .5, 2])
    cam = np.array([1.55, -1.25, 1.35])
    w.add_camera(name="third_person", pos=cam, xyaxes=look_at(cam, [0.25, -0.05, 0.75]), fovy=40)
    side = np.array([0.45, -1.6, 1.0])
    w.add_camera(name="side", pos=side, xyaxes=look_at(side, [0.3, -0.1, 0.75]), fovy=40)
    close = np.array([0.75, -0.55, 1.0])
    w.add_camera(name="closeup", pos=close, xyaxes=look_at(close, [0.30, -0.10, 0.74]), fovy=45)
    return spec


def write_scene(sonic_root, out, seed=0, with_block=True):
    spec = build_spec(sonic_root, seed, with_block)
    spec.compile()                      # fail early if the overlay does not compile
    Path(out).write_text(spec.to_xml())
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sonic-root", default="~/GR00T-WholeBodyControl")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print(write_scene(a.sonic_root, a.out, a.seed))
