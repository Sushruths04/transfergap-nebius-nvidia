# kairos_mobile_demo_v1 (a model/engineering check, not a scientific result)

`python -m transfergap.sim.kairos_mobile demo --out ...` (seed 0, start pose x -1.3 m, y -0.9 m, yaw 0.9 rad). The KAIROS robot in MuJoCo (no Isaac Sim): Summit XLS chassis
(lab URDF mesh), planar holonomic base driven by velocity- and acceleration-limited position servos, four visual omni wheels, UR10e + Robotiq 2F-140 on the top plate
0.38062 m above the base link (0.5076 m above the floor). Phases: drive to the table (5.16 s, parked within 1 cm / 0.01 rad of the parking pose), pick and place the block
onto the tray with the unchanged scripted controller (12.91 s, placed), drive away (2 s, base moving with the arm folded). Identical on the laptop and on the GPU cluster (same phase report).
Not modelled: wheel/floor contact and wheel motors; the arm-mount yaw convention is not checked against the real robot; the real task table height differs. Lab mesh files stay out of git (`sim/assets/kairos/`).
Video: `deliverables/kairos_mobile_demo_2026-10-06.mp4` (untracked).
