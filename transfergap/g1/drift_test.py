"""Apply the frozen protocol of results/g1_pelvis_drift_v1 to extracted rows (output of drift_features.py on seeds 1200-1279)."""
import json, sys
from math import comb
import numpy as np

proto = json.load(open(sys.argv[2])); rows = json.load(open(sys.argv[1]))
mu, sd, thr = proto["position_window"]["mu"], proto["position_window"]["sd"], proto["drift_threshold_cm"]
inw = [r for r in rows if all(abs(r[k] - mu[k]) <= 2 * sd[k] for k in ("dx", "dy", "dz"))]
lo = [r for r in inw if r["drift_cm"] < thr]; hi = [r for r in inw if r["drift_cm"] >= thr]
g = lambda L: sum(r["lift_cm"] >= 5 for r in L)
def fisher(a, b, c, d):                       # one-sided: grasp more likely in the low-drift group
    n = a + b + c + d; r1 = a + b; c1 = a + c
    return sum(comb(c1, x) * comb(n - c1, r1 - x) for x in range(a, min(r1, c1) + 1)) / comb(n, r1)
out = dict(n_rollouts=len(rows), n_grasp_all=g(rows), n_in_window=len(inw), n_low=len(lo), n_high=len(hi),
           grasp_low=g(lo), grasp_high=g(hi))
enough = len(inw) >= 30 and min(len(lo), len(hi)) >= 8
if enough:
    pl, ph = g(lo) / len(lo), g(hi) / len(hi)
    p = fisher(g(lo), len(lo) - g(lo), g(hi), len(hi) - g(hi))
    out.update(p_low=pl, p_high=ph, diff=pl - ph, fisher_one_sided=p, replicated=bool(pl - ph >= 0.25 and p < 0.05))
else:
    out["verdict"] = "underpowered: fewer than 30 in-window rollouts or fewer than 8 in a group"
print(json.dumps(out, indent=2))
