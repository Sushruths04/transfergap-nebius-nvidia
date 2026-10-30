"""Behaviour cloning from the verified data engine (UR5e episodes of ONE human demonstration, scripted fix-stack successes).

Two policies:
  vision : two 96x128 camera images (third-person + wrist) + joint positions + last gripper command -> an 8-step action chunk
  lowdim : privileged baseline without images: joint positions + last gripper command + block xy offset + time since start
Action = 6 joint position targets + gripper (0..255), at 25 Hz. L1 loss on normalised actions, random-shift augmentation for vision.

    python scripts/train_bc.py --data DIR --mode vision --out OUT --epochs 40
"""
import argparse
import glob
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

K = 8


def load(data, val_frac=0.1):
    files = sorted(glob.glob(str(Path(data) / "*.npz")))
    ep = [np.load(f) for f in files]
    return files, [{"img": e["img"], "q": e["q"], "a": e["a"]} for e in ep]


def block_offsets(files):
    from transfergap.sim.scene import sample_block_xy
    return [np.asarray(sample_block_xy(int(Path(f).stem.split("_")[1])), np.float32) - np.array([0.45, -0.12], np.float32) for f in files]


class Net(nn.Module):
    def __init__(self, mode, qdim=7, adim=7):
        super().__init__()
        self.mode = mode

        def enc():
            c = lambda i, o: nn.Sequential(nn.Conv2d(i, o, 3, 2, 1), nn.GroupNorm(8, o), nn.ReLU())
            return nn.Sequential(c(3, 32), c(32, 64), c(64, 128), c(128, 256), nn.AdaptiveAvgPool2d(1), nn.Flatten())
        if mode == "vision":
            self.e1, self.e2 = enc(), enc()
            din = 512 + qdim
        else:
            din = qdim
        self.mlp = nn.Sequential(nn.Linear(din, 512), nn.ReLU(), nn.Linear(512, 512), nn.ReLU(), nn.Linear(512, K * adim))
        self.adim = adim

    def forward(self, img, s):
        if self.mode == "vision":
            x = img.permute(0, 3, 1, 2).float() / 255.0
            h = torch.cat([self.e1(x[..., :128]), self.e2(x[..., 128:]), s], 1)
        else:
            h = s
        return self.mlp(h).view(-1, K, self.adim)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--mode", default="vision", choices=["vision", "lowdim"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--bs", type=int, default=256)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files, eps = load(a.data)
    offs = block_offsets(files) if a.mode == "lowdim" else None
    nval = max(3, len(eps) // 10)
    tr, va = list(range(len(eps) - nval)), list(range(len(eps) - nval, len(eps)))
    allq = np.concatenate([e["q"] for e in eps])
    alla = np.concatenate([e["a"] for e in eps])
    st = {"q_mean": allq.mean(0).tolist(), "q_std": (allq.std(0) + 1e-3).tolist(), "a_mean": alla.mean(0).tolist(), "a_std": (alla.std(0) + 1e-3).tolist()}
    qm, qs, am, asd = (torch.tensor(st[k], dtype=torch.float32) for k in ("q_mean", "q_std", "a_mean", "a_std"))
    dev = "cuda"

    def sample(idx, ids):
        imgs, S, A = [], [], []
        for i in ids:
            e = eps[i]
            T = len(e["q"])
            for t in idx.get(i, range(T)):
                prev_g = e["a"][max(t - 1, 0), 6] / 255.0
                s = np.concatenate([(e["q"][t] - st["q_mean"][:6]) / st["q_std"][:6], [prev_g]]).astype(np.float32)
                if a.mode == "lowdim":
                    s = np.concatenate([s, offs[i] * 30.0, [t / T]]).astype(np.float32)
                ch = e["a"][np.minimum(np.arange(t, t + K), T - 1)]
                imgs.append(e["img"][t] if a.mode == "vision" else 0)
                S.append(s)
                A.append((ch - st["a_mean"]) / st["a_std"])
        return imgs, np.stack(S), np.stack(A).astype(np.float32)

    Xi, Xs, Ya = sample({}, tr)
    Vi, Vs, Va_ = sample({}, va)
    if a.mode == "vision":
        Xi = torch.from_numpy(np.stack(Xi))
        Vi = torch.from_numpy(np.stack(Vi))
    else:
        Xi = Vi = None
    Xs, Ya, Vs, Va_ = map(torch.from_numpy, (Xs, Ya, Vs, Va_))
    net = Net(a.mode, qdim=Xs.shape[1]).to(dev)
    opt = torch.optim.AdamW(net.parameters(), 3e-4, weight_decay=1e-4)
    steps = a.epochs * (len(Xs) // a.bs)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, steps)
    print(f"{a.mode}: {len(tr)} train / {len(va)} val episodes, {len(Xs)} / {len(Vs)} samples, {steps} steps", flush=True)
    t0, log = time.time(), []
    for epoch in range(a.epochs):
        perm = torch.randperm(len(Xs))
        net.train()
        tl = 0.0
        for b in range(len(Xs) // a.bs):
            ix = perm[b * a.bs:(b + 1) * a.bs]
            img = None
            if Xi is not None:
                img = Xi[ix].to(dev)
                dx, dy = np.random.randint(-4, 5, 2)
                img = torch.roll(img, (int(dy), int(dx)), (1, 2))
            pred = net(img, Xs[ix].to(dev))
            loss = F.l1_loss(pred, Ya[ix].to(dev))
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
            tl += float(loss)
        net.eval()
        with torch.no_grad():
            vl = float(np.mean([float(F.l1_loss(net(Vi[i:i + 512].to(dev) if Vi is not None else None, Vs[i:i + 512].to(dev)), Va_[i:i + 512].to(dev))) for i in range(0, len(Vs), 512)]))
        log.append({"epoch": epoch, "train_l1": tl / (len(Xs) // a.bs), "val_l1": vl, "s": round(time.time() - t0)})
        print(log[-1], flush=True)
    torch.save({"model": net.state_dict(), "mode": a.mode, "stats": st, "qdim": Xs.shape[1]}, out / f"policy_{a.mode}.pt")
    (out / f"train_log_{a.mode}.json").write_text(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
