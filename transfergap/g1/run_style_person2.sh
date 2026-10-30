#!/bin/bash
# G1 copying person 2 (Pexels 7205253, hand_at_grasp demo): raw path at her pace and at robot pace, and the
# safe_path_v2-projected path at robot pace. Plans are made on the laptop (runs/demos/woman_v2*.plan.json).
set -e
G1=$HOME/transfergap_g1/g1
DP=$HOME/transfergap_g1/woman_v2.plan.json TAG=_woman CONDS="nominal human" bash "$G1/run_style.sh"
DP=$HOME/transfergap_g1/woman_v2_safe.plan.json TAG=_womansafe CONDS="nominal" bash "$G1/run_style.sh"
