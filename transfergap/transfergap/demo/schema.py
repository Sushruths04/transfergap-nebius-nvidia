"""Source-agnostic human demonstration: a pinch-point trajectory plus hand aperture, in a table-anchored frame.

Frame convention (the "demo frame"): metres, right-handed, z up, the table top is the plane z = 0. Any source
(synthetic generator, GEM-X/SOMA body estimate, mocap) is converted into this frame before it reaches the
segmenter and the retargeter, so the robot side never sees source-specific formats.

Fields
  t           (T,)   seconds, strictly increasing
  pinch       (T, 3) midpoint between thumb tip and index tip (or the best available hand point, see `meta`)
  aperture    (T,)   thumb-tip to index-tip distance, metres
  object_xyz  (3,)   estimated centre of the object before the grasp, demo frame
  goal_xyz    (3,)   estimated centre of the placement target (where the object should rest), demo frame
  source      str    "synthetic", "gemx_soma", "mocap", ...
  meta        dict   provenance (clip, model versions, assumptions); JSON-serialisable
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SCHEMA = "transfergap.human_demo/v1"


@dataclass
class HumanDemo:
    t: np.ndarray
    pinch: np.ndarray
    aperture: np.ndarray
    object_xyz: np.ndarray
    goal_xyz: np.ndarray
    source: str
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        self.t = np.asarray(self.t, float)
        self.pinch = np.asarray(self.pinch, float)
        self.aperture = np.asarray(self.aperture, float)
        self.object_xyz = np.asarray(self.object_xyz, float)
        self.goal_xyz = np.asarray(self.goal_xyz, float)
        self.validate()

    def validate(self):
        T = self.t.shape[0]
        if self.t.ndim != 1 or T < 10:
            raise ValueError("t must be 1-D with at least 10 samples")
        if np.any(np.diff(self.t) <= 0):
            raise ValueError("t must be strictly increasing")
        if self.pinch.shape != (T, 3) or self.aperture.shape != (T,):
            raise ValueError(f"pinch must be ({T}, 3) and aperture ({T},)")
        if self.object_xyz.shape != (3,) or self.goal_xyz.shape != (3,):
            raise ValueError("object_xyz and goal_xyz must be 3-vectors")
        for name in ("t", "pinch", "aperture", "object_xyz", "goal_xyz"):
            if not np.all(np.isfinite(getattr(self, name))):
                raise ValueError(f"{name} contains non-finite values")
        if np.any(self.aperture < 0):
            raise ValueError("aperture must be non-negative")
        if not isinstance(self.source, str) or not self.source:
            raise ValueError("source must be a non-empty string")
        json.dumps(self.meta)

    @property
    def fps(self):
        return float(1.0 / np.median(np.diff(self.t)))

    def save(self, path):
        path = Path(path)
        np.savez_compressed(path, schema=SCHEMA, t=self.t, pinch=self.pinch, aperture=self.aperture,
                            object_xyz=self.object_xyz, goal_xyz=self.goal_xyz, source=self.source,
                            meta=json.dumps(self.meta, sort_keys=True))
        return path

    @classmethod
    def load(cls, path):
        z = np.load(path, allow_pickle=False)
        if str(z["schema"]) != SCHEMA:
            raise ValueError(f"unsupported demo schema {z['schema']!r}")
        return cls(z["t"], z["pinch"], z["aperture"], z["object_xyz"], z["goal_xyz"], str(z["source"]),
                   json.loads(str(z["meta"])))
