"""relation.py -- Brick 3 of the solution-reasoning scaffold (see claude/DESIGN_solution_reasoning_scaffold.md).

The authors, once they've found the REFERENCE (Brick 2), HYPOTHESISE the win RELATION between the workspace and that
reference and then reduce the discrepancy while watching PROGRESS (Brick 1). This is that reasoning core: it enumerates
the small, general relation set the authors pick from -- {MATCH, CONNECT, ORDER, ARRANGE, REACH} -- expresses each as a
FRAME-NATIVE DISCREPANCY (a scalar gap that is 0 exactly when the relation is satisfied), and TESTS each hypothesis
against the environment's OWN behaviour: the relation whose discrepancy is CONFIDENTLY SHRINKING under play is the one
the environment is rewarding, so it is selected and its drive-target exposed to the policy. Abduction against the env's
own signal -- never a hand-set answer, never a game-id.

CONTAMINATION BOUNDARY: the relation SET is general; WHICH relation wins a given game is discovered here by measuring
discrepancy against the live frames, not encoded. Names no game (answer_lint-enforced). ORDER and ARRANGE are
enumerated but their driving PRIMITIVES are Brick 4 (their discrepancy is left None until then); REACH and CONNECT are
driven now via the existing planner target; MATCH is measured (its edit primitive is also Brick 4). So the framework is
complete and the discovery is the agent's; the deeper primitives fill in behind the same tester.
"""
from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass, field
from math import hypot
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .referent import Referent


@dataclass
class RelationCtx:
    """What a relation needs about the controllable element to judge/drive its discrepancy, read off the policy."""
    cursor: Optional[int] = None            # the avatar/cursor colour, if the game routes a body; else None
    passable: frozenset = field(default_factory=frozenset)
    bg: int = 0


def _centroid_colour(g: np.ndarray, colour: int) -> Optional[Tuple[float, float]]:
    m = (g == colour)
    if not m.any():
        return None
    ys, xs = np.where(m)
    return float(ys.mean()), float(xs.mean())


def _bbox_centre(b: Tuple[int, int, int, int]) -> Tuple[float, float]:
    r0, c0, r1, c1 = b
    return (r0 + r1) / 2.0, (c0 + c1) / 2.0


def _bbox_area(b: Tuple[int, int, int, int]) -> int:
    r0, c0, r1, c1 = b
    return (r1 - r0 + 1) * (c1 - c0 + 1)


def _contains(b: Tuple[int, int, int, int], pt: Tuple[float, float]) -> bool:
    r0, c0, r1, c1 = b
    return r0 <= pt[0] <= r1 and c0 <= pt[1] <= c1


def _bfs_dist(g: np.ndarray, start: Tuple[int, int], goal: Tuple[int, int], passable: frozenset,
              goal_bbox: Optional[Tuple[int, int, int, int]] = None) -> Optional[int]:
    """4-connected step distance from `start` to `goal` over cells whose colour is passable (the goal/start cells and
    the goal bbox are always traversable). None if no passable set or the goal is unreachable. This is the maze-honest
    REACH discrepancy: it shrinks monotonically as the body actually approaches, where straight-line distance does not."""
    if not passable:
        return None
    H, W = g.shape
    sr, sc = start
    gr, gc = goal
    if not (0 <= sr < H and 0 <= sc < W and 0 <= gr < H and 0 <= gc < W):
        return None

    def ok(r, c):
        if not (0 <= r < H and 0 <= c < W):
            return False
        if (r, c) == (gr, gc):
            return True
        if goal_bbox is not None and goal_bbox[0] <= r <= goal_bbox[2] and goal_bbox[1] <= c <= goal_bbox[3]:
            return True
        return int(g[r, c]) in passable
    seen = {(sr, sc)}
    q = deque([(sr, sc, 0)])
    while q:
        r, c, d = q.popleft()
        if (r, c) == (gr, gc):
            return d
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if (nr, nc) not in seen and ok(nr, nc):
                seen.add((nr, nc)); q.append((nr, nc, d + 1))
    return None


def _line_bg_gap(g: np.ndarray, a: Tuple[float, float], b: Tuple[float, float], bg: int) -> int:
    """Count background cells on the straight segment a->b (a proxy for an unfilled CONNECT route between two nodes)."""
    (r0, c0), (r1, c1) = a, b
    n = int(max(abs(r1 - r0), abs(c1 - c0)))
    if n <= 1:
        return 0
    gap = 0
    for t in range(1, n):
        r = int(round(r0 + (r1 - r0) * t / n)); c = int(round(c0 + (c1 - c0) * t / n))
        if 0 <= r < g.shape[0] and 0 <= c < g.shape[1] and int(g[r, c]) == bg:
            gap += 1
    return gap


# ---- the relation set: each is (name, discrepancy, drive-target) ------------------------------------------------
class _Relation:
    name = "?"
    drivable = False                                          # does Brick 3 expose a planner target for it yet?

    def discrepancy(self, g: np.ndarray, refs: List[Referent], ctx: RelationCtx) -> Optional[float]:
        return None

    def target(self, g: np.ndarray, refs: List[Referent], ctx: RelationCtx) -> Optional[Tuple[int, int]]:
        return None


class Reach(_Relation):
    """Pilot the controllable body to a distinguished goal referent. Discrepancy = distance from the cursor to the
    goal; target = the goal cell. Goal = the smallest referent the cursor is not already inside (goal markers/framed
    cells are small and set apart) -- a frame-native stand-in for 'the framed cell to reach'."""
    name = "REACH"
    drivable = True

    def _goal(self, g, refs, ctx):
        cc = _centroid_colour(g, ctx.cursor) if ctx.cursor is not None else None
        if cc is None or not refs:
            return None, None
        cand = [r for r in refs if not _contains(r.bbox, cc)]
        if not cand:
            return None, None
        goal = min(cand, key=lambda r: _bbox_area(r.bbox))    # a goal is a small, distinct region
        return cc, goal

    def discrepancy(self, g, refs, ctx):
        cc, goal = self._goal(g, refs, ctx)
        if cc is None:
            return None
        gc = _bbox_centre(goal.bbox)
        start = (int(round(cc[0])), int(round(cc[1])))
        gcell = (int(round(gc[0])), int(round(gc[1])))
        d = _bfs_dist(g, start, gcell, ctx.passable, goal.bbox)   # maze-honest distance (monotone as we approach)
        if d is not None:
            return float(d)
        return float(hypot(cc[0] - gc[0], cc[1] - gc[1]))     # fallback: no passable set / unreachable -> straight line

    def target(self, g, refs, ctx):
        cc, goal = self._goal(g, refs, ctx)
        if goal is None:
            return None
        gr, gc = _bbox_centre(goal.bbox)
        return int(round(gr)), int(round(gc))


class Connect(_Relation):
    """Link matched endpoint pairs. Discrepancy = total background gap on the straight route between each pair's two
    ends (shrinks as a connecting path fills). Target (Brick-3 coarse; Brick-4 routes properly) = the midpoint of the
    widest-gap pair, or, if a cursor exists, the nearer endpoint of that pair to approach first."""
    name = "CONNECT"
    drivable = True

    def _pairs(self, refs):
        return [r for r in refs if r.kind == "endpoints" and len(r.detail.get("centroids", [])) == 2]

    def discrepancy(self, g, refs, ctx):
        eps = self._pairs(refs)
        if not eps:
            return None
        return float(sum(_line_bg_gap(g, tuple(r.detail["centroids"][0]), tuple(r.detail["centroids"][1]), ctx.bg)
                         for r in eps))

    def target(self, g, refs, ctx):
        eps = self._pairs(refs)
        if not eps:
            return None
        widest = max(eps, key=lambda r: _line_bg_gap(g, tuple(r.detail["centroids"][0]),
                                                      tuple(r.detail["centroids"][1]), ctx.bg))
        a, b = widest.detail["centroids"]
        cc = _centroid_colour(g, ctx.cursor) if ctx.cursor is not None else None
        if cc is not None:                                    # approach the nearer end of the widest pair first
            near = a if hypot(cc[0] - a[0], cc[1] - a[1]) <= hypot(cc[0] - b[0], cc[1] - b[1]) else b
            return int(round(near[0])), int(round(near[1]))
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)      # no cursor -> the gap's midpoint (a place to draw through)
        return int(round(mid[0])), int(round(mid[1]))


class Match(_Relation):
    """Make a workspace panel equal a reference panel (edit-to-match). Discrepancy = the minimum Hamming distance
    (per-cell mismatch fraction) between any two equal-shape panels -- 0 when a workspace has been driven to equal the
    reference. Measured now; its EDIT primitive is Brick 4 (so not drivable at the click tier here, to keep the click
    win intact)."""
    name = "MATCH"
    drivable = False

    def _groups(self, g, refs):
        groups: Dict[Tuple[int, int], List[np.ndarray]] = defaultdict(list)
        for r in refs:
            if r.kind != "panel":
                continue
            r0, c0, r1, c1 = r.bbox
            sub = g[r0:r1 + 1, c0:c1 + 1]
            groups[sub.shape].append(sub)
        return groups

    def discrepancy(self, g, refs, ctx):
        best = None
        for shape, subs in self._groups(g, refs).items():
            for i in range(len(subs)):
                for j in range(i + 1, len(subs)):
                    ham = float((subs[i] != subs[j]).mean())
                    best = ham if best is None else min(best, ham)
        return best


class Order(_Relation):
    """Act on items in the reference's sequence (legend-driven order). Enumerated; its sequencing primitive is Brick 4,
    so no discrepancy is emitted yet (never selected until then)."""
    name = "ORDER"


class Arrange(_Relation):
    """Build/assemble the reference's pattern (block arrangement). Enumerated; its push-to-pattern primitive is Brick 4,
    so no discrepancy is emitted yet."""
    name = "ARRANGE"


class RelationBank:
    """The tester. Each observe() records every relation's current discrepancy; a relation is SELECTED when its
    discrepancy is confidently DECREASING under play (net decrease, mostly non-increasing, real range, enough obs) --
    i.e. the environment is rewarding it. Exposes the selected relation + a drive-target for the policy to pursue.
    General: no game named, no relation privileged; the frames decide which relation is being satisfied."""

    def __init__(self, min_obs: int = 5, min_range: float = 1.0, mono_thresh: float = 0.6):
        self.relations: List[_Relation] = [Reach(), Connect(), Match(), Order(), Arrange()]
        self.hist: Dict[str, List[Optional[float]]] = {r.name: [] for r in self.relations}
        self.last_target: Dict[str, Optional[Tuple[int, int]]] = {r.name: None for r in self.relations}
        self.n = 0
        self.min_obs = int(min_obs)
        self.min_range = float(min_range)
        self.mono_thresh = float(mono_thresh)

    def observe(self, frame, refs: List[Referent], ctx: RelationCtx) -> None:
        g = np.asarray(frame)
        for r in self.relations:
            try:
                d = r.discrepancy(g, refs, ctx)
                t = r.target(g, refs, ctx)
            except Exception:
                d, t = None, None                             # a relation must never crash the policy
            self.hist[r.name].append(None if d is None else float(d))
            self.last_target[r.name] = t
        self.n += 1

    @staticmethod
    def _decreasing(seq: List[Optional[float]]):
        """(non-increasing fraction, range, net decrease) over the non-None subsequence, or None if too few points."""
        vals = [v for v in seq if v is not None]
        if len(vals) < 2:
            return None
        d = np.diff(np.asarray(vals, dtype=float))
        noninc = float((d <= 0).mean())
        return noninc, float(max(vals) - min(vals)), float(vals[0] - vals[-1])

    def _rel(self, name: str) -> _Relation:
        return next(r for r in self.relations if r.name == name)

    def selected(self) -> Optional[str]:
        """The relation whose discrepancy is confidently shrinking (ranked by net decrease), or None."""
        best, best_key = None, None
        for name, seq in self.hist.items():
            vals = [v for v in seq if v is not None]
            if len(vals) < self.min_obs:
                continue
            m = self._decreasing(seq)
            if m is None:
                continue
            noninc, rng, netdec = m
            if noninc >= self.mono_thresh and rng >= self.min_range and netdec > 0:
                key = (netdec, noninc)
                if best_key is None or key > best_key:
                    best_key, best = key, name
        return best

    def drive_target(self) -> Optional[Tuple[int, int]]:
        """A cell for the policy to pursue: the SELECTED relation's target if one is confidently selected; otherwise
        the first DRIVABLE relation (REACH, then CONNECT) that currently proposes a target -- an initial hypothesis to
        test by seeing whether driving it shrinks its discrepancy. None if nothing drivable applies."""
        sel = self.selected()
        if sel is not None and self._rel(sel).drivable and self.last_target.get(sel) is not None:
            return self.last_target[sel]
        for name in ("REACH", "CONNECT"):
            if self.last_target.get(name) is not None:
                return self.last_target[name]
        return None

    def discrepancies(self) -> Dict[str, Optional[float]]:
        """The latest discrepancy per relation (telemetry / for Brick 4 to reason over)."""
        return {n: (seq[-1] if seq else None) for n, seq in self.hist.items()}
