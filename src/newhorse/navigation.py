"""
navigation.py -- brick 13: GRID NAVIGATION over logical cells (harvested from Redux `spatial_map`,
re-expressed reset-free through the lens). Once the agency (brick 12) knows the cursor's per-action move,
the agent can PATH the cursor to a target -- but the maze has walls it must discover by bumping.

The load-bearing idea (Redux): a wall is a DIRECTED EDGE fact, not a whole-cell property. The fact actually
measured is "from cell K, moving direction D moved me / did not." A cell-level belief throws the direction
away, but a move that failed may be the avatar's leading edge clipping a corner rather than the target cell
being solid -- attributing that to the CELL mislabels traversable floor and then mis-steers every plan. So
we record only the measured directed edge. UNMEASURED edges are optimistically passable (never invent a
wall we haven't hit; let the bump teach us).

FMap: adaptive_immune_system (d=0.144) -- remember SPECIFIC measured threats (walls), and DEFEASIBLY: a
BLOCKED edge decays back to unknown over time (a trigger may have opened it) and is invalidated the instant
its target cell's pixels are seen to change (a moving object slid off it). Nothing silent.
"""
from __future__ import annotations
from collections import deque
from typing import Dict, Tuple, Optional, Iterable, List, Set

Cell = Tuple[int, int]
Dir = Tuple[int, int]


def _unit(v: Tuple[int, int]) -> Dir:
    return ((v[0] > 0) - (v[0] < 0), (v[1] > 0) - (v[1] < 0))


class GridNav:
    """Directed-edge traversability over logical cells, with BFS pathing and a greedy fallback."""

    def __init__(self, ttl: int = 80):
        self.edge: Dict[Tuple[Cell, Dir], bool] = {}    # (cell, unit-dir) -> True(free) / False(blocked)
        self.edge_seen: Dict[Tuple[Cell, Dir], int] = {}
        self.free: Set[Cell] = set()
        self.visits: Dict[Cell, int] = {}               # times the cursor was AT a cell (for the explore tiebreak)
        self.ttl = int(ttl)
        self.t = 0
        self.log: List[str] = []

    def observe_move(self, frm: Cell, direction: Dir, moved: bool) -> None:
        """Record the measured outcome of stepping from `frm` in `direction`. moved=False -> a WALL edge."""
        d = _unit(direction)
        if d == (0, 0):
            return
        self.t += 1
        frm = (int(frm[0]), int(frm[1]))
        self.edge[(frm, d)] = bool(moved)
        self.edge_seen[(frm, d)] = self.t
        self.free.add(frm)
        self.visits[frm] = self.visits.get(frm, 0) + 1      # the cursor was here this step
        if moved:
            self.free.add((frm[0] + d[0], frm[1] + d[1]))
        self.log.append("NAV  %s dir=%s -> %s" % (frm, d, "FREE" if moved else "WALL"))

    def is_blocked(self, frm: Cell, direction: Dir) -> bool:
        """Did we MEASURE that stepping from `frm` in `direction` does nothing? Unmeasured -> False (optimistic)."""
        return self.edge.get(((int(frm[0]), int(frm[1])), _unit(direction))) is False

    def decay(self) -> None:
        """A wall not re-touched in a while may have opened (a trigger) -> reopen it to UNKNOWN (passable)."""
        for k, st in list(self.edge.items()):
            if st is False and (self.t - self.edge_seen.get(k, 0)) > self.ttl:
                del self.edge[k]

    def invalidate(self, changed_cells: Iterable[Cell]) -> None:
        """Reactive dynamism: an edge LEADING INTO a cell whose pixels changed is no longer trusted as a wall."""
        cc = set((int(r), int(c)) for (r, c) in changed_cells)
        for ek, st in list(self.edge.items()):
            if st is False and (ek[0][0] + ek[1][0], ek[0][1] + ek[1][1]) in cc:
                del self.edge[ek]

    def _passable_dirs(self, cell: Cell, dirs: Iterable[Dir]):
        # optimistic: a direction is passable unless known-blocked. Expand LEAST-VISITED neighbours first so
        # that among equal-length optimistic paths, BFS prefers routes through unwalked territory (this is what
        # breaks the 2-cycle a plain optimistic replanner falls into when the direct route is walled).
        passable = [_unit(d) for d in dirs if self.edge.get((cell, _unit(d))) is not False]
        passable.sort(key=lambda d: self.visits.get((cell[0] + d[0], cell[1] + d[1]), 0))
        return passable

    def first_step(self, start: Cell, goal: Cell, dirs: Iterable[Dir], max_expand: int = 20000) -> Optional[Dir]:
        """BFS over the optimistic graph; return the FIRST-step direction of a shortest path to goal, or None.
        The optimistic graph is UNBOUNDED (unmeasured edges are passable), so the search is BOUNDED by
        `max_expand` cells -- past that, give up and let the caller step greedily (prevents a runaway BFS)."""
        start = (int(start[0]), int(start[1])); goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return None
        dirs = list(dirs)
        seen = {start}
        q: deque = deque()
        for d in self._passable_dirs(start, dirs):
            nb = (start[0] + d[0], start[1] + d[1])
            if nb not in seen:
                seen.add(nb); q.append((nb, d))
        expanded = 0
        while q and expanded < max_expand:
            node, first = q.popleft()
            expanded += 1
            if node == goal:
                return first
            for d in self._passable_dirs(node, dirs):
                nb = (node[0] + d[0], node[1] + d[1])
                if nb not in seen:
                    seen.add(nb); q.append((nb, first))
        return None

    def _bfs_known_free(self, start: Cell, goal: Cell, dirs: List[Dir]) -> Optional[Dir]:
        """BFS using ONLY edges proven FREE (exploit the map already walked). First-step dir to goal, or None."""
        start = (int(start[0]), int(start[1])); goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return None
        seen = {start}; q: deque = deque(); first_of = {}
        for d in dirs:
            if self.edge.get((start, d)) is True:
                nb = (start[0] + d[0], start[1] + d[1])
                if nb not in seen:
                    seen.add(nb); first_of[nb] = d; q.append(nb)
        while q:
            node = q.popleft()
            if node == goal:
                return first_of[node]
            for d in dirs:
                if self.edge.get((node, d)) is True:
                    nb = (node[0] + d[0], node[1] + d[1])
                    if nb not in seen:
                        seen.add(nb); first_of[nb] = first_of[node]; q.append(nb)
        return None

    def _frontier_step(self, start: Cell, goal: Cell, dirs: List[Dir]) -> Optional[Dir]:
        """Systematic FRONTIER exploration (harvested from Redux spatial_map): if the goal is not reachable
        through known-free cells, push the boundary between KNOWN-FREE and UNKNOWN outward toward the goal.
        Guarantees coverage so a hidden corridor is always found (FMap: federated_learning -- cover every
        region, don't collapse to a biased subset). If `start` has an untried direction, probe the one nearest
        the goal; else BFS over known-free cells to the nearest-to-goal FRONTIER cell (one with an untried dir)."""
        start = (int(start[0]), int(start[1]))
        untried = [d for d in dirs if (start, d) not in self.edge]
        if untried:
            return min(untried, key=lambda d: abs(start[0] + d[0] - goal[0]) + abs(start[1] + d[1] - goal[1]))
        seen = {start}; q: deque = deque(); first_of = {}
        for d in dirs:
            if self.edge.get((start, d)) is True:
                nb = (start[0] + d[0], start[1] + d[1])
                if nb not in seen:
                    seen.add(nb); first_of[nb] = d; q.append(nb)
        best, best_key = None, None
        while q:
            node = q.popleft()
            if any((node, d) not in self.edge for d in dirs):          # a frontier: has an unexplored direction
                key = abs(node[0] - goal[0]) + abs(node[1] - goal[1])
                if best_key is None or key < best_key:
                    best_key, best = key, node
            for d in dirs:
                if self.edge.get((node, d)) is True:
                    nb = (node[0] + d[0], node[1] + d[1])
                    if nb not in seen:
                        seen.add(nb); first_of[nb] = first_of[node]; q.append(nb)
        return first_of.get(best) if best is not None else None

    def step_toward(self, start: Cell, goal: Cell, dirs: Iterable[Dir]) -> Optional[Dir]:
        """Move now, cheapest-and-most-certain first:
        (1) EXPLOIT   -- goal reachable through PROVEN-FREE cells -> that first step (certain, no bump needed);
        (2) OPTIMISTIC -- else BFS the optimistic graph (unmeasured edges passable) -> head STRAIGHT for the goal
            in open terrain, learning any wall by bumping (brick 13, restored). This is the tier m0r0 needs: a
            direct approach the systematic frontier sweep (3) starves by wandering the whole boundary first;
        (3) FRONTIER  -- only when optimism is WALLED OFF (first_step returns None: every optimistic route hits a
            known wall) push the KNOWN-FREE/UNKNOWN boundary toward the goal (systematic coverage, brick 21) so a
            corridor far off the direct line is still found;
        (4) FALLBACK  -- the least-visited non-wall neighbour toward the goal.
        Ordering matters: (2) before (3) restores the open-terrain beeline (m0r0 L1) that brick 21 regressed by
        promoting frontier coverage above it, while (3) still rescues the narrow-corridor maze (2) thrashes on."""
        start = (int(start[0]), int(start[1]))
        dirs = [_unit(d) for d in dirs]
        exploit = self._bfs_known_free(start, goal, dirs)
        if exploit is not None:
            return exploit
        optimistic = self.first_step(start, goal, dirs)
        if optimistic is not None:
            return optimistic
        frontier = self._frontier_step(start, goal, dirs)
        if frontier is not None:
            return frontier
        cands = []
        for d in dirs:
            if self.edge.get((start, d)) is False:          # skip known walls
                continue
            nb = (start[0] + d[0], start[1] + d[1])
            cands.append((self.visits.get(nb, 0), abs(nb[0] - goal[0]) + abs(nb[1] - goal[1]), d))
        if not cands:
            return None
        cands.sort()
        return cands[0][2]
