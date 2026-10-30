"""Export a small, anonymous static report from the scored result files."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((RESULTS / name / "summary.json").read_text())


def main():
    arms = {}
    for robot in ("ur5e", "ur10e"):
        name = f"gap_budget_v2_{robot}"
        source = load(name)
        assert source["robot"].startswith(robot)
        assert source["heldout"]["paired_gap_corrected_minus_full"]["n"] == 60
        arms[robot] = {
            "source": name,
            "code_commit": source["git_commit"][:12],
            "dev_seeds": source["dev"]["seeds"],
            "heldout_seeds": source["heldout"]["seeds"],
            "budget": source["dev"]["budget"],
            "dev_full": source["dev"]["conditions"]["full"],
            "heldout": source["heldout"]["conditions"],
            "paired_gain": source["heldout"]["paired_gap_corrected_minus_full"],
            "correction": source["heldout"]["correction"],
        }

    cosmos = {}
    for version in ("v1", "v2"):
        name = f"cosmos_critic_{version}"
        source = load(name)
        result = source["results"]
        assert result["n"] == (120 if version == "v1" else 116)
        cosmos[version] = {
            "source": name,
            "run_commit": source["run"]["git_commit"][:12],
            "seeds": source["seeds"],
            "camera": source.get("camera", "v1"),
            "success": result["success"],
            "stage": result["stage"],
            "static_controls": result.get("static_controls"),
        }

    source = load("g1_contact_v1")
    g1 = {
        "source": "g1_contact_v1",
        "protocol": source["protocol_id"],
        "code_commit_at_scoring": source["code_commit_at_scoring"][:12],
        "conditions": {},
    }
    for name, condition in source["conditions"].items():
        assert condition["rollouts"] == 30 and condition["trials"] == 10
        g1["conditions"][name] = {
            "oracle": condition["oracle"],
            "rollouts": condition["rollouts"],
            "trials": condition["trials"],
            "touch": condition["touch_rollout_rate"],
            "grasp": condition["grasp_rollout_rate"],
            "place": condition["place_rollout_rate"],
            "place_seed_any": condition["place_trial_any_rollout"],
            "mixed_place_seeds": condition["place_trials_with_mixed_outcomes"],
        }

    payload = {
        "title": "TransferGap",
        "scope": "Recorded MuJoCo simulation results; no physical robot result.",
        "arms": arms,
        "cosmos": cosmos,
        "g1": g1,
    }
    (HERE / "data.json").write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
