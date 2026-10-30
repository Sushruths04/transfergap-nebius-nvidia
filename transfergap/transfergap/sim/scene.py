"""Fixed-base UR arm (UR5e or UR10e) + Robotiq 2F-85 pick-and-place scene, built programmatically with MjSpec.

Assets: mujoco_menagerie (Apache-2.0), fetched by setup_sim.sh into assets/menagerie.
"""
from __future__ import annotations

from pathlib import Path

import mujoco
import os

import numpy as np

ASSETS = Path(__file__).parent / "assets" / "menagerie"
G = mujoco.mjtGeom
BLOCK_HALF, BLOCK_MASS = 0.02, 0.05          # 4 cm cube, ~wood density
TRAY_XY, TRAY_FLOOR, TRAY_WALL = (0.45, 0.22), 0.004, 0.025
BLOCK_CENTER = np.array([0.45, -0.12])       # nominal block xy; seed jitters it
BLOCK_JITTER = 0.03                          # +/- uniform, metres
HOME_Q = [-1.5708, -1.5708, 1.5708, -1.5708, -1.5708, 0]   # menagerie "home" keyframe (same for both arms)
# robot key -> (menagerie dir, mjcf file, episode robot label). Same joint/site names; table layout unchanged.
ROBOTS = {"ur5e": ("universal_robots_ur5e", "ur5e.xml", "ur5e_2f85_fixed"),
          "ur10e": ("universal_robots_ur10e", "ur10e.xml", "ur10e_2f85_fixed"),
          # the lab's KAIROS arm: UR10e + Robotiq 2F-140 (gripper built by kairos_model from the lab description)
          "kairos": ("universal_robots_ur10e", "ur10e.xml", "kairos_ur10e_2f140_fixed"),
          # the same arm on the lab's mobile base (Summit XLS chassis, planar holonomic base), parked at the origin for the task
          "kairos_mobile": ("universal_robots_ur10e", "ur10e.xml", "kairos_mobile_ur10e_2f140")}
OPENING_M = {"ur5e": 0.085, "ur10e": 0.085, "kairos": 0.128, "kairos_mobile": 0.128}   # fully open pad gap (2F-140: measured 128.5 mm in the model)
YAW_CLEARANCE_M = 0.025         # rotate the tool to the block's yaw only if the block would not clear the opening by this
GRIPPER_2F140 = {"kairos", "kairos_mobile"}      # every other robot uses the menagerie Robotiq 2F-85
DEFAULT_ROBOT = "ur5e"
FINGER_KEYS = ("driver", "coupler", "spring", "follower", "pad")


def look_at(pos, target, up=(0, 0, 1)):
    f = np.asarray(target, float) - pos
    f /= np.linalg.norm(f)
    x = np.cross(f, up)
    x /= np.linalg.norm(x)
    return [*x, *np.cross(x, f)]


def sample_block_xy(seed, jitter=BLOCK_JITTER):
    return BLOCK_CENTER + np.random.default_rng(seed).uniform(-jitter, jitter, 2)


def robot_ready(robot=DEFAULT_ROBOT):
    if robot in GRIPPER_2F140:
        from . import kairos_model
        return ((ASSETS / ROBOTS[robot][0]).exists() and kairos_model.ready()
                and (robot != "kairos_mobile" or kairos_model.base_ready()))
    return (ASSETS / ROBOTS[robot][0]).exists() and (ASSETS / "robotiq_2f85").exists()


# distractor kinds (name, geom type, size(half extents / radius+halfheight), colour): objects the depth-only
# perception must NOT pick. "can_equal" is a cylinder as tall as it is wide: the hardest to tell from a cube.
DISTRACTORS = {"tall_cylinder": (G.mjGEOM_CYLINDER, [0.022, 0.035, 0], [.2, .3, .8, 1]),
               "can_equal": (G.mjGEOM_CYLINDER, [0.025, 0.025, 0], [.8, .8, .2, 1]),
               "bar": (G.mjGEOM_BOX, [0.012, 0.045, 0.015], [.5, .2, .6, 1]),
               "flat_plate": (G.mjGEOM_BOX, [0.04, 0.03, 0.006], [.9, .9, .9, 1])}


def sample_block_yaw(seed):
    """Block yaw about z, uniform over the cube's symmetry interval (-45, 45] degrees (its own seed stream)."""
    return float(np.deg2rad(np.random.default_rng(seed + 30_000).uniform(-45, 45)))


def sample_distractors(seed, n, block_xy, block_half, kinds=tuple(DISTRACTORS)):
    """n static table objects with seeded kinds/poses, kept clear of the block (fingers), the tray and the table edge."""
    rng = np.random.default_rng(seed + 40_000)
    out, placed = [], [np.asarray(block_xy, float), np.asarray(TRAY_XY, float)]
    keep = [0.10 + block_half, 0.15]
    tries = 0
    while len(out) < n and tries < 500:
        tries += 1
        xy = np.array([rng.uniform(0.28, 0.62), rng.uniform(-0.30, 0.30)])
        if any(np.linalg.norm(xy - p) < k + 0.04 for p, k in zip(placed, keep)):
            continue
        kind = kinds[len(out) % len(kinds)] if len(kinds) < 4 else kinds[rng.integers(len(kinds))]
        out.append(dict(kind=kind, xy=xy.tolist(), yaw=float(rng.uniform(0, np.pi))))
        placed.append(xy)
        keep.append(0.05)
    return out


def apply_hq_visuals(spec):
    """Visual-only upgrade (TG_HQ=1): sky gradient, checker floor, speckled wood table, softer lighting, bigger shadow map, antialiasing.
    Touches no physics (no masses, frictions, contacts or geometry sizes), so results are unchanged; only rendered pixels differ."""
    T, M = mujoco.mjtTexture, mujoco.mjtBuiltin
    spec.add_texture(name="hq_sky", type=T.mjTEXTURE_SKYBOX, builtin=M.mjBUILTIN_GRADIENT, rgb1=[.55, .70, .90], rgb2=[.08, .10, .16], width=512, height=3072)
    spec.add_texture(name="hq_floor", type=T.mjTEXTURE_2D, builtin=M.mjBUILTIN_CHECKER, rgb1=[.20, .23, .28], rgb2=[.26, .29, .35], width=512, height=512,
                     mark=mujoco.mjtMark.mjMARK_EDGE, markrgb=[.32, .35, .42])
    spec.add_texture(name="hq_wood", type=T.mjTEXTURE_2D, builtin=M.mjBUILTIN_FLAT, rgb1=[.64, .50, .36], rgb2=[.55, .42, .29], width=512, height=512,
                     mark=mujoco.mjtMark.mjMARK_RANDOM, markrgb=[.48, .36, .24], random=0.06)
    fl = spec.add_material(name="hq_floor_m", texrepeat=[6, 6], texuniform=True, reflectance=0.12)
    fl.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = "hq_floor"
    wd = spec.add_material(name="hq_wood_m", texrepeat=[3, 3], texuniform=True, specular=0.15, shininess=0.2)
    wd.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = "hq_wood"
    spec.geom("floor").material = "hq_floor_m"
    spec.geom("table").material = "hq_wood_m"
    spec.visual.headlight.ambient = [.35, .35, .38]
    spec.visual.headlight.diffuse = [.45, .45, .45]
    spec.visual.quality.shadowsize = 4096
    spec.visual.quality.offsamples = 8
    w = spec.worldbody
    w.add_light(pos=[-1.2, -1.4, 1.8], dir=[0.5, 0.6, -0.9], type=mujoco.mjtLightType.mjLIGHT_SPOT, diffuse=[.35, .33, .30], castshadow=True)


def build_spec(seed=0, robot=DEFAULT_ROBOT, block_half=BLOCK_HALF, block_yaw=0.0, distractors=(),
               block_jitter=BLOCK_JITTER, twin=None):
    if robot not in ROBOTS:
        raise ValueError(f"unknown robot {robot!r}; choose from {sorted(ROBOTS)}")
    folder, xml, _ = ROBOTS[robot]
    if not robot_ready(robot):
        raise FileNotFoundError(f"menagerie assets for {robot} missing; run transfergap/sim/setup_sim.sh")
    spec = mujoco.MjSpec.from_file(str(ASSETS / folder / xml))
    if robot in GRIPPER_2F140:
        from . import kairos_model
        grip = kairos_model.build_gripper_spec()
    else:
        grip = mujoco.MjSpec.from_file(str(ASSETS / "robotiq_2f85" / "2f85.xml"))
    spec.option.cone, spec.option.impratio, spec.option.timestep = mujoco.mjtCone.mjCONE_ELLIPTIC, 10, 0.002
    spec.attach(grip, site=spec.site("attachment_site"), prefix="g_")
    for b in spec.bodies:                    # the real UR runs internal gravity compensation
        if b.name != "world":
            b.gravcomp = 1
    mobile = robot == "kairos_mobile"
    if mobile:                               # the arm now rides on the planar KAIROS base (parked at the origin for the task)
        from . import kairos_model
        spec = kairos_model.mount_on_base(spec)
    w = spec.worldbody
    w.add_light(pos=[0.3, 0, 2], dir=[0, 0, -1], type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL, diffuse=[.7, .7, .7])
    if mobile:
        from . import kairos_model
        w.add_geom(name="floor", type=G.mjGEOM_PLANE, size=[4, 4, .05], pos=[0, 0, kairos_model.FLOOR_Z], rgba=[.25, .28, .32, 1])
        # the chassis front edge is at x = 0.36: the table starts just beyond it (same top height as the arm base plane)
        w.add_geom(name="table", type=G.mjGEOM_BOX, size=[.45, .6, .02], pos=[.82, 0, -.02],
                   rgba=[.62, .5, .38, 1], friction=[.8, .005, .0001], condim=4, contype=3, conaffinity=3)
    else:
        w.add_geom(name="floor", type=G.mjGEOM_PLANE, size=[3, 3, .05], pos=[0, 0, -.75], rgba=[.25, .28, .32, 1])
        w.add_geom(name="table", type=G.mjGEOM_BOX, size=[.6, .6, .02], pos=[.3, 0, -.02],
                   rgba=[.62, .5, .38, 1], friction=[.8, .005, .0001], condim=4)
    if twin is not None:                     # the author's real geometry (sim/twin.py): measured box and target container
        from . import twin as T
        spec.geom("table").pos = [spec.geom("table").pos[0], spec.geom("table").pos[1], twin["table"]["top_z_m"] - 0.02]
        f = T.robot_frame(twin)
        top = twin["table"]["top_z_m"]
        hx, hy, hz = T.box_half_extents(twin)
        tx, ty = f["target_xy"]
        ix, iy = np.asarray(twin["target"]["inner_size_m"], float) / 2
        wt, wh, ft = twin["target"]["wall_thickness_m"], twin["target"]["wall_height_m"], twin["target"]["floor_thickness_m"]
        w.add_geom(name="tray_floor", type=G.mjGEOM_BOX, size=[ix + wt, iy + wt, ft / 2], pos=[tx, ty, top + ft / 2],
                   rgba=[.15, .15, .17, 1], friction=[.8, .005, .0001], condim=4)
        for i, (dx, dy, sx, sy) in enumerate([(ix + wt / 2, 0, wt / 2, iy + wt), (-ix - wt / 2, 0, wt / 2, iy + wt),
                                              (0, iy + wt / 2, ix, wt / 2), (0, -iy - wt / 2, ix, wt / 2)]):
            w.add_geom(name=f"tray_wall{i}", type=G.mjGEOM_BOX, size=[sx, sy, wh / 2], pos=[tx + dx, ty + dy, top + ft + wh / 2],
                       rgba=[.15, .15, .17, 1], friction=[.8, .005, .0001], condim=4)
        j = twin["jitter_m"]
        bx, by = np.asarray(f["object_xy"]) + np.random.default_rng(seed).uniform(-j, j, 2)
        blk = w.add_body(name="block", pos=[bx, by, top + hz + 1e-4], quat=[np.cos(block_yaw / 2), 0, 0, np.sin(block_yaw / 2)])
        blk.add_freejoint(name="block_free")
        blk.add_geom(name="block_geom", type=G.mjGEOM_BOX, size=[hx, hy, hz], mass=twin["object"]["mass_kg"],
                     friction=[1.0, .01, .001], condim=4, rgba=[.85, .15, .1, 1],
                     solref=[.004, 1], solimp=[.95, .99, .001, .5, 2])
    else:
        # shallow tray: static floor plate + four walls
        tx, ty = TRAY_XY
        h, t, hz = 0.075, 0.005, TRAY_WALL / 2
        w.add_geom(name="tray_floor", type=G.mjGEOM_BOX, size=[h, h, TRAY_FLOOR / 2], pos=[tx, ty, TRAY_FLOOR / 2],
                   rgba=[.2, .55, .3, 1], friction=[.8, .005, .0001], condim=4)
        for i, (dx, dy, sx, sy) in enumerate([(h, 0, t, h), (-h, 0, t, h), (0, h, h, t), (0, -h, h, t)]):
            w.add_geom(name=f"tray_wall{i}", type=G.mjGEOM_BOX, size=[sx, sy, hz], pos=[tx + dx, ty + dy, TRAY_FLOOR + hz],
                       rgba=[.2, .55, .3, 1], friction=[.8, .005, .0001], condim=4)
        bx, by = sample_block_xy(seed, block_jitter)
        mass = BLOCK_MASS * (block_half / BLOCK_HALF) ** 3          # same density at every size
        blk = w.add_body(name="block", pos=[bx, by, block_half + 1e-4],
                         quat=[np.cos(block_yaw / 2), 0, 0, np.sin(block_yaw / 2)])
        blk.add_freejoint(name="block_free")
        apple = os.environ.get("TG_OBJECT") == "apple"          # sphere of radius block_half (an apple is about 0.035); same mass rule
        blk.add_geom(name="block_geom", type=G.mjGEOM_SPHERE if apple else G.mjGEOM_BOX, size=[block_half, 0, 0] if apple else [block_half] * 3, mass=mass,
                     friction=[1.0, .01, .001], condim=4, rgba=[.85, .15, .1, 1],
                     solref=[.004, 1], solimp=[.95, .99, .001, .5, 2])
    for i, dd in enumerate(distractors):
        gt, sz, rgba = DISTRACTORS[dd["kind"]]
        sz = np.array(sz, float)
        zc = sz[1] if gt == G.mjGEOM_CYLINDER else sz[2]
        w.add_geom(name=f"distractor{i}", type=gt, size=sz, rgba=rgba, friction=[.8, .005, .0001],
                   pos=[*dd["xy"], zc], quat=[np.cos(dd["yaw"] / 2), 0, 0, np.sin(dd["yaw"] / 2)])
    w.add_camera(name="third_person", pos=[1.25, -1.1, .85], xyaxes=look_at(np.array([1.25, -1.1, .85]), [.3, .05, .2]))
    w.add_camera(name="top", pos=[.4, .05, 1.3], xyaxes=[0, -1, 0, 1, 0, 0])
    if mobile:                               # wide view that keeps the whole approach path in frame
        w.add_camera(name="wide", pos=[1.9, -2.4, 1.15], xyaxes=look_at(np.array([1.9, -2.4, 1.15]), [-0.1, -0.1, -0.1]))
    # wrist depth camera (a stand-in for a D455 on the wrist: 58 deg vertical FOV, mounted on the tool's -x side,
    # set back from the flange, looking along the tool z axis = down in the pick pose). The real mount is not modelled.
    spec.body("g_base").add_camera(name="wrist", pos=[-0.08, 0, -0.10], quat=[0, 1, 0, 0], fovy=58)
    if os.environ.get("TG_HQ") == "1":
        apply_hq_visuals(spec)
    return spec


class Scene:
    """Compiled scene plus cached ids. goal_xyz is where the block centre rests on the tray."""

    def __init__(self, seed=0, robot=DEFAULT_ROBOT, block_half=BLOCK_HALF, block_yaw=0.0, distractors=(),
                 block_jitter=BLOCK_JITTER, twin=None):
        if twin is None and robot in ROBOTS:
            from . import twin as _T
            twin = _T.from_env()               # TG_TWIN=/path/twin.json applies the author's real geometry to every scene in the process
        self.twin = twin
        if twin is not None:
            from . import twin as _T
            block_half = float(_T.box_half_extents(twin)[2])       # resting height of the block centre
        self.seed, self.robot, self.block_half, self.block_yaw = seed, robot, block_half, block_yaw
        self.distractors = list(distractors)
        self.spec = build_spec(seed, robot, block_half, block_yaw, self.distractors, block_jitter, twin)
        self.robot_label = ROBOTS[robot][2]
        self.home_q = list(HOME_Q)
        self.model = m = self.spec.compile()
        self.data = mujoco.MjData(m)
        name = lambda kind, n: mujoco.mj_name2id(m, kind, n)
        B, J = mujoco.mjtObj.mjOBJ_BODY, mujoco.mjtObj.mjOBJ_JOINT
        if twin is not None:
            tf = _T.robot_frame(twin)["target_xy"]
            self.tray_xy = tuple(tf)
            self.tray_half = tuple(np.asarray(twin["target"]["inner_size_m"], float) / 2)
            self.tray_floor = twin["target"]["floor_thickness_m"]
            self.goal_xyz = np.array([*tf, twin["table"]["top_z_m"] + self.tray_floor + block_half])
        else:
            self.tray_xy, self.tray_half, self.tray_floor = TRAY_XY, (0.075, 0.075), TRAY_FLOOR
            self.goal_xyz = np.array([*TRAY_XY, TRAY_FLOOR + block_half])
        self.block_body, self.block_geom = name(B, "block"), name(mujoco.mjtObj.mjOBJ_GEOM, "block_geom")
        self.table_geom = name(mujoco.mjtObj.mjOBJ_GEOM, "table")
        self.tool_body = name(B, "g_base")
        self.arm_qadr = [m.jnt_qposadr[name(J, n)] for n in
                         ("shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_1_joint",
                          "wrist_2_joint", "wrist_3_joint")]
        self.arm_dof = [m.jnt_dofadr[name(J, n)] for n in
                        ("shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_1_joint",
                         "wrist_2_joint", "wrist_3_joint")]
        self.grip_act = name(mujoco.mjtObj.mjOBJ_ACTUATOR, "g_fingers_actuator")
        self.pinch_site = name(mujoco.mjtObj.mjOBJ_SITE, "g_pinch")
        self.pinch_off = m.site_pos[self.pinch_site].copy()   # pinch site in the g_base frame
        self.block_qadr = m.jnt_qposadr[name(J, "block_free")]
        # geom classification for contact logic: finger bodies vs everything else on the robot
        robot_bodies = set(range(1, m.nbody)) - {self.block_body}
        self.finger_bodies = {b for b in robot_bodies if any(k in mujoco.mj_id2name(m, B, b) for k in FINGER_KEYS)}
        self.link_bodies = robot_bodies - self.finger_bodies
        self.reset()

    def reset(self):
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        d.qpos[self.arm_qadr] = self.home_q
        d.ctrl[:6] = self.home_q
        mujoco.mj_forward(m, d)
        return d

    def block_pos(self):
        return self.data.xpos[self.block_body].copy()

    def block_vel(self):
        return self.data.cvel[self.block_body][3:].copy()   # linear part (world-aligned, about subtree com)

    def contact_flags(self):
        """(forbidden, finger_touching_block) from current contacts. Forbidden = non-finger robot link
        touching the table or the block."""
        m, d = self.model, self.data
        forbidden = touching = False
        for c in d.contact[:d.ncon]:
            b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
            for a, b, ga, gb in ((b1, b2, c.geom1, c.geom2), (b2, b1, c.geom2, c.geom1)):
                if a in self.link_bodies and (gb == self.table_geom or b == self.block_body):
                    forbidden = True
                if a in self.finger_bodies and b == self.block_body:
                    touching = True
        return forbidden, touching
