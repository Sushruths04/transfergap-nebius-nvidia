"""Score the held-out perception_hard_v1 run against the acceptance bars frozen in its protocol (no thresholds here:
they are read from protocol.json). Writes heldout_scorecard.md next to it.

    python -m transfergap.sim.perception_hard_score --dir results/perception_hard_v1 --dev results/perception_hard_dev_d
"""
import argparse
import json
import math
from pathlib import Path

ROBOTS = ("ur5e", "ur10e", "kairos")


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - h) / d), min(1.0, (c + h) / d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--dev", required=True)
    a = ap.parse_args()
    d, dev = Path(a.dir), Path(a.dev)
    P = json.loads((d / "protocol.json").read_text())
    must, sizes = P["acceptance"]["must_pass_ge_0.90"], P["sizes_half_m"]
    R = {r: json.loads((d / r / "heldout" / "results.json").read_text())["cells"] for r in ROBOTS}
    D = {r: json.loads((dev / r / "dev" / "results.json").read_text())["cells"] for r in ROBOTS}
    pooled = lambda cells, c: (sum(cells[f"{c}/half{h:g}"]["success"] for h in sizes),
                               sum(cells[f"{c}/half{h:g}"]["n"] for h in sizes))
    L = [f"# Held-out scorecard, protocol {P['protocol']} (frozen at code commit {P['code_commit_at_freeze'][:7]})", "",
         f"Held-out seeds {P['heldout_seeds']} (40 seeds x 3 cube sizes = 120 episodes per cell), pooled; Wilson 95% interval; "
         "dev rate (seeds 0-9) for comparison. `*` = acceptance bar (>= 0.90 pooled, declared before the run).", "",
         "| condition | " + " | ".join(ROBOTS) + " |", "|---|" + "---|" * len(ROBOTS)]
    fails = []
    for c in P["conditions"]:
        cells = []
        for r in ROBOTS:
            k, n = pooled(R[r], c)
            lo, hi = wilson(k, n)
            dk, dn = pooled(D[r], c)
            cells.append(f"{k}/{n} [{lo:.2f}, {hi:.2f}] (dev {dk/dn:.2f})")
            if c in must and k / n < 0.90:
                fails.append((c, r, k, n))
        L.append(f"| {'*' if c in must else ''}{c} | " + " | ".join(cells) + " |")
    L += ["", f"**Acceptance: {len(must) * len(ROBOTS) - len(fails)} of {len(must) * len(ROBOTS)} bar cells met.** "
          + ("Failed: " + str(fails) if fails else "None failed."), "",
          "Report-only conditions are stress tests beyond a stated tolerance (camera calibration error, 20 mm depth noise, "
          "arm in view without a retry); their rates are results, not pass/fail."]
    (d / "heldout_scorecard.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[-4:]))


if __name__ == "__main__":
    main()
