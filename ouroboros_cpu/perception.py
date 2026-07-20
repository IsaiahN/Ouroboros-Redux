"""perception.py -- Step 4: ONE object/transition layer, replacing v18's inline ObjectExtractor +
ObjectTracker and the composer's separate target perception. proprioception (Step 3) sits on top of this.

The two gates this layer must guarantee (Step 1):
  1a OBJECT PERMANENCE -- nothing with a BEHAVIORAL signature is ever dropped, regardless of colour.
     Colour segmentation is only a SEED for static structure; the authority is BEHAVIOUR. A bg-coloured
     thing that MOVES, BLOCKS, or CHANGES is surfaced as a component even though colour-segmentation
     (which skips background) would miss it. (A truly bg-coloured, non-changing, non-responding region is
     genuinely indistinguishable from background -- correctly nothing, because it has no observable
     existence to act on.)
  1b TRANSITIONS -- not just instantaneous state: move / appear / disappear / transform across frames.

This layer is colour-segmentation for convenience + behaviour for truth. It does NOT type self/world
(that is proprioception's job, on top of this); it provides the objects + transitions both consume.

Verified on SYNTHETIC grids (constructed from the gates, NOT from real games).
"""
import numpy as np
from collections import deque


def background_color(grid):
    v, c = np.unique(grid, return_counts=True)
    return int(v[np.argmax(c)])


class Obj:
    __slots__ = ("color", "cells", "oid", "bg_colored")

    def __init__(self, color, cells, oid=-1, bg_colored=False):
        self.color = int(color)
        self.cells = frozenset(cells)
        self.oid = oid
        self.bg_colored = bg_colored   # surfaced by BEHAVIOUR despite being background-coloured (gate 1a)

    @property
    def centroid(self):
        rs = [r for r, _ in self.cells]; cs = [c for _, c in self.cells]
        return (sum(rs) / len(rs), sum(cs) / len(cs))

    @property
    def norm_shape(self):
        rmin = min(r for r, _ in self.cells); cmin = min(c for _, c in self.cells)
        return frozenset((r - rmin, c - cmin) for r, c in self.cells)

    def __repr__(self):
        return f"Obj(color={self.color}, n={len(self.cells)}{', bg' if self.bg_colored else ''})"


def _cc(mask):
    """4-connected components of a boolean mask -> list of cell-sets."""
    H, W = mask.shape; seen = np.zeros_like(mask, bool); out = []
    for i in range(H):
        for j in range(W):
            if not mask[i, j] or seen[i, j]:
                continue
            comp = []; dq = deque([(i, j)]); seen[i, j] = True
            while dq:
                r, c = dq.popleft(); comp.append((r, c))
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < H and 0 <= nc < W and mask[nr, nc] and not seen[nr, nc]:
                        seen[nr, nc] = True; dq.append((nr, nc))
            out.append(comp)
    return out


def segment(grid, bg=None):
    """Colour-coherent non-background objects (the static SEED)."""
    grid = np.asarray(grid)
    if bg is None:
        bg = background_color(grid)
    objs = []
    for col in np.unique(grid):
        if int(col) == bg:
            continue
        for comp in _cc(grid == col):
            objs.append(Obj(int(col), comp))
    return objs


def behavioral_permanence(prev_grid, cur_grid, bg=None):
    """GATE 1a: surface bg-coloured regions that CHANGED across the transition -- a behavioural component
    colour-segmentation would drop. Returns Objs flagged bg_colored. (Cells where cur OR prev touched
    background but the value changed -> a participant that is background-coloured at this frame.)"""
    prev = np.asarray(prev_grid); cur = np.asarray(cur_grid)
    if prev.shape != cur.shape:
        return []
    if bg is None:
        bg = background_color(cur)
    changed = prev != cur
    bg_touch = (cur == bg) | (prev == bg)            # a bg-coloured cell was involved
    mask = changed & bg_touch
    out = []
    for comp in _cc(mask):
        out.append(Obj(bg, comp, bg_colored=True))
    return out


class Perception:
    """One stack: segment + track + behavioural permanence. Stateful across frames for transitions."""

    def __init__(self):
        self.prev_grid = None
        self.prev_objs = []
        self._next_oid = 0
        self.bg = None

    def _assign_ids(self, objs):
        """Stable ids by (shape,color,proximity) match to previous frame -- object permanence/continuity."""
        used = set()
        for o in objs:
            best = None; best_d = 1e9; best_k = None
            for k, p in enumerate(self.prev_objs):
                if k in used or p.color != o.color or p.norm_shape != o.norm_shape:
                    continue
                d = abs(p.centroid[0] - o.centroid[0]) + abs(p.centroid[1] - o.centroid[1])
                if d < best_d:
                    best, best_d, best_k = p, d, k
            if best is not None:
                o.oid = best.oid; used.add(best_k)
            else:
                o.oid = self._next_oid; self._next_oid += 1
        return objs

    def track(self, prev_objs, cur_objs):
        """GATE 1b: move / appear / disappear / transform events between two object sets."""
        events = {"move": [], "appear": [], "disappear": [], "transform": []}
        used = set()
        cur_by_id = {}
        for o in cur_objs:
            cur_by_id.setdefault(o.oid, o)
        prev_by_id = {p.oid: p for p in prev_objs}
        for oid, o in cur_by_id.items():
            if oid in prev_by_id:
                p = prev_by_id[oid]; used.add(oid)
                dr = round(o.centroid[0] - p.centroid[0]); dc = round(o.centroid[1] - p.centroid[1])
                if (dr, dc) != (0, 0):
                    events["move"].append((oid, dr, dc))
                if o.norm_shape != p.norm_shape:
                    events["transform"].append((oid, p.color, o.color))
            else:
                events["appear"].append((oid, o.color))
        for oid, p in prev_by_id.items():
            if oid not in cur_by_id:
                events["disappear"].append((oid, p.color))
        return events

    def update(self, grid):
        """Ingest a frame. Returns (objects, events). objects include behavioural bg-coloured participants
        (gate 1a); events are the transitions (gate 1b)."""
        grid = np.asarray(grid)
        if self.bg is None:
            self.bg = background_color(grid)
        objs = segment(grid, self.bg)
        if self.prev_grid is not None:
            objs = objs + behavioral_permanence(self.prev_grid, grid, self.bg)   # gate 1a
        objs = self._assign_ids(objs)
        events = self.track(self.prev_objs, objs) if self.prev_grid is not None else \
            {"move": [], "appear": [(o.oid, o.color) for o in objs], "disappear": [], "transform": []}
        self.prev_grid = grid.copy(); self.prev_objs = objs
        return objs, events
