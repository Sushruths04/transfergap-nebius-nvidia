"""Writes figures/v2_numbers.tex (macros) and figures/rule_table.tex (Table: rule comparison) from recount_v2.json."""
import json
from pathlib import Path
H = Path(__file__).parent
d = json.loads((H / "recount_v2.json").read_text())
f1 = lambda x: f"{x:.1f}".replace("-", "$-$")
fs = lambda x: f"{x:+.1f}".replace("-", "$-$")
M = []
def mac(n, v): M.append(f"\\newcommand{{\\{n}}}{{{v}}}")
for arm, a in (("Five", "ur5e"), ("Ten", "ur10e")):
    e = d[f"err_x0.5/{a}"]
    mac(f"ehFull{arm}", e["full"]); mac(f"ehMargin{arm}", f1(e["top_minus_second_pp"][0]))
    mac(f"ehMarginLo{arm}", f1(e["top_minus_second_pp"][1])); mac(f"ehMarginHi{arm}", f1(e["top_minus_second_pp"][2]))
    for key, nm in (("depth_nominal", "DnNom"), ("depth_calib_0p5deg_5mm", "DnHalf"), ("depth_calib_1deg_10mm", "DnOne")):
        r = d[f"{key}/{a}"]
        mac(f"{nm}Perc{arm}", f1(r["budget_pp"]["perception"][0])); mac(f"{nm}Largest{arm}", r["largest"])
m = json.loads((H.parent / "transfergap" / "results" / "sensitivity_v2" / "perception_measured.json").read_text())
for key, nm in (("nominal", "mmNom"), ("calib_0p5deg_5mm", "mmHalf"), ("calib_1deg_10mm", "mmOne")):
    mac(nm, f"{1000 * m[key]['rms_axis_m']:.1f}" if key != "nominal" else f"{1000 * m[key]['rms_axis_m']:.2f}")
p5, p10 = d["perc_x0.25/ur5e"]["rule"], d["perc_x0.25/ur10e"]["rule"]
c5, c10 = d["perc_x0.25_cal_x2/ur5e"]["rule"], d["perc_x0.25_cal_x2/ur10e"]["rule"]
for n, r in (("A", p5), ("B", p10)):
    mac("rp" + n, f1(r["rule_pp"][0])); mac("rl" + n, f1(r["always_look_again_pp"][0])); mac("rh" + n, f1(r["hindsight_pp"]))
    dd = r["rule_minus_look_again_pp"]; mac("rd" + n, fs(dd[0])); mac("rd" + n + "lo", f1(dd[1])); mac("rd" + n + "hi", f1(dd[2]))
for n, r in (("A", c5), ("B", c10)):
    mac("rc" + n, f1(r["rule_pp"][0]))
    dd = r["rule_minus_look_again_pp"]; mac("re" + n, fs(dd[0])); mac("re" + n + "lo", f1(dd[1])); mac("re" + n + "hi", f1(dd[2]))
for n, a in (("A", "ur5e"), ("B", "ur10e")):
    t = d[f"timing_measured/{a}"]; r = t["rule"]
    mac("tmFull" + n, t["full"]); mac("tmBud" + n, f1(t["budget_pp"]["timing"][0]))
    mac("tmMar" + n, f1(t["top_minus_second_pp"][0])); mac("tmMarLo" + n, f1(t["top_minus_second_pp"][1])); mac("tmMarHi" + n, f1(t["top_minus_second_pp"][2]))
    mac("tmRule" + n, f1(r["rule_pp"][0])); dd = r["rule_minus_look_again_pp"]
    mac("tmDiff" + n, fs(dd[0])); mac("tmDiffLo" + n, f1(dd[1])); mac("tmDiffHi" + n, f1(dd[2]))
(H / "figures" / "v2_numbers.tex").write_text("\n".join(M) + "\n")
T = []
for s, nm in (("perc_x0.25", r"Perception $\times$0.25"), ("perc_x0.25_cal_x2", r"+ calibration $\times$2")):
    for a, an in (("ur5e", "UR5e"), ("ur10e", "UR10e")):
        r = d[f"{s}/{a}"]["rule"]
        T.append(f"  {nm} & {an} & {r['pick']} & {f1(r['rule_pp'][0])} & {f1(r['always_look_again_pp'][0])} & "
                 f"{fs(r['rule_minus_look_again_pp'][0])} [{f1(r['rule_minus_look_again_pp'][1])}, {f1(r['rule_minus_look_again_pp'][2])}] & {f1(r['hindsight_pp'])} \\\\")
(H / "figures" / "rule_table.tex").write_text("\n".join(T) + "\n")
print("\n".join(T)); print("\n".join(M))
