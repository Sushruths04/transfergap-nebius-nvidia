---
type: nvidia-model
updated: 2026-09-30
tags: [nvidia, gem-x, soma, perception, core]
---

# GEM-X (with SOMA)

**Role.** Core. Human RGB video -> 77-joint SOMA body motion -> SMPL -> [[SONIC]]. Its error is the perception share of the G1 gap budget. From the NVIDIA DAIR group (GENMO, arXiv 2505.01425, ICCV 2025).

| Field | Value | Tag |
|---|---|---|
| Code | NVlabs/GEM-X, pinned `32992550dba114c62243fb55e361311972dce8f9`; Apache-2.0 | VERIFIED |
| Checkpoint license | UNVERIFIED |  |
| Checkpoint | `gem_soma.ckpt` auto-downloads from HF unauthenticated | [[Implementation Status]] |
| Input | A video file (`--video path.mp4`) works; no camera needed on the cloud box | VERIFIED |
| Status | Installed and run end-to-end on a placeholder Wikimedia clip Sept 27; output `hpe_results.pt` (2.4 MB). Files only on the VM | [[Implementation Status]] |

**Bridge command (proven):** `soma_pt_to_sonic_v3.py --pt <hpe_results.pt> --fps 30 --loop`. Alternative not yet re-verified: `webcam_stream.py --source <video>`. Env vars `GEMX_ROOT`, `SONIC_ROOT`.

**Gotchas.**
- The bridge script needs `soma` (GEM-X) and `gear_sonic` in one Python env: `uv pip install -e gear_sonic --no-deps` into GEM-X's venv, plus `pyzmq`, `msgpack`, `msgpack_numpy`.
- Install script adds `onnxruntime` only for macOS; the YOLOX detector needs `onnxruntime-gpu` on Linux.
- `KeyError: 'joint_parent_ids'`: the current HF `nvidia/soma-x` `SOMA_neutral.npz` uses a newer schema than the pinned `soma` submodule (v0.3.1). Symlink `inputs/soma_assets` to the submodule's `third_party/soma/assets/`.
- `python3.12-dev` + `ninja-build` in one apt command failed silently; install `python3.12-dev` alone and `ninja` via pip.
- Wrists and fingers are not tracked; streamed as zeros. Use GEM-X hand keypoints rather than WiLoR (CC BY-NC-ND).
- `soma-retargeter` skipped (needs an SSH key; not needed).

**Sources.** https://github.com/NVlabs/GEM-X · [[10_nvidia_stack]] · [[Implementation Status]] · [[Lessons Learned]] · [[People and Labs]] · [[Knowledge/README|Knowledge]]
