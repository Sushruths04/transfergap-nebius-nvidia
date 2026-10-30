# The MuJoCo minor version flips the closed-loop G1 controller (2026-10-06)

While rebuilding the `full` image for the end-to-end check (`docker/e2e.sh`) the unpinned sim venv resolved to mujoco 3.15.0 (the first image, built 2026-10-04, has 3.14.0;
the only other package that differed was filelock 4.0.10 -> 4.0.12). The same closed-loop hybrid controller, seeds 1200-1203, same pod, same weights, same plans:

| sim venv | block lift per seed (cm) | grasped (lift >= 5 cm) |
|---|---|---|
| mujoco 3.15.0 (rebuilt image, `rows_mujoco_3_15_0.json`) | 0.4, 0.1, 1.4, 0.2 | 0 / 4 |
| mujoco 3.14.0 (same pod, `uv pip install mujoco==3.14.0 filelock==4.0.10`, `rows_mujoco_3_14_0.json`) | 13.1, 15.3, 15.7, 14.7 | 4 / 4 |

Reading: the closed-loop G1 result depends on the MuJoCo minor version. Small sample (4 seeds each, nondeterministic simulator) but the contrast is stark and the only intended change was the simulator package.
It does NOT explain the host-vs-image gap in `results/g1_in_image_v1`: the host pod has mujoco 3.14.0 as well (venv check printed 3.14.0). It is a second, separate environment sensitivity,
and it is why the image now pins the sim venv (`docker/sim_venv_pins.txt`, asserted in the Dockerfile) and why the e2e check requires at least half of its G1 rollouts to grasp.
