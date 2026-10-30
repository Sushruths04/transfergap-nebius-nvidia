"""Data layer for the TransferGap app. No Gradio imports, so it is unit-testable.

Everything here reads precomputed results or reuses ``transfergap.metrics`` / ``transfergap.hosted``.
Nothing in this module re-implements scoring or statistics.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


def find_project_root():
    """Directory holding the ``transfergap`` package and ``results/``.

    Order: $TRANSFERGAP_ROOT, the repo layout (app/ sits inside the project dir), then the app dir
    itself (a Hugging Face Space bundle with ``transfergap/`` and ``results/`` copied next to app.py).
    """
    candidates = [os.environ.get("TRANSFERGAP_ROOT"), APP_DIR.parent, APP_DIR]
    for cand in candidates:
        if cand and (Path(cand) / "transfergap" / "metrics.py").is_file():
            return Path(cand).resolve()
    raise RuntimeError("Cannot find the transfergap package; set TRANSFERGAP_ROOT to the project directory")


ROOT = find_project_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from transfergap.hosted import call_model  # noqa: E402
from transfergap.metrics import paired_gap, score_episode, summarize  # noqa: E402

RESULTS_DIR = ROOT / "results"
EXAMPLE_EPISODES = ROOT / "examples" / "fixture_episodes.jsonl"

# Runs recorded before summary.json carried a "robot" field. New runs should write "robot" themselves.
LEGACY_ROBOTS = {"gap_budget_v1": "UR5e + Robotiq 2F-85"}

# The fixed correction menu (mirrors transfergap.sim.errors.CORRECTIONS, which needs numpy to import).
CORRECTION_MENU = {
    "perception": ("look_again", "re-perceive the object from close range before grasping"),
    "calibration": ("touch_probe_calibration", "touch-probe a known fixture to re-estimate the tool frame"),
    "timing": ("speed_cap_3", "cap execution speed at 3x robot nominal"),
}
STAGE_LABELS = {"perception": "Perception", "calibration": "Tool calibration", "timing": "Timing",
                "retargeting": "Retargeting", "contact": "Contact / grasp", "all": "All stages at once"}


# ----------------------------------------------------------------------------------------- runs

@dataclass
class Run:
    name: str
    path: Path
    summary: dict
    robot: str
    robot_inferred: bool
    recorded: str
    warnings: list = field(default_factory=list)

    @property
    def commit(self):
        return (self.summary.get("git_commit") or "unknown")[:7]

    @property
    def has_heldout(self):
        return isinstance(self.summary.get("heldout"), dict) and "conditions" in self.summary["heldout"]


def _seed_range(seeds):
    if isinstance(seeds, (list, tuple)) and len(seeds) == 2:
        return f"{seeds[0]}-{seeds[1]}"
    return "unrecorded"


def recorded_date(summary_path, summary):
    """Explicit ``recorded_at`` if the run wrote one, else the git date of the commit that added the file."""
    explicit = summary.get("recorded_at")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()[:10]
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", summary_path.name],
                             cwd=summary_path.parent, capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "date not recorded"


def load_run(run_dir):
    """Parse ``<run_dir>/summary.json``. Raises ValueError if it is not a gap-budget summary."""
    run_dir = Path(run_dir)
    path = run_dir / "summary.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    dev = summary.get("dev")
    if not isinstance(dev, dict) or not isinstance(dev.get("budget"), dict) or not isinstance(dev.get("conditions"), dict):
        raise ValueError(f"{path} has no dev.budget / dev.conditions")
    robot = summary.get("robot")
    inferred = not (isinstance(robot, str) and robot.strip())
    if inferred:
        robot = LEGACY_ROBOTS.get(run_dir.name, run_dir.name)
    return Run(name=run_dir.name, path=run_dir, summary=summary, robot=robot, robot_inferred=inferred,
               recorded=recorded_date(path, summary))


def discover_runs(results_dir=None):
    """All ``results/*/summary.json`` gap-budget runs, sorted by name. Returns (runs, problems)."""
    results_dir = Path(results_dir or RESULTS_DIR)
    runs, problems = [], []
    if not results_dir.is_dir():
        return runs, [f"results directory not found: {results_dir}"]
    for sub in sorted(p for p in results_dir.iterdir() if p.is_dir()):
        if not (sub / "summary.json").is_file():
            continue
        try:
            # Other result kinds (e.g. the Cosmos critic) declare themselves and are not gap-budget runs.
            if json.loads((sub / "summary.json").read_text(encoding="utf-8")).get("kind", "gap_budget") != "gap_budget":
                continue
            runs.append(load_run(sub))
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            problems.append(f"skipped {sub.name}: {exc}")
    return runs, problems


def provenance(run, split="dev"):
    """The label every precomputed panel carries: recorded run, date, commit, seed range."""
    block = run.summary.get(split) or {}
    seeds = _seed_range(block.get("seeds"))
    split_name = "held-out" if split == "heldout" else split
    return (f"Recorded run `{run.name}` · {run.recorded} · commit `{run.commit}` · "
            f"{split_name} seeds {seeds} · robot: {run.robot}" + (" (inferred: run predates the robot field)" if run.robot_inferred else ""))


# ------------------------------------------------------------------------------ table builders

def stage_label(stage):
    return STAGE_LABELS.get(stage, stage.replace("_", " ").capitalize())


def budget_rows(runs):
    """One row per (run, stage): paired recovery in pp with its bootstrap 95% CI. Includes the all-oracle row."""
    rows = []
    for run in runs:
        dev = run.summary["dev"]
        for stage, b in dev["budget"].items():
            rows.append({"robot": run.robot, "run": run.name, "stage": stage, "stage_label": stage_label(stage),
                         "delta_pp": b["delta_pp"], "ci_low": b["ci95_pp"][0], "ci_high": b["ci95_pp"][1],
                         "n": b["n"], "kind": "single"})
        allg = (dev.get("interaction") or {}).get("oracle_all")
        if allg:
            rows.append({"robot": run.robot, "run": run.name, "stage": "all", "stage_label": stage_label("all"),
                         "delta_pp": allg["delta_pp"], "ci_low": allg["ci95_pp"][0], "ci_high": allg["ci95_pp"][1],
                         "n": allg["n"], "kind": "all"})
    return rows


def _reasons(counts):
    return ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in counts.items()) or "-"


def success_rows(runs, split="dev"):
    """Per-condition success with Wilson 95% CI (as written by gap_budget.cond_table)."""
    rows = []
    for run in runs:
        block = run.summary.get(split)
        if not isinstance(block, dict):
            continue
        for cond, t in block.get("conditions", {}).items():
            lo, hi = t["wilson_95"]
            rows.append({"Robot": run.robot, "Run": run.name, "Condition": cond, "Oracle": t.get("oracle") or "none",
                         "Success": f"{t['successes']}/{t['n']}", "Rate": f"{100 * t['success_rate']:.0f}%",
                         "Wilson 95% CI": f"[{100 * lo:.0f}%, {100 * hi:.0f}%]",
                         "Failure reasons": _reasons(t.get("failure_reasons", {}))})
    return rows


def ci_excludes_zero(ci):
    lo, hi = ci
    return lo > 0 or hi < 0


def correction_view(run):
    """Before/after held-out numbers plus a plain-language verdict. The verdict is recomputed from the CI."""
    if not run.has_heldout:
        return None
    held = run.summary["heldout"]
    corr = held.get("correction") or run.summary["dev"].get("chosen_correction")
    conds = held["conditions"]
    before = conds.get("full")
    after = conds.get(f"full+{corr}")
    gap = held["paired_gap_corrected_minus_full"]
    excludes = ci_excludes_zero(gap["ci95_pp"])
    lo, hi = gap["ci95_pp"]
    if excludes and gap["delta_pp"] > 0:
        verdict = (f"Yes: the paired 95% CI [{lo:+.1f}, {hi:+.1f}] pp excludes zero. "
                   f"`{corr}` is a verified improvement on these held-out seeds.")
    elif excludes:
        verdict = (f"The paired 95% CI [{lo:+.1f}, {hi:+.1f}] pp excludes zero on the negative side. "
                   f"`{corr}` made things worse on held-out seeds.")
    else:
        verdict = (f"No: the paired 95% CI [{lo:+.1f}, {hi:+.1f}] pp includes zero. "
                   f"`{corr}` is not a verified improvement.")
    return {"correction": corr, "component": run.summary["dev"].get("chosen_component"),
            "choice_rule": run.summary["dev"].get("choice_rule", ""), "before": before, "after": after,
            "gap": gap, "excludes_zero": excludes, "improved": excludes and gap["delta_pp"] > 0,
            "verdict": verdict, "recorded_flag": held.get("ci_excludes_zero")}


# ------------------------------------------------------------------------------ upload & score

def parse_jsonl(text):
    episodes = []
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            ep = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {i}: not valid JSON ({exc.msg})") from None
        if not isinstance(ep, dict):
            raise ValueError(f"line {i}: each line must be one JSON object")
        episodes.append(ep)
    if not episodes:
        raise ValueError("the file contains no episodes")
    return episodes


GROUP_FIELDS = ("source", "protocol_id", "robot", "method", "sensor")


def _group_key(ep):
    return tuple(ep[k] for k in GROUP_FIELDS) + (ep.get("oracle"),)


def score_upload(episodes, allow_fixtures=False):
    """Score with ``metrics.summarize`` / ``score_episode``; add ``paired_gap`` when exactly two conditions."""
    report = summarize(episodes, allow_fixtures=allow_fixtures)   # validates everything, raises ValueError
    per_episode = []
    for ep in episodes:
        r = score_episode(ep)
        per_episode.append({"trial": ep["trial_id"], "seed": ep["seed"], "robot": ep["robot"], "method": ep["method"],
                            "oracle": ep.get("oracle") or "-", "success": "yes" if r["success"] else "no",
                            "failure reasons": ", ".join(r["failure_reasons"]) or "-",
                            "final error (cm)": round(100 * r["final_object_error_m"], 2),
                            "settled (s)": round(r["settled_duration_s"], 2)})
    paired = None
    groups = {}
    for ep in episodes:
        groups.setdefault(_group_key(ep), []).append(ep)
    if len(groups) == 2:
        (ka, a), (kb, b) = sorted(groups.items(), key=lambda kv: tuple(map(str, kv[0])))
        name = lambda k: f"{k[3]}" + (f" [oracle={k[5]}]" if k[5] else "")  # noqa: E731
        try:
            g = paired_gap(a, b)
            paired = {"a": name(ka), "b": name(kb), **g, "excludes_zero": ci_excludes_zero(g["paired_bootstrap_95_pp"])}
        except ValueError as exc:
            paired = {"a": name(ka), "b": name(kb), "error": str(exc)}
    return {"report": report, "episodes": per_episode, "paired": paired}


# ------------------------------------------------------------------------------ live diagnosis

def diagnose_status(env=None):
    """(enabled, message). Never reveals the key; only whether it is set."""
    env = os.environ if env is None else env
    if not env.get("NEBIUS_API_KEY"):
        return False, ("Live diagnosis is disabled: `NEBIUS_API_KEY` is not set in this app's environment. "
                       "Every other tab works offline from recorded results. To enable it, set `NEBIUS_API_KEY` "
                       "and `NEMOTRON_MODEL` (an exact Nemotron model ID on Nebius Token Factory) as secrets.")
    if not env.get("NEMOTRON_MODEL"):
        return False, ("`NEBIUS_API_KEY` is set, but `NEMOTRON_MODEL` is not. Set it to the exact Nemotron model ID "
                       "available to your Nebius Token Factory account.")
    return True, f"Live diagnosis enabled. Model: `{env['NEMOTRON_MODEL']}` via Nebius Token Factory."


def failure_trace(run):
    """The structured trace sent to the model: measured numbers only, no simulator internals."""
    dev = run.summary["dev"]
    return {"robot": run.robot, "task": "pick a 4 cm block and place it in a tray",
            "dev_seeds": dev.get("seeds"),
            "conditions": {c: {"oracle": t.get("oracle"), "success": f"{t['successes']}/{t['n']}",
                               "failure_reasons": t.get("failure_reasons", {})} for c, t in dev["conditions"].items()},
            "gap_budget_pp": {s: {"recovery_pp": round(b["delta_pp"], 1), "ci95_pp": [round(x, 1) for x in b["ci95_pp"]]}
                              for s, b in dev["budget"].items()},
            "oracle_all_recovery_pp": round((dev.get("interaction") or {}).get("oracle_all_recovery_pp", float("nan")), 1)}


def diagnosis_messages(run):
    menu = {stage: {"correction": c, "what_it_does": d} for stage, (c, d) in CORRECTION_MENU.items()}
    system = ("You are a robotics failure-diagnosis assistant. You read a measured transfer-gap budget from paired "
              "simulator trials and propose exactly one correction from a fixed menu. Respond with only a JSON object "
              'with keys "stage", "correction", "rationale" (at most 3 sentences), and "expected_effect". '
              "Use only stage and correction names from the menu. Do not invent measurements or claim the fix works; "
              "it will be verified on held-out trials.")
    user = json.dumps({"failure_trace": failure_trace(run), "correction_menu": menu})
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_proposal(content):
    """Extract and check the model's JSON proposal against the fixed menu. Returns (proposal|None, problem|None)."""
    text = content.strip()   # tolerate ```json fences or a <think> preamble: take the outermost {...}
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None, "response is not a JSON object"
    try:
        proposal = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None, "response is not valid JSON"
    stage, corr = proposal.get("stage"), proposal.get("correction")
    if stage not in CORRECTION_MENU:
        return proposal, f"stage {stage!r} is not in the menu"
    if corr != CORRECTION_MENU[stage][0]:
        return proposal, f"correction {corr!r} does not match the menu entry for {stage}"
    return proposal, None


def receipt_dir():
    preferred = ROOT / "runs" / "app_receipts"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except OSError:
        return Path(tempfile.gettempdir()) / "transfergap_receipts"


def run_diagnosis(run, out_dir=None, caller=call_model):
    """One Nemotron call via the existing hosted adapter. Returns a dict safe to display (no credentials)."""
    enabled, message = diagnose_status()
    if not enabled:
        return {"ok": False, "message": message}
    out_dir = Path(out_dir or receipt_dir())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"diagnose-{run.name}-{stamp}-{uuid.uuid4().hex[:6]}.json"
    try:
        receipt = caller("nemotron", diagnosis_messages(run), path)
    except (RuntimeError, ValueError, OSError) as exc:
        # hosted.call_model already strips raw error bodies/headers; its messages never contain the key.
        return {"ok": False, "message": f"Call failed: {exc}", "receipt_path": str(path)}
    proposal, problem = parse_proposal(receipt.get("content", ""))
    rule_choice = run.summary["dev"].get("chosen_component")
    return {"ok": True, "proposal": proposal, "problem": problem, "rule_choice": rule_choice,
            "agrees_with_rule": bool(proposal) and problem is None and proposal.get("stage") == rule_choice,
            "receipt": {k: receipt.get(k) for k in ("requested_model", "returned_model", "endpoint_host", "created_at",
                                                    "latency_s", "usage", "request_sha256", "status", "response_id")},
            "content": receipt.get("content", ""), "receipt_path": str(path)}
