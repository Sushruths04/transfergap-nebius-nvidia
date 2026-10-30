"""Placement-gap metric per robot and condition from rollout episode logs (episodes_<robot>.jsonl).

For each episode: gap = horizontal distance (cm) between the object's final position and the goal, max lift (cm) above the start height,
and whether the object ended released within the task's position tolerance. Reports median, p90 and the within-tolerance rate with a
Wilson interval. Reads logs only; nothing is simulated. Usage: python contact_gap.py <dir with episodes_*.jsonl> <out.json>
"""
import json, math, sys
from pathlib import Path


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]


def main(src, out):
    res = {}
    for f in sorted(Path(src).glob("episodes_*.jsonl")):
        robot = f.stem.split("_", 1)[1]
        rows = {}
        for line in open(f):
            e = json.loads(line)
            s = e["states"]
            goal = e["task"]["goal_xyz"]
            tol = e["task"]["position_tolerance_m"]
            end = s[-1]["object_xyz"]
            gap = math.hypot(end[0] - goal[0], end[1] - goal[1]) * 100
            lift = (max(x["object_xyz"][2] for x in s) - s[0]["object_xyz"][2]) * 100
            ok = bool(s[-1]["released"]) and gap <= tol * 100
            rows.setdefault(e["method"], []).append((gap, lift, ok, tol * 100))
        res[robot] = {}
        for m, v in rows.items():
            g = [a[0] for a in v]
            k = sum(a[2] for a in v)
            res[robot][m] = {"n": len(v), "tolerance_cm": v[0][3], "gap_median_cm": round(pct(g, .5), 2), "gap_p90_cm": round(pct(g, .9), 2),
                             "lift_median_cm": round(pct([a[1] for a in v], .5), 2), "within_tol": k, "within_tol_ci95": [round(x, 3) for x in wilson(k, len(v))]}
    json.dump({"source_dir": str(src), "note": "gap = final object xy vs goal xy; simulation only", "results": res}, open(out, "w"), indent=1)
    for r, d in res.items():
        for m, x in d.items():
            print(f"{r:7s} {m:24s} n={x['n']} median gap {x['gap_median_cm']:6.2f} cm  p90 {x['gap_p90_cm']:6.2f}  within tol {x['within_tol']}/{x['n']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
