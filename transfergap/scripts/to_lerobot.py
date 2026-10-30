"""Verified data engine, step 2: convert the verified-success traces of scripts/export_dataset.py into a LeRobot-style dataset
(parquet per episode + meta/info.json, episodes.jsonl, tasks.jsonl). State-only: no camera frames yet (those need the GPU renderer).
Downsampled from the 100 Hz control ticks to --fps. observation.state = arm joint positions (rad); action = the position command
(arm joints + gripper) at the next sampled tick. Only episodes the physics scorer labelled successful are written; failures stay in index.json.

    python3 scripts/to_lerobot.py runs/dataset_v1 runs/dataset_v1_lerobot [--fps 25]
Uses pyarrow (system python). Format fields follow LeRobot v2.1 naming; not validated against the LeRobot loader here.
"""
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def main(src, dst, fps=25):
    src, dst = Path(src), Path(dst)
    idx = json.loads((src / "index.json").read_text())
    (dst / "data" / "chunk-000").mkdir(parents=True, exist_ok=True)
    (dst / "meta").mkdir(parents=True, exist_ok=True)
    robots = sorted({e["robot"] for e in idx["episodes"]})
    tasks = [{"task_index": 0, "task": "pick the block and place it in the tray, copying the person's demonstrated style"}]
    eps, gi, n_ok = [], 0, 0
    for e in idx["episodes"]:
        if not e["success"]:
            continue
        tr = json.loads((src / f"{e['name']}.json").read_text())["trace"]
        step = max(1, round(100 / fps))
        rows = tr[::step]
        T = len(rows)
        state = [r["q"] for r in rows]
        action = [rows[min(i + 1, T - 1)]["ctrl"] for i in range(T)]
        tbl = pa.table({"observation.state": state, "action": action, "timestamp": [i / fps for i in range(T)], "frame_index": list(range(T)),
                        "episode_index": [n_ok] * T, "index": list(range(gi, gi + T)), "task_index": [0] * T,
                        "robot": [e["robot"]] * T})
        pq.write_table(tbl, dst / "data" / "chunk-000" / f"episode_{n_ok:06d}.parquet")
        eps.append({"episode_index": n_ok, "tasks": [tasks[0]["task"]], "length": T, "robot": e["robot"], "seed": e["seed"], "source_demo": idx["demo"]})
        gi += T
        n_ok += 1
    (dst / "meta" / "episodes.jsonl").write_text("".join(json.dumps(x) + "\n" for x in eps))
    (dst / "meta" / "tasks.jsonl").write_text("".join(json.dumps(x) + "\n" for x in tasks))
    info = {"codebase_version": "v2.1", "robot_type": "+".join(robots), "total_episodes": n_ok, "total_frames": gi, "fps": fps, "splits": {"train": f"0:{n_ok}"},
            "features": {"observation.state": {"dtype": "float32", "shape": [6]}, "action": {"dtype": "float32", "shape": [7]}},
            "note": "state-only, simulation, derived from one human demonstration with the frozen fix stack; failures excluded (see index.json of the source run)"}
    (dst / "meta" / "info.json").write_text(json.dumps(info, indent=1))
    print(f"wrote {n_ok} verified episodes, {gi} frames, robots {robots} -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 25)
