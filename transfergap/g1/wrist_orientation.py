"""Exploratory look at wrist orientation vs grasp outcome, from the logged diag.npz of results/g1_pelvis_drift_v1 (zero GPU).
Run where the scene xml + diag files live (the cluster pod):  python wrist_orientation.py RUN_DIR OUT_JSON
Per rollout: at the hand-close frame (t_go + 300/50 s, the same frame as g1/drift_features.py) take the right wrist-yaw link
orientation from forward kinematics of the logged qpos and report tilt from vertical, roll/pitch/yaw of the link relative to the
pelvis frame, and the pelvis drift. Outcome = block lift >= 5 cm (grasp). EXPLORATORY: n = 80, several features, no correction."""
import json, sys
from pathlib import Path
import numpy as np, mujoco

run, out = Path(sys.argv[1]), sys.argv[2]
CLOSE_S = 300 / 50.0
rows = []
for seed in range(1200, 1280):
    e = json.loads((run / f"seed{seed}_r0.episode.json").read_text())
    d = np.load(run / f"seed{seed}_r0.diag.npz", allow_pickle=True)
    m = mujoco.MjModel.from_xml_path(str(run / f"scene_seed{seed}.xml")); dat = mujoco.MjData(m)
    t = d["t"]; i = int(np.argmin(abs(t - (e["t_go_s"] + CLOSE_S))))
    dat.qpos[:d["qpos"].shape[1]] = d["qpos"][i]; mujoco.mj_kinematics(m, dat)
    bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "right_wrist_yaw_link"); pid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "pelvis")
    R = dat.xmat[bid].reshape(3, 3); Rp = dat.xmat[pid].reshape(3, 3); Rrel = Rp.T @ R
    tilt = {ax: float(np.degrees(np.arccos(np.clip(abs(R[2, k]), 0, 1)))) for k, ax in enumerate("xyz")}   # angle of link axis from vertical
    roll = float(np.degrees(np.arctan2(Rrel[2, 1], Rrel[2, 2]))); pitch = float(np.degrees(-np.arcsin(np.clip(Rrel[2, 0], -1, 1)))); yaw = float(np.degrees(np.arctan2(Rrel[1, 0], Rrel[0, 0])))
    s = e.get("states")
    z = [x["object_xyz"][2] for x in json.loads((run / f"seed{seed}_r0.episode.json").read_text()).get("states", [])] if s is None else [x["object_xyz"][2] for x in s]
    lift = 100 * (max(z) - z[0]) if z else float("nan")
    pel = d["qpos"][i][:2]
    rows.append({"seed": seed, "lift_cm": lift, "grasp": bool(lift >= 5), "tilt_x": tilt["x"], "tilt_y": tilt["y"], "tilt_z": tilt["z"],
                 "rel_roll": roll, "rel_pitch": pitch, "rel_yaw": yaw, "drift_cm": float(np.linalg.norm(pel) * 100)})
Path(out).write_text(json.dumps(rows))
print(len(rows), "rows;", sum(r["grasp"] for r in rows), "grasped")
