"""TransferGap: CI for human-to-robot transfer. Gradio product surface.

Run from the project directory:  .venv/bin/python app/app.py
All panels except "Diagnose (live)" read precomputed results and work offline.
"""
from __future__ import annotations

import html
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gradio as gr  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
from plotly.subplots import make_subplots  # noqa: E402

import backend as B  # noqa: E402

# Validated categorical slots (blue, orange, aqua), assigned to robots in fixed discovery order.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, MUTED, GRID = "#6b6a66", "#8f8e89", "rgba(128,128,128,0.18)"
GOOD, WARN = "#1b8a5a", "#b26a00"

RUNS, PROBLEMS = B.discover_runs()
RUN_BY_NAME = {r.name: r for r in RUNS}
ROBOT_COLOR = {}
for _r in RUNS:
    ROBOT_COLOR.setdefault(_r.robot, SERIES[len(ROBOT_COLOR) % len(SERIES)])
HELDOUT_RUNS = [r.name for r in RUNS if r.has_heldout]


def esc(x):
    return html.escape(str(x))


def prov_html(text):
    """Provenance chip. Markdown-ish backticks become <code>."""
    parts = esc(text).split("`")
    body = "".join(f"<code>{p}</code>" if i % 2 else p for i, p in enumerate(parts))
    return f'<div class="tg-prov"><span class="tg-prov-tag">RECORDED</span>{body}</div>'


def base_layout(fig, height=420, title=None):
    fig.update_layout(height=height, margin=dict(l=56, r=20, t=56 if title else 24, b=48),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", size=13, color=INK),
                      title=dict(text=title, x=0, xanchor="left", font=dict(size=15)) if title else None,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
                      hoverlabel=dict(font_size=13), bargap=0.32, bargroupgap=0.08)
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=INK))
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=MUTED, zerolinewidth=1, tickfont=dict(color=INK))
    return fig


def empty_fig(msg):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(color=MUTED, size=14))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return base_layout(fig, 300)


# ------------------------------------------------------------------------------------- figures

def budget_figure(runs):
    rows = B.budget_rows(runs)
    if not rows:
        return empty_fig("No recorded gap-budget runs found in results/")
    df = pd.DataFrame(rows)
    stage_order = list(dict.fromkeys(df[df.kind == "single"].stage_label)) + [B.stage_label("all")]
    fig = go.Figure()
    for robot, sub in df.groupby("robot", sort=False):
        sub = sub.set_index("stage_label").reindex([s for s in stage_order if s in set(sub.stage_label)]).reset_index()
        color = ROBOT_COLOR.get(robot, SERIES[0])
        fig.add_bar(
            x=sub.stage_label, y=sub.delta_pp, name=robot, marker_color=color,
            marker_opacity=[0.45 if k == "all" else 1.0 for k in sub.kind],
            marker_line_width=0, marker_cornerradius=4,
            error_y=dict(type="data", symmetric=False, array=sub.ci_high - sub.delta_pp,
                         arrayminus=sub.delta_pp - sub.ci_low, color=INK, thickness=1.4, width=6),
            customdata=list(zip(sub.ci_low, sub.ci_high, sub.n, sub.run)),
            hovertemplate=("<b>%{x}</b><br>" + esc(robot) + "<br>recovery %{y:+.1f} pp"
                           "<br>95% CI [%{customdata[0]:+.1f}, %{customdata[1]:+.1f}] pp"
                           "<br>n = %{customdata[2]} paired trials<br>run %{customdata[3]}<extra></extra>"),
            text=[f"{v:+.1f}" for v in sub.delta_pp], textposition="outside", textfont=dict(color=INK, size=12),
            cliponaxis=False)
    fig.update_xaxes(categoryorder="array", categoryarray=stage_order)
    fig.update_yaxes(title_text="Success recovered when stage is oracle-replaced (pp)", ticksuffix="")
    fig.add_vline(x=len(stage_order) - 1.5, line=dict(color=GRID, width=1, dash="dot"))
    return base_layout(fig, 440)


def correction_figure(view):
    before, after, gap, corr = view["before"], view["after"], view["gap"], view["correction"]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.55, 0.45], horizontal_spacing=0.14,
                        subplot_titles=("Held-out success (Wilson 95% CI)", "Paired gain, corrected minus full (pp)"))
    labels = ["Uncorrected", f"Corrected: {corr}"]
    vals = [100 * before["success_rate"], 100 * after["success_rate"]]
    lo = [100 * before["wilson_95"][0], 100 * after["wilson_95"][0]]
    hi = [100 * before["wilson_95"][1], 100 * after["wilson_95"][1]]
    fig.add_bar(x=labels, y=vals, marker_color=["#9a9993", SERIES[0]], marker_line_width=0, marker_cornerradius=4,
                error_y=dict(type="data", symmetric=False, array=[h - v for h, v in zip(hi, vals)],
                             arrayminus=[v - l for v, l in zip(vals, lo)], color=INK, thickness=1.4, width=6),
                text=[f"{v:.0f}%  ({t['successes']}/{t['n']})" for v, t in zip(vals, (before, after))],
                textposition="inside", insidetextanchor="end", textfont=dict(color="white", size=13),
                customdata=list(zip(lo, hi)), showlegend=False,
                hovertemplate="<b>%{x}</b><br>%{y:.1f}% success<br>Wilson 95% [%{customdata[0]:.0f}, %{customdata[1]:.0f}]%<extra></extra>",
                row=1, col=1)
    d, (glo, ghi) = gap["delta_pp"], gap["ci95_pp"]
    color = GOOD if view["improved"] else (WARN if not view["excludes_zero"] else "#c0392b")
    fig.add_scatter(x=[d], y=["gain"], mode="markers", marker=dict(size=14, color=color, line=dict(color="white", width=2)),
                    error_x=dict(type="data", symmetric=False, array=[ghi - d], arrayminus=[d - glo], color=color,
                                 thickness=2.5, width=10),
                    showlegend=False,
                    hovertemplate=f"paired gain {d:+.1f} pp<br>95% CI [{glo:+.1f}, {ghi:+.1f}] pp<br>n = {gap['n']} paired seeds<extra></extra>",
                    row=1, col=2)
    fig.add_vline(x=0, line=dict(color=INK, width=1.5, dash="dash"), row=1, col=2)
    fig.add_annotation(x=0, y=1.0, yref="y2 domain", xref="x2", text="zero", showarrow=False, yshift=10,
                       font=dict(color=MUTED, size=11))
    fig.add_annotation(x=d, y="gain", xref="x2", yref="y2", text=f"<b>{d:+.1f} pp</b>  [{glo:+.1f}, {ghi:+.1f}]",
                       showarrow=False, yshift=26, font=dict(color=INK, size=13))
    span = max(abs(glo), abs(ghi), 5) * 1.35
    fig.update_xaxes(range=[min(-span * 0.35, glo * 1.3), span], row=1, col=2, showgrid=True, gridcolor=GRID,
                     zeroline=False, ticksuffix=" pp")
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False, row=1, col=2)
    fig.update_yaxes(range=[0, 105], ticksuffix="%", row=1, col=1)
    base_layout(fig, 400)
    fig.update_annotations(font_color=INK)
    return fig


# ------------------------------------------------------------------------------------- panels

def headline_html():
    run = next((r for r in RUNS if r.has_heldout), None)
    if run is None:
        return '<div class="tg-card">No held-out result recorded yet.</div>'
    v = B.correction_view(run)
    b, a, g = v["before"], v["after"], v["gap"]
    verdict = "Yes" if v["improved"] else "No"
    vclass = "tg-good" if v["improved"] else "tg-warn"
    tiles = [
        ("Held-out success, uncorrected", f"{100 * b['success_rate']:.0f}%", f"{b['successes']}/{b['n']} seeds"),
        (f"After <code>{esc(v['correction'])}</code>", f"{100 * a['success_rate']:.0f}%", f"{a['successes']}/{a['n']} seeds"),
        ("Paired gain", f"{g['delta_pp']:+.1f} pp", f"95% CI [{g['ci95_pp'][0]:+.1f}, {g['ci95_pp'][1]:+.1f}]"),
        ("CI excludes zero?", f'<span class="{vclass}">{verdict}</span>', f"n = {g['n']} paired held-out trials"),
    ]
    cells = "".join(f'<div class="tg-tile"><div class="tg-tile-k">{k}</div><div class="tg-tile-v">{val}</div>'
                    f'<div class="tg-tile-s">{s}</div></div>' for k, val, s in tiles)
    return (f'<div class="tg-tiles">{cells}</div>'
            f'<p class="tg-note">{esc(run.robot)}, simulated (MuJoCo, real contact). Largest dev budget item: '
            f'<b>{esc(v["component"])}</b> → correction chosen by a frozen rule, then tested once on unseen seeds. '
            f'Error magnitudes are assumptions, not measured from a real human-to-robot pipeline.</p>'
            + prov_html(B.provenance(run, "heldout")))


PIPELINE = [
    ("1", "Human demo", "One RGB video of a person doing the task. GEM-X + SOMA recover body motion.", "G1 path proven"),
    ("2", "Robot", "Same task on each robot: UR5e + Robotiq arm in MuJoCo; Unitree G1 via GEAR-SONIC.", "Arm measured"),
    ("3", "Failure", "Success is scored from simulator state by metrics.py, never by a model's opinion.", "Measured"),
    ("4", "Stage attribution", "Replace one stage at a time with ground truth (oracle) and measure paired recovery.", "Measured (arm)"),
    ("5", "Correction", "Largest budget item selects a fix from a fixed menu; Nemotron proposes it from the trace.", "Measured (arm)"),
    ("6", "Verified", "Fix frozen on dev seeds, tested once on held-out seeds. Claim only if the CI excludes zero.", "Measured (arm)"),
]


def pipeline_html():
    steps = []
    for i, (n, title, desc, status) in enumerate(PIPELINE):
        steps.append(f'<div class="tg-step"><div class="tg-step-n">{n}</div><div class="tg-step-t">{title}</div>'
                     f'<div class="tg-step-d">{esc(desc)}</div><div class="tg-pill">{esc(status)}</div></div>')
        if i < len(PIPELINE) - 1:
            steps.append('<div class="tg-arrow" aria-hidden="true">→</div>')
    return f'<div class="tg-pipe">{"".join(steps)}</div>'


def runs_provenance_html(split="dev"):
    if not RUNS:
        return prov_html("No recorded runs found")
    return "".join(prov_html(B.provenance(r, split)) for r in RUNS)


def interaction_md():
    lines = []
    for r in RUNS:
        it = r.summary["dev"].get("interaction") or {}
        if "sum_of_single_recoveries_pp" in it:
            lines.append(f"- **{r.robot}**: single-stage recoveries sum to {it['sum_of_single_recoveries_pp']:+.1f} pp; "
                         f"replacing all stages at once recovers {it['oracle_all_recovery_pp']:+.1f} pp. "
                         f"The {it['oracle_all_recovery_pp'] - it['sum_of_single_recoveries_pp']:+.1f} pp difference "
                         "is interaction: some trials only succeed once several errors are removed together.")
    return "\n".join(lines)


def caveats_md():
    out = []
    for r in RUNS:
        cav = r.summary.get("caveats") or []
        if cav:
            out.append(f"**{r.name}** ({r.robot})\n" + "\n".join(f"- {c}" for c in cav))
    consts = RUNS[0].summary.get("constants") if RUNS else None
    if consts:
        out.append("**Assumed error model** (frozen in `protocol.json` before held-out trials)\n```json\n"
                   + json.dumps(consts, indent=1) + "\n```")
    return "\n\n".join(out) or "No caveats recorded."


def correction_panel(name):
    run = RUN_BY_NAME.get(name)
    view = B.correction_view(run) if run else None
    if view is None:
        return (empty_fig("This run has no held-out correction test"), "", pd.DataFrame(), prov_html("no held-out data"))
    cls = "tg-verdict-good" if view["improved"] else "tg-verdict-warn"
    rule = esc(view["choice_rule"])
    verdict = (f'<div class="tg-verdict {cls}"><div class="tg-verdict-h">Does the 95% CI exclude zero? '
               f'{"Yes" if view["excludes_zero"] else "No"}</div><div>{esc(view["verdict"]).replace("`", "")}</div>'
               f'<div class="tg-verdict-s">How the fix was chosen: {rule}. Dev budget pointed at '
               f'<b>{esc(view["component"])}</b> → <code>{esc(view["correction"])}</code>. Protocol frozen in git before '
               f'any held-out trial ran.</div></div>')
    table = pd.DataFrame(B.success_rows([run], "heldout")).drop(columns=["Robot", "Run"])
    return correction_figure(view), verdict, table, prov_html(B.provenance(run, "heldout"))


# ------------------------------------------------------------------------------------- upload

def _read_upload(file):
    if file is None:
        raise ValueError("Upload a .jsonl file first, or click 'Load example'.")
    path = Path(file if isinstance(file, str) else file.name)
    return path.name, path.read_text(encoding="utf-8")


def score_file(file, allow_fixtures):
    try:
        name, text = _read_upload(file)
        res = B.score_upload(B.parse_jsonl(text), allow_fixtures=bool(allow_fixtures))
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, OSError) as exc:
        msg = (f'<div class="tg-verdict tg-verdict-warn"><div class="tg-verdict-h">Could not score this file</div>'
               f'<div>{esc(exc)}</div><div class="tg-verdict-s">Episodes must follow the contract in '
               f'transfergap/README.md (schema_version 1, timestamped object states, frozen task tolerances).'
               + (" For hand-authored examples, tick 'Allow fixture data'." if "fixture" in str(exc).lower() else "")
               + '</div></div>')
        return msg, pd.DataFrame(), pd.DataFrame(), "", {}
    groups = res["report"]["groups"]
    n = sum(g["episodes"] for g in groups)
    k = sum(g["successes"] for g in groups)
    fixture_note = (" Contains <b>fixture</b> data: hand-authored, not model performance."
                    if res["report"]["contains_fixtures"] else "")
    head = (f'<div class="tg-verdict tg-verdict-good"><div class="tg-verdict-h">Scored {n} episodes from '
            f'{esc(name)}: {k} succeeded</div><div>{len(groups)} condition group(s). Conditions with different oracle '
            f'values are never pooled.{fixture_note}</div></div>')
    gdf = pd.DataFrame([{"source": g["source"], "protocol": g["protocol_id"], "robot": g["robot"], "method": g["method"],
                         "sensor": g["sensor"], "oracle": g["oracle"] or "-", "success": f"{g['successes']}/{g['episodes']}",
                         "rate": f"{100 * g['success_rate']:.0f}%",
                         "Wilson 95% CI": f"[{100 * g['success_wilson_95'][0]:.0f}%, {100 * g['success_wilson_95'][1]:.0f}%]"}
                        for g in groups])
    p = res["paired"]
    if p is None:
        pmd = "_Paired comparison runs automatically when the file holds exactly two conditions over the same trials._"
    elif "error" in p:
        pmd = f"**Paired comparison not possible** ({p['a']} vs {p['b']}): {p['error']}"
    else:
        lo, hi = p["paired_bootstrap_95_pp"]
        pmd = (f"**Paired comparison** B = `{p['b']}` minus A = `{p['a']}`: **{p['success_gap_b_minus_a_pp']:+.1f} pp**, "
               f"paired bootstrap 95% CI [{lo:+.1f}, {hi:+.1f}] pp over {p['paired_trials']} trials. "
               f"CI excludes zero: **{'yes' if p['excludes_zero'] else 'no'}**. _{p['interval_note']}_")
    return head, gdf, pd.DataFrame(res["episodes"]), pmd, res["report"]


def load_example():
    return str(B.EXAMPLE_EPISODES), True


# ------------------------------------------------------------------------------------- diagnose

def diagnose_banner():
    enabled, msg = B.diagnose_status()
    cls = "tg-verdict-good" if enabled else "tg-verdict-off"
    title = "Live: Nemotron on Nebius Token Factory" if enabled else "Live diagnosis disabled"
    return f'<div class="tg-verdict {cls}"><div class="tg-verdict-h">{title}</div><div>{esc(msg).replace("`", "")}</div></div>'


def diagnose_prompt(name):
    run = RUN_BY_NAME.get(name)
    return json.dumps(B.diagnosis_messages(run), indent=1) if run else ""


def diagnose(name):
    run = RUN_BY_NAME.get(name)
    if run is None:
        return "Pick a recorded run first.", {}
    res = B.run_diagnosis(run)
    if not res["ok"]:
        return f"**{res['message']}**", {}
    prop = res["proposal"] or {}
    if res["problem"]:
        head = f"**Nemotron's answer did not pass the menu check:** {res['problem']}. It is shown below but not used."
    else:
        agree = ("agrees with" if res["agrees_with_rule"] else "differs from")
        head = (f"### Proposed fix: `{prop.get('correction')}` for stage **{prop.get('stage')}**\n"
                f"{prop.get('rationale', '')}\n\nThis {agree} the frozen rule's choice on dev "
                f"(**{res['rule_choice']}**). The proposal is advisory: only the held-out paired test in the "
                f"Correction tab counts as evidence.")
    r = res["receipt"]
    lat = r.get("latency_s")
    head += (f"\n\n<small>Receipt: model `{r.get('returned_model') or r.get('requested_model')}`, "
             f"latency {lat:.1f} s, request sha256 `{(r.get('request_sha256') or '')[:12]}…`, "
             f"saved to `{Path(res['receipt_path']).name}`. Credentials are never stored or shown.</small>"
             if lat is not None else "")
    return head, {"model_output": res["content"], "receipt": r}


# ------------------------------------------------------------------------------------- layout

CSS = """
.gradio-container {max-width: 1180px !important; margin: 0 auto !important;}
.tg-hero {padding: 28px 4px 10px;}
.tg-hero h1 {font-size: 2.1rem; line-height: 1.15; margin: 0 0 6px; font-weight: 700; letter-spacing: -0.02em;}
.tg-hero h1 span {color: #2a78d6;}
.tg-hero p {font-size: 1.05rem; margin: 0; opacity: .8;}
.tg-badges {display:flex; gap:8px; flex-wrap:wrap; margin-top:12px;}
.tg-badge {font-size:.78rem; padding:3px 10px; border-radius:999px; border:1px solid var(--border-color-primary); opacity:.9;}
.tg-pitch {font-size: 1.04rem; line-height: 1.6; max-width: 900px;}
.tg-pipe {display:flex; align-items:stretch; gap:6px; flex-wrap:wrap; margin: 10px 0 6px;}
.tg-step {flex: 1 1 140px; min-width: 140px; border:1px solid var(--border-color-primary); border-radius:12px;
          padding:12px; background: var(--block-background-fill); display:flex; flex-direction:column; gap:6px;}
.tg-step-n {width:24px; height:24px; border-radius:50%; background:#2a78d6; color:#fff; font-weight:700;
            font-size:.8rem; display:flex; align-items:center; justify-content:center;}
.tg-step-t {font-weight:700;}
.tg-step-d {font-size:.84rem; opacity:.8; line-height:1.4; flex:1;}
.tg-pill {align-self:flex-start; font-size:.72rem; padding:2px 8px; border-radius:999px;
          background: rgba(42,120,214,.12); color:#2a78d6; font-weight:600;}
.tg-arrow {display:flex; align-items:center; font-size:1.3rem; opacity:.45;}
@media (max-width: 760px) {.tg-arrow {display:none;} .tg-step {flex-basis: 100%;}}
.tg-tiles {display:grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap:10px; margin: 8px 0;}
.tg-tile {border:1px solid var(--border-color-primary); border-radius:12px; padding:14px 16px; background: var(--block-background-fill);}
.tg-tile-k {font-size:.8rem; opacity:.75;}
.tg-tile-v {font-size:2rem; font-weight:700; letter-spacing:-0.02em; margin: 4px 0;}
.tg-tile-s {font-size:.8rem; opacity:.7;}
.tg-good {color:#1b8a5a;} .tg-warn {color:#b26a00;}
.tg-note {font-size:.9rem; opacity:.85; margin: 6px 0;}
.tg-prov {font-size:.78rem; opacity:.85; margin: 4px 0; display:flex; gap:8px; align-items:baseline; flex-wrap:wrap;}
.tg-prov-tag {font-size:.66rem; font-weight:700; letter-spacing:.06em; padding:1px 6px; border-radius:4px;
              border:1px solid currentColor; opacity:.7;}
.tg-verdict {border-radius:12px; padding:14px 16px; border:1px solid; margin: 6px 0;}
.tg-verdict-h {font-weight:700; font-size:1.05rem; margin-bottom:4px;}
.tg-verdict-s {font-size:.84rem; opacity:.8; margin-top:6px;}
.tg-verdict-good {border-color: rgba(27,138,90,.45); background: rgba(27,138,90,.08);}
.tg-verdict-warn {border-color: rgba(178,106,0,.45); background: rgba(178,106,0,.08);}
.tg-verdict-off {border-color: var(--border-color-primary); background: var(--block-background-fill);}
.tg-foot {font-size:.8rem; opacity:.65; padding: 14px 0 4px;}
"""

HERO = """
<div class="tg-hero">
  <h1>TransferGap: <span>CI for human-to-robot transfer</span></h1>
  <p>Before you fine-tune, find where a human demonstration breaks on each robot, which pipeline stage is to blame,
  and whether a targeted fix actually repairs it.</p>
  <div class="tg-badges"><span class="tg-badge">Nebius Token Factory</span><span class="tg-badge">NVIDIA Nemotron</span>
  <span class="tg-badge">MuJoCo, real contact</span><span class="tg-badge">Paired trials, frozen protocol</span></div>
</div>
"""

PITCH = """<div class="tg-pitch">Robot teams buy human demonstration video and hope it transfers. When it does not,
nobody can say <i>why</i>: was it perception, calibration, retargeting, timing? TransferGap runs the same task
across robots, scores every rollout from simulator state, and then swaps one pipeline stage at a time for ground
truth. The success each swap recovers is that stage's share of the <b>transfer gap budget</b>. The largest item picks
a correction from a fixed menu, the protocol is frozen in git, and the fix is tested once on held-out seeds.
We report an improvement only when the paired 95% confidence interval excludes zero.</div>"""


def build():
    with gr.Blocks(title="TransferGap: CI for human-to-robot transfer") as demo:
        gr.HTML(HERO)
        if PROBLEMS:
            gr.Markdown("\n".join(f"- {p}" for p in PROBLEMS))
        with gr.Tabs():
            with gr.Tab("Overview"):
                gr.HTML(PITCH)
                gr.Markdown("### Pipeline")
                gr.HTML(pipeline_html())
                gr.Markdown("### Headline held-out result")
                gr.HTML(headline_html())

            with gr.Tab("Gap Budget"):
                gr.Markdown("### Where does success go?\nEach bar is the success recovered when one stage is replaced "
                            "by simulator ground truth, paired by seed against the full pipeline (95% paired bootstrap "
                            "CI). Taller bar = that stage costs more. Robots appear here automatically as new "
                            "`results/<run>/summary.json` files are recorded.")
                gr.Plot(budget_figure(RUNS), show_label=False)
                gr.HTML(runs_provenance_html("dev"))
                gr.Markdown(interaction_md())
                gr.Markdown("### Success per condition (dev seeds, Wilson 95% CI)")
                gr.Dataframe(pd.DataFrame(B.success_rows(RUNS, "dev")), interactive=False, wrap=True)
                with gr.Accordion("Caveats and assumed error model", open=False):
                    gr.Markdown(caveats_md())

            with gr.Tab("Correction"):
                gr.Markdown("### Did the fix work on trials it has never seen?\nThe correction was chosen on dev seeds "
                            "by a fixed rule, written to `protocol.json`, committed, and only then run on held-out seeds.")
                pick = gr.Dropdown(HELDOUT_RUNS, value=HELDOUT_RUNS[0] if HELDOUT_RUNS else None, label="Recorded run",
                                   visible=len(HELDOUT_RUNS) > 1)
                c_fig, c_verdict, c_table, c_prov = correction_panel(pick.value)
                verdict = gr.HTML(c_verdict)
                plot = gr.Plot(c_fig, show_label=False)
                prov = gr.HTML(c_prov)
                table = gr.Dataframe(c_table, interactive=False, wrap=True, label="Held-out conditions")
                pick.change(correction_panel, pick, [plot, verdict, table, prov])

            with gr.Tab("Upload & Score"):
                gr.Markdown("### Score your own rollouts\nUpload an episodes `.jsonl` (one episode per line, schema in "
                            "`transfergap/README.md`). Scoring uses the same `metrics.py` code as the recorded runs: "
                            "lift + released-and-settled-at-goal predicate, Wilson CIs, no pooling across oracles.")
                with gr.Row():
                    up = gr.File(label="Episodes (.jsonl)", file_types=[".jsonl", ".json", ".txt"], scale=3)
                    with gr.Column(scale=2):
                        allow = gr.Checkbox(False, label="Allow fixture data (hand-authored examples, not performance)")
                        go_btn = gr.Button("Score episodes", variant="primary")
                        ex_btn = gr.Button("Load example fixture", variant="secondary")
                s_head = gr.HTML()
                s_groups = gr.Dataframe(interactive=False, wrap=True, label="Condition groups")
                s_pair = gr.Markdown()
                s_eps = gr.Dataframe(interactive=False, wrap=True, label="Per episode")
                with gr.Accordion("Raw report (JSON)", open=False):
                    s_raw = gr.JSON()
                outs = [s_head, s_groups, s_eps, s_pair, s_raw]
                go_btn.click(score_file, [up, allow], outs)
                ex_btn.click(load_example, None, [up, allow]).then(score_file, [up, allow], outs)

            with gr.Tab("Diagnose (live)"):
                gr.Markdown("### Ask Nemotron to read the failure trace\nOne call through the project's hosted adapter "
                            "(`transfergap/hosted.py`). The model sees measured numbers only and must pick from a fixed "
                            "correction menu; its answer is checked against that menu and never overrides the benchmark.")
                gr.HTML(diagnose_banner())
                enabled, _ = B.diagnose_status()
                d_run = gr.Dropdown([r.name for r in RUNS], value=RUNS[0].name if RUNS else None, label="Recorded run")
                d_btn = gr.Button("Diagnose with Nemotron" if enabled else "Diagnose (disabled: no NEBIUS_API_KEY)",
                                  variant="primary", interactive=enabled and bool(RUNS))
                d_out = gr.Markdown()
                d_json = gr.JSON(label="Model output and receipt")
                with gr.Accordion("Exact request that would be sent", open=not enabled):
                    d_prompt = gr.Code(diagnose_prompt(d_run.value), language="json")
                d_run.change(diagnose_prompt, d_run, d_prompt)
                d_btn.click(diagnose, d_run, [d_out, d_json])

        gr.HTML('<div class="tg-foot">All panels except Diagnose read precomputed results from <code>results/</code> '
                'and work offline. Simulated results; error magnitudes are stated assumptions. '
                'Scoring code: transfergap/metrics.py.</div>')
    return demo


THEME = gr.themes.Soft(primary_hue="blue", neutral_hue="stone",
                       font=[gr.themes.Font("Inter"), "ui-sans-serif", "system-ui", "sans-serif"])

demo = build()

if __name__ == "__main__":
    demo.launch(theme=THEME, css=CSS, server_name=os.environ.get("GRADIO_SERVER_NAME", "127.0.0.1"),
                max_file_size="50mb")
