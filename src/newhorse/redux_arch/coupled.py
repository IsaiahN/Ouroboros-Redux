"""
coupled.py -- redux-triality: reclaim new-horse `coupled_agency.py` (brick 25), re-pointed at discovered structure.

m0r0 (the only richly-winnable dev game: 5 winning recordings) is a MIRROR TWO-BODY game: one navy body on a
cyan half, one on a green half, split by a grey maze. A shared action moves BOTH bodies -- LAW-0 measured:
ACTION1/2 (vertical) move both the SAME way; ACTION3/4 (horizontal) move them MIRRORED (opposite columns), so the
column-sum (cL+cR) is invariant and arbitrary joint targets are reachable only by BREAKING the mirror with a wall
that blocks one body. A single-body navigator cannot solve this (steering one body displaces the other), which is
why the current agent wins 0 on m0r0 and this organ must be reclaimed.

`TwoBodyAgency` detects the >1 controllable components of a colour and learns EACH body's per-action displacement
(majority of NON-ZERO moves -- a blocked (0,0) is wall evidence, not effect evidence) plus the conserved quantity.
`find_two_body_colour` discovers WHICH colour is the coupled cursor (>=2 components that translate under actions).
Discovered structure only; never a baked map.
"""
from __future__ import annotations
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import ndimage

Vec = Tuple[int, int]


class TwoBodyAgency:
    def __init__(self, colour: int, *, max_shift: int = 40, min_obs: int = 3, max_body_cells: int = 400):
        self.colour = int(colour)
        self.max_shift, self.min_obs, self.max_body_cells = int(max_shift), int(min_obs), int(max_body_cells)
        self.disp: Dict[int, Dict[str, List[Vec]]] = defaultdict(lambda: defaultdict(list))
        self._nbodies: Optional[int] = None

    def _components(self, frame: np.ndarray) -> List[Tuple[float, float]]:
        m = np.asarray(frame) == self.colour
        if not m.any():
            return []
        lab, k = ndimage.label(m)
        out = []
        for i in range(1, k + 1):
            ys, xs = np.where(lab == i)
            if ys.size > self.max_body_cells:
                continue
            out.append((float(ys.mean()), float(xs.mean())))
        return sorted(out, key=lambda c: (round(c[1]), round(c[0])))     # left-to-right, stable while not crossing

    def observe(self, before: np.ndarray, action: str, after: np.ndarray) -> None:
        b, a = self._components(before), self._components(after)
        if not b or len(b) != len(a):
            return
        if self._nbodies is None:
            self._nbodies = len(b)
        elif len(b) != self._nbodies:
            return
        for i, (c0, c1) in enumerate(zip(b, a)):
            d = (int(round(c1[0] - c0[0])), int(round(c1[1] - c0[1])))
            if abs(d[0]) + abs(d[1]) <= self.max_shift:
                self.disp[i][action].append(d)

    @staticmethod
    def _majority(ds: List[Vec]) -> Optional[Vec]:
        nz = [d for d in ds if d != (0, 0)]
        if not nz:
            return None
        shift, cnt = Counter(nz).most_common(1)[0]
        return shift if cnt >= max(1, len(nz) // 2) else None

    def n_controllable(self) -> int:
        return int(self._nbodies or 0)

    def body_map(self, body: int) -> Dict[str, Vec]:
        return {a: self._majority(ds) for a, ds in self.disp.get(body, {}).items() if self._majority(ds) is not None}

    def ready(self) -> bool:
        if not self._nbodies or self._nbodies < 2:
            return False
        return all(len(self.body_map(i)) >= 2 for i in range(self._nbodies))

    def conserved(self) -> Dict[str, bool]:
        """Which joint quantity is invariant: `<axis>_sum` (cL+cR const, the mirror) or `<axis>_diff` (cL-cR const,
        rigid translation), read across the actions both bodies have a mapped shift for."""
        out: Dict[str, bool] = {}
        if (self._nbodies or 0) < 2:
            return out
        acts = [a for a in self.disp[0] if self._majority(self.disp[0].get(a, [])) is not None
                and self._majority(self.disp[1].get(a, [])) is not None]
        if not acts:
            return out
        for axis, k in (("row", 0), ("col", 1)):
            out["%s_sum" % axis] = all((self._majority(self.disp[0][a])[k] + self._majority(self.disp[1][a])[k]) == 0
                                       for a in acts)
            out["%s_diff" % axis] = all((self._majority(self.disp[0][a])[k] - self._majority(self.disp[1][a])[k]) == 0
                                        for a in acts)
        return out


def find_two_body_colour(frames: List[np.ndarray], max_body_cells: int = 400) -> Optional[int]:
    """The coupled cursor's colour = the one whose components are consistently >=2 AND translate across frames
    (two small mobile bodies), preferring the most-mobile such colour. Excludes big static regions/walls."""
    F = [np.asarray(f) for f in frames]
    best, best_motion = None, -1.0
    for c in sorted(set(int(v) for f in F for v in np.unique(f))):
        counts, motion, last = [], 0.0, None
        for f in F:
            m = (f == c)
            if not m.any():
                counts.append(0); last = None; continue
            lab, k = ndimage.label(m)
            comps = [np.where(lab == i) for i in range(1, k + 1)]
            comps = [(ys, xs) for ys, xs in comps if ys.size <= max_body_cells]
            counts.append(len(comps))
            cen = tuple(sorted((round(xs.mean()), round(ys.mean())) for ys, xs in comps))
            if last is not None and cen != last:
                motion += 1
            last = cen
        if counts and int(np.median(counts)) >= 2 and motion > best_motion:
            best, best_motion = c, motion
    return best


def learn_two_body(frames: List[np.ndarray], acts: List[str]) -> Tuple[Optional[int], Optional[TwoBodyAgency]]:
    """Discover the coupled colour and learn both bodies' per-action displacement from a frame/action stream."""
    colour = find_two_body_colour(frames)
    if colour is None:
        return None, None
    ag = TwoBodyAgency(colour)
    for i in range(1, len(frames)):
        ag.observe(frames[i - 1], acts[i], frames[i])
    return colour, ag
