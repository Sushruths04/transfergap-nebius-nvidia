"""GPU-VM side: LoRA fine-tuning of NVIDIA Cosmos-Reason2-2B (Qwen3-VL architecture) as a pick-and-place success
critic on labelled simulator rollout clips (transfergap.sim.critic_data), and evaluation of the zero-shot model vs
the fine-tuned adapter on the frozen splits. Run in the VM's Cosmos venv (transformers >= 5, peft, qwen-vl-utils):

    python cosmos_critic_ft.py --data ~/critic_data --out ~/critic_ft_v1 [--eval-only]

Scoring (identical for zero-shot and fine-tuned): the model sees the clip (4 fps, <= 32 frames, 320x240) and the
fixed question below; the predicted label is the answer with the higher total log-likelihood, "success" or
"failure". Training: LoRA r=16, alpha=32, dropout 0.05 on the language model's attention + MLP projections, vision
tower frozen, AdamW lr 1e-4, batch 1 x grad-accum 8, 2 epochs, loss only on the answer tokens. All values fixed in
results/cosmos_critic_ft_v1/protocol.json before training; the val split is used only to keep the better epoch.
"""
import argparse
import json
import math
import random
import time
from pathlib import Path

import torch

MODEL = "nvidia/Cosmos-Reason2-2B"
QUESTION = ("This video shows a robot arm in a simulator. The task: pick up the red block from the table and place "
            "it inside the green tray, then let go. Did the robot complete the task? Answer with one word: success "
            "or failure.")
ANSWERS = ("success", "failure")
FPS, MAX_FRAMES = 4.0, 32


def load(data):
    rows = [json.loads(l) for l in open(Path(data) / "labels.jsonl")]
    for r in rows:
        r["path"] = str(Path(data) / r["clip"])
    return rows


def build(processor, path, answer=None):
    from qwen_vl_utils import process_vision_info
    msgs = [{"role": "user", "content": [{"type": "video", "video": path, "fps": FPS, "max_frames": MAX_FRAMES,
                                          "resized_height": 240, "resized_width": 320},
                                         {"type": "text", "text": QUESTION}]}]
    prompt = processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    images, videos, vkw = process_vision_info(msgs, return_video_kwargs=True, return_video_metadata=True)
    vids, metas = (zip(*videos) if videos and isinstance(videos[0], tuple) else (videos, None))
    kw = dict(text=[prompt + (answer or "")], videos=list(vids), return_tensors="pt", **(vkw or {}))
    if metas is not None:
        kw["video_metadata"] = list(metas)
    enc = processor(**kw)
    n_prompt = len(processor(text=[prompt], videos=list(vids), return_tensors="pt", **(vkw or {}),
                             **({"video_metadata": list(metas)} if metas is not None else {}))["input_ids"][0])
    return enc, n_prompt


@torch.no_grad()
def score(model, processor, row, dev):
    lls = []
    for ans in ANSWERS:
        enc, n_prompt = build(processor, row["path"], ans)
        enc = {k: v.to(dev) for k, v in enc.items()}
        logits = model(**enc).logits[0, :-1].float()
        ids = enc["input_ids"][0, 1:]
        lp = torch.log_softmax(logits, -1).gather(1, ids[:, None])[:, 0]
        lls.append(float(lp[n_prompt - 1:].sum()))
    return {"pred": lls[0] > lls[1], "ll_success": lls[0], "ll_failure": lls[1]}


def evaluate(model, processor, rows, dev, tag):
    out = []
    for i, r in enumerate(rows):
        s = score(model, processor, r, dev)
        out.append({**{k: r[k] for k in ("clip", "demo", "robot", "condition", "seed", "split", "success")}, **s})
        if i % 50 == 0:
            print(f"[{tag}] {i}/{len(rows)}", flush=True)
    return out


def metrics(res):
    tp = sum(r["pred"] and r["success"] for r in res)
    tn = sum((not r["pred"]) and (not r["success"]) for r in res)
    p, n = sum(r["success"] for r in res), sum(not r["success"] for r in res)
    acc = (tp + tn) / max(len(res), 1)
    bal = 0.5 * (tp / max(p, 1) + tn / max(n, 1))
    return {"n": len(res), "positives": p, "accuracy": round(acc, 4), "balanced_accuracy": round(bal, 4),
            "true_positive_rate": round(tp / max(p, 1), 4), "true_negative_rate": round(tn / max(n, 1), 4),
            "predicted_success_rate": round(sum(r["pred"] for r in res) / max(len(res), 1), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--eval-only", action="store_true")
    a = ap.parse_args()
    from peft import LoraConfig, get_peft_model
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dev = "cuda"
    rows = load(a.data)
    split = {s: [r for r in rows if r["split"] == s] for s in ("train", "val", "test")}
    processor = AutoProcessor.from_pretrained(MODEL)
    model = Qwen3VLForConditionalGeneration.from_pretrained(MODEL, dtype=torch.bfloat16).to(dev).eval()
    t0 = time.time()
    zs = evaluate(model, processor, split["test"], dev, "zero-shot test")
    (out / "zero_shot_test.jsonl").write_text("".join(json.dumps(r) + "\n" for r in zs))
    report = {"zero_shot_test": metrics(zs), "zero_shot_seconds": round(time.time() - t0)}
    print(json.dumps(report), flush=True)
    if a.eval_only:
        (out / "report.json").write_text(json.dumps(report, indent=1))
        return
    cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                     target_modules=r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)")
    model = get_peft_model(model, cfg)
    model.print_trainable_parameters()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)
    accum, best, rng = 8, None, random.Random(0)
    for ep in range(a.epochs):
        model.train()
        tr = list(split["train"])
        rng.shuffle(tr)
        tot, t1 = 0.0, time.time()
        for i, r in enumerate(tr):
            enc, n_prompt = build(processor, r["path"], ANSWERS[0] if r["success"] else ANSWERS[1])
            enc = {k: v.to(dev) for k, v in enc.items()}
            labels = enc["input_ids"].clone()
            labels[:, :n_prompt] = -100
            loss = model(**enc, labels=labels).loss / accum
            loss.backward()
            tot += float(loss) * accum
            if (i + 1) % accum == 0:
                opt.step()
                opt.zero_grad()
            if i % 100 == 0:
                print(f"[train ep{ep}] {i}/{len(tr)} loss {tot / (i + 1):.4f} ({time.time() - t1:.0f}s)", flush=True)
        model.eval()
        val = metrics(evaluate(model, processor, split["val"], dev, f"val ep{ep}"))
        report[f"val_ep{ep}"] = {**val, "train_loss": round(tot / len(tr), 4)}
        print(json.dumps(report[f"val_ep{ep}"]), flush=True)
        if best is None or val["balanced_accuracy"] > best[0]:
            best = (val["balanced_accuracy"], ep)
            model.save_pretrained(out / "adapter")
    report["kept_epoch"] = best[1]
    from peft import PeftModel
    base = Qwen3VLForConditionalGeneration.from_pretrained(MODEL, dtype=torch.bfloat16).to(dev)
    model = PeftModel.from_pretrained(base, out / "adapter").eval()
    ft = evaluate(model, processor, split["test"], dev, "fine-tuned test")
    (out / "fine_tuned_test.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ft))
    report["fine_tuned_test"] = metrics(ft)
    for name, res in (("zero_shot", zs), ("fine_tuned", ft)):
        for grp in ("unseen_user_demo", "seen_demos"):
            sub = [r for r in res if (r["demo"] == "user_box") == (grp == "unseen_user_demo")]
            report[f"{name}_test_{grp}"] = metrics(sub)
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
