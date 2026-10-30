"""Named transfer-gap perturbations. Each maps to a ScriptedPickPlace keyword (see controller docstring)."""
from __future__ import annotations

# label -> kwargs; levels chosen to span "harmless" to "breaks the grasp"
PERTURBATIONS = {"baseline": {}}
for _name, _levels in {
    "target_offset_m": (0.01, 0.02, 0.03, 0.05),   # perception error on block position
    "tcp_offset_m": (0.01, 0.02, 0.03, 0.04),               # tool-frame calibration error
    "grip_force_scale": (0.1, 0.04, 0.03, 0.02),                     # actuator force limit; 1.0 = 5 N (~90 N at the pads), block weighs 0.5 N
    "timing_scale": (2.0, 3.0, 4.0, 6.0),                         # faster execution
}.items():
    for _v in _levels:
        PERTURBATIONS[f"{_name}={_v}"] = {_name: _v}
