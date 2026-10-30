# TransferGap static report

Free static bundle generated from recorded result files. It makes no live model calls and contains no API credentials.

The validated bundle is also at the [private TransferGap Static Space](https://huggingface.co/spaces/sush0401/transfergap), commit `9f1ac430f643b979c3498f9b6a5983e8868ba4ad`. The host requires sign-in; all 12 remote files were checked against the local bundle after upload. The local instructions below work without a Hugging Face account.

From `transfergap/`:

```bash
python3 static_report/generate.py
python3 -m http.server 8765
```

Open `http://127.0.0.1:8765/static_report/`. Serve from the `transfergap/` directory so report links to `results/` work. For a static host, copy `static_report/` as the site root and copy these result Markdown files into `results/` beside it: `gap_budget_v2_ur5e/summary.md`, `gap_budget_v2_ur10e/summary.md`, `g1_contact_v1/summary.md`, `cosmos_critic_v1/summary.md`, and `cosmos_critic_v2/summary.md`. The relative links in `index.html` currently expect `static_report/` and `results/` as sibling directories; preserve that layout when publishing.

For a reviewable [Hugging Face Static Space](https://huggingface.co/docs/hub/spaces-sdks-static) bundle, run `python3 static_report/build_bundle.py --out /tmp/transfergap-static-space`. The builder copies only the site assets and five Markdown reports, rewrites relative links for the Space root, and adds the required `sdk: static` README metadata. It refuses to overwrite a nonempty directory. The bundle is small and contains no raw runs or secrets.

`generate.py` asserts the expected run sizes and writes only curated summary data to `data.json`. The report is a research prototype: arm errors are assumed, G1 contact is not driven by a human demonstration, and Cosmos versions were scored on different splits.
