"""Re-run the 500-seed arm study (conditions full and look_again, both arms) and require the committed successes exactly.
Must be a real script file with a main guard: multiprocessing 'spawn' cannot re-import a program read from stdin."""
import json
import sys

from transfergap.metrics import score_episode
from transfergap.sim import gap_budget_large as L
from transfergap.sim.gap_budget import _job, _pool


def main():
    ref = json.load(open("results/gap_budget_v3/summary.json"))["arms"]
    bad = []
    for robot in L.ROBOT_LIST:
        eps = _pool(_job, [(s, "full", c, "v2", robot) for s in L.SEEDS for c in (None, "look_again")])
        k = {}
        for e in eps:
            k[e["condition"]] = k.get(e["condition"], 0) + int(score_episode(e)["success"])
        got = (k["full"], k["full+look_again"])
        want = (ref[robot]["full_successes"], ref[robot]["corrections"]["look_again"]["successes"])
        print(robot, "full / look_again", got, "committed", want, flush=True)
        if got != want:
            bad.append(robot)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
