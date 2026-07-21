"""
coupled_agency.py -- brick 25 CARVE 1: MULTI-CONTROLLABLE PERCEPTION.

The single-cursor `agency` (brick 12) models ONE body. Rendered + measured on m0r0 and ka59, both are
TWO-BODY games where a shared action moves BOTH bodies -- often MIRRORED (m0r0: ACTION3 sends body-L left and
body-R right; ka59 the same at a larger stride). A one-body navigator cannot solve them: steering one body
displaces the other. This module perceives the multiple bodies and learns EACH body's per-action displacement,
then reads the COUPLING and its CONSERVED QUANTITIES -- the structure the planner (CARVE 2/3) must respect.

The altitude payoff (why conserved quantities matter): under m0r0's mirror, ACTION3/4 change (cL-cR) but leave
(cL+cR) INVARIANT. So the reachable joint set is a lower-dimensional slice; arbitrary targets are unreachable by
control alone and can only be reached by BREAKING the invariant with a withheld resource -- a wall that blocks
one body so the shared action moves only the other. Reading the invariant is the first step of steering.

FMap: goodharts_law (d=0.112) -- a component is a BODY only if its motion is action-CONTINGENT (varies with WHICH
action), not mere drift; kauffman_nk_landscapes -- high coupling means you must NOT optimize one body in isolation,
so we expose the coupling matrix rather than a per-body illusion of independence. Nothing silent; never encodes an
answer (bodies, coupling, and invariants are all discovered from displacement, no game identity).
"""
from __future__ import annotations
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import ndimage

Vec = Tuple[int, int]


class CoupledAgency:
    """Track the >1 controllable components of a colour and learn each body's per-action displacement + coupling."""

    def __init__(self, colour: int, *, background: int = 0, max_shift: int = 40, min_obs: int = 3,
                 max_body_cells: int = 400):
        self.colour = int(colour)
        self.bg = int(background)
        self.max_shift = int(max_shift)
        self.min_obs = int(min_obs)
        self.max_body_cells = int(max_body_cells)
        # disp[body_index][action] -> list of (dr,dc); bodies are ordered by column then row (stable while
        # they don't cross), so index 0 is the left/top-most body each frame.
        self.disp: Dict[int, Dict[str, List[Vec]]] = defaultdict(lambda: defaultdict(list))
        self._nbodies: Optional[int] = None
        self.log: List[str] = []

    def _components(self, frame: np.ndarray) -> List[Tuple[float, float]]:
        """Sorted centroids (by col, then row) of each connected component of `colour` -- one per body."""
        m = np.asarray(frame) == self.colour
        if not m.any():
            return []
        lab, k = ndimage.label(m)
        out = []
        for i in range(1, k + 1):
            ys, xs = np.where(lab == i)
            if ys.size > self.max_body_cells:
                continue                                      # too big to be a body (e.g. a filled region)
            out.append((float(ys.mean()), float(xs.mean())))
        return sorted(out, key=lambda c: (round(c[1]), round(c[0])))

    def observe(self, before: np.ndarray, action: str, after: np.ndarray) -> None:
        """Record each body's centroid displacement under `action`. Bodies matched by sorted position (stable
        while they don't cross); a step where the body count changes is skipped (ambiguous match)."""
        b = self._components(before)
        a = self._components(after)
        if not b or len(b) != len(a):
            return
        if self._nbodies is None:
            self._nbodies = len(b)
        elif len(b) != self._nbodies:
            return                                            # count changed -> don't corrupt the maps
        for i, (c0, c1) in enumerate(zip(b, a)):
            d = (int(round(c1[0] - c0[0])), int(round(c1[1] - c0[1])))
            if abs(d[0]) + abs(d[1]) <= self.max_shift:
                self.disp[i][action].append(d)
        self.log.append("COUPLED  action=%s n=%d bodies moved=%s"
                        % (action, len(b), [self._majority(self.disp[i].get(action, [])) for i in range(len(b))]))

    @staticmethod
    def _majority(ds: List[Vec]) -> Optional[Vec]:
        """The body's shift under an action: the majority among its NON-ZERO moves (a (0,0) is a blocked move --
        wall evidence, not effect evidence -- so it must not out-vote the real displacement; cf. agency brick 23)."""
        nz = [d for d in ds if d != (0, 0)]
        if not nz:
            return None
        shift, cnt = Counter(nz).most_common(1)[0]
        return shift if cnt >= max(1, len(nz) // 2) else None

    # ---- readout -----------------------------------------------------------------------
    def n_controllable(self) -> int:
        return int(self._nbodies or 0)

    def ready(self) -> bool:
        """Trust the coupling once every body has a mapped shift for >= 2 actions, from enough observations."""
        if not self._nbodies or self._nbodies < 2:
            return False
        for i in range(self._nbodies):
            mapped = [a for a, ds in self.disp[i].items()
                      if len(ds) >= self.min_obs and self._majority(ds) is not None]
            if len(mapped) < 2:
                return False
        return True

    def body_map(self, body: int) -> Dict[str, Vec]:
        """One body's action -> majority shift."""
        return {a: self._majority(ds) for a, ds in self.disp[body].items() if self._majority(ds) is not None}

    def coupling(self, action: str) -> List[Optional[Vec]]:
        """The per-body displacement tuple for `action` -- the coupling signature (how the bodies move TOGETHER)."""
        n = self._nbodies or 0
        return [self._majority(self.disp[i].get(action, [])) for i in range(n)]

    def conserved_axes(self) -> Dict[str, bool]:
        """For the 2-body case, which linear combos are INVARIANT under EVERY mapped action:
        SUM (cL+cR) and/or DIFFERENCE (cL-cR), per axis (row 'r', col 'c'). A conserved axis is a barrier the
        planner must break with a wall. Returns e.g. {'col_sum': True, 'col_diff': False, ...}."""
        out: Dict[str, bool] = {}
        if (self._nbodies or 0) != 2:
            return out
        actions = [a for a in set(self.disp[0]) | set(self.disp[1])
                   if self._majority(self.disp[0].get(a, [])) is not None
                   and self._majority(self.disp[1].get(a, [])) is not None]
        if not actions:
            return out
        for axis, k in (("row", 0), ("col", 1)):
            sum_inv = all((self._majority(self.disp[0][a])[k] + self._majority(self.disp[1][a])[k]) == 0
                          for a in actions)
            dif_inv = all((self._majority(self.disp[0][a])[k] - self._majority(self.disp[1][a])[k]) == 0
                          for a in actions)
            out["%s_sum" % axis] = bool(sum_inv)
            out["%s_diff" % axis] = bool(dif_inv)
        return out
