#!/usr/bin/env bash
# Creates transfergap/.venv and fetches UR5e, UR10e + Robotiq 2F-85 from mujoco_menagerie (Apache-2.0).
# NOTICE: mujoco_menagerie assets are Apache-2.0 (c) Google DeepMind and contributors; not redistributed here.
# If assets/MENAGERIE_COMMIT exists, that exact commit is checked out (pinned); otherwise HEAD is used and recorded.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -d "$ROOT/.venv" ] || python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install -q --upgrade pip
"$ROOT/.venv/bin/pip" install -q "mujoco>=3.2" numpy "imageio[ffmpeg]"
A="$ROOT/transfergap/sim/assets"; M="$A/menagerie"
DIRS=(universal_robots_ur5e universal_robots_ur10e robotiq_2f85)
PIN=""; [ -f "$A/MENAGERIE_COMMIT" ] && PIN="$(tr -d '[:space:]' < "$A/MENAGERIE_COMMIT")"
if [ ! -d "$M/.git" ]; then
  mkdir -p "$A"
  git clone -q --filter=blob:none --no-checkout --depth 1 https://github.com/google-deepmind/mujoco_menagerie "$M"
fi
git -C "$M" sparse-checkout set "${DIRS[@]}"      # also extends an older clone that lacks the UR10e
if [ -n "$PIN" ] && [ "$(git -C "$M" rev-parse HEAD 2>/dev/null || true)" != "$PIN" ]; then
  git -C "$M" fetch -q --filter=blob:none --depth 1 origin "$PIN"
  git -C "$M" checkout -q "$PIN"
else
  git -C "$M" checkout -q
fi
for d in "${DIRS[@]}"; do [ -d "$M/$d" ] || { echo "missing $d after checkout" >&2; exit 1; }; done
git -C "$M" rev-parse HEAD > "$A/MENAGERIE_COMMIT"
echo "ready: $("$ROOT/.venv/bin/python" -c 'import mujoco;print("mujoco",mujoco.__version__)'), menagerie $(cat "$A/MENAGERIE_COMMIT")"
