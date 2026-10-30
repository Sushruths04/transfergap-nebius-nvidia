"""KAIROS arm tool: Robotiq 2F-140 gripper (plus the UR-to-Robotiq adapter) for the MuJoCo pick-and-place scene.

The KAIROS arm is a UR10e, which the scene already has from mujoco_menagerie; what is specific to KAIROS is the
gripper, so only that is built here, from the lab's robot-description files (xacro + meshes). Those files are NOT
part of this repository and the generated model is git-ignored (`sim/assets/kairos/`): run `prepare()` once on a
machine that has the description folder, then `build_gripper_spec()` needs only MuJoCo.

    python -m transfergap.sim.kairos_model prepare --src <path to .../urdf/gripper> [--out sim/assets/kairos]

Model choices (what the real stack does, reproduced): the URDF's mimic joints become MuJoCo joint equalities
through MuJoCo's own URDF import (inner knuckle = -finger, inner finger = +finger, right outer knuckle = -finger);
the closed linkage loop is not modelled, as in the ROS/Isaac description. Names match what scene.py expects from a gripper: body `base`,
site `pinch`, actuator `fingers_actuator` (control 0..255 -> finger joint 0..0.7 rad), finger bodies whose names
contain one of scene.FINGER_KEYS.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import mujoco
import numpy as np

ASSETS = Path(__file__).parent / "assets" / "kairos"
G_MESH, G_BOX, G_CYL = mujoco.mjtGeom.mjGEOM_MESH, mujoco.mjtGeom.mjGEOM_BOX, mujoco.mjtGeom.mjGEOM_CYLINDER
URDF = "g140.urdf"
FINGER_JOINT, FINGER_MAX = "finger_joint", 0.7
MIMIC = (("left_inner_knuckle_joint", -1.0), ("left_inner_finger_joint", 1.0),
         ("right_outer_knuckle_joint", -1.0), ("right_inner_knuckle_joint", -1.0),
         ("right_inner_finger_joint", 1.0))
# body renames so that scene.FINGER_KEYS ("driver", "coupler", "spring", "follower", "pad") classify them as finger parts
RENAME = {"robotiq_140_base_link": "base",
          "left_outer_knuckle": "left_driver", "right_outer_knuckle": "right_driver",
          "left_inner_knuckle": "left_spring_link", "right_inner_knuckle": "right_spring_link",
          "left_outer_finger": "left_follower", "right_outer_finger": "right_follower",
          "left_inner_finger": "left_coupler", "right_inner_finger": "right_coupler",
          "left_inner_finger_pad": "left_pad", "right_inner_finger_pad": "right_pad"}
# pinch point in the `base` frame: midway between the pads when a 4 cm block is held (finger joint about 0.5 rad)
PINCH_Z = 0.1986
GRIP_FORCE_N_M = 8.0          # finger-joint torque limit (scaled by the scene's grip_force_scale)
KP = 20.0


def ready(assets: Path = ASSETS) -> bool:
    return (assets / URDF).exists() and (assets / "mesh").is_dir()


def prepare(src_gripper_dir: str | Path, out: str | Path = ASSETS, prefix_xacro: bool = True) -> Path:
    """Expand the gripper xacro to a URDF and stage meshes under distinct names (visual vs collision share file
    names in the source). Needs the `xacro` package; writes `out/g140.urdf` and `out/mesh/`."""
    import os
    import tempfile

    import xacro
    src, out = Path(src_gripper_dir).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:             # xacro resolves includes next to the top-level file
        urdf_dir = Path(tmp) / "urdf"
        shutil.copytree(src / "urdf", urdf_dir)
        wrap = urdf_dir / "wrap_tmp.xacro"
        wrap.write_text(
            '<?xml version="1.0"?>\n<robot xmlns:xacro="http://wiki.ros.org/xacro" name="kairos_2f140">\n'
            '  <xacro:include filename="robotiq_2f_140_macro.urdf.xacro"/>\n'
            '  <link name="flange"/>\n'
            '  <xacro:robotiq_gripper name="g" prefix="" parent="flange" include_ros2_control="false">\n'
            '    <origin xyz="0 0 0.011" rpy="0 0 0"/>\n  </xacro:robotiq_gripper>\n</robot>\n')
        try:
            os.chdir(urdf_dir)
            text = xacro.process_file(str(wrap)).toprettyxml(indent="  ")
        finally:
            os.chdir(cwd)
    mesh = out / "mesh"
    mesh.mkdir(exist_ok=True)
    for kind, tag in (("visual", "v_"), ("collision", "c_")):
        for f in (src / "meshes" / kind).glob("*.stl"):
            shutil.copy(f, mesh / (tag + f.name))
    shutil.copy(src / "meshes" / "collision" / "ur_to_robotiq_adapter.stl", mesh / "v_ur_to_robotiq_adapter.stl")
    text = (text.replace("file:///urdf/gripper/meshes/visual/", "v_").replace("file:///urdf/gripper/meshes/collision/", "c_")
            .replace("v_ur_to_robotiq_adapter.dae", "v_ur_to_robotiq_adapter.stl"))
    text = text.replace('<robot name="kairos_2f140">',
                        '<robot name="kairos_2f140"><mujoco><compiler meshdir="mesh" fusestatic="false" '
                        'discardvisual="false" balanceinertia="true"/></mujoco>', 1)
    (out / URDF).write_text(text)
    return out / URDF


def build_gripper_spec(assets: Path = ASSETS) -> mujoco.MjSpec:
    """MjSpec of the 2F-140 ready to be attached to a UR flange site (prefix it with `g_` in the scene)."""
    if not ready(assets):
        raise FileNotFoundError("KAIROS gripper model not prepared; run transfergap.sim.kairos_model prepare --src ...")
    spec = mujoco.MjSpec.from_file(str(assets / URDF))
    for old, new in RENAME.items():
        spec.body(old).name = new
    base = spec.body("base")
    base.add_site(name="pinch", pos=[0, 0, PINCH_Z], size=[0.004] * 3, rgba=[1, 0, 0, 0.5])
    # visual meshes never collide; collision meshes and pad boxes do
    for g in spec.geoms:
        mesh = g.meshname or ""
        if mesh.startswith("v_"):
            g.contype, g.conaffinity, g.group = 0, 0, 1
        else:
            g.group = 3
    for side in ("left", "right"):
        pad = spec.body(f"{side}_pad")
        for g in pad.geoms:
            g.friction = [1.2, 0.01, 0.001]
            g.condim = 4
            g.solref, g.solimp = [0.004, 1], [0.95, 0.99, 0.001, 0.5, 2]
    names = [b.name for b in spec.bodies if b.name not in ("world", "")]
    for i, a in enumerate(names):                          # the linkage must not collide with itself
        for b in names[i + 1:]:
            spec.add_exclude(name=f"x_{a}_{b}", bodyname1=a, bodyname2=b)
    for j in spec.joints:
        j.armature = 2e-3
        j.damping = [0.02, 0.0, 0.0]
    # the URDF loader already turns the mimic joints into joint equalities (checked by the tests); none added here
    g = np.zeros(10)
    g[0] = KP * FINGER_MAX / 255.0
    b = np.zeros(10)
    b[1] = -KP
    spec.add_actuator(name="fingers_actuator", target=FINGER_JOINT, trntype=mujoco.mjtTrn.mjTRN_JOINT,
                      gaintype=mujoco.mjtGain.mjGAIN_FIXED, biastype=mujoco.mjtBias.mjBIAS_AFFINE,
                      gainprm=g, biasprm=b, ctrllimited=True, ctrlrange=[0, 255],
                      forcelimited=True, forcerange=[-GRIP_FORCE_N_M, GRIP_FORCE_N_M])
    return spec


# --- mobile base (RB-KAIROS = Robotnik Summit XLS chassis, four omni wheels) --------------------------------------------
# From the lab's expanded URDF (rbkairos_ur10_140f_d455f): base_link is 0.127 m above the footprint (= wheel radius), the arm
# base sits on the top plate 0.38062 m above base_link, wheels at (+-0.2225, +-0.2045) of base_link, radius 0.127, width 0.087.
# The chassis mesh spans x +-0.36, y +-0.289, z -0.061..0.382 in the base_link frame, so its top plate is the arm base plane.
# Modelling choices (stated, not hidden): the base is a PLANAR holonomic body (slide x, slide y, hinge yaw) driven by position
# servos on a velocity-limited setpoint (live/kairos_drive in sim/kairos_mobile.py); the wheels are visual and spin with the
# omni-wheel kinematics, the wheel/floor contact and the four wheel motors are NOT simulated. Mass of the base is the URDF's 125 kg
# plus wheels. The arm faces the chassis front (+x): the yaw convention of the real mount is not checked against the robot.
BASE_DIR = ASSETS / "base"
BASE_MESHES = ("summit_xls_chassis.stl", "summit_xls_chapas_inox_tapas.stl")
BASE_LINK_Z = -0.38062                 # base_link height relative to the arm base (the plate is at +0.38062 above base_link)
FLOOR_Z = BASE_LINK_Z - 0.127          # floor height when the arm base is at z = 0
WHEEL_R, WHEEL_W, WHEEL_XY = 0.127, 0.087, (0.2225, 0.2045)
CHASSIS_X, CHASSIS_Y = 0.36, 0.289     # collision footprint half extents (mesh bounding box)
CHASSIS_Z = (-0.061, 0.382)            # collision z range in the base_link frame
BASE_MASS = 125.0
BASE_JOINTS = ("base_x", "base_y", "base_yaw")
BASE_KP, BASE_KV = (4.0e4, 4.0e4, 8.0e3), (4.0e3, 4.0e3, 1.5e3)   # servo gains (N/m, N s/m; N m/rad, N m s/rad)
WHEELS = (("front_right", 1, -1), ("front_left", 1, 1), ("back_left", -1, 1), ("back_right", -1, -1))


def base_ready(assets: Path = BASE_DIR) -> bool:
    return all((assets / f).exists() for f in BASE_MESHES)


def mount_on_base(arm: mujoco.MjSpec) -> mujoco.MjSpec:
    """Root spec holding the planar KAIROS base with `arm` (UR10e + gripper, already attached) on its top plate.
    Names of the arm are unchanged; the three base actuators are appended AFTER the arm's so ctrl[:6] stays the arm."""
    if not base_ready():
        raise FileNotFoundError("KAIROS base meshes missing in sim/assets/kairos/base (lab asset, copied from the description)")
    spec = mujoco.MjSpec()
    for f in BASE_MESHES:
        spec.add_mesh(name=f[:-4], file=str((BASE_DIR / f).resolve()))
    base = spec.worldbody.add_body(name="kairos_base", pos=[0, 0, BASE_LINK_Z])
    for n, axis, typ in (("base_x", [1, 0, 0], mujoco.mjtJoint.mjJNT_SLIDE), ("base_y", [0, 1, 0], mujoco.mjtJoint.mjJNT_SLIDE),
                         ("base_yaw", [0, 0, 1], mujoco.mjtJoint.mjJNT_HINGE)):
        base.add_joint(name=n, type=typ, axis=axis, damping=0.0, armature=1.0)
    base.add_geom(name="kb_chassis_vis", type=G_MESH, meshname="summit_xls_chassis", contype=0, conaffinity=0, group=1,
                  rgba=[.82, .84, .86, 1], mass=BASE_MASS)
    base.add_geom(name="kb_plate_vis", type=G_MESH, meshname="summit_xls_chapas_inox_tapas", pos=[0, 0, 0.38062],
                  contype=0, conaffinity=0, group=1, rgba=[.7, .72, .75, 1], mass=0.0)
    zc, zh = (CHASSIS_Z[0] + CHASSIS_Z[1]) / 2, (CHASSIS_Z[1] - CHASSIS_Z[0]) / 2
    base.add_geom(name="kb_chassis_col", type=G_BOX, size=[CHASSIS_X, CHASSIS_Y, zh], pos=[0, 0, zc], contype=2,
                  conaffinity=2, group=3, rgba=[1, 0, 0, 0.1], mass=0.0)
    for name, sx, sy in WHEELS:
        w = base.add_body(name=f"kb_wheel_{name}", pos=[sx * WHEEL_XY[0], sy * WHEEL_XY[1], 0.0])
        w.add_joint(name=f"kb_wheel_{name}_joint", type=mujoco.mjtJoint.mjJNT_HINGE, axis=[0, 1, 0], damping=0.0, armature=0.01)
        w.add_geom(name=f"kb_wheel_{name}_vis", type=G_CYL, size=[WHEEL_R, WHEEL_W / 2, 0], quat=[0.70710678, 0.70710678, 0, 0],
                   contype=0, conaffinity=0, group=1, rgba=[.12, .12, .12, 1], mass=6.5)
    site = base.add_site(name="arm_mount", pos=[0, 0, -BASE_LINK_Z])
    spec.option.cone, spec.option.impratio, spec.option.timestep = mujoco.mjtCone.mjCONE_ELLIPTIC, 10, 0.002
    spec.option.integrator = arm.option.integrator            # keep the arm's integrator (implicitfast)
    spec.attach(arm, site=site, prefix="")                      # prefix "": the arm keeps its joint/site names
    for j, kp, kv in zip(BASE_JOINTS, BASE_KP, BASE_KV):         # appended after the arm's actuators
        g = np.zeros(10); g[0] = kp
        b = np.zeros(10); b[1], b[2] = -kp, -kv
        spec.add_actuator(name=f"{j}_servo", target=j, trntype=mujoco.mjtTrn.mjTRN_JOINT, gaintype=mujoco.mjtGain.mjGAIN_FIXED,
                          biastype=mujoco.mjtBias.mjBIAS_AFFINE, gainprm=g, biasprm=b)
    return spec


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--src", required=True)
    p.add_argument("--out", default=str(ASSETS))
    a = ap.parse_args()
    print(prepare(a.src, a.out))


if __name__ == "__main__":
    sys.exit(main())
