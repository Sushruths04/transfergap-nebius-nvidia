"""Replay a GEM-X hpe_results.pt to SONIC as SMPL Protocol v3 (like upstream soma_pt_to_sonic_v3.py) with a hold:
the first frame is streamed repeatedly until --go-file exists, then the clip plays once at --fps, then --done-file is
written. Needed because SONIC only tracks the stream after ENTER switches it to ZMQ mode; frames sent before that are
consumed and dropped (found 2026-10-02: a whole 50 s clip played out before streaming was enabled).
Run from the SONIC repo root in the GEM-X venv:
    python ~/transfergap_g1/live/pt_stream.py --gemx-root ~/GEM-X --sonic-root . --pt X.pt --fps 21.4 \
        --go-file RUN/go --done-file RUN/done
"""
import argparse
import os
import sys
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gemx-root", required=True)
    ap.add_argument("--sonic-root", required=True)
    ap.add_argument("--pt", required=True)
    ap.add_argument("--fps", type=float, required=True)
    ap.add_argument("--go-file", required=True)
    ap.add_argument("--done-file", required=True)
    ap.add_argument("--smooth", type=float, default=0.5)
    ap.add_argument("--port", type=int, default=5556)
    a = ap.parse_args()
    sys.path.insert(0, str(Path(a.gemx_root).expanduser()))
    sys.path.insert(0, str(Path(a.sonic_root).expanduser() / "gear_sonic/examples/live_camera_teleop"))
    import torch
    from gem.utils.soma_utils.soma_layer import SomaLayer
    from soma_to_smpl import SomaToSmpl, SonicV3Publisher
    g = torch.load(a.pt, weights_only=False)["body_params_global"]
    T = g["body_pose"].shape[0]
    soma = SomaLayer(data_root=str(Path(a.gemx_root).expanduser() / "inputs" / "soma_assets"), low_lod=True,
                     device="cuda", identity_model_type="mhr", mode="warp")
    conv = SomaToSmpl(soma, device="cuda", smooth=a.smooth, sonic_root=a.sonic_root)
    frames = [conv.convert({k: g[k][t] for k in ("body_pose", "global_orient", "identity_coeffs", "scale_params")})
              for t in range(T)]
    pub = SonicV3Publisher(port=a.port, sonic_root=a.sonic_root)
    print(f"[pt_stream] {T} frames converted; holding the first pose until {a.go_file}", flush=True)
    dt = 1.0 / a.fps
    while not os.path.exists(a.go_file):
        pub.publish(frames[0])
        time.sleep(dt)
    print("[pt_stream] go", flush=True)
    t0 = time.time()
    for i, f in enumerate(frames):
        pub.publish(f)
        time.sleep(max(0.0, t0 + (i + 1) * dt - time.time()))
    for _ in range(int(2 * a.fps)):                  # hold the last pose briefly
        pub.publish(frames[-1])
        time.sleep(dt)
    Path(a.done_file).write_text("done\n")
    print("[pt_stream] done", flush=True)
    pub.close()


if __name__ == "__main__":
    main()
