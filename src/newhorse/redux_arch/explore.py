"""
explore.py -- redux-triality: reclaim new-horse `exploration.py` (brick 10a), re-pointed at DISCOVERED structure.

new-horse's Explorer was count-based novelty over ACTIONS (anti-collapse: don't let one action dominate before
others are tried). Here it is extended to STATE COVERAGE -- novelty over the avatar's CELLS -- because in a maze
trying all four actions is quick but *covering the board* (and thereby stumbling into a win) needs cell-level
curiosity. An action's pull = the novelty of the cell it would ENTER, `1/(1+visits)`; the bonus DECAYS with
visits (the Goodhart guard: novelty cannot be farmed by thrashing -- a revisited cell stops paying). Coverage is
guaranteed early and converges late.

Purpose (spec v6, the empowerment/curiosity bootstrap): manufacture a gradient when reward is 0 -- explore broadly
enough to STUMBLE INTO a win, giving the reward-priced market its first currency. Uses only discovered structure
(the passable set + the learned action vecs); never a baked route.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Callable

Cell = Tuple[int, int]
Vec = Tuple[int, int]


@dataclass
class CuriosityExplorer:
    cell_visits: Dict[Cell, int] = field(default_factory=dict)
    action_visits: Dict[str, int] = field(default_factory=dict)

    def cell_novelty(self, cell: Cell) -> float:
        return 1.0 / (1.0 + self.cell_visits.get(cell, 0))

    def action_novelty(self, a: str) -> float:
        return 1.0 / (1.0 + self.action_visits.get(a, 0))

    def choose(self, avatar_px: Cell, action_vecs: Dict[str, Vec],
               passable: Optional[Callable[[Cell], bool]] = None, stride: int = 1) -> Optional[Tuple[str, Cell]]:
        """Pick the PASSABLE action whose destination cell is most NOVEL (tie-broken by the least-tried action).
        Returns (action, entered_cell) or None if boxed in. `entered_cell` is in stride units for visit-counting."""
        s = max(1, int(stride))
        options = []
        for a, v in action_vecs.items():
            dest_px = (avatar_px[0] + v[0], avatar_px[1] + v[1])
            if passable is not None and not passable(dest_px):
                continue
            cell = (int(round(dest_px[0] / s)), int(round(dest_px[1] / s)))
            options.append((a, cell))
        if not options:
            return None
        a, cell = max(options, key=lambda o: (self.cell_novelty(o[1]), self.action_novelty(o[0])))
        return a, cell

    def visit(self, action: str, cell: Cell) -> None:
        self.action_visits[action] = self.action_visits.get(action, 0) + 1
        self.cell_visits[cell] = self.cell_visits.get(cell, 0) + 1

    def coverage(self) -> int:
        """Distinct cells visited so far -- the anti-collapse / breadth metric."""
        return len(self.cell_visits)


@dataclass
class DirectedExplorer:
    """BOUNDARY-DIRECTED empowerment (Tether §4.4 + §3.5). When reward is 0 on a graduated level (SUPPORT fails),
    curiosity must NOT run globally -- it is aimed at the NOVEL bin: the new actors the boundary diff just surfaced.
    The intrinsic gradient is (a) novelty -- reach an UNDER-probed novel actor -- and (b) EMPOWERMENT -- the agent
    CHANGED it (contact that alters the new actor is evidence of control, the Hinton&Nowlan slope where the reward
    is a needle). Concentrates the action budget on new actors, and on the ones it can actually affect. Domain-
    general: a 'novel actor' is whatever the boundary diff flagged NOVEL; it names no game."""
    tries: Dict = field(default_factory=dict)          # novel-target key -> times driven toward
    changed: Dict = field(default_factory=dict)        # novel-target key -> times contact CHANGED the board there
    _last: Optional[object] = None

    def choose(self, targets):
        """targets = list of (key, centroid). Least-tried novel actor first; once all tried, the most PRODUCTIVE
        (most-changed) one. Returns (key, centroid) and registers the attempt, or None if no targets."""
        if not targets:
            self._last = None
            return None
        untried = [t for t in targets if self.tries.get(t[0], 0) == 0]
        pick = untried[0] if untried else max(
            targets, key=lambda t: (self.changed.get(t[0], 0), -self.tries.get(t[0], 0)))
        self._last = pick[0]
        self.tries[pick[0]] = self.tries.get(pick[0], 0) + 1
        return pick

    def credit(self, did_change: bool) -> bool:
        """Empowerment feedback for the LAST chosen target: if contacting it changed the board, it is productive."""
        if self._last is not None and did_change:
            self.changed[self._last] = self.changed.get(self._last, 0) + 1
        return did_change

    def empowerment(self, key) -> float:
        return 1.0 / (1.0 + self.tries.get(key, 0)) + float(self.changed.get(key, 0))

    def productive(self):
        return [k for k, v in self.changed.items() if v > 0]
