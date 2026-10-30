"""GPU-VM side: GEM-X `hpe_results.pt` -> per-frame SOMA joint positions (npz). Run inside the GEM-X environment,
from the GEM-X repository root (so `inputs/soma_assets` resolves as in GEM-X's own demo):

    python /path/to/gemx_export_joints.py --pt outputs/demo_soma/<clip>/hpe_results.pt --out <clip>_joints.npz

Mirrors GEM-X `scripts/demo/demo_soma.py` (commit 32992550): `SomaLayer(data_root="inputs/soma_assets",
low_lod=True, identity_model_type="mhr", mode="warp")` applied to `body_params_global`, reading `["joints"]`
(77 joints per frame). The output keeps the raw SOMA world frame (y up); the laptop side
(`transfergap.demo.gemx`) converts it to the demo frame. Joint names are taken from the SOMA asset file and
written alongside so the laptop side never guesses the joint order. UNVERIFIED until first run on the VM.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from gem.utils.soma_utils.soma_layer import SomaLayer


def body_params(pred, key="body_params_global"):
    if key in pred:
        return pred[key]
    tail = "_params_" + key.replace("body_params_", "")
    for k in pred:
        if k.endswith(tail):
            return pred[k]
    raise KeyError(key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--assets", default="inputs/soma_assets")
    a = ap.parse_args()
    pred = torch.load(a.pt, map_location="cpu")
    params = {k: v.float().cuda() for k, v in body_params(pred).items()}
    soma = SomaLayer(data_root=a.assets, low_lod=True, device="cuda:0", identity_model_type="mhr", mode="warp")
    with torch.no_grad():
        joints = soma(**params)["joints"].cpu().numpy()            # (T, 77, 3), SOMA world frame
    names = None
    for npz in Path(a.assets).rglob("SOMA_neutral.npz"):
        z = np.load(npz)
        key = next((k for k in z.files if k.endswith("joint_names")), None)
        if key is not None:
            names = [str(n) for n in z[key]]
            break
    if names is not None and len(names) == joints.shape[1] + 1 and names[0] == "Root":
        names = names[1:]                                           # SomaLayer outputs the 77 non-root joints
    if names is None or len(names) != joints.shape[1]:
        raise SystemExit(f"cannot match joint names ({None if names is None else len(names)}) to {joints.shape}")
    np.savez_compressed(a.out, joints=joints, joint_names=np.array(names), fps=a.fps, frame="soma_world_y_up",
                        meta=json.dumps({"source_pt": Path(a.pt).name, "gemx_layer": "SomaLayer(mhr, warp, low_lod)"}))
    print(f"wrote {a.out}: joints {joints.shape}")


if __name__ == "__main__":
    main()
