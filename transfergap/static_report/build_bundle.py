"""Build a small Hugging Face Static Space bundle from the validated report."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPORTS = ("gap_budget_v2_ur5e", "gap_budget_v2_ur10e", "g1_contact_v1",
           "cosmos_critic_v1", "cosmos_critic_v2")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if out == HERE or out == ROOT or ROOT in out.parents:
        raise ValueError("bundle output must be outside the project tree")
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"bundle directory is not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    for filename in ("index.html", "styles.css", "app.js", "data.json"):
        content = (HERE / filename).read_text()
        if filename in ("index.html", "app.js"):
            content = content.replace("../results/", "results/")
        (out / filename).write_text(content)
    for name in REPORTS:
        dest = out / "results" / name
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "results" / name / "summary.md", dest / "summary.md")
        if name.startswith("cosmos"):
            shutil.copy2(ROOT / "results" / name / "confusion_matrix.png", dest / "confusion_matrix.png")
    (out / "README.md").write_text("""---
title: TransferGap Evidence Report
emoji: 🤖
colorFrom: gray
colorTo: green
sdk: static
license: mit
short_description: Recorded simulator evidence for robot transfer gaps
---

# TransferGap

Recorded simulator results for a research prototype. No live inference, robot control, or secrets.
""")
    print(out)


if __name__ == "__main__":
    main()
