"""
budget.py -- brick 15: the BUDGET MODEL. Induce the agent's remaining action budget by WATCHING the HUD
bar deplete (harvested from Redux `budget_model`, re-expressed reset-free). ls20 GAME_OVERs at ~130 steps
because a bottom timer bar runs out; the agent must KNOW that to spend decisively.

The Redux lesson, kept: measure the bar's LENGTH, do NOT divide an area by a guessed drain rate (that bug
made the agent believe it had half its budget for the life of the project). Here: the meter is the bottom-
band colour whose extent only ever DECREASES; the number of actions left is the bar length divided by the
MEASURED columns-lost-per-action (a measured quantity, not a constant).

FMap: optimal_foraging_theory (d=0.180) -- a forager commits to the best patch as its budget depletes, but
ABANDONS a patch whose return has dropped. So budget-awareness drives DECISIVENESS (commit to the best goal
as time runs low) WITHOUT over-committing to an unreachable one (a goal proven a wall is still abandoned).
Nothing about any game is configured -- every quantity is induced from the frame. Nothing silent.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Optional, List, Dict
import numpy as np


class BudgetModel:
    """Induced, not configured: the remaining-action budget read off a depleting HUD bar."""

    def __init__(self, *, band_lo: int = 56, band_hi: int = 64, min_obs: int = 6):
        self.band_lo, self.band_hi = int(band_lo), int(band_hi)
        self.min_obs = int(min_obs)
        self.hist: Dict[int, List[int]] = defaultdict(list)   # colour -> band column-span over steps
        self.meter: Optional[int] = None                       # the colour that measures remaining budget
        self.bar_hist: List[int] = []                          # the meter bar's length over steps
        self.log: List[str] = []

    def _band(self, frame: np.ndarray) -> np.ndarray:
        return np.asarray(frame)[self.band_lo:self.band_hi]

    def _span(self, frame: np.ndarray, colour: int) -> int:
        """Bar LENGTH = number of COLUMNS in the band containing `colour` (measure length, not area)."""
        b = self._band(frame)
        return int(np.any(b == colour, axis=0).sum())

    def observe(self, before: np.ndarray, after: np.ndarray) -> None:
        b = self._band(after)
        for c in np.unique(b):
            self.hist[int(c)].append(int(np.any(b == int(c), axis=0).sum()))
        self._induce_meter()
        if self.meter is not None:
            self.bar_hist.append(self._span(after, self.meter))
        self.log.append("BUDGET  meter=%s bar=%s" % (self.meter, self.bar_hist[-1] if self.bar_hist else None))

    def _induce_meter(self) -> None:
        """The meter is the bottom-band colour whose span NET-DECREASES the most over the run (a depleting
        bar), and is bar-like (wide). Excludes colours that only grow (the elapsed fill) or are static."""
        best, best_drop = None, 0
        for c, s in self.hist.items():
            if len(s) < self.min_obs:
                continue
            drop = s[0] - s[-1]                                 # net decrease over the run
            if drop > best_drop and max(s) >= 8:
                best_drop, best = drop, c
        if best is not None:
            self.meter = best

    def cols_per_action(self) -> Optional[float]:
        """MEASURED columns the bar loses per action (a quantity, not a guessed constant). Median of the
        positive per-step drops, so refills/noise don't skew it."""
        h = self.bar_hist
        drops = [h[i - 1] - h[i] for i in range(1, len(h)) if h[i - 1] - h[i] > 0]
        if not drops:
            return None
        return float(np.median(drops))

    def actions_left(self, frame: np.ndarray) -> Optional[float]:
        """Bar length now / measured columns-per-action -- COUNTED off the bar, not inferred."""
        if self.meter is None:
            return None
        cpa = self.cols_per_action()
        if not cpa:
            return None
        return self._span(frame, self.meter) / cpa

    def fraction_left(self, frame: np.ndarray) -> Optional[float]:
        """Remaining budget as a fraction of the fullest the bar has ever been (one 'life')."""
        if self.meter is None or not self.bar_hist:
            return None
        cur = self._span(frame, self.meter)
        one_life = max(max(self.bar_hist), cur)
        return cur / one_life if one_life else None
