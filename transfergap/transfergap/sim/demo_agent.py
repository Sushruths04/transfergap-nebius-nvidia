"""Nemotron 3 Super as the diagnosing agent for demo_budget: reads the dev gap budget (task success AND style),
picks the next correction from the fixed menu, and its choice is frozen in git next to the rule's choice BEFORE
held-out trials. If the two disagree, stage_heldout evaluates both on the same held-out seeds.

  python -m transfergap.sim.demo_agent --demo <spec> --robot <ur5e|ur10e> [--base a,b]
  -> results/<run>/agent_choice.json (+ agent_receipt.json). Commit both with protocol.json before held-out.

The agent sees only aggregate dev statistics (no simulator state, no held-out data). Its answer is validated
against the menu; an invalid answer is recorded as such and the rule's choice stands.
"""
from __future__ import annotations

import argparse
import json

from ..diagnose import extract_json
from ..hosted import call_model
from . import errors_demo as E
from .demo_budget import res_dir

MODEL = "nvidia/nemotron-3-super-120b-a12b"
FIX_DOC = {"look_again": "re-perceive the object from close range after approaching (perception)",
           "smooth_demo": "low-pass filter the estimated human hand path before retargeting (retargeting)",
           "touch_probe_calibration": "touch a known fixture once to re-estimate the tool-frame offset (calibration)",
           "speed_cap_3": "cap execution speed at 3x robot nominal (timing; keeps more of the human's pace)",
           "speed_cap_2": "cap execution speed at 2x robot nominal (timing)",
           "speed_cap_1.5": "cap execution speed at 1.5x robot nominal (timing; slowest, safest)",
           "safe_path": "project the copied human path so it never goes below the object-contact height (fixes a "
                        "style that is itself infeasible for the robot; costs a little style)"}


def menu(spec, base):
    m = [c for c in (E.next_correction(k, base) for k in E.components_for(spec)) if c]
    return m + ([] if "safe_path" in base else ["safe_path"])


def prompt(dev, base, options):
    brief = {
        "task": "a robot copies one human pick-and-place demonstration, following the human's hand path (style)",
        "adopted_fixes": list(base),
        "success_by_condition": {c: {"success_rate": round(t["success_rate"], 3), "n": t["n"],
                                     "failure_reasons": t["failure_reasons"]} for c, t in dev["conditions"].items()},
        "success_budget_pp": {c: {"recovery_pp": round(b["delta_pp"], 1), "ci95_pp": [round(x, 1) for x in b["ci95_pp"]]}
                              for c, b in dev["success_budget"].items()},
        "style_budget": {c: {"path_rmse_reduction_cm": round(100 * v["path_rmse_m"]["mean"], 2),
                             "speed_profile_corr_gain": round(v["speed_profile_corr"]["mean"], 3)}
                         for c, v in dev["style_budget"].items()},
        "style_full_condition": {k: round(v, 3) for k, v in dev["style"]["full"].items()},
        "menu": {o: FIX_DOC[o] for o in options},
    }
    return [{"role": "system", "content": "You are a robotics failure-diagnosis agent. Choose exactly one correction "
             "from the menu that will most improve task success on unseen trials while preserving the human's "
             "style where possible. Reply with ONLY a JSON object: {\"correction\": <menu key>, \"rationale\": "
             "<= 60 words}."},
            {"role": "user", "content": json.dumps(brief)}]


def choose(spec, robot, base=()):
    R = res_dir(spec, robot, base)
    dev = json.loads((R / "dev_results.json").read_text())
    options = menu(spec, base)
    receipt_path = R / "agent_receipt.json"
    out = {"model": MODEL, "menu": options, "rule_choice": dev["chosen_correction"], "valid": False}
    try:
        rec = call_model("nemotron", prompt(dev, base, options), receipt_path, model=MODEL, max_tokens=4096,
                         timeout=300)
        ans = extract_json(rec["content"])
        corr = ans.get("correction") if isinstance(ans, dict) else None
        if corr not in options:
            raise ValueError(f"off-menu answer {corr!r}")
        out.update(valid=True, agent_choice=corr, rationale=str(ans.get("rationale", ""))[:600],
                   response_id=rec.get("response_id"), latency_s=rec.get("latency_s"), usage=rec.get("usage"))
    except Exception as exc:                                   # recorded, rule's choice stands
        out.update(error=f"{type(exc).__name__}: {exc}")
    out["agrees_with_rule"] = out.get("agent_choice") == out["rule_choice"]
    (R / "agent_choice.json").write_text(json.dumps(out, indent=1))
    rec_txt = receipt_path.read_text() if receipt_path.exists() else ""
    if rec_txt:                                               # strip the echoed prompt to keep the receipt small
        r = json.loads(rec_txt)
        r.pop("request", None)
        receipt_path.write_text(json.dumps(r, indent=1))
    print(json.dumps({k: out.get(k) for k in ("rule_choice", "agent_choice", "agrees_with_rule", "valid", "error")}))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--robot", default="ur5e")
    ap.add_argument("--base", default="")
    a = ap.parse_args()
    choose(E.parse_demo_spec(a.demo), a.robot, tuple(x for x in a.base.split(",") if x))


if __name__ == "__main__":
    main()
