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

    def both_action_count(self) -> int:
        """Actions under which BOTH bodies have a consistent non-zero shift -- the count of genuinely coupled
        controls. Real two-body control moves both bodies under most actions; a paint/co-existence coincidence does
        not."""
        if (self._nbodies or 0) < 2:
            return 0
        m0, m1 = self.body_map(0), self.body_map(1)
        return sum(1 for a in m0 if a in m1)

    def is_coupled(self, min_both: int = 3) -> bool:
        """Accept as a real TWO-BODY cursor only if: exactly 2 bodies, each mapped, they co-move under >= min_both
        actions, AND a joint quantity is conserved (the mirror/rigid invariant). This rejects paint games whose
        multiple components merely CO-EXIST and drift (no conserved coupling, few co-moving actions)."""
        return (self.ready() and self.n_controllable() == 2
                and self.both_action_count() >= min_both
                and any(self.conserved().values()))

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
    vals, cnts = np.unique(np.concatenate([f.ravel() for f in F]), return_counts=True)
    bg = int(vals[int(np.argmax(cnts))])                 # the background is never the coupled cursor
    best, best_motion = None, -1.0
    for c in sorted(set(int(v) for f in F for v in np.unique(f))):
        if c == bg:
            continue
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


def two_body_drive_action(bodies: List[Tuple[int, int]], ag: "TwoBodyAgency",
                          passable, goal: str = "meet") -> Optional[str]:
    """Drive the two coupled bodies toward the win relation MEET (become one component). Greedy: pick the action
    that most reduces the inter-body Manhattan distance, PREDICTING each body's move via its learned map and
    treating a move into a non-passable cell as BLOCKED (the body stays) -- which is exactly the wall-break that
    lets the mirror invariant be broken (a shared action moves only the un-blocked body). Generic (min inter-body
    distance), never an m0r0 hand-solve. `passable(body_index, dest_cell)->bool`."""
    if len(bodies) < 2:
        return None
    maps = [ag.body_map(0), ag.body_map(1)]
    acts = set(maps[0]) | set(maps[1])
    best, best_d = None, None
    for a in sorted(acts):
        nb = []
        for i, (r, c) in enumerate(bodies):
            d = maps[i].get(a, (0, 0))
            dest = (r + d[0], c + d[1])
            nb.append(dest if passable(i, dest) else (r, c))
        dist = abs(nb[0][0] - nb[1][0]) + abs(nb[0][1] - nb[1][1])
        if best_d is None or dist < best_d:
            best_d, best = dist, a
    return best


def two_body_goal_action(bodies: List[Tuple[int, int]], ag: "TwoBodyAgency", passable, target: Tuple[int, int],
                         which: int = 0) -> Optional[str]:
    """Drive the coupled two-body state so that body `which` approaches a TARGET CELL (not the other body). This is
    the generalisation of two_body_drive_action's MEET (min body-body distance) to an arbitrary goal referent --
    used by the goal-HYPOTHESIS probe when the transferred MEET goal stops yielding reward on a graduated level and
    a NEW actor becomes the candidate objective. Greedy over the learned per-body maps; a blocked move keeps the
    body (mirror-break emerges). `passable(body_index, dest_cell)->bool`."""
    if len(bodies) <= which:
        return None
    maps = [ag.body_map(0), ag.body_map(1)]
    acts = set(maps[0]) | set(maps[1])
    best, best_d = None, None
    for a in sorted(acts):
        nb = []
        for i, (r, c) in enumerate(bodies):
            d = maps[i].get(a, (0, 0))
            dest = (r + d[0], c + d[1])
            nb.append(dest if passable(i, dest) else (r, c))
        dist = abs(nb[which][0] - target[0]) + abs(nb[which][1] - target[1])
        if best_d is None or dist < best_d:
            best_d, best = dist, a
    return best


from .dsl import Context as _Context
from .minting import two_part_mdl as _two_part_mdl

# the atoms already IN Γ (the current kernel). A size-1 mint of any of these is a RE-DERIVATION, not a Region-III
# fill (NOVELTY TEST: φ ∉ atoms(Γ)). New novelty requires a NEW atom type (e.g. a two-body relational predicate)
# or a composition Γ cannot reduce to a single atom.
_KERNEL_ATOM_PREFIXES = ("INTENDED_FREE", "INTENDED_COLOUR==", "colour==", "ACTS_TOWARD", "NEAR", "TOUCH",
                         "SAME_ROW", "SAME_COL")


def coupled_transition_mint(frames: List[np.ndarray], acts: List[str], passable=({5}, {5}), max_size: int = 1):
    """Run the residual-driven MDL minter (the RED BLOCK) on a two-body game's TRANSITION residual: Γ predicts
    each body moves by its learned map; the residual is where a body is BLOCKED (a wall). Returns (Mint, verdict)
    where verdict applies the NOVELTY TEST -- 'RE-DERIVATION' if φ reduces to an existing kernel atom, else
    'NOVEL'. Honest by construction: on m0r0 the per-body dynamics are pure affordance, so it re-derives
    INTENDED_FREE (machinery validated, NOT a Region-III fill)."""
    colour, ag = learn_two_body(frames, acts)
    if colour is None or ag is None or not ag.ready():
        return None, "no-coupling"
    exc = []
    for i in range(1, len(frames)):
        b0 = _bodies_c(frames[i - 1], colour); b1 = _bodies_c(frames[i], colour)
        if len(b0) != 2 or len(b1) != 2:
            continue
        h, w = np.asarray(frames[i - 1]).shape
        for j in range(2):
            vec = ag.body_map(j).get(acts[i])
            if not vec or vec == (0, 0):
                continue
            r, c = b0[j]; ir, ic = r + vec[0], c + vec[1]
            icol = int(np.asarray(frames[i - 1])[ir, ic]) if (0 <= ir < h and 0 <= ic < w) else -1
            exc.append((_Context(focus_rc=b0[j], focus_colour=colour, target_rc=b0[j], action_vec=vec,
                                 intended_free=(icol in passable[j]), intended_colour=(icol if icol >= 0 else None)),
                        b0[j] != b1[j]))
    if len(exc) < 2:
        return None, "no-exceptions"
    m = _two_part_mdl(exc, max_size=max_size)
    if m is None:
        return None, "no-mint"
    names = {a.name for a in m.predicate.atoms}
    novel = not all(any(n.startswith(p) for p in _KERNEL_ATOM_PREFIXES) for n in names)
    return m, ("NOVEL" if novel else "RE-DERIVATION")


def coupled_goal_mint(frames: List[np.ndarray], levels: List[int], colour: Optional[int] = None, max_size: int = 1):
    """Tier-2 GOAL-mint from a two-body game's REWARD residual: abduce the win relation from where the level
    advanced. Context = (focus=body0, target=body1); outcome = did the level advance next step. Returns
    (Mint, verdict). On m0r0 this mints NEAR(body0,body1) -- the two bodies MEET -- purely from reward. HONEST
    NOVELTY: the RELATION (NEAR) is an existing kernel atom → verdict RE-DERIVATION; the novelty is
    REPRESENTATIONAL (NEAR applied to TWO controllable bodies -- a binding the single-focus kernel could not
    express, enabled by the reclaimed two-body perception), NOT a brand-new predicate. m0r0 validates goal
    abduction, it is not a fresh-predicate Region-III fill."""
    if colour is None:
        colour = find_two_body_colour(frames)
    if colour is None:
        return None, "no-two-body-colour"
    exc = []
    for i in range(len(frames) - 1):
        b = _bodies_c(frames[i], colour)
        reward = levels[i + 1] > levels[i]
        if len(b) == 1:
            f = t = b[0]                                    # merged -> the two bodies coincide (distance 0)
        elif len(b) == 2:
            f, t = b[0], b[1]
        else:
            continue
        exc.append((_Context(focus_rc=f, focus_colour=colour, target_rc=t, action_vec=(0, 0)), bool(reward)))
    if sum(1 for _, o in exc if o) == 0:
        return None, "no-reward"
    m = _two_part_mdl(exc, max_size=max_size)
    if m is None:
        return None, "no-mint"
    names = {a.name for a in m.predicate.atoms}
    novel = not all(any(n.startswith(p) for p in _KERNEL_ATOM_PREFIXES) for n in names)
    return m, ("NOVEL" if novel else "RE-DERIVATION")


def _bodies_c(frame, colour, max_body_cells=400):
    m = np.asarray(frame) == colour
    if not m.any():
        return []
    lab, k = ndimage.label(m); out = []
    for i in range(1, k + 1):
        ys, xs = np.where(lab == i)
        if ys.size <= max_body_cells:
            out.append((int(round(ys.mean())), int(round(xs.mean()))))
    return sorted(out, key=lambda p: p[1])


def _two_body_bfs(bodies, ag, passable_cell, stride, goal_fn, max_expand: int = 40000) -> Optional[str]:
    """JOINT-STATE BFS over the coupled two-body state (both body cells). Each action moves EACH body by its
    learned per-action displacement UNLESS its destination cell is non-passable (blocked → the body stays) — so a
    wall that blocks one body while the shared action moves the other (breaking the mirror invariant) emerges
    naturally. Returns the FIRST action of the shortest joint path to a state where `goal_fn(state)` holds, or None.
    `goal_fn((cell0, cell1)) -> bool` in CELL units. `passable_cell(body_index, (row,col)_cell) -> bool`."""
    from collections import deque
    s = max(1, int(stride))
    to_cell = lambda p: (int(round(p[0] / s)), int(round(p[1] / s)))
    maps = [{a: (int(round(v[0] / s)), int(round(v[1] / s))) for a, v in ag.body_map(i).items()} for i in range(2)]
    acts = sorted(set(maps[0]) | set(maps[1]))
    start = (to_cell(bodies[0]), to_cell(bodies[1]))
    if goal_fn(start):
        return None
    seen = {start: None}
    q = deque([start]); expand = 0
    while q and expand < max_expand:
        st = q.popleft(); expand += 1
        c0, c1 = st
        for a in acts:
            d0, d1 = maps[0].get(a, (0, 0)), maps[1].get(a, (0, 0))
            n0 = (c0[0] + d0[0], c0[1] + d0[1]); n1 = (c1[0] + d1[0], c1[1] + d1[1])
            n0 = n0 if passable_cell(0, n0) else c0
            n1 = n1 if passable_cell(1, n1) else c1
            ns = (n0, n1)
            if ns == st or ns in seen:
                continue
            seen[ns] = (st, a)
            if goal_fn(ns):
                cur, first = ns, a
                while seen[cur] is not None:
                    prev, act = seen[cur]; first = act; cur = prev
                return first
            q.append(ns)
    return None


def two_body_search_action(bodies: List[Tuple[int, int]], ag: "TwoBodyAgency", passable_cell,
                           stride: int = 1, max_expand: int = 40000) -> Optional[str]:
    """Joint BFS to MEET: the two bodies become adjacent/overlapping (one component). The m0r0-L1 win relation.
    Fixes the greedy driver's local-minimum stall (separate maze halves needing a channel + mirror-break)."""
    adjacent = lambda st: abs(st[0][0] - st[1][0]) + abs(st[0][1] - st[1][1]) <= 1
    return _two_body_bfs(bodies, ag, passable_cell, stride, adjacent, max_expand)


def two_body_deliver_action(bodies, ag, passable_cell, target0, target1, stride: int = 1,
                            reach0: int = 2, reach1: int = 2, max_expand: int = 60000) -> Optional[str]:
    """Joint BFS to DELIVER: body0 into zone0 AND body1 into zone1 simultaneously (each within `reach` cells of its
    target centroid). The paired two-zone goal for a coupled-body curriculum graduation (e.g. m0r0 L2: route each
    body to its own symmetric zone). The coupling is exactly what makes it a puzzle — a shared action moves both, so
    getting each into a DIFFERENT zone needs the joint search, not two independent drives. Targets in PIXEL coords."""
    s = max(1, int(stride))
    t0 = (int(round(target0[0] / s)), int(round(target0[1] / s)))
    t1 = (int(round(target1[0] / s)), int(round(target1[1] / s)))
    def goal_fn(st):
        c0, c1 = st
        return (abs(c0[0] - t0[0]) + abs(c0[1] - t0[1]) <= reach0 and
                abs(c1[0] - t1[0]) + abs(c1[1] - t1[1]) <= reach1)
    return _two_body_bfs(bodies, ag, passable_cell, stride, goal_fn, max_expand)


def learn_two_body(frames: List[np.ndarray], acts: List[str]) -> Tuple[Optional[int], Optional[TwoBodyAgency]]:
    """Discover the coupled colour and learn both bodies' per-action displacement from a frame/action stream."""
    colour = find_two_body_colour(frames)
    if colour is None:
        return None, None
    ag = TwoBodyAgency(colour)
    for i in range(1, len(frames)):
        ag.observe(frames[i - 1], acts[i], frames[i])
    return colour, ag
