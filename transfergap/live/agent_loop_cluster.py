"""Nemotron-in-the-loop diagnosis for a NEW demo: simulation on the GPU cluster, the Nemotron call from the laptop.

    set -a; . <env with NEBIUS_API_KEY>; set +a
    python live/agent_loop_cluster.py --demo-remote /ws/transfergap/demos/newdemo_r6.npz --demo-local /tmp/nd/newdemo_r6.npz \
        --robots ur5e ur10e --max-rounds 4

Per robot and round (pre-registered protocol demo_budget_v1, one correction per round):
  1 dev stage on the cluster (render venv, CPU; seeds 0-59)        -> protocol.json + dev_results.json, committed in the cluster checkout
  2 Nemotron-3-Super (Nebius Token Factory) picks one correction from the fixed menu, from the dev statistics only (sim/demo_agent.py);
    the key stays on the laptop, only the aggregate dev statistics leave the cluster
  3 agent_choice.json is committed BEFORE the held-out trials, then the held-out stage runs on the cluster (seeds 1000-1059; the rule's
    choice and, if different, the agent's are both evaluated)
The next round adopts the agent's valid choice (else the rule's) until the diagnosis stops or --max-rounds is reached.
The cluster checkout is a git repo on the volume (ctx_unified_r6) because the protocol refuses to run on uncommitted files.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NS = "isaac-sim"
REMOTE = "/ws/transfergap/ctx_unified_r6"
PY = "/ws/transfergap/envs/render/bin/python"


def kubectl(*a, check=True, capture=True, tries=8):
    """The VPN link to the cluster drops now and then: retry (every call here is idempotent)."""
    import time
    r = None
    for _ in range(tries):
        r = subprocess.run(["kubectl", *a], capture_output=capture, text=True)
        if not r.returncode or not check:
            return r
        time.sleep(6)
    raise RuntimeError(f"kubectl {' '.join(a[:3])} failed after {tries} tries: {(r.stderr or r.stdout)[-300:]}")


def run_retry(cmd, tries=8):
    import time
    for _ in range(tries):
        r = subprocess.run(cmd, capture_output=True)
        if not r.returncode:
            return r
        time.sleep(6)
    raise RuntimeError(f"{' '.join(cmd[:4])} failed after {tries} tries")


def pod():
    return kubectl("get", "pods", "-n", NS, "-l", "app=tg-dev", "-o", "name").stdout.split()[0].split("/")[1]


def remote(p, script):
    return kubectl("exec", "-n", NS, p, "--", "bash", "-c", script).stdout


def res_name(tag, robot, base):
    return f"demo_budget_v1_{tag}_{robot}" + ("" if not base else "__after-" + "+".join(base))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo-remote", required=True)
    ap.add_argument("--demo-local", required=True)
    ap.add_argument("--robots", nargs="+", default=["ur5e", "ur10e"])
    ap.add_argument("--max-rounds", type=int, default=4)
    a = ap.parse_args()
    if not os.environ.get("NEBIUS_API_KEY"):
        sys.exit("NEBIUS_API_KEY not set")
    p = pod()
    env = f"cd {REMOTE} && export MUJOCO_GL=egl PYTHONPATH=. OMP_NUM_THREADS=1"
    sys.path.insert(0, str(ROOT))
    from transfergap.sim import errors_demo as E
    tag = E.parse_demo_spec(a.demo_local)["tag"]
    summary = {}
    for robot in a.robots:
        base, rounds = (), []
        for rnd in range(a.max_rounds):
            name = res_name(tag, robot, base)
            b = ",".join(base)
            print(f"[{robot} round {rnd}] base={b or '-'} dev ...", flush=True)
            remote(p, f"{env} && {PY} -m transfergap.sim.demo_budget dev --demo {a.demo_remote} --robot {robot} --strict"
                      + (f" --base {b}" if b else "") + f" > /ws/transfergap/dev_{robot}_{rnd}.log 2>&1; "
                      f"git add results/{name}; git commit -q -m 'dev {robot} round {rnd}'; echo done")
            proto = json.loads(remote(p, f"cat {REMOTE}/results/{name}/protocol.json"))
            if proto.get("chosen_correction") is None:
                print(f"[{robot} round {rnd}] diagnosis stops: no useful fix left", flush=True)
                rounds.append({"round": rnd, "base": list(base), "stop": True})
                break
            local = ROOT / "results" / name
            local.mkdir(parents=True, exist_ok=True)
            tar = run_retry(["kubectl", "exec", "-n", NS, p, "--", "tar", "-C", f"{REMOTE}/results/{name}", "-cf", "-", "."]).stdout
            subprocess.run(["tar", "-xf", "-", "-C", str(local)], input=tar, check=True)
            cmd = [sys.executable, "-m", "transfergap.sim.demo_agent", "--demo", a.demo_local, "--robot", robot, "--base", b]
            out = subprocess.run(cmd, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True, timeout=900)
            print(out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-300:], flush=True)
            choice = json.loads((local / "agent_choice.json").read_text())
            for f in ("agent_choice.json", "agent_receipt.json"):
                run_retry(["kubectl", "cp", str(local / f), f"{NS}/{p}:{REMOTE}/results/{name}/{f}"])
            print(f"[{robot} round {rnd}] heldout ...", flush=True)
            remote(p, f"{env} && git add results/{name}; git commit -q -m 'agent choice {robot} round {rnd}'; "
                      f"{PY} -m transfergap.sim.demo_budget heldout --demo {a.demo_remote} --robot {robot}"
                      + (f" --base {b}" if b else "") + f" > /ws/transfergap/heldout_{robot}_{rnd}.log 2>&1; tail -3 /ws/transfergap/heldout_{robot}_{rnd}.log")
            tar = run_retry(["kubectl", "exec", "-n", NS, p, "--", "tar", "-C", f"{REMOTE}/results/{name}", "-cf", "-", "."]).stdout
            subprocess.run(["tar", "-xf", "-", "-C", str(local)], input=tar, check=True)
            held = json.loads((local / "heldout_results.json").read_text()) if (local / "heldout_results.json").exists() else {}
            nxt = choice.get("agent_choice") if choice.get("valid") else choice["rule_choice"]
            rounds.append({"round": rnd, "base": list(base), "rule": choice["rule_choice"], "agent": choice.get("agent_choice"),
                           "agree": choice.get("agrees_with_rule"), "valid": choice.get("valid"),
                           "heldout_gap": held.get("paired_gap_corrected_minus_full"), "adopted": nxt})
            base = base + (nxt,)
        summary[robot] = rounds
    (ROOT / "results" / f"demo_agent_loop_{tag}.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
