"""progress.py -- Brick 1 of the solution-reasoning scaffold (see claude/DESIGN_solution_reasoning_scaffold.md).

The solution authors follow a DENSE progress gradient the agent currently ignores: a bar/region that fills as they
approach the goal, even when `levels_completed` stays 0 until the whole puzzle is solved. This reads that gradient
FRAME-NATIVELY (no embodied priors, no game-id): the progress signal is the COLOUR whose cell-count rises most
MONOTONICALLY across the stream. That single structural feature covers bars filling, grids filling with correct-colour
tiles, and corridors filling with a path -- all of which are "a colour's count only goes up". A confidence gate rejects
noise/toggles (a colour that dips is not progress). The per-step DELTA is a dense reward the policy reinforces on.

Deliberately general: it names no game; it privileges no colour; whether a signal exists is decided by monotonicity of
the frames themselves, and which relation actually wins is still left for the agent to discover downstream (Brick 3).
"""
from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Optional
import numpy as np


class ProgressProbe:
    """Tracks per-colour cell counts across a frame stream and reports the most monotonically-increasing one as the
    progress signal, with a confidence gate so noise is not mistaken for progress."""

    def __init__(self, min_obs: int = 6, min_range: int = 3, mono_thresh: float = 0.8):
        self.counts: Dict[int, List[int]] = defaultdict(list)   # colour -> count per observation (backfilled)
        self.n = 0
        self.min_obs = int(min_obs)
        self.min_range = int(min_range)
        self.mono_thresh = float(mono_thresh)

    def observe(self, frame) -> None:
        g = np.asarray(frame)
        vals, cnts = np.unique(g, return_counts=True)
        seen = {int(v): int(c) for v, c in zip(vals.tolist(), cnts.tolist())}
        for c in set(seen) | set(self.counts):
            c = int(c)
            if c not in self.counts:
                self.counts[c] = [0] * self.n                   # backfill a colour first seen mid-stream
            self.counts[c].append(seen.get(c, 0))
        self.n += 1

    @staticmethod
    def _mono(seq: List[int]):
        """(non-decreasing fraction, range, net increase) for a count sequence."""
        if len(seq) < 2:
            return 0.0, 0, 0
        d = np.diff(np.asarray(seq))
        nondec = float((d >= 0).mean())
        return nondec, int(max(seq) - min(seq)), int(seq[-1] - seq[0])

    def best_colour(self) -> Optional[int]:
        """The colour whose count is a confident monotone-rising progress signal, or None. Ranks by net increase then
        monotonicity; requires enough observations, a real range, a net increase, and non-decreasing >= mono_thresh."""
        best, best_key = None, None
        for c, seq in self.counts.items():
            if len(seq) < self.min_obs:
                continue
            nondec, rng, inc = self._mono(seq)
            if nondec >= self.mono_thresh and rng >= self.min_range and inc > 0:
                key = (inc, nondec)
                if best_key is None or key > best_key:
                    best_key, best = key, int(c)
        return best

    def confident(self) -> bool:
        return self.best_colour() is not None

    def value(self) -> float:
        """Normalised progress in [0,1] for the best colour (0 if none)."""
        c = self.best_colour()
        if c is None:
            return 0.0
        seq = self.counts[c]
        lo, hi = min(seq), max(seq)
        return (seq[-1] - lo) / (hi - lo) if hi > lo else 0.0

    def delta(self) -> float:
        """Change in the best colour's count from the previous observation to the current (0 if no confident signal)."""
        c = self.best_colour()
        if c is None or len(self.counts[c]) < 2:
            return 0.0
        seq = self.counts[c]
        return float(seq[-1] - seq[-2])
