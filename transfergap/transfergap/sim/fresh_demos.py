"""Re-evaluate the frozen demo stacks on NEVER-USED seeds 5000-5059 (removes the adaptive-seed-reuse caveat).
No stack, constant or code is changed; stacks are those of demo_generalization_v5 (question A/B) and user_demo_v1.
  python -m transfergap.sim.fresh_demos
"""
import json
from pathlib import Path
from . import errors_demo as E
from .demo_budget import _job, _pool, by_cond, cond_table, gap

SEEDS = list(range(5000, 5060))
P1 = ("speed_cap_3", "look_again", "touch_probe_calibration", "speed_cap_2", "safe_path_v2")
P2 = ("look_again", "touch_probe_calibration", "safe_path_v2")
RUNS = [("P1_notebook", "runs/demos/pexels_8135753_notebook.npz", P1),
        ("P1_markers", "runs/demos/pexels_8135753_markers.npz", P1),
        ("P1_orange_marker", "runs/demos/pexels_8135753_orange_marker.npz", P1),
        ("P1_notepad", "runs/demos/pexels_8135753_notepad.npz", P1),
        ("P2_box_own_stack", "runs/demos/pexels_7205253_woman_box_v2.npz", P2),
        ("P2_box_P1_stack", "runs/demos/pexels_7205253_woman_box_v2.npz", P1),
        ("P3_recording_P1_stack", "runs/demos/live/user_take1_right.npz", P1)]
def main():
    out = Path("runs/fresh_demos"); out.mkdir(parents=True, exist_ok=True)
    res = {"seeds": [SEEDS[0], SEEDS[-1]], "rows": {}}
    for name, path, fixes in RUNS:
        spec = E.parse_demo_spec(path)
        for robot in ("ur5e", "ur10e"):
            jobs = [(spec, s, "full", None, robot, (), "raw") for s in SEEDS] + \
                   [(spec, s, "full", None, robot, fixes, "stack") for s in SEEDS]
            eps = _pool(_job, jobs)
            g = by_cond(eps)
            res["rows"][f"{name}/{robot}"] = {"conditions": cond_table(eps), "gap": gap(g["raw"], g["stack"]), "stack": list(fixes)}
            c = res["rows"][f"{name}/{robot}"]["conditions"]
            print(name, robot, {k: (v.get("successes", v.get("k")), v.get("n")) for k, v in c.items()}, flush=True)
    (out / "summary.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
