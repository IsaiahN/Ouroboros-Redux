# -*- coding: utf-8 -*-
"""A spatial occupancy map for an avatar that moves on a lattice (one discrete action = one cell step).

The agent learns traversability purely from movement OUTCOMES -- no priors about the game:
  - the avatar OCCUPIES a cell            -> FREE
  - it tried to step into a neighbour and MOVED   -> that neighbour is FREE
  - it tried to step into a neighbour and DID NOT MOVE -> that neighbour is BLOCKED (wall / obstacle)

Exploration is FRONTIER-driven: head toward the nearest FREE cell that borders an UNKNOWN cell, so the whole
reachable map gets covered instead of cycling in place. The world is DYNAMIC (triggers can open a wall, objects
move), so BLOCKED cells EXPIRE back to UNKNOWN after a time-to-live, and any contradicting observation overrides
the map immediately -- the map is a decaying belief, not ground truth.
"""
from collections import deque

UNKNOWN, FREE, BLOCKED = 0, 1, 2


class SpatialMap:
    # THE MAP SPEAKS. What it has learned to be impassable is not a fact it holds, it is a DECISION the agent acts
    # on every step -- and it was held silently. Set by whoever builds the map; narration is once-keyed so the
    # stream stays evidence rather than a log.
    emit = None

    def _say(self, msg, key):
        if self.emit is None:
            return
        seen = getattr(self, "_said", None)
        if seen is None:
            seen = self._said = set()
        if key in seen:
            return
        seen.add(key)
        try:
            self.emit(msg)
        except Exception:
            pass

    def __init__(self, ttl=60):
        self.cell = {}            # (r,c) lattice coord -> UNKNOWN/FREE/BLOCKED
        self.seen = {}            # (r,c) -> last step index it was (re)observed
        self.ttl = int(ttl)       # BLOCKED cells older than this expire to UNKNOWN (dynamism)
        self.t = 0
        # DIRECTED EDGE memory: the fact actually measured is "from cell K, moving D moved me / did not move me".
        # A cell-level belief throws the direction away, but the avatar spans several pixels, so a failed move can be
        # its leading edge clipping a corner rather than the target cell being solid -- attributing that to the CELL
        # mislabels traversable floor and the mislabel then steers every future plan. The edge records only what was
        # measured. Unmeasured edges are NOT walls (never invent one we haven't hit; let the bump teach us).
        self.edge = {}            # ((r,c), (dr,dc)) -> FREE/BLOCKED
        self.edge_seen = {}       # ((r,c), (dr,dc)) -> last step index observed

    # ---- belief updates -------------------------------------------------
    def _set(self, k, st):
        self.cell[k] = st
        self.seen[k] = self.t

    def visit(self, cell):
        """The avatar is HERE this step -> FREE and current."""
        self.t += 1
        self._set(cell, FREE)

    def record_neighbour(self, frm, direction, moved):
        """Outcome of trying to step from `frm` one lattice cell in `direction`=(dr,dc) in {-1,0,1}^2."""
        dr = (direction[0] > 0) - (direction[0] < 0)
        dc = (direction[1] > 0) - (direction[1] < 0)
        if (dr, dc) == (0, 0):
            return
        frm = (int(frm[0]), int(frm[1]))
        nk = (frm[0] + dr, frm[1] + dc)
        self._set(nk, FREE if moved else BLOCKED)
        self.edge[(frm, (dr, dc))] = FREE if moved else BLOCKED     # the DIRECTED measured fact
        self.edge_seen[(frm, (dr, dc))] = self.t

    def edge_blocked(self, frm, direction):
        """Did we MEASURE that stepping from `frm` in `direction` does nothing? Unmeasured => False (optimistic)."""
        dr = (direction[0] > 0) - (direction[0] < 0)
        dc = (direction[1] > 0) - (direction[1] < 0)
        return self.edge.get(((int(frm[0]), int(frm[1])), (dr, dc))) == BLOCKED

    def blocked_edges(self):
        return {k for k, st in self.edge.items() if st == BLOCKED}

    def decay(self):
        """A wall we haven't re-touched in a while may have opened (trigger) or an object may have moved off it."""
        for k, st in list(self.cell.items()):
            if st == BLOCKED and (self.t - self.seen.get(k, 0)) > self.ttl:
                self.cell[k] = UNKNOWN
        for k, st in list(self.edge.items()):                # edges decay on the same terms -- one belief, one policy
            if st == BLOCKED and (self.t - self.edge_seen.get(k, 0)) > self.ttl:
                self.edge[k] = UNKNOWN

    def invalidate(self, cells):
        """Coordinate-specific, REACTIVE dynamism: a cell whose pixels/area were OBSERVED to change can no longer
        be trusted as a wall, so reopen it for re-checking immediately -- the complement to time-based decay. This
        is what lets the agent respond when a trigger opens a wall or a moving object slides on/off a cell, rather
        than waiting out a timer."""
        _ch = set((int(k[0]), int(k[1])) for k in cells)
        for k in _ch:
            if self.cell.get(k) == BLOCKED:
                self.cell[k] = UNKNOWN
                self.seen[k] = self.t
        for ek, st in list(self.edge.items()):               # an edge LEADING INTO a changed cell is no longer trusted
            if st == BLOCKED and (ek[0][0] + ek[1][0], ek[0][1] + ek[1][1]) in _ch:
                self.edge[ek] = UNKNOWN
                self.edge_seen[ek] = self.t

    # ---- queries --------------------------------------------------------
    def status(self, k):
        return self.cell.get(k, UNKNOWN)

    def distance(self, a, b):
        """Learned step-cost from a to b over FREE (traversed) cells -- BFS on the graph we actually walked. Returns the
        step count, or None if b is not reachable from a through known-free cells. This is 'we have crossed the board,
        so we know the costs', cached in the map rather than re-derived."""
        a = (int(a[0]), int(a[1])); b = (int(b[0]), int(b[1]))
        if a == b:
            return 0
        prev = {a: 0}; q = deque([a])
        while q:
            cur = q.popleft(); d = prev[cur]
            for nb in self._free_neighbours(cur):
                if nb not in prev:
                    prev[nb] = d + 1
                    if nb == b:
                        return d + 1
                    q.append(nb)
        return None

    def reachable(self, start, budget):
        """The set of FREE cells reachable from start within `budget` steps -- the budget HORIZON on the learned graph
        (which cells the agent can still get to before it runs out of actions)."""
        start = (int(start[0]), int(start[1]))
        prev = {start: 0}; q = deque([start]); out = {start}
        while q:
            cur = q.popleft(); d = prev[cur]
            if d >= budget:
                continue
            for nb in self._free_neighbours(cur):
                if nb not in prev:
                    prev[nb] = d + 1; out.add(nb); q.append(nb)
        return out

    def nearest_reachable_to(self, start, target, max_r=8):
        """BFS from start over FREE cells; return the reachable FREE cell CLOSEST (manhattan) to `target` and within
        max_r of it, with its distance-from-start: (cell, manhattan_to_target, dist_from_start) or None. This is what
        lets 'route to a BLOCKED target' work -- e.g. a lock glyph inside a walled box: aim at the door's reachable
        frontier and step in, instead of failing because the target cell itself is blocked."""
        start = (int(start[0]), int(start[1])); target = (int(target[0]), int(target[1]))
        prev = {start: 0}; q = deque([start]); best = None
        while q:
            cur = q.popleft(); d = prev[cur]
            man = abs(cur[0] - target[0]) + abs(cur[1] - target[1])
            if man <= max_r and (best is None or (man, d) < (best[1], best[2])):
                best = (cur, man, d)
            for nb in self._free_neighbours(cur):
                if nb not in prev:
                    prev[nb] = d + 1; q.append(nb)
        return best

    def _free_neighbours(self, k):
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (k[0] + dr, k[1] + dc)
            if self.cell.get(nb, UNKNOWN) == FREE:
                yield nb

    def _has_unknown_neighbour(self, k):
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if self.cell.get((k[0] + dr, k[1] + dc), UNKNOWN) == UNKNOWN:
                return True
        return False

    def _unknown_neighbours(self, k):
        return sum(1 for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
                   if self.cell.get((k[0] + dr, k[1] + dc), UNKNOWN) == UNKNOWN)

    def frontier_step(self, pos, prefer=None, info_gain=False):
        """BFS over FREE cells from `pos` to a FREE cell bordering UNKNOWN. Return the (dr,dc) lattice direction of
        the FIRST step toward it, or None if the reachable map is fully explored.

        Two PRIORITIES (the agent picks; see _priority_* in the traversal taxonomy):
        - default (info_gain=False): NEAREST frontier -- cheap, sweeps the local edge. `prefer` (recent travel
          direction) breaks ties so exploration runs in lines (momentum) not veers.
        - info_gain=True: EXPECTED-INFORMATION frontier -- among ALL reachable frontier cells, head to the one that
          maximizes unknown-neighbours-revealed PER step of travel (novelty / curiosity: 'go where I learn most',
          not merely 'the nearest edge'). Opening onto a large unknown region 6 steps away beats a 1-cell pocket
          2 steps away. This is _priority_novelty over the frontier set, and it is what finds a far chamber (the L1
          box) without grinding every local nook first."""
        start = (int(pos[0]), int(pos[1]))
        if self.cell.get(start, UNKNOWN) == BLOCKED:
            self._set(start, FREE)                      # we are standing here, so it is free
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if prefer is not None:
            pd = ((prefer[0] > 0) - (prefer[0] < 0), (prefer[1] > 0) - (prefer[1] < 0))
            if pd in dirs:
                dirs = [pd] + [d for d in dirs if d != pd]   # carry momentum: keep going the same way first
        if not info_gain:
            # already at a frontier -> step directly into an unknown neighbour (momentum-first)
            if self._has_unknown_neighbour(start):
                for dr, dc in dirs:
                    if self.cell.get((start[0] + dr, start[1] + dc), UNKNOWN) == UNKNOWN:
                        return (dr, dc)
        prev = {start: None}; dist = {start: 0}
        q = deque([start])
        goal = None; best = None; best_score = -1.0
        while q:
            cur = q.popleft()
            for nb in self._free_neighbours(cur):
                if nb not in prev:
                    prev[nb] = cur; dist[nb] = dist[cur] + 1
                    if self._has_unknown_neighbour(nb):
                        if not info_gain:
                            goal = nb; q.clear(); break
                        # info-gain: unknown cells revealed per step of travel to reach this frontier
                        score = self._unknown_neighbours(nb) / float(dist[nb])
                        if score > best_score:
                            best_score = score; best = nb
                    q.append(nb)
            else:
                continue
            break
        if info_gain:
            goal = best
        if goal is None:
            return None
        path = [goal]
        while prev[path[-1]] is not None:
            path.append(prev[path[-1]])
        path.reverse()                                  # start ... goal
        nxt = path[1] if len(path) >= 2 else goal
        return (nxt[0] - start[0], nxt[1] - start[1])

    def ego(self, pos, directions=None):
        """The EGOCENTRIC view of the same belief: the world-frame map read relative to where the avatar IS now.

        The allocentric map answers 'what is the world like' (cells, frontier, reachability -- true regardless of who
        is standing where). Action selection needs the other question -- 'if I step THAT way from HERE, what do I
        already know?' -- which is this. Both are views over one memory, never two memories: an egocentric belief that
        could disagree with the allocentric one is how a navigator ends up with two maps and trusts neither.

        Returns {(dr,dc): {'cell', 'state', 'edge_blocked', 'known'}} for each direction off `pos`.
        """
        pos = (int(pos[0]), int(pos[1]))
        out = {}
        for d in (directions or ((-1, 0), (1, 0), (0, -1), (0, 1))):
            dr = (d[0] > 0) - (d[0] < 0); dc = (d[1] > 0) - (d[1] < 0)
            nb = (pos[0] + dr, pos[1] + dc)
            st = self.cell.get(nb, UNKNOWN)
            eb = self.edge.get((pos, (dr, dc))) == BLOCKED
            out[(dr, dc)] = {"cell": nb, "state": st, "edge_blocked": eb,
                             "known": (st != UNKNOWN) or ((pos, (dr, dc)) in self.edge)}
        return out

    def coverage(self):
        free = sum(1 for s in self.cell.values() if s == FREE)
        blocked = sum(1 for s in self.cell.values() if s == BLOCKED)
        return dict(free=free, blocked=blocked, known=len(self.cell))
