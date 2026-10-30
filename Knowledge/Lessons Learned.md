---
type: lessons
updated: 2026-09-30
tags: [lessons, gotchas, nebius, sonic, tooling]
---

# Lessons Learned

Practical gotchas already hit, so nobody repeats them. Source is [[Implementation Status]] unless noted. Back to [[Home]] · [[Knowledge/README|Knowledge]].

## Nebius and cloud
- **Spot preemption.** The preemptible L40S was preempted mid-TensorRT build (clean `systemd poweroff`, not an OOM). Restart failed with `NotEnoughResources: VM schedule timeout`. Fix: snapshot the boot disk, create a new on-demand instance from the snapshot. See [[Nebius Infrastructure]].
- **Image project IDs are region-scoped.** `project-e07public-images` resolves only `eu-south1`; `eu-north1` uses `project-e00public-images`.
- **Preemptible cannot convert.** `preemptible spec cannot be removed after instance creation`: recreate. Preemptible needs `--recovery-policy fail` and `--preemptible-on-preemption stop`.
- **Preset change forbidden** on `gpu-l40s-a`: delete the instance object (disk snapshotted first) and recreate with a larger preset.
- **Stop, do not delete**, when idle; never infer billing state (see banner).
- **CLI auth expired**: needs an interactive `nebius profile create`; an agent cannot do it.

## SONIC / GEM-X
- **`deploy.sh sim` interactive `[Y/n]` prompt** is undocumented; `nohup` hits EOF and exits. Use `echo y | bash deploy.sh sim` or run in tmux.
- **tmux needed** for raw single-keypress controls (`tmux send-keys`); no `--pty` option.
- **`]` starts the control loop.** `#` (switch to ZMQ) alone leaves the binary in `WAIT_FOR_CONTROL`, so `g1_debug` never appears.
- **Port 5555 taken** by `nv-hostengine`; use `--camera-port 5560` (and `--port 5550` for the GR00T server).
- **`MUJOCO_GL=egl`** for headless image publishing, or it tries to open an X11/GLFW window.
- **`soma_assets` symlink** to the submodule's bundled assets avoids the `KeyError: 'joint_parent_ids'` schema mismatch.
- **Missing deps** surfaced one at a time: `pyzmq`, `msgpack`, `msgpack_numpy`, `onnxruntime-gpu`; install `gear_sonic` into GEM-X's venv (`uv pip install -e gear_sonic --no-deps`).
- **chumpy / uv build fix.** `chumpy` (a WiLoR dependency) has a legacy `setup.py` needing `pip` and `setuptools`, absent in a minimal `uv` venv: `uv pip install pip setuptools wheel`, then `--no-build-isolation`.
- **apt gotcha.** Combined `apt-get install python3.12-dev ninja-build` failed silently; install `python3.12-dev` alone, `ninja` via pip.
- **TensorRT 10.13 exactly**; newer versions can give incorrect inference. It is a gated download, not scriptable.
- **README vs tutorial contradiction** on `--zmq-port/--zmq-topic` for `deploy.sh` (flags swallowed as the positional mode); follow the tutorial. Upstream PR candidate.
- **Sim scene assets**: copy mesh assets into a merged `assets/` folder or the saved XML's relative paths break.
- **Frame mismatch**: MuJoCo `base` has `quat="0 0 0 -1"` (180 degrees about Z); URDF does not. Negate target X/Y for URDF-frame IK; 7.2 mm residual remains from the two models' attachment points.
- **Nondeterminism** of SONIC+MuJoCo (issue #274): several rollouts per G1 trial.
- **`webcam_stream.py --source <video>`** is untested by us; the two-step path is proven.

## Data and formats
- **LeRobot v2.1** required by GR00T at the pinned commit; `pip install lerobot` writes v3. See [[GR00T N1.7]].
- **HiPHI** needs unit/axis conversion (cm to m, Y-up to Z-up, ZXY Euler); validate with a round-trip FK check.
- **GEM-X streams zero hands**, so G1 hands never close.
- **Pin upstream commits**; `main` moves.

## Research and tooling process
- **WebFetch paraphrase risk.** Summarizing fetch tools can invent or misattribute flags (the GR00T HF card fetch looked conflated with N1/N1.5). VERIFIED means the primary page was fetched, not the full PDF read. Read source with `git show` before running any command; never run a command from a paraphrase (`transfergap/scripts/gpu_bootstrap.md` rule).
- **Heredoc git commits are blocked by the permission classifier.** Use plain `git commit -m "..." -m "..."` ([[Agent Handoff]]).
- **`runs/` is gitignored**, so the Nemotron receipt needs the user's `git add -f`.
- **Nothing authored on the VM is in git.** Copy code off first: `build_scene.py`, `ur5e_ik.py`, `gripper_heuristic.py`, scene files, TensorRT build.
- **Blog numbers vs paper numbers.** The RHO blog's figures are not in the paper's abstract; do not cite them as the paper's ([[01_transfer_sota]]).
- **Report 03 said a demo URL was mandatory; the rules page says not required for Physical AI.** Rules page wins.
- **Protocol drift bug**: `summarize()` could pool episodes with drifting tolerances; now rejected (`validate_protocol_consistency`).
- **Simulator oracle trap**: policies/corrections must not read `sim.check_success`.
- **Sweep reading**: grip-force axis is uninformative (nominal grip about 180x block weight); failures are almost all `no_lift`.

See [[Decision Log]], [[Ideas Backlog]].
