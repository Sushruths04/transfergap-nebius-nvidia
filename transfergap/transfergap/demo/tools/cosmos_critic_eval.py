"""Score Cosmos-Reason2-2B (zero-shot and with the trained LoRA critic adapter) on NEW labelled clips, no training.

    python cosmos_critic_eval.py --data DIR_WITH_labels.jsonl_AND_clips --adapter runs/cosmos_critic_adapter --out OUT

Runs in the Cosmos venv (transformers >= 5, peft, qwen-vl-utils) on one GPU. Same question, frame rate and scoring as
cosmos_critic_ft.py (imported, not copied), so the numbers are comparable with results/cosmos_critic_ft_v1. The adapter was
trained on other demos' clips with seeds 2000-2049; the clips scored here come from a demo and seeds it never saw.
Writes zero_shot.jsonl, fine_tuned.jsonl and report.json (overall and per robot x condition).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cosmos_critic_ft as C


def per_cell(res):
    cells = {}
    for r in res:
        cells.setdefault(f"{r['robot']}/{r['condition']}", []).append(r)
    return {k: C.metrics(v) for k, v in sorted(cells.items())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from peft import PeftModel
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dev = "cuda"
    rows = C.load(a.data)
    processor = AutoProcessor.from_pretrained(C.MODEL)
    model = Qwen3VLForConditionalGeneration.from_pretrained(C.MODEL, dtype=torch.bfloat16).to(dev).eval()
    t0 = time.time()
    zs = C.evaluate(model, processor, rows, dev, "zero-shot")
    (out / "zero_shot.jsonl").write_text("".join(json.dumps(r) + "\n" for r in zs))
    model = PeftModel.from_pretrained(model, a.adapter).eval()
    ft = C.evaluate(model, processor, rows, dev, "fine-tuned")
    (out / "fine_tuned.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ft))
    rep = {"model": C.MODEL, "adapter": str(a.adapter), "n_clips": len(rows), "seconds": round(time.time() - t0),
           "zero_shot": C.metrics(zs), "fine_tuned": C.metrics(ft),
           "zero_shot_by_cell": per_cell(zs), "fine_tuned_by_cell": per_cell(ft)}
    (out / "report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
