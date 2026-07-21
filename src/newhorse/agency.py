"""
agency.py -- brick 12: AGENT-vs-ENVIRONMENT SEPARATION. Identify the controllable (the cursor) and learn
its per-action displacement map, SEPARATING it from action-independent background churn. This is the real
ls20 fix: the maze redraws ~50 cells/step (near-identical under every action), which drowned the piece's
signal in the whole-frame residual; here we isolate the piece by HOW it responds to WHICH action.

Harvested from Redux `effect_classifier.robust_action_map` + `cell_scale`, re-expressed reset-free/online.

The cursor is the colour whose per-action centroid displacement is:
  * CONSISTENT   -- a clear majority shift for each action (not noise), AND
  * DISCRIMINATIVE -- different actions produce different shifts (it responds to WHICH action), AND
  * AXIS-ALIGNED -- moves along a row or a column (a cursor step), for >= 2 distinct shifts.
Background animation / drift moves the same way (or randomly) regardless of the action -> consistent but
NOT discriminative, or not consistent -> rejected. A static HUD/timer never moves -> rejected.

FMap: goodharts_law (d=0.112). Consistency alone is a gameable measure -- a drifting background scores
high on "moves when a step happens." The DISCRIMINATIVE + AXIS-ALIGNED requirement is the anti-Goodhart
guard: the body is the thing whose motion depends on WHICH action I choose, not merely that I acted.

The learned map recovers the STRIDE for free (median axis-aligned shift magnitude = ls20's 5), so a "move"
is expressed at the world's true quantum, not a hardcoded unit. Nothing silent.
"""
from __future__ import annotations
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import ndimage


class CursorAgency:
    """Online identifier of the controllable + its per-action displacement map, guarded against background."""

    def __init__(self, *, background: Optional[int] = None, max_shift: int = 12,
                 min_actions: int = 2, max_cursor_cells: int = 400):
        self.bg = background
        self.max_shift = int(max_shift)             # ignore implausibly large single-step jumps (teleport/noise)
        self.min_actions = int(min_actions)         # need >= this many actions mapped before trusting a cursor
        self.max_cursor_cells = int(max_cursor_cells)
        self.disp: Dict[int, Dict[str, List[Tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
        self._map: Dict[str, Tuple[int, int]] = {}  # cursor's action -> majority shift
        self._colour: Optional[int] = None
        self.log: List[str] = []

    def _centroid(self, frame: np.ndarray, colour: int) -> Optional[Tuple[float, float]]:
        """Centroid of the LARGEST CONNECTED COMPONENT of `colour` -- NOT the mean of all same-colour cells.
        A colour often appears in several places (the moving block AND static glyphs/legends of the same
        colour); averaging them dilutes the mover's displacement (measured live on ls20: the mean shifted 2px
        while the block truly moved 5). Tracking the largest component isolates the body from static twins."""
        mask = np.asarray(frame) == colour
        if not mask.any():
            return None
        lab, k = ndimage.label(mask)
        if k == 0:
            return None
        sizes = ndimage.sum(mask, lab, range(1, k + 1))
        idx = int(np.argmax(sizes)) + 1
        if sizes[idx - 1] > self.max_cursor_cells:          # largest component too big to be a cursor
            return None
        ys, xs = np.where(lab == idx)
        return (float(ys.mean()), float(xs.mean()))

    def observe(self, before: np.ndarray, action: str, after: np.ndarray) -> None:
        """Record each non-background colour's centroid displacement under `action` this step."""
        b, a = np.asarray(before), np.asarray(after)
        bg = self.bg if self.bg is not None else int(np.bincount(b.ravel()).argmax())
        for col in (int(v) for v in np.unique(b) if int(v) != bg):
            c0, c1 = self._centroid(b, col), self._centroid(a, col)
            if c0 is None or c1 is None:
                continue
            d = (int(round(c1[0] - c0[0])), int(round(c1[1] - c0[1])))
            if abs(d[0]) + abs(d[1]) <= self.max_shift:
                self.disp[col][action].append(d)
        self._reeval()
        self.log.append("AGENCY  observed action=%s -> cursor_colour=%s map=%s"
                        % (action, self._colour, self._map))

    def _amap_for(self, colour: int) -> Dict[str, Tuple[int, int]]:
        """The action->shift map for one colour: a shift is kept only if a MAJORITY of that action's
        observations agree on it (consistency)."""
        amap: Dict[str, Tuple[int, int]] = {}
        for a, ds in self.disp[colour].items():
            nz = [d for d in ds if d != (0, 0)]
            if not nz:
                continue
            shift, cnt = Counter(nz).most_common(1)[0]
            if cnt >= max(1, len(ds) // 2):         # consistent majority for this action
                amap[a] = shift
        return amap

    def _reeval(self) -> None:
        """Pick the cursor: the colour whose map is most (axis-aligned, discriminative, consistent).
        Require >= 2 DISTINCT AXIS-ALIGNED shifts -- the anti-Goodhart guard against uniform drift."""
        best, best_key, best_map = None, None, {}
        for colour in list(self.disp):
            amap = self._amap_for(colour)
            if len(amap) < self.min_actions:
                continue
            distinct = set(amap.values())
            axis_aligned = len({s for s in distinct if (s[0] == 0) != (s[1] == 0)})
            key = (axis_aligned, len(distinct), len(amap))
            if best_key is None or key > best_key:
                best_key, best, best_map = key, colour, amap
        if best is not None and best_key[0] >= 2:   # >= 2 distinct axis-aligned shifts -> a real cursor
            self._colour, self._map = best, best_map

    # ---- readout -----------------------------------------------------------------------
    def ready(self) -> bool:
        return self._colour is not None and len(self._map) >= self.min_actions

    def cursor_colour(self) -> Optional[int]:
        return self._colour

    def action_map(self) -> Dict[str, Tuple[int, int]]:
        return dict(self._map)

    def predict(self, action: str) -> Optional[Tuple[int, int]]:
        """The learned displacement of the cursor under `action` (None if not yet mapped)."""
        return self._map.get(action)

    def stride(self) -> Optional[int]:
        """The world's move quantum: the median magnitude of the cursor's axis-aligned shifts (ls20 -> 5)."""
        mags = [abs(dr) + abs(dc) for (dr, dc) in self._map.values() if abs(dr) + abs(dc) >= 2]
        return int(round(float(np.median(mags)))) if mags else None
