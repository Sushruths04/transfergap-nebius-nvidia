"""Split a human pick-and-place demo into skills from hand aperture and pinch-point motion.

Deterministic and parameter-light: grasp = the hand closes (aperture falls below a threshold between its open and
closed levels and stays there), release = it opens again. Lift ends when the pinch point reaches most of its peak
height after the grasp; the place phase starts when it comes back down before the release. Reach starts when the
hand first moves. All thresholds are module constants so a frozen protocol can record them.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

CLOSE_FRAC = 0.5        # threshold = closed + CLOSE_FRAC * (open - closed)
HOLD_S = 0.10           # aperture must stay past the threshold this long to count (hysteresis against jitter)
SMOOTH_S = 0.10         # moving-average window for aperture and pinch
MOVE_SPEED = 0.05       # m/s: the hand counts as moving above this speed
LIFT_FRAC = 0.8         # lift ends / place starts at this fraction of the peak height above the grasp height


@dataclass
class Segments:
    reach_start: int
    grasp: int
    lift_end: int
    place_start: int
    release: int
    end: int

    def as_dict(self):
        return asdict(self)


def _smooth(x, n):
    if n <= 1:
        return np.asarray(x, float)
    k = np.ones(n) / n
    pad = n // 2
    xp = np.pad(np.asarray(x, float), [(pad, n - 1 - pad)] + [(0, 0)] * (np.ndim(x) - 1), mode="edge")
    if np.ndim(x) == 1:
        return np.convolve(xp, k, mode="valid")
    return np.stack([np.convolve(xp[:, i], k, mode="valid") for i in range(xp.shape[1])], axis=1)


def _first_run(mask, start, hold):
    """First index >= start where mask holds for `hold` consecutive samples."""
    run = 0
    for i in range(start, len(mask)):
        run = run + 1 if mask[i] else 0
        if run >= hold:
            return i - hold + 1
    return None


def segment(demo):
    """Segments (sample indices) for a HumanDemo. Raises ValueError if no grasp/release can be found.
    If demo.meta["events"] = {"grasp": i, "release": j} is given (e.g. from a tracked object starting/stopping to
    move in motion capture), those indices are used instead of the aperture threshold."""
    dt = float(np.median(np.diff(demo.t)))
    ev = demo.meta.get("events")
    n_s = max(1, int(round(SMOOTH_S / dt)))
    hold = max(1, int(round(HOLD_S / dt)))
    ap = _smooth(demo.aperture, n_s)
    p = _smooth(demo.pinch, n_s)
    T = len(ap)
    head = max(hold, T // 10)
    if ev is not None:
        grasp, release = int(ev["grasp"]), int(ev["release"])
        if not 0 < grasp < release < T:
            raise ValueError(f"invalid events {ev}")
    else:
        open_level = float(np.median(ap[:head]))
        closed_level = float(np.percentile(ap, 5))
        if open_level - closed_level < 0.01:
            raise ValueError("hand aperture never changes by more than 1 cm; no grasp visible")
        thr = closed_level + CLOSE_FRAC * (open_level - closed_level)
        grasp = _first_run(ap < thr, 0, hold)
        if grasp is None:
            raise ValueError("no grasp found (aperture never stays closed)")
        release = _first_run(ap > thr, grasp + hold, hold)
        if release is None:
            raise ValueError("no release found (aperture never reopens after the grasp)")
    speed = np.linalg.norm(np.gradient(p, demo.t, axis=0), axis=1)
    moving = np.flatnonzero(speed[:grasp] > MOVE_SPEED)
    reach_start = int(moving[0]) if moving.size else 0
    z0 = p[grasp, 2]
    zc = p[grasp:release + 1, 2]
    peak = float(zc.max())
    if peak - z0 < 0.01:
        raise ValueError("the object is never lifted more than 1 cm between grasp and release")
    level = z0 + LIFT_FRAC * (peak - z0)
    above = np.flatnonzero(zc >= level)
    lift_end = grasp + int(above[0])
    place_start = grasp + int(above[-1])
    return Segments(reach_start, int(grasp), int(lift_end), int(place_start), int(release), T - 1)


def keyframes(demo, seg):
    """Positions and durations the retargeter needs, read off the (unsmoothed) demo at the segment indices."""
    t, p = demo.t, demo.pinch
    win = slice(seg.grasp, seg.release + 1)
    return {
        "grasp_pinch": p[seg.grasp].tolist(),
        "release_pinch": p[seg.release].tolist(),
        "peak_height_above_grasp_m": float(p[win, 2].max() - p[seg.grasp, 2]),
        "durations_s": {"reach": float(t[seg.grasp] - t[seg.reach_start]),
                        "lift": float(t[seg.lift_end] - t[seg.grasp]),
                        "transport": float(t[seg.place_start] - t[seg.lift_end]),
                        "place": float(t[seg.release] - t[seg.place_start])},
        "segments": seg.as_dict(),
    }
