"""Combine UR5e + Robotiq 2F-85 into one MuJoCo scene for the TransferGap
wheeled-arm (Line B) embodiment, using MuJoCo's native MjSpec attach API.
Public models only: mujoco_menagerie's universal_robots_ur5e + robotiq_2f85.
"""
import mujoco
from pathlib import Path

MENAGERIE = Path.home() / 'mujoco_menagerie'
OUT_DIR = Path.home() / 'transfergap_wheeled_arm'

arm_spec = mujoco.MjSpec.from_file(str(MENAGERIE / 'universal_robots_ur5e' / 'ur5e.xml'))
gripper_spec = mujoco.MjSpec.from_file(str(MENAGERIE / 'robotiq_2f85' / '2f85.xml'))

# Find the attachment site on the arm's wrist
site = arm_spec.site('attachment_site')
assert site is not None, 'attachment_site not found on ur5e'

# Attach the gripper's worldbody-level bodies at that site
attached = arm_spec.attach(gripper_spec, site=site, prefix='gripper_')

# Add a ground plane + light so the combined model is directly viewable
arm_spec.worldbody.add_geom(
    name='floor', type=mujoco.mjtGeom.mjGEOM_PLANE,
    size=[2, 2, 0.1], pos=[0, 0, 0],
    rgba=[0.8, 0.8, 0.8, 1],
)
arm_spec.worldbody.add_light(name='top_light', pos=[0, 0, 2], type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL)

model = arm_spec.compile()
print(f'Compiled OK: {model.nq} DOF, {model.nbody} bodies, {model.ngeom} geoms')

out_path = OUT_DIR / 'ur5e_2f85_scene.xml'
xml_str = arm_spec.to_xml()
out_path.write_text(xml_str)
print(f'Saved combined scene to {out_path}')
