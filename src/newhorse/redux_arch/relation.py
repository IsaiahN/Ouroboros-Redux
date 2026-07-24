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
    reach_goal: Optional[Tuple[int, int, int, int]] = None   # the LOCKED goal bbox the bank pins across frames (REACH)
    match_roles: Optional[Tuple[np.ndarray, np.ndarray]] = None   # (WORKSPACE, REFERENCE) sub-grids, role by mutation


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


def _overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    """Do two bboxes intersect? (used to keep a locked goal pinned to the referent that still covers it)."""
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


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

    def _goal_bbox(self, g, refs, ctx):
        """The goal bbox: the bank's LOCKED goal if it pinned one (stable across frames -> monotone discrepancy),
        otherwise the smallest referent the cursor is not already inside (standalone fallback for direct use)."""
        cc = _centroid_colour(g, ctx.cursor) if ctx.cursor is not None else None
        if cc is None:
            return None, None
        if ctx.reach_goal is not None:
            return cc, ctx.reach_goal
        cand = [r for r in refs if not _contains(r.bbox, cc)]
        if not cand:
            return cc, None
        return cc, min(cand, key=lambda r: _bbox_area(r.bbox)).bbox

    def discrepancy(self, g, refs, ctx):
        cc, gb = self._goal_bbox(g, refs, ctx)
        if cc is None or gb is None:
            return None
        gc = _bbox_centre(gb)
        start = (int(round(cc[0])), int(round(cc[1])))
        gcell = (int(round(gc[0])), int(round(gc[1])))
        d = _bfs_dist(g, start, gcell, ctx.passable, gb)      # maze-honest distance (monotone as we approach)
        if d is not None:
            return float(d)
        return float(hypot(cc[0] - gc[0], cc[1] - gc[1]))     # fallback: no passable set / unreachable -> straight line

    def target(self, g, refs, ctx):
        cc, gb = self._goal_bbox(g, refs, ctx)
        if gb is None:
            return None
        gr, gc = _bbox_centre(gb)
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
    """Bring a WORKSPACE panel to equal a REFERENCE panel -- the concept behind edit-to-match (ft09/cd82) AND Locksmith
    (ls20: make the KEY match the LOCK). The two can differ by a dihedral ROTATION/REFLECTION and/or a RECOLOUR, so the
    discrepancy is TRANSFORM-AWARE (Lane-C `panel_transform_distance`): the number of primitive operators still to apply
    (rotation steps + recolours), or the raw cell-edit distance when they are the same shape but not transform-related
    (ft09). 0 exactly when the workspace equals the reference. Measured + a RESIDUAL exposed (what a driver must undo);
    the operator/edit DRIVE is the Locksmith L2/L3 bricks, so not drivable here (keeps the click win intact)."""
    name = "MATCH"
    drivable = False

    def _panels(self, g, refs):
        out = []
        for r in refs:
            if r.kind != "panel":
                continue
            r0, c0, r1, c1 = r.bbox
            out.append(g[r0:r1 + 1, c0:c1 + 1])
        return out

    def _best_pair(self, g, refs):
        from .transform import panel_transform_distance
        panels = self._panels(g, refs)
        best = None                                           # (dist, residual)
        for i in range(len(panels)):
            for j in range(i + 1, len(panels)):
                d, t = panel_transform_distance(panels[i], panels[j])
                if d is None:
                    continue
                if best is None or d < best[0]:
                    best = (float(d), t)
        return best

    def discrepancy(self, g, refs, ctx):
        if ctx.match_roles is not None:                       # role-aware: measure the DIRECTED workspace->reference gap
            from .transform import panel_transform_distance
            d, _ = panel_transform_distance(ctx.match_roles[0], ctx.match_roles[1])
            if d is not None:
                return float(d)
        best = self._best_pair(g, refs)                       # fallback: closest matchable panel pair (no roles yet)
        return best[0] if best is not None else None

    def residual(self, g, refs, ctx):
        """The RESIDUAL transform (rotation/recolour still to null) relating WORKSPACE->REFERENCE (directed, when roles
        are known) or the closest matchable panel pair -- what the Locksmith operator planner (L2/L3) must reduce to
        identity. Exposed now; consumed by L2."""
        if ctx.match_roles is not None:
            from .transform import panel_transform_distance
            _, t = panel_transform_distance(ctx.match_roles[0], ctx.match_roles[1])
            return t
        best = self._best_pair(g, refs)
        return best[1] if best is not None else None


def _levenshtein(a: List[int], b: List[int]) -> int:
    """Edit distance between two token sequences (insert/delete/substitute). This is the ORDER-native discrepancy: it
    counts the moves to bring one sequence to the other's ORDER, so a PERMUTATION reads as a few edits (not many cell
    diffs, as 2-D MATCH would). Distinct from MATCH by construction."""
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (0 if a[i - 1] == b[j - 1] else 1))
        prev = cur
    return prev[n]


class Order(_Relation):
    """Act on items in the reference's SEQUENCE (legend-driven order: family B -- tr87/su15/sb26). Discrepancy = the
    minimum EDIT DISTANCE between two ordered token sequences read from the frame (a REFERENCE sequence and a WORKSPACE
    sequence being brought to it) -- 0 when a workspace sequence matches the reference's order. Order-native (a
    permutation is a few edits), distinct from MATCH's 2-D content comparison. Measured now; the act-in-order DRIVE is a
    later brick, so not drivable here. Needs >=2 ordered sequences (else None)."""
    name = "ORDER"

    def _sequences(self, refs):
        return [tuple(r.detail["sequence"]) for r in refs
                if r.kind == "legend" and len(r.detail.get("sequence", [])) >= 2]

    def discrepancy(self, g, refs, ctx):
        seqs = self._sequences(refs)
        if len(seqs) < 2:
            return None
        best = None
        for i in range(len(seqs)):
            for j in range(i + 1, len(seqs)):
                d = _levenshtein(list(seqs[i]), list(seqs[j]))
                best = d if best is None else min(best, d)
        return None if best is None else float(best)


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
        self.target_hist: Dict[str, List[Optional[Tuple[int, int]]]] = {r.name: [] for r in self.relations}
        self.n = 0
        self.min_obs = int(min_obs)
        self.min_range = float(min_range)
        self.mono_thresh = float(mono_thresh)
        self._reach_goal: Optional[Tuple[int, int, int, int]] = None   # the pinned REACH goal (identity lock)
        self._shape: Tuple[int, int] = (0, 0)
        self._last = None                                    # (frame, refs, ctx) of the last observe (for match_residual)
        self._region_hash: Dict[Tuple[int, int, int, int], List[bytes]] = {}   # panel bbox -> recent content hashes
        self._region_sub: Dict[Tuple[int, int, int, int], np.ndarray] = {}     # panel bbox -> latest sub-grid
        self._roles: Optional[Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]] = None   # (ws_bbox, ref_bbox)
        self._role_win = 8

    def _resolve_reach_goal(self, g: np.ndarray, refs: List[Referent], ctx: RelationCtx):
        """Pin the REACH goal ACROSS frames: keep tracking the same goal region (the referent that still overlaps the
        locked bbox) so the discrepancy sequence measures distance to ONE goal and stays monotone as the body
        approaches. Re-pin (to the smallest referent the cursor is not inside) only when the lock is lost."""
        cc = _centroid_colour(g, ctx.cursor) if ctx.cursor is not None else None
        if cc is None:
            self._reach_goal = None
            return None
        cand = [r for r in refs if not _contains(r.bbox, cc)]
        if not cand:
            self._reach_goal = None
            return None
        if self._reach_goal is not None:
            keep = [r for r in cand if _overlap(r.bbox, self._reach_goal)]
            if keep:
                self._reach_goal = min(keep, key=lambda r: _bbox_area(r.bbox)).bbox
                return self._reach_goal
        self._reach_goal = min(cand, key=lambda r: _bbox_area(r.bbox)).bbox
        return self._reach_goal

    def match_residual(self):
        """The RESIDUAL transform (rotation/recolour still to null) for the closest workspace/reference panel pair in
        the last observed frame -- what the Locksmith operator planner (L2/L3) must reduce to identity. None until a
        matchable panel pair appears. Exposed now; its consumer is the L2 operator-effect learner."""
        if self._last is None:
            return None
        g, refs, ctx = self._last
        return self._rel("MATCH").residual(g, refs, ctx)

    def _resolve_roles(self, g: np.ndarray, refs: List[Referent]):
        """Assign WORKSPACE vs REFERENCE roles by INVARIANCE, not position or size: across recent frames the WORKSPACE is
        the panel region whose content MUTATES (the agent is acting on it), the REFERENCE is a panel of the SAME shape
        whose content is INVARIANT (the target the agent is bringing the workspace to). General principle -- it names no
        game and reads no pixel threshold; it just watches which region the agent changes. Feeds directed MATCH."""
        cur = {}
        for r in refs:
            if r.kind != "panel":
                continue
            b = r.bbox
            sub = g[b[0]:b[2] + 1, b[1]:b[3] + 1]
            cur[b] = sub
            self._region_hash.setdefault(b, []).append(sub.tobytes())
            if len(self._region_hash[b]) > self._role_win:
                self._region_hash[b] = self._region_hash[b][-self._role_win:]
            self._region_sub[b] = sub
        for b in [k for k in self._region_hash if k not in cur]:   # prune regions gone from the frame (level redraw)
            self._region_hash.pop(b, None); self._region_sub.pop(b, None)
        mutated = [b for b, hs in self._region_hash.items() if len(hs) >= 3 and len(set(hs)) > 1]
        invariant = [b for b, hs in self._region_hash.items() if len(hs) >= 3 and len(set(hs)) == 1]
        self._roles = None
        for ws in mutated:                                    # a workspace + an invariant reference of the SAME shape
            for ref in invariant:
                if self._region_sub[ws].shape == self._region_sub[ref].shape:
                    self._roles = (ws, ref)
                    return
        return

    def role_bboxes(self):
        """(workspace_bbox, reference_bbox) if roles were assigned, else None. Telemetry / for the L2 operator learner
        (which watches the WORKSPACE and attributes its changes to the agent's contacts)."""
        return self._roles

    def observe(self, frame, refs: List[Referent], ctx: RelationCtx) -> None:
        g = np.asarray(frame)
        self._shape = (int(g.shape[0]), int(g.shape[1]))
        self._last = (g, list(refs), ctx)
        self._resolve_roles(g, refs)
        if self._roles is not None:
            ws, ref = self._roles
            ctx.match_roles = (self._region_sub[ws], self._region_sub[ref])
        ctx.reach_goal = self._resolve_reach_goal(g, refs, ctx)   # pin the goal so REACH's discrepancy is comparable
        for r in self.relations:
            try:
                d = r.discrepancy(g, refs, ctx)
                t = r.target(g, refs, ctx)
            except Exception:
                d, t = None, None                             # a relation must never crash the policy
            self.hist[r.name].append(None if d is None else float(d))
            self.last_target[r.name] = t
            self.target_hist[r.name].append(t)
        self.n += 1

    def _target_stable(self, name: str) -> bool:
        """Precision gate: a relation is trusted only if its DRIVE-TARGET is COHERENT across the recent window -- a real
        relation has a persistent goal, while a spurious selection (a discrepancy that shrank because unrelated cells
        teleported, e.g. two 'nodes' swapping colour/position) has a target that jumps around. Relations that expose no
        target (measured-only, e.g. MATCH) are not penalised. REACH's goal-lock keeps its target pinned -> stable."""
        import math
        recent = [t for t in self.target_hist[name][-self.min_obs:] if t is not None]
        if len(recent) < 2:
            return True                                        # no target to destabilise (measured-only relation)
        spread = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in recent for b in recent)
        thresh = max(4.0, 0.08 * min(self._shape) if min(self._shape) else 4.0)
        return spread <= thresh

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
        """The relation whose discrepancy is confidently shrinking under play (ranked by net decrease), or None -- the
        relation's own shrinking gap IS the reward signal being tested; a driven relation that keeps closing its
        discrepancy is the hypothesis the environment rewards."""
        best, best_key = None, None
        for name, seq in self.hist.items():
            vals = [v for v in seq if v is not None]
            if len(vals) < self.min_obs:
                continue
            m = self._decreasing(seq)
            if m is None:
                continue
            noninc, rng, netdec = m
            if noninc >= self.mono_thresh and rng >= self.min_range and netdec > 0 and self._target_stable(name):
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

    def selected_delta(self) -> float:
        """The DROP in the selected relation's discrepancy from the previous step to the current (positive = the gap
        closed = good). 0.0 if no relation is selected or too few points. This is the dense reward the effect tier
        reinforces on when a relation is confidently selected (Brick 4b)."""
        sel = self.selected()
        if sel is None:
            return 0.0
        seq = [v for v in self.hist[sel] if v is not None]
        if len(seq) < 2:
            return 0.0
        return float(seq[-2] - seq[-1])
