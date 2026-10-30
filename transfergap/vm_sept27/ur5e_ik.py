"""Closed-loop IK for the UR5e arm using Pinocchio (CLIK / damped least-squares),
following the Open-TeleVision pattern referenced in the TransferGap plan.
Solves for 6 joint angles given a target end-effector (ee_link) pose.
"""
import numpy as np
import pinocchio as pin
from pathlib import Path

URDF_PATH = str(Path.home() / 'dex-urdf' / 'robots' / 'arms' / 'ur5e' / 'ur5e.urdf')

model = pin.buildModelFromUrdf(URDF_PATH)
data = model.createData()
EE_FRAME = 'ee_link'
ee_id = model.getFrameId(EE_FRAME)
print(f'Loaded UR5e: {model.nq} DOF, target frame "{EE_FRAME}" id={ee_id}')

def solve_ik(target_pos, target_quat_wxyz, q_init=None, max_iters=200, eps=1e-4, damp=1e-6):
    """Damped least-squares CLIK. target_quat_wxyz: [w,x,y,z]."""
    q = q_init.copy() if q_init is not None else pin.neutral(model)
    w, x, y, z = target_quat_wxyz
    target_R = pin.Quaternion(w, x, y, z).matrix()
    target_se3 = pin.SE3(target_R, np.array(target_pos))

    for i in range(max_iters):
        pin.forwardKinematics(model, data, q)
        pin.updateFramePlacement(model, data, ee_id)
        current_se3 = data.oMf[ee_id]
        err = pin.log(current_se3.inverse() * target_se3).vector
        if np.linalg.norm(err) < eps:
            return q, True, i
        J = pin.computeFrameJacobian(model, data, q, ee_id, pin.ReferenceFrame.LOCAL)
        JJt = J.dot(J.T) + damp * np.eye(6)
        dq = J.T.dot(np.linalg.solve(JJt, err))
        q = pin.integrate(model, q, dq * 0.5)
    return q, False, max_iters

# Test: solve for a plausible reachable target near the arm's typical workspace
target_pos = [0.4, 0.2, 0.4]
target_quat = [1.0, 0.0, 0.0, 0.0]  # identity orientation
q_sol, converged, iters = solve_ik(target_pos, target_quat)
print(f'IK converged={converged} in {iters} iters')
print(f'Solution joint angles (rad): {q_sol}')

# Verify by forward kinematics
pin.forwardKinematics(model, data, q_sol)
pin.updateFramePlacement(model, data, ee_id)
achieved = data.oMf[ee_id]
print(f'Target pos: {target_pos}')
print(f'Achieved pos: {achieved.translation}')
print(f'Position error: {np.linalg.norm(achieved.translation - np.array(target_pos)):.6f} m')
