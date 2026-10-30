"""Diagnosis agent: structured failure trace -> ONE parameterised correction from a FIXED menu.

Two diagnosers produce the same proposal shape and pass the same strict validator:
  * rule_based_diagnosis  deterministic baseline (the frozen gap_budget_v1 choice rule + default params)
  * nemotron_diagnosis    Nemotron 3 Super on Nebius Token Factory (OpenAI-compatible), with a receipt

Proposal schema (anything else is rejected, like adapters.validate_plan):
  {"target_stage": str, "operator": str, "params": {...}, "rationale": str (optional, <= 1000 chars)}

The loop (run_loop) is: build trace from DEV episodes -> diagnose -> apply each validated correction on DEV
seeds, paired against the uncorrected pipeline -> report. It refuses held-out seeds everywhere. Held-out
verification of a chosen correction must go through a frozen, committed protocol (see sim/gap_budget.py).

Simulator state is used here only to LABEL and SCORE finished episodes (oracle substitution, failure
reasons). Corrections change controller inputs; none reads success or privileged state at run time.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import multiprocessing as mp
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .hosted import call_model

ROOT = Path(__file__).resolve().parents[1]            # transfergap/ project dir
RUNS = ROOT / "runs" / "diagnose"
SUPER_MODEL = "nvidia/nemotron-3-super-120b-a12b"
TRACE_SCHEMA = "transfergap.failure_trace/v1"
RATIONALE_MAX = 1000
# Failure reason (metrics.score_episode) -> task stage it is observed at.
STAGE_OF_REASON = {"no_lift": "grasp", "not_released_and_settled_at_goal": "place",
                   "forbidden_collision": "collision", "fallen": "collision"}

# THE FIXED MENU. Bounds are ASSUMPTIONS chosen to stay inside what the simulator models.
MENU = {
    "look_again": {
        "target_stage": "perception",
        "summary": "Object-relative target anchoring: after the approach phase, re-perceive the object from close "
                   "range (per-axis sigma 4 mm per look) and re-anchor grasp targets to the new estimate. "
                   "looks = number of close-range looks averaged.",
        "params": {"looks": {"type": "int", "min": 1, "max": 3}}},
    "tool_frame_calibration": {
        "target_stage": "calibration",
        "summary": "Tool-frame calibration. method=touch_probe: touch a known fixture `probes` times (per-axis "
                   "sigma 2 mm each) and correct the tool-point model by the averaged measurement. "
                   "method=fixed_offset: add a constant offset_m [dx, dy, dz] (metres) to the tool-point model.",
        "params": {"method": {"type": "enum", "values": ["touch_probe", "fixed_offset"]},
                   "probes": {"type": "int", "min": 1, "max": 3, "when": "touch_probe"},
                   "offset_m": {"type": "vec3", "abs_max": 0.03, "when": "fixed_offset"}}},
    "grip_force": {
        "target_stage": "contact",
        "summary": "Scale the gripper actuator force limit by `scale`.",
        "params": {"scale": {"type": "float", "min": 0.5, "max": 2.0}}},
    "timing_scale": {
        "target_stage": "timing",
        "summary": "Cap the execution speed factor (relative to robot nominal; human-paced demos run 1-4.5x) "
                   "at speed_cap.",
        "params": {"speed_cap": {"type": "float", "min": 1.0, "max": 4.5}}},
}
DEFAULT_PARAMS = {"look_again": {"looks": 1}, "tool_frame_calibration": {"method": "touch_probe", "probes": 1},
                  "grip_force": {"scale": 1.5}, "timing_scale": {"speed_cap": 3.0}}
OPERATOR_FOR_STAGE = {v["target_stage"]: k for k, v in MENU.items()}


# ---------------------------------------------------------------- validation

def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def validate_correction(proposal):
    """Return a normalised copy of a menu correction, or raise ValueError. Off-menu = rejected."""
    if not isinstance(proposal, dict):
        raise ValueError("Correction must be a JSON object")
    allowed, required = {"target_stage", "operator", "params", "rationale"}, {"target_stage", "operator", "params"}
    if set(proposal) - allowed or required - set(proposal):
        raise ValueError(f"Correction keys must be {sorted(required)} plus optional 'rationale'")
    op = proposal["operator"]
    if not isinstance(op, str) or op not in MENU:
        raise ValueError(f"Operator {op!r} is not on the correction menu {sorted(MENU)}")
    if proposal["target_stage"] != MENU[op]["target_stage"]:
        raise ValueError(f"Operator {op} acts on stage {MENU[op]['target_stage']!r}, not {proposal['target_stage']!r}")
    params = proposal["params"]
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    out = {}
    if op == "tool_frame_calibration":
        method = params.get("method")
        if method == "touch_probe":
            expect = {"method", "probes"}
        elif method == "fixed_offset":
            expect = {"method", "offset_m"}
        else:
            raise ValueError("tool_frame_calibration.method must be 'touch_probe' or 'fixed_offset'")
        out["method"] = method
    else:
        expect = set(MENU[op]["params"])
    if set(params) != expect:
        raise ValueError(f"{op} params must be exactly {sorted(expect)}")
    for name in sorted(expect - {"method"}):
        spec, value = MENU[op]["params"][name], params[name]
        if spec["type"] == "int":
            if not isinstance(value, int) or isinstance(value, bool) or not spec["min"] <= value <= spec["max"]:
                raise ValueError(f"{op}.{name} must be an integer in [{spec['min']}, {spec['max']}]")
            out[name] = int(value)
        elif spec["type"] == "float":
            if not _is_num(value) or not spec["min"] <= value <= spec["max"]:
                raise ValueError(f"{op}.{name} must be a finite number in [{spec['min']}, {spec['max']}]")
            out[name] = float(value)
        elif spec["type"] == "vec3":
            if (not isinstance(value, list) or len(value) != 3 or not all(map(_is_num, value))
                    or max(abs(v) for v in value) > spec["abs_max"]):
                raise ValueError(f"{op}.{name} must be 3 finite numbers with |x| <= {spec['abs_max']} m")
            out[name] = [float(v) for v in value]
    result = {"target_stage": MENU[op]["target_stage"], "operator": op, "params": out}
    if "rationale" in proposal:
        r = proposal["rationale"]
        if not isinstance(r, str) or len(r) > RATIONALE_MAX:
            raise ValueError(f"rationale must be a string of at most {RATIONALE_MAX} characters")
        result["rationale"] = r
    return result


def correction_tag(proposal):
    p = proposal["params"]
    return proposal["operator"] + "[" + ",".join(
        f"{k}={'/'.join(f'{x:g}' for x in v) if isinstance(v, list) else (f'{v:g}' if isinstance(v, float) else v)}"
        for k, v in sorted(p.items())) + "]"


def _no_constants(c):
    raise ValueError(f"non-finite number {c} in model output")


def extract_json(content):
    """Strict: the whole reply (minus a <think> block and one optional ```json fence) must be one JSON value."""
    text = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.S)
    if fence:
        text = fence.group(1)
    try:
        return json.loads(text, parse_constant=_no_constants)
    except json.JSONDecodeError:
        raise ValueError("Model output is not a single JSON object (no prose allowed)") from None


# ---------------------------------------------------------------- seeds guard

def split_seeds():
    from .sim.gap_budget import DEV_SEEDS, HELDOUT_SEEDS
    return list(DEV_SEEDS), list(HELDOUT_SEEDS)


def assert_dev_only(seeds):
    dev, held = split_seeds()
    seeds = [int(s) for s in seeds]
    if not seeds:
        raise ValueError("no seeds")
    if set(seeds) & set(held):
        raise ValueError("held-out seeds must never enter diagnosis or dev tuning")
    if not set(seeds) <= set(dev):
        raise ValueError(f"diagnosis runs on dev seeds {dev[0]}-{dev[-1]} only")
    return seeds


# ---------------------------------------------------------------- trace

def _sha256_json(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def build_trace(episodes, source="unknown"):
    """Structured failure trace from dev oracle-substitution episodes (conditions of sim/errors.CONDITIONS)."""
    from .metrics import score_episode
    from .sim import errors, gap_budget
    seeds = assert_dev_only(sorted({e["seed"] for e in episodes}))
    groups = gap_budget.by_cond(episodes)
    missing = set(errors.CONDITIONS) - set(groups)
    if missing:
        raise ValueError(f"trace needs every oracle condition; missing {sorted(missing)}")
    table = gap_budget.cond_table(episodes)
    singles = [c for c in errors.CONDITIONS if c.startswith("oracle_") and c != "oracle_all"]
    budget, interaction = gap_budget.budget(groups, singles)
    ok = {c: {e["seed"]: score_episode(e)["success"] for e in rows} for c, rows in groups.items()}
    rows = []
    for e in sorted(groups["full"], key=lambda e: e["seed"]):
        s = score_episode(e)
        rows.append({
            "seed": e["seed"], "success": s["success"], "failure_reasons": s["failure_reasons"],
            "failed_stages": sorted({STAGE_OF_REASON.get(r, "other") for r in s["failure_reasons"]}),
            "rescued_by_oracle": [c for c in errors.COMPONENTS if not s["success"] and ok[f"oracle_{c}"][e["seed"]]],
            "rescued_by_all_oracles": bool(not s["success"] and ok["oracle_all"][e["seed"]]),
            # Observable to a real system: the commanded execution speed. Perception and calibration error
            # vectors are simulator-only and deliberately NOT included.
            "commanded_speed_factor": round(float(e["perturbation"].get("timing_scale", 1.0)), 3),
            "final_object_error_m": round(s["final_object_error_m"], 4)})
    trace = {
        "schema": TRACE_SCHEMA, "robot": episodes[0]["robot"], "task": episodes[0]["protocol_id"],
        "split": "dev", "seeds": seeds, "source": source,
        "budget_pp": {k: {"delta_pp": round(v["delta_pp"], 2), "ci95_pp": [round(x, 2) for x in v["ci95_pp"]],
                          "n_paired": v["n"]} for k, v in budget.items()},
        "budget_not_measured": {"contact": "nominal grip is ~180x block weight; contact oracle not informative"},
        "interaction_pp": {"sum_of_single_recoveries": round(interaction["sum_of_single_recoveries_pp"], 2),
                           "all_oracles_recovery": round(interaction["oracle_all_recovery_pp"], 2)},
        "conditions": {c: {"oracle": t["oracle"], "n": t["n"], "success_rate": round(t["success_rate"], 4),
                           "failure_reasons": t["failure_reasons"]} for c, t in table.items()},
        "full_condition_episodes": rows,
        "stage_vocabulary": {"failed_stages": sorted(set(STAGE_OF_REASON.values())),
                             "oracle_components": list(errors.COMPONENTS)},
    }
    validate_trace(trace)
    return trace


def validate_trace(trace):
    if not isinstance(trace, dict) or trace.get("schema") != TRACE_SCHEMA:
        raise ValueError(f"trace must have schema {TRACE_SCHEMA}")
    if trace.get("split") != "dev":
        raise ValueError("only dev traces may be diagnosed")
    assert_dev_only(trace["seeds"])
    if not isinstance(trace.get("budget_pp"), dict) or not trace["budget_pp"]:
        raise ValueError("trace needs a budget_pp table")
    for k, v in trace["budget_pp"].items():
        if k not in OPERATOR_FOR_STAGE or not _is_num(v.get("delta_pp")):
            raise ValueError(f"bad budget entry {k!r}")
    return trace


def simulate_dev_trace_episodes(seeds, procs=None, job=None):
    from .sim import errors, gap_budget
    seeds = assert_dev_only(seeds)
    return _map(job or gap_budget._job, [(s, c, None) for s in seeds for c in errors.CONDITIONS], procs)


def load_dev_episodes(path, seeds_limit=None):
    eps = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    if seeds_limit:
        keep = set(split_seeds()[0][:seeds_limit])
        eps = [e for e in eps if e["seed"] in keep]
    assert_dev_only({e["seed"] for e in eps})
    return eps


# ---------------------------------------------------------------- diagnosers

def rule_based_diagnosis(trace):
    """Deterministic baseline = the frozen gap_budget_v1 rule: argmax single-oracle recovery (ties broken in
    perception, calibration, timing order), then the menu operator for that stage with default params."""
    validate_trace(trace)
    order = ["perception", "calibration", "timing", "contact"]
    b = {k: v["delta_pp"] for k, v in trace["budget_pp"].items()}
    stage = max(b, key=lambda k: (round(b[k], 9), -order.index(k)))
    if b[stage] <= 0:
        raise ValueError("no stage has positive recovery on dev; nothing to correct")
    op = OPERATOR_FOR_STAGE[stage]
    return validate_correction({"target_stage": stage, "operator": op, "params": copy.deepcopy(DEFAULT_PARAMS[op]),
                                "rationale": f"rule: largest dev budget item {stage} ({b[stage]:+.1f} pp); "
                                             f"default params"})


def diagnosis_messages(trace):
    system = (
        "You are the TransferGap diagnosis agent. You read a structured failure trace from paired simulation trials "
        "of a robot pick-and-place task. budget_pp[stage].delta_pp is success with that pipeline stage replaced by "
        "simulator ground truth minus success of the full pipeline, paired by seed, with a 95% bootstrap CI. "
        "full_condition_episodes lists each uncorrected trial with its failure reasons, failed task stages and which "
        "single-stage oracle rescued it. Choose exactly ONE correction from the fixed menu and set its parameters "
        "within the stated bounds. Reply with only one JSON object with keys target_stage, operator, params and "
        f"rationale (at most {RATIONALE_MAX} characters). No other keys, no text outside the JSON. Do not claim the "
        "correction will work; it will be tested on development seeds and verified on held-out seeds you never see.")
    menu = {op: {"target_stage": m["target_stage"], "summary": m["summary"], "params": m["params"]}
            for op, m in MENU.items()}
    return [{"role": "system", "content": system},
            {"role": "user", "content": json.dumps({"correction_menu": menu, "failure_trace": trace})}]


def nemotron_diagnosis(trace, receipt_path, model=None, max_tokens=4096, timeout=300):
    """One hosted call. The receipt always ends with validated true/false. Returns (proposal|None, receipt)."""
    validate_trace(trace)
    model = model or os.environ.get("NEMOTRON_SUPER_MODEL", SUPER_MODEL)
    path = Path(receipt_path)
    extra = {"diagnoser": "nemotron_super", "trace_sha256": _sha256_json(trace), "menu_sha256": _sha256_json(MENU)}
    try:
        receipt = call_model("nemotron", diagnosis_messages(trace), path, model=model,
                             max_tokens=max_tokens, timeout=timeout)
    except RuntimeError as exc:                          # request failed; receipt says status=failed
        receipt = json.loads(path.read_text())
        receipt.update(extra, validated=False, validation_error=str(exc))
        path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return None, receipt
    proposal = None
    try:
        proposal = validate_correction(extract_json(receipt["content"]))
        receipt.update(validated=True, validated_correction=proposal)
    except ValueError as exc:
        receipt.update(validated=False, validation_error=str(exc))
    finally:
        receipt.update(extra)
        path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return proposal, receipt


# ---------------------------------------------------------------- apply on dev

def corrected_perturbation(seed, proposal):
    """Full-error perturbation for `seed` with a validated correction applied. With default params this is
    identical to sim/errors.build_perturbation(seed, 'full', <frozen correction>). Extra looks/probes draw from
    separate RNG streams so the frozen per-seed draws are untouched."""
    import numpy as np
    from .sim import errors
    proposal = validate_correction(proposal)
    op, p = proposal["operator"], proposal["params"]
    pert, _ = errors.build_perturbation(seed, "full")
    e = errors.sample_errors(seed)
    if op == "look_again":
        rng = np.random.default_rng([int(seed), 424243, 1])
        draws = [e["look_again_err_xy"]] + [rng.normal(0.0, errors.LOOK_AGAIN_SIGMA_M, 2) for _ in range(p["looks"] - 1)]
        pert["look_again_err_xy"] = np.mean(draws, axis=0).tolist()
    elif op == "tool_frame_calibration" and p["method"] == "touch_probe":
        rng = np.random.default_rng([int(seed), 424243, 2])
        draws = [e["probe_noise_m"]] + [rng.normal(0.0, errors.PROBE_SIGMA_M, 3) for _ in range(p["probes"] - 1)]
        pert["tcp_probe_noise_m"] = np.mean(draws, axis=0).tolist()
    elif op == "tool_frame_calibration":
        # tcp_offset_vec is the controller's tool-point model error; adding offset_m shifts the model.
        pert["tcp_offset_vec"] = (np.asarray(pert["tcp_offset_vec"]) + p["offset_m"]).tolist()
    elif op == "grip_force":
        pert["grip_force_scale"] = pert["grip_force_scale"] * p["scale"]
    elif op == "timing_scale":
        pert["timing_scale"] = min(pert["timing_scale"], p["speed_cap"])
    return pert


def _dev_job(args):
    from .sim.rollout import run_episode
    seed, proposal = args
    if proposal is None:
        from .sim import errors
        pert, tag = errors.build_perturbation(seed, "full")[0], "full"
    else:
        pert, tag = corrected_perturbation(seed, proposal), "full+" + correction_tag(proposal)
    return run_episode(seed, pert, label=tag, oracle="none", condition=tag)


def _map(fn, jobs, procs=None):
    procs = procs if procs is not None else min(20, mp.cpu_count() or 2)
    if procs <= 1:
        return [fn(j) for j in jobs]
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    with mp.get_context("spawn").Pool(procs) as pool:
        return pool.map(fn, jobs, chunksize=2)


def evaluate_on_dev(proposals, seeds, procs=None, job=_dev_job):
    """Paired dev evaluation of each distinct proposal against the uncorrected pipeline on the same seeds."""
    from .sim import gap_budget
    seeds = assert_dev_only(seeds)
    distinct = {}
    for p in proposals:
        distinct.setdefault(correction_tag(p), validate_correction(p))
    jobs = [(s, None) for s in seeds] + [(s, p) for p in distinct.values() for s in seeds]
    eps = _map(job, jobs, procs)
    assert_dev_only({e["seed"] for e in eps})
    groups = gap_budget.by_cond(eps)
    table = gap_budget.cond_table(eps)
    out = {}
    for tag in distinct:
        g = gap_budget.gap(groups["full"], groups[f"full+{tag}"])
        out[tag] = {"full": table["full"], "corrected": table[f"full+{tag}"], "paired_gap_corrected_minus_full": g,
                    "ci_excludes_zero": g["ci95_pp"][0] > 0 or g["ci95_pp"][1] < 0}
    return out, eps


# ---------------------------------------------------------------- loop

def _git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return os.environ.get("TRANSFERGAP_GIT_COMMIT", "unknown")


def run_loop(trace_path=None, dev_episodes=None, llm="auto", model=None, seeds_limit=None, apply=True,
             out_dir=None, procs=None, job=_dev_job, trace_job=None):
    """diagnose -> apply on dev seeds -> report. Never touches held-out seeds. Returns the report dict."""
    if llm not in {"auto", "off", "required"}:
        raise ValueError("llm must be auto, off or required")
    has_key = bool(os.environ.get("NEBIUS_API_KEY"))
    if llm == "required" and not has_key:
        raise ValueError("--llm required but NEBIUS_API_KEY is not set; refusing to run without the live call")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(out_dir) if out_dir else RUNS / f"{stamp}-{os.getpid()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    dev_seeds = split_seeds()[0][:seeds_limit] if seeds_limit else split_seeds()[0]

    if trace_path:
        trace = validate_trace(json.loads(Path(trace_path).read_text()))
    else:
        default = ROOT / "runs" / "gap_budget" / "dev.jsonl"
        src = Path(dev_episodes) if dev_episodes else (default if default.exists() else None)
        if src is not None:
            eps, source = load_dev_episodes(src, seeds_limit), str(src)
        else:
            eps = simulate_dev_trace_episodes(dev_seeds, procs, trace_job)
            source = "simulated in this run"
            (run_dir / "trace_episodes.jsonl").write_text("".join(json.dumps(e) + "\n" for e in eps))
        trace = build_trace(eps, source)
    (run_dir / "trace.json").write_text(json.dumps(trace, indent=1))

    proposals = {}
    try:
        proposals["rule_based"] = rule_based_diagnosis(trace)
        rule = {"status": "ok", "proposal": proposals["rule_based"]}
    except ValueError as exc:
        rule = {"status": "no_correction", "reason": str(exc)}
    (run_dir / "rule_based.json").write_text(json.dumps(rule, indent=1))

    if llm == "off" or not has_key:
        llm_result = {"status": "skipped", "reason": "--llm off" if llm == "off" else "NEBIUS_API_KEY not set"}
    else:
        proposal, receipt = nemotron_diagnosis(trace, run_dir / "nemotron_super_receipt.json", model=model)
        llm_result = {"status": receipt["status"], "validated": receipt["validated"],
                      "receipt": str(run_dir / "nemotron_super_receipt.json"),
                      "response_id": receipt.get("response_id"), "latency_s": receipt.get("latency_s"),
                      "usage": receipt.get("usage"), "proposal": proposal,
                      "validation_error": receipt.get("validation_error")}
        if proposal is not None:
            proposals["nemotron_super"] = proposal

    report = {"schema": "transfergap.diagnosis_report/v1", "created_at": datetime.now(timezone.utc).isoformat(),
              "git_commit": _git_commit(), "run_dir": str(run_dir), "trace_sha256": _sha256_json(trace),
              "split": "dev", "seeds": trace["seeds"], "rule_based": rule, "nemotron_super": llm_result,
              "heldout_touched": False}
    if "rule_based" in proposals and "nemotron_super" in proposals:
        a, b = proposals["rule_based"], proposals["nemotron_super"]
        report["agreement"] = {"same_operator": a["operator"] == b["operator"],
                               "same_params": a["operator"] == b["operator"] and a["params"] == b["params"]}
    if apply and proposals:
        results, eps = evaluate_on_dev(list(proposals.values()), trace["seeds"], procs, job)
        (run_dir / "dev_correction_episodes.jsonl").write_text("".join(json.dumps(e) + "\n" for e in eps))
        report["dev_evaluation"] = {"by_correction": results,
                                    "by_diagnoser": {k: correction_tag(p) for k, p in proposals.items()},
                                    "note": "dev seeds only; a held-out claim needs a frozen, committed protocol"}
    (run_dir / "report.json").write_text(json.dumps(report, indent=1, allow_nan=False))
    return report
