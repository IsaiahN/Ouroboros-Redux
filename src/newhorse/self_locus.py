"""
self_locus.py -- brick 10b: identify the CONTROLLABLE (the agent's own body) by action-CONTINGENT
movement, replacing the smallest-object heuristic the first ls20 run showed to be wrong (STAY beat
every unit-shift of the smallest object because that object was not the controllable).

MAP §9.2 / §3: the agent must find which object is ITS locus -- the pose is a vantage that acts, and the
first thing to know is which body responds to the act. FMap: goodharts_law (d=0.119, nearest of the 46)
is the sharp warning here: "moves when I act" as a target admits SPURIOUS correlates -- an object that
drifts on its own, or that happens to move on the same step I act, would be mis-claimed as self. So the
test is not correlation but CONTINGENCY: the object's displacement must VARY WITH WHICH ACTION I take.
An object that moves identically under every action (or moves without depending on my choice) is
autonomous, not self. That interventional contrast is the Goodhart guard.

Keyed by COLOUR signature -- ARC objects keep their colour across frames, so colour is a stable
cross-step handle for "the same body" without needing a global tracker here (the loop's tracker still
owns identity; this module only accrues per-colour, per-action displacement evidence). Nothing silent.
"""
from __future__ import annotations
from typing import Dict, List, Optional


def _centroid(cells):
    rs = [c[0] for c in cells]; cs = [c[1] for c in cells]
    return (sum(rs) / len(rs), sum(cs) / len(cs))


class SelfLocus:
    """Accrues, per colour and per action, how far that colour's object moved -- then names the
    controllable as the colour whose motion is CONTINGENT on the action (moves, and moves differently
    depending on which action), not the one that moves regardless."""

    def __init__(self, *, min_events: int = 2, move_eps: float = 0.5):
        self.min_events = int(min_events)          # need at least this many recorded moves before trusting a colour
        self.move_eps = float(move_eps)            # below this displacement counts as "did not move"
        self.by_colour: Dict[int, Dict[str, List[float]]] = {}   # colour -> action -> [displacement magnitudes]
        self.log: List[str] = []

    def observe(self, action: str, before_objs, after_objs) -> None:
        """Record each colour's displacement under `action` this step (matched before->after by colour+overlap)."""
        for b in before_objs:
            col = min(b.colours)
            cands = [a for a in after_objs if a.colours & b.colours]
            if not cands:
                continue
            # prefer the overlapping same-colour body; else the nearest same-colour object
            a = max(cands, key=lambda o: len(o.cells & b.cells))
            bc, ac = _centroid(b.cells), _centroid(a.cells)
            disp = ((ac[0] - bc[0]) ** 2 + (ac[1] - bc[1]) ** 2) ** 0.5
            self.by_colour.setdefault(col, {}).setdefault(action, []).append(disp)
        self.log.append("LOCUS  action=%s known_colours=%s" % (action, sorted(self.by_colour)))

    def _events(self, col: int) -> int:
        return sum(len(v) for v in self.by_colour.get(col, {}).values())

    def _contingency(self, col: int) -> float:
        """Score a colour's controllability: it must MOVE and its motion must DEPEND on the action.
        spread of mean-displacement across actions = the interventional contrast (Goodhart guard)."""
        acts = self.by_colour.get(col, {})
        means = {a: (sum(v) / len(v)) for a, v in acts.items() if v}
        if not means:
            return 0.0
        moved = max(means.values())
        if moved < self.move_eps:
            return 0.0                              # never really moves -> not the controllable
        if len(means) < 2:
            return 0.0                              # only one action seen -> cannot yet establish contingency
        return max(means.values()) - min(means.values())   # motion varies with the action -> contingent -> self

    def controllable_colour(self) -> Optional[int]:
        best, best_score = None, 0.0
        for col in self.by_colour:
            if self._events(col) < self.min_events:
                continue
            s = self._contingency(col)
            if s > best_score:
                best, best_score = col, s
        return best

    def pick(self, objs):
        """Return the controllable object among `objs` (the one wearing the contingent colour), or None
        if no colour has yet proven contingent (cold start -> the caller falls back to a heuristic)."""
        col = self.controllable_colour()
        if col is None:
            return None
        cands = [o for o in objs if col in o.colours]
        if not cands:
            return None
        return min(cands, key=lambda o: o.size)
