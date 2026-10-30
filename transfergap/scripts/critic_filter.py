"""Verified data engine, step 4: attach the Cosmos-Reason2 critic's verdict to every episode of the LeRobot-style dataset and report what a
critic-only filter would admit (purity) versus the physics label.

    python3 scripts/critic_filter.py runs/dataset_v1_lerobot results/critic_dataset_v1/fine_tuned.jsonl results/critic_dataset_v1/zero_shot.jsonl
Adds `critic_pass`, `critic_margin` (log-likelihood of "success" minus "failure") and `physics_success` to meta/episodes.jsonl, writes
meta/episodes_filtered.jsonl (episodes with BOTH verdicts positive) and meta/critic_filter.json. Clips are matched by robot and seed; the critic
clips of the fix-stack condition correspond to the dataset's episodes.
"""
import json
import sys
from pathlib import Path


def load(p):
    return [json.loads(l) for l in open(p)]


def main(ds, ft, zs):
    ds = Path(ds)
    ft, zs = load(ft), load(zs)
    by = {(r["robot"], r["seed"]): r for r in ft if r["condition"] == "fix"}
    eps = [json.loads(l) for l in open(ds / "meta" / "episodes.jsonl")]
    keep = []
    for e in eps:
        r = by.get((e["robot"], e["seed"]))
        e["physics_success"] = True            # only physics successes are exported
        e["critic_pass"] = bool(r["pred"]) if r else None
        e["critic_margin"] = round(r["ll_success"] - r["ll_failure"], 3) if r else None
        if e["critic_pass"]:
            keep.append(e)
    (ds / "meta" / "episodes.jsonl").write_text("".join(json.dumps(e) + "\n" for e in eps))
    (ds / "meta" / "episodes_filtered.jsonl").write_text("".join(json.dumps(e) + "\n" for e in keep))

    def purity(rows, key):
        adm = [r for r in rows if r[key]]
        good = sum(1 for r in adm if r["success"])
        return {"admitted": len(adm), "physically_successful": good, "purity": round(good / max(len(adm), 1), 4)}

    summary = {"episodes": len(eps), "critic_pass": len(keep), "critic_margin_min": min(e["critic_margin"] for e in eps if e["critic_margin"] is not None),
               "pool_240_clips": {"no_filter": {"admitted": len(ft), "physically_successful": sum(r["success"] for r in ft), "purity": round(sum(r["success"] for r in ft) / len(ft), 4)},
                                  "zero_shot_critic": purity(zs, "pred"), "lora_critic": purity(ft, "pred")}}
    (ds / "meta" / "critic_filter.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
