"""The controller may read the block pose only through ScriptedPickPlace.perceive(), and never success/scoring.
The error models (v1 errors.py, v2 errors_v2.py incl. the retargeting stage) may read no simulator state at all."""
import ast
import inspect
import sys
import unittest

try:
    import mujoco
    from transfergap.sim import controller
    from transfergap.sim.controller import ScriptedPickPlace
    from transfergap.sim.scene import ASSETS, Scene, robot_ready
    READY = int(mujoco.__version__.split(".")[0]) >= 3 and (ASSETS / "universal_robots_ur5e").exists()
    READY_10 = READY and robot_ready("ur10e")
except ImportError:
    READY = READY_10 = False
from transfergap.sim import errors, errors_v2
from transfergap.sim.errors import build_perturbation, sample_errors

PRIVILEGED = {"block_pos", "block_vel", "contact_flags", "block_body", "block_geom", "block_qadr",
              "table_geom", "link_bodies", "finger_bodies"}
FORBIDDEN_WORDS = ("success", "score", "metrics", "check_success")


def _check_module(tc, module, allowed_fn=None):
    """No privileged attribute outside `allowed_fn` (anywhere if None); no reference to success/scoring."""
    tree = ast.parse(inspect.getsource(module))
    parents = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            parents[ch] = node
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in PRIVILEGED:
            fn, cur = None, node
            while cur in parents:
                cur = parents[cur]
                if isinstance(cur, ast.FunctionDef):
                    fn = cur.name
                    break
            tc.assertTrue(allowed_fn is not None and fn == allowed_fn,
                          f"{module.__name__}: privileged attribute {node.attr} used in {fn}()")
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
            {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | \
            {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
             for a in n.names} | {getattr(n, "module", None) or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    for w in FORBIDDEN_WORDS:
        tc.assertFalse([n for n in names if w in n.lower()], f"{module.__name__} references {w!r}")
    return tree


class ErrorModelsReadNoSimState(unittest.TestCase):
    def test_error_modules_are_pure(self):
        for mod in (errors, errors_v2):
            tree = _check_module(self, mod, allowed_fn=None)
            imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
                       {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
            self.assertFalse(imported & {"mujoco", "scene", "rollout", "controller", "metrics"}, mod.__name__)
            self.assertFalse([i for i in imported if "mujoco" in i or "scene" in i], mod.__name__)


@unittest.skipUnless(READY, "needs mujoco>=3 and menagerie assets")
class PrivilegedGuard(unittest.TestCase):
    def test_static_block_pose_read_only_inside_perceive(self):
        _check_module(self, controller, allowed_fn="perceive")

    def _run_with_spy(self, seed, robot, pert):
        scene = Scene(seed, robot)
        callers = []
        spied = ("block_pos", "block_vel", "contact_flags")
        for attr in spied:
            real = getattr(scene, attr)

            def spy(real=real, attr=attr):
                f = sys._getframe(1)
                callers.append((attr, f.f_code.co_filename.rsplit("/", 1)[-1], f.f_code.co_name))
                return real()
            setattr(scene, attr, spy)
        ctl = ScriptedPickPlace(scene, **pert)
        sub = round(1 / (scene.model.opt.timestep * 100))
        while not ctl.done:
            ctl.step(0.01)
            for _ in range(sub):
                mujoco.mj_step(scene.model, scene.data)
        return callers

    def test_runtime_v2_all_errors_and_corrections_ur5e(self):
        for corr in (None, "look_again", "ik_resolve", "touch_probe_calibration", "speed_cap_3"):
            pert, _ = errors_v2.build_perturbation(3, "full", corr)
            callers = self._run_with_spy(3, "ur5e", pert)
            self.assertEqual(set(callers), {("block_pos", "controller.py", "perceive")}, corr)

    @unittest.skipUnless(READY_10, "needs UR10e menagerie assets")
    def test_runtime_v2_ur10e(self):
        for corr in (None, "look_again", "ik_resolve"):
            pert, _ = errors_v2.build_perturbation(4, "full", corr)
            callers = self._run_with_spy(4, "ur10e", pert)
            self.assertEqual(set(callers), {("block_pos", "controller.py", "perceive")}, corr)

    def test_retarget_error_is_added_to_the_joint_command_only(self):
        import numpy as np
        dq = [0.01, -0.02, 0.0, 0.005, 0.0, -0.01]
        scene = Scene(0)
        ctl = ScriptedPickPlace(scene, retarget_q_err=dq)
        ctl.step(0.01)
        self.assertTrue(np.allclose(scene.data.ctrl[:6], np.clip(ctl.q + dq, ctl.lo, ctl.hi)))
        ref = Scene(0)
        ctl0 = ScriptedPickPlace(ref)
        ctl0.step(0.01)
        self.assertTrue(np.allclose(ctl.q, ctl0.q))          # the IK itself is unaffected (exact-IK oracle)

    def test_runtime_block_pose_only_via_perceive(self):
        scene = Scene(0)
        callers = []
        real = scene.block_pos

        def spy():
            f = sys._getframe(1)
            callers.append((f.f_code.co_filename.rsplit("/", 1)[-1], f.f_code.co_name))
            return real()
        scene.block_pos = spy
        pert, _ = build_perturbation(0, "full", "look_again")
        ctl = ScriptedPickPlace(scene, **pert)
        sub = round(1 / (scene.model.opt.timestep * 100))
        while not ctl.done:
            ctl.step(0.01)
            for _ in range(sub):
                mujoco.mj_step(scene.model, scene.data)
        self.assertTrue(callers)
        self.assertEqual(set(callers), {("controller.py", "perceive")})
        self.assertGreaterEqual(len(callers), 2)   # initial perception + look-again

    def test_perceive_adds_the_configured_error(self):
        scene = Scene(1)
        ctl = ScriptedPickPlace(scene, perception_err_xy=[0.01, -0.02])
        d = ctl.belief - scene.block_pos()
        self.assertAlmostEqual(d[0], 0.01)
        self.assertAlmostEqual(d[1], -0.02)
        self.assertEqual(d[2], 0.0)


class ErrorModel(unittest.TestCase):
    def test_deterministic_and_paired(self):
        a, b = sample_errors(5), sample_errors(5)
        self.assertEqual(a["tcp_offset_vec"].tolist(), b["tcp_offset_vec"].tolist())
        full, _ = build_perturbation(5, "full")
        op, o = build_perturbation(5, "oracle_perception")
        self.assertEqual(o, "perception")
        self.assertEqual(op["perception_err_xy"], [0.0, 0.0])
        self.assertEqual(op["tcp_offset_vec"], full["tcp_offset_vec"])   # other components unchanged
        self.assertEqual(op["timing_scale"], full["timing_scale"])
        allp, _ = build_perturbation(5, "oracle_all")
        self.assertEqual((allp["timing_scale"], allp["tcp_offset_vec"]), (1.0, [0.0] * 3))

    def test_calibration_direction_random_and_magnitude_bounded(self):
        import numpy as np
        vecs = np.array([sample_errors(s)["tcp_offset_vec"] for s in range(200)])
        self.assertLessEqual(np.linalg.norm(vecs, axis=1).max(), 0.03 + 1e-12)
        dirs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
        self.assertTrue(np.all(np.abs(dirs.mean(axis=0)) < 0.2))   # not a fixed direction

    def test_corrections(self):
        f, _ = build_perturbation(7, "full")
        c, _ = build_perturbation(7, "full", "speed_cap_3")
        self.assertLessEqual(c["timing_scale"], 3.0)
        self.assertEqual(c["timing_scale"], min(f["timing_scale"], 3.0))
        with self.assertRaises(ValueError):
            build_perturbation(7, "oracle_all", "look_again")

    @unittest.skipUnless(READY, "needs mujoco")
    def test_touch_probe_leaves_only_probe_noise(self):
        import numpy as np
        scene = Scene(2)
        ctl = ScriptedPickPlace(scene, tcp_offset_vec=[0.02, -0.01, 0.015], tcp_probe_noise_m=[0.001, 0, 0])
        self.assertTrue(np.allclose(ctl.tcp, [0.001, 0, 0]))


if __name__ == "__main__":
    unittest.main()
