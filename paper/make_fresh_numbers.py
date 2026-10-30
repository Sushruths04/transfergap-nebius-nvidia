"""Writes figures/fresh_numbers.tex (Table 1 fresh columns) and figures/sens_table.tex (Table 2) from recount_sensitivity.json."""
import json
from pathlib import Path
H = Path(__file__).parent
d = json.loads((H / "recount_sensitivity.json").read_text())
KEY = {"Notebook": "P1_notebook", "Markers": "P1_markers", "Orange": "P1_orange_marker", "Notepad": "P1_notepad",
       "PTwoOwn": "P2_box_own_stack", "PTwoPOne": "P2_box_P1_stack", "Own": "P3_recording_P1_stack"}
L = []
raws, stacks = [], []
for k, v in KEY.items():
    for arm, a in (("Five", "ur5e"), ("Ten", "ur10e")):
        r = d["fresh_demos"][f"{v}/{a}"]
        L += [f"\\newcommand{{\\fr{k}{arm}Raw}}{{{r['raw'][0]}}}", f"\\newcommand{{\\fr{k}{arm}Stack}}{{{r['stack'][0]}}}"]
        raws.append(r["raw"][0]); stacks.append(r["stack"][0])
L += [f"\\newcommand{{\\frRawMax}}{{{max(raws)}}}", f"\\newcommand{{\\frStackMin}}{{{min(stacks)}}}"]
(H / "figures" / "fresh_numbers.tex").write_text("\n".join(L) + "\n")
NAME = {"base": "Nominal", "err_x0.5": "Errors $\\times$0.5", "err_x2": "Errors $\\times$2", "block_3cm": "3\\,cm block",
        "block_5cm": "5\\,cm block", "jitter_5cm": "$\\pm$5\\,cm jitter", "perc_x0.25": "Perception $\\times$0.25",
        "perc_x0.25_cal_x2": "+ calibration $\\times$2"}
ST = {"perception": "perception", "calibration": "calibration", "timing": "timing", "retargeting": "retargeting"}
T = []
for s, n in NAME.items():
    a, b = d[f"{s}/ur5e"], d[f"{s}/ur10e"]
    lg = a["largest"] if a["largest"] == b["largest"] else f"{a['largest']}/{b['largest']}"
    T.append(f"  {n} & {a['full']}/{b['full']} & {a['budget_pp']['perception']:+.1f}/{b['budget_pp']['perception']:+.1f}".replace('-', '$-$') + f" & {lg} \\\\")
(H / "figures" / "sens_table.tex").write_text("\n".join(T) + "\n")
rp = {a: d[f"perc_x0.25/{a}"]["eval140_pp"] for a in ("ur5e", "ur10e")}
rc = {a: d[f"perc_x0.25_cal_x2/{a}"]["eval140_pp"] for a in ("ur5e", "ur10e")}
R = lambda x: f"{x:.1f}".replace("-", "$-$")
M = {"rpRuleFive": rp["ur5e"]["rule"], "rpRuleTen": rp["ur10e"]["rule"], "rpLAFive": rp["ur5e"]["always_look_again"], "rpLATen": rp["ur10e"]["always_look_again"],
     "rpBestFive": rp["ur5e"]["hindsight_best"], "rpBestTen": rp["ur10e"]["hindsight_best"],
     "rcRuleFive": rc["ur5e"]["rule"], "rcRuleTen": rc["ur10e"]["rule"], "rcLAFive": rc["ur5e"]["always_look_again"], "rcLATen": rc["ur10e"]["always_look_again"]}
with open(H / "figures" / "fresh_numbers.tex", "a") as f:
    for k, v in M.items():
        f.write(f"\\newcommand{{\\{k}}}{{{R(v)}}}\n")
print(open(H / "figures" / "sens_table.tex").read())
