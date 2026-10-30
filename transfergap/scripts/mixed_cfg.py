"""Shared episode configuration for the generalisation data: per-seed cube size and number of distractor objects."""
import numpy as np

SIZES = (0.015, 0.02, 0.025, 0.03, 0.035)      # cube half edge in metres (3 to 7 cm cubes; the default 4 cm cube is 0.02)


def cfg(seed):
    rng = np.random.default_rng(seed + 77_000)
    return float(rng.choice(SIZES)), int(rng.choice([0, 3]))
