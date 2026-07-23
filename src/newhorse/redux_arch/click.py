"""
click.py -- redux-triality: the CLICK modality (ACTION6 coordinate clicks) + a where-to-click perception.

Coverage gap this closes (docs/DEV_SET_SURVEY.md): 6/25 dev games (s5i5, lp85, tn36, vc33, r11l, ft09) offer
ONLY a coordinate click (ACTION6). The directional stack filters `v == 6`, so the agent literally cannot act on
~24% of the dev set. This module gives it a coordinate to click and an epistemic policy for choosing which.

Two pure pieces (unit-tested without the wire):
  click_targets(frame)   -- the referent prior generalised from COLOUR to COORDINATE space: rank the centroids of
                            distinct non-background components (the interactive tokens) as candidate click points.
  ClickProber            -- curiosity/empowerment over click TARGETS: cycle unvisited candidates first, then prefer
                            the ones observed to CHANGE the board (epistemic action), with a coarse grid sweep as a
                            fallback when the frame has too few components. It manufactures its own gradient on games
                            with no reward and no gameplay recordings to imitate.

We reclaim the MECHANISM (choose-a-click-that-informs), never a per-game answer. LAW 0: the prober SEES the frame
change before it "says" a target is productive.
"""
from __future__ import annotations
from typing import List, Optional, Tuple, Dict
import numpy as np
from scipy import ndimage as _ndi


def _background(frame: np.ndarray) -> int:
    """The most common colour is the field/background (the non-interactive substrate)."""
    vals, cnts = np.unique(np.asarray(frame), return_counts=True)
    return int(vals[int(np.argmax(cnts))])


def click_targets(frame: np.ndarray, bg: Optional[int] = None, min_px: int = 1,
                  max_frac: float = 0.20, top: int = 24) -> List[Tuple[int, int]]:
    """Candidate click points = centroids of distinct non-background components, ranked by salience.

    Salience prefers RARER colours (a colour used for few pixels is likelier an interactive token than a bulk fill)
    and MODERATE-sized components (drop single-pixel noise ties by keeping them last, drop giant fills over
    max_frac of the board). Returns (row, col) centroids, de-duplicated, best-first, capped at `top`.
    """
    f = np.asarray(frame)
    if f.ndim != 2:
        return []
    h, w = f.shape
    area = h * w
    if bg is None:
        bg = _background(f)
    colour_total = {int(c): int(n) for c, n in zip(*np.unique(f, return_counts=True))}
    scored: List[Tuple[float, Tuple[int, int]]] = []
    for colour in sorted(colour_total):
        if colour == bg:
            continue
        lab, k = _ndi.label(f == colour)
        for i in range(1, k + 1):
            ys, xs = np.where(lab == i)
            size = ys.size
            if size < min_px or size > max_frac * area:
                continue
            r, c = int(round(ys.mean())), int(round(xs.mean()))
            # rarer colour -> smaller score (ranks first); tiny (1px) noise pushed later via a size floor
            rarity = colour_total[colour] / area
            noise_penalty = 2.0 if size == 1 else 0.0
            scored.append((rarity + noise_penalty, (r, c)))
    scored.sort(key=lambda t: t[0])
    out: List[Tuple[int, int]] = []
    seen = set()
    for _, rc in scored:
        if rc in seen:
            continue
        seen.add(rc)
        out.append(rc)
        if len(out) >= top:
            break
    return out


def grid_sweep(frame: np.ndarray, n: int = 8) -> List[Tuple[int, int]]:
    """Fallback candidate points: an n x n lattice over the board (used when components are too few to probe)."""
    f = np.asarray(frame)
    h, w = f.shape
    rs = [int((i + 0.5) * h / n) for i in range(n)]
    cs = [int((j + 0.5) * w / n) for j in range(n)]
    return [(r, c) for r in rs for c in cs]


class ClickProber:
    """Curiosity/empowerment over click TARGETS -- the epistemic-action policy for a coordinate-click game.

    Bootstraps with the perceptual candidates (component centroids). Each beat it returns the least-tried target;
    once every candidate has been tried at least once it prefers targets that were OBSERVED to change the board
    (productive), falling back to a coarse grid sweep if nothing perceptual ever moved. This mirrors the directional
    CuriosityExplorer, but over WHERE-TO-CLICK instead of where-to-step.
    """

    def __init__(self, candidates: List[Tuple[int, int]], sweep: Optional[List[Tuple[int, int]]] = None):
        # de-dup while preserving perceptual order, then append any sweep points not already present
        self.targets: List[Tuple[int, int]] = []
        seen = set()
        for rc in list(candidates) + list(sweep or []):
            if rc not in seen:
                seen.add(rc)
                self.targets.append(rc)
        self.tries: Dict[Tuple[int, int], int] = {t: 0 for t in self.targets}
        self.changed: Dict[Tuple[int, int], int] = {t: 0 for t in self.targets}
        self._last: Optional[Tuple[int, int]] = None

    def choose(self) -> Optional[Tuple[int, int]]:
        """Pick the next (row, col) to click. None only if there are no candidates at all."""
        if not self.targets:
            return None
        untried = [t for t in self.targets if self.tries[t] == 0]
        if untried:
            pick = untried[0]                                   # sweep every candidate at least once first
        else:
            # exploit: most-productive target, tie-broken by least-tried (keep sampling productive regions)
            pick = max(self.targets, key=lambda t: (self.changed[t], -self.tries[t]))
            if self.changed[pick] == 0:                         # nothing perceptual ever moved -> least-tried anything
                pick = min(self.targets, key=lambda t: self.tries[t])
        self._last = pick
        return pick

    def observe(self, prev_frame: np.ndarray, new_frame: np.ndarray) -> bool:
        """Record whether the last click changed the board (the empowerment signal). Returns did-change."""
        if self._last is None:
            return False
        self.tries[self._last] += 1
        did = not np.array_equal(np.asarray(prev_frame), np.asarray(new_frame))
        if did:
            self.changed[self._last] += 1
        return did

    def refresh(self, new_candidates: List[Tuple[int, int]]) -> int:
        """Fold freshly-perceived candidate points into the pool (the board changed -> new tokens may exist).
        Existing targets keep their tries/changed history. Returns how many NEW targets were added."""
        added = 0
        for rc in new_candidates:
            if rc not in self.tries:
                self.targets.append(rc)
                self.tries[rc] = 0
                self.changed[rc] = 0
                added += 1
        return added

    def productive(self) -> List[Tuple[int, int]]:
        """Targets that have been observed to change the board (the learned interactive points)."""
        return [t for t in self.targets if self.changed[t] > 0]
