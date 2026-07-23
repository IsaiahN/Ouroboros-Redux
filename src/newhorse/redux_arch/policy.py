"""
policy.py -- redux-triality: the CONTROL-INVERSION adapter. The ARC-AGI-3 eval harness owns the loop
(`Agent.main`: `while not is_done and action_counter <= MAX_ACTIONS: choose_action(frames, latest)`) and, when no
single game is pinned, runs a SWARM -- one agent instance per game on its own thread, all under one scorecard. Our
reclaimed organs were loop-owned (run_*_live drove their own for/while); the harness cannot score that shape.

`ReduxPolicy` re-expresses the organs as a STATEFUL per-step policy: warmup -> route (classify game family) ->
dispatch the matching organ, all as internal phase state advanced one action per call. Two payoffs, both forced by
the harness:
  * swarm/eval-native by construction (drop-in behind a 10-line Agent subclass), and
  * precise per-action spend -- which is the SCORE. RHAE = (human_actions / ai_actions)^2, and THINKING is free
    (only state-changing actions count). So we burn the MINIMUM warmup that identifies the family, then act to
    the organ. A 40-action warmup would be near-zero RHAE even on a win.

The `Blackboard` is the cross-game transfer the official swarm lacks (it shares no state between concurrent
agents): a family/organ prior keyed by game-id PREFIX, so a MECHANISM recognised on one game seeds the router on a
structurally-similar one -- reclaim mechanisms, not answers, and let them compound across the set.
"""
from __future__ import annotations
from typing import List, Optional, Tuple, Dict, Any
import threading
import numpy as np
from scipy import ndimage as _ndi
from .replay import learn_basis, learn_basis_trailaware
from .goal import salient_targets, approachable_component_centroid
from .planner import plan_action, bfs_path_action
from .explore import CuriosityExplorer
from .coupled import (learn_two_body, two_body_search_action, two_body_drive_action, two_body_goal_action,
                      two_body_deliver_action)
from .click import click_targets, grid_sweep, ClickProber
from .bridge import _px_centroid
from .dsl import Predicate, make_atom
from .live_goal_run import _learn_passable, _two_bodies

ACTS_TOWARD = Predicate(frozenset({make_atom("ACTS_TOWARD")}))

# game families the router dispatches to
PENDING, CLICK, TWO_BODY, DIRECTIONAL, UNDRIVABLE = "pending", "click", "two_body", "directional", "undrivable"


class Blackboard:
    """Thread-safe cross-game memory for the swarm. Keyed by game-id PREFIX (family, not instance). Stores learned
    MECHANISMS (which organ / which coupled colour), never per-game answers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._d: Dict[str, Dict[str, Any]] = {}

    def post(self, key: str, **facts: Any) -> None:
        with self._lock:
            self._d.setdefault(key, {}).update(facts)

    def get(self, key: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._d.get(key, {}))


BLACKBOARD = Blackboard()


class GoalProbe:
    """Abductive GOAL-HYPOTHESIS search for a two-body game after a KEEP graduation. The motion model transferred,
    but the transferred goal (MEET) stopped yielding reward on the new level -- so the OBJECTIVE changed even though
    the coupling didn't. With no reward yet to abduce from (cold start: no L2 recording), we ENUMERATE candidate
    goals -- MEET first (cheap: maybe it still works), then NEAR(body, X) for each NEW actor colour X the level
    added -- and probe each for a budget of actions, rotating when it doesn't pay off. Live reward arbitrates; once
    a hypothesis pays, coupled_goal_mint can CONSOLIDATE it. Reclaim the mechanism (abduce-then-verify), never the
    answer."""

    def __init__(self, referent_colours, meet_first: bool = True, budget: int = 22):
        self.hypotheses = [("meet", None)] if meet_first else []
        if referent_colours:
            self.hypotheses.append(("deliver", None))          # paired two-zone goal (route each body to its zone)
        self.hypotheses += [("near", int(c)) for c in referent_colours]
        if not self.hypotheses:
            self.hypotheses = [("meet", None)]
        self.idx = 0
        self.steps = 0
        self.budget = int(budget)
        self.locked = False

    def current(self):
        return self.hypotheses[self.idx]

    def tick(self) -> None:
        if self.locked:
            return
        self.steps += 1
        if self.steps >= self.budget:
            self.rotate()

    def rotate(self) -> None:
        self.idx = (self.idx + 1) % len(self.hypotheses)
        self.steps = 0

    def lock(self) -> None:
        """A hypothesis paid off (reward). Stop rotating -- this is the level's objective."""
        self.locked = True


def _prefix(game_id: str) -> str:
    return (game_id or "").split("-")[0]


def _md(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _largest_zones(grid, colours, exclude: Optional[int] = None, k: int = 2):
    """The k largest components among `colours` (the level's new actors), each as (size, centroid_px, radius_px,
    colour). Used to resolve a paired DELIVER goal to the two big symmetric zones a curriculum level added."""
    g = np.asarray(grid)
    out = []
    for col in colours:
        if exclude is not None and int(col) == int(exclude):
            continue
        m = g == int(col)
        if not m.any():
            continue
        lab, n = _ndi.label(m)
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            cen = (int(round(ys.mean())), int(round(xs.mean())))
            rad = max(int(ys.max() - ys.min()), int(xs.max() - xs.min())) / 2.0
            out.append((int(ys.size), cen, rad, int(col)))
    out.sort(key=lambda t: t[0], reverse=True)
    return out[:k]


def _assign_zones(bodies, zones, stride: int):
    """Assign the two bodies to the two zones minimising total distance; return ((c0,reach0),(c1,reach1)) for
    body0→zone, body1→zone, reach in CELLS (from the zone radius)."""
    _, cA, rA, _ = zones[0]
    _, cB, rB, _ = zones[1]
    reachA = max(1, int(rA / max(1, stride)))
    reachB = max(1, int(rB / max(1, stride)))
    if _md(bodies[0], cB) + _md(bodies[1], cA) < _md(bodies[0], cA) + _md(bodies[1], cB):
        return (cB, reachB), (cA, reachA)
    return (cA, reachA), (cB, reachB)


def _nearest_colour_centroid(grid, colour: int, ref_cell, exclude: Optional[int] = None):
    """Centroid of the colour-`colour` component nearest `ref_cell` (the candidate goal referent to drive toward).
    None if the colour is absent. `exclude` skips the bodies' own colour so a body never targets itself."""
    if exclude is not None and int(colour) == int(exclude):
        return None
    m = np.asarray(grid) == int(colour)
    if not m.any():
        return None
    lab, k = _ndi.label(m)
    best, best_d = None, None
    for i in range(1, k + 1):
        ys, xs = np.where(lab == i)
        c = (int(round(ys.mean())), int(round(xs.mean())))
        d = abs(c[0] - ref_cell[0]) + abs(c[1] - ref_cell[1])
        if best_d is None or d < best_d:
            best_d, best = d, c
    return best


def level_delta(prev_frame, new_frame, prev_avail, new_avail) -> Dict[str, Any]:
    """The curriculum diff at a level boundary: what's NEW in the graduated environment. A level transition is a
    distribution shift (the board redraws + mechanics are added); the residual/mint architecture wants to know what
    changed so it can KEEP what transferred and mint only against the surprise. Pure + testable."""
    pv = {int(x) for x in np.unique(np.asarray(prev_frame))}
    nv = {int(x) for x in np.unique(np.asarray(new_frame))}
    pa = {int(a) for a in prev_avail}
    na = {int(a) for a in new_avail}
    return dict(new_colours=sorted(nv - pv), gone_colours=sorted(pv - nv),
                new_actions=sorted(na - pa), gone_actions=sorted(pa - na))


class ReduxPolicy:
    """Stateful per-step brain fitting the ARC-AGI-3 Agent contract. Feed each observed frame via observe(grid,
    available); call choose() for the next (label, data). label is 'A<n>'; data is {'x','y'} for A6 (click) else None."""

    def __init__(self, game_id: str = "", blackboard: Optional[Blackboard] = None, warmup_cap: int = 8) -> None:
        self.game_id = game_id
        self.bb = blackboard if blackboard is not None else BLACKBOARD
        self.warmup_cap = int(warmup_cap)
        self.frames: List[np.ndarray] = []
        self.acts: List[str] = []
        self._pending = "RESET"                 # the action that will have produced the NEXT observed frame
        self.n_emitted = 0
        self.family = PENDING
        self._avail: List[int] = []
        # curriculum / level-boundary state
        self.level = 0
        self._lvl0 = 0                          # index in self.frames where the CURRENT level's stream begins
        self._warm_start = 0                    # n_emitted at the current level's start (per-level warmup gate)
        self.prior: Optional[Dict[str, Any]] = None     # the frozen transferred model at the last boundary
        self.level_model: Optional[Dict[str, Any]] = None   # current hypothesis of THIS level's mechanics
        self.level_deltas: List[Dict[str, Any]] = []
        self._probe: Optional[GoalProbe] = None         # active goal-hypothesis search (two-body, post-KEEP)
        # learned organ params
        self.cursor: Optional[int] = None
        self.vecs: Dict[str, Tuple[int, int]] = {}
        self.passable: set = set()
        self.target_colour: Optional[int] = None
        self.stride = 1
        self.tb_colour: Optional[int] = None
        self.ag = None
        self.tb_pass: List[set] = [set(), set()]
        self.prober: Optional[ClickProber] = None
        self.explorer: Optional[CuriosityExplorer] = None

    # ---- observation -------------------------------------------------------------------------------------------
    def observe(self, grid, available: List[int], levels_completed: int = 0) -> None:
        """Record the freshly observed frame (result of the previously emitted action) + its available actions. If
        the level advanced, run the curriculum re-derivation (freeze prior, diff, keep/re-parameterize/re-derive)."""
        old_avail = list(self._avail)
        self.frames.append(np.asarray(grid))
        self.acts.append(self._pending if len(self.frames) > 1 else "RESET")
        self._avail = [int(a) for a in available]
        if int(levels_completed) > self.level:
            if self._probe is not None and not self._probe.locked:
                self._probe.lock()                          # the active hypothesis paid off -> it IS the objective
            self._on_level_change(int(levels_completed), old_avail)
        self.level = int(levels_completed)

    def _labels(self, avail: List[int]) -> List[str]:
        return ["A%d" % v for v in avail]

    def _cycle(self, labels: List[str]) -> str:
        return labels[self.n_emitted % len(labels)] if labels else "A5"

    # ---- the per-step decision (control-inversion core) --------------------------------------------------------
    def choose(self) -> Tuple[str, Optional[dict]]:
        lbl, data = self._decide()
        self._pending = lbl
        self.n_emitted += 1
        return lbl, data

    def _decide(self) -> Tuple[str, Optional[dict]]:
        avail = self._avail
        dirs = [v for v in avail if 1 <= v <= 5]
        labels = self._labels(avail)
        # action-set routing knowable immediately: click-only games have NO directional actions
        if self.family == PENDING and not dirs and 6 in avail:
            self.family = CLICK
            self.bb.post(_prefix(self.game_id), family=CLICK)
        if self.family == CLICK:
            return self._act_click()
        # minimal warmup: observe each directional action ~once (THINKING is free; ACTIONS are squared-costly).
        # Counted PER LEVEL (self._warm_start), so a re-derivation on a graduated level re-warms cleanly.
        warmup_needed = 0 if not dirs else min(self.warmup_cap, max(len(dirs), 2))
        if (self.n_emitted - self._warm_start) < warmup_needed:
            return self._cycle(labels), None
        if self.family == PENDING:
            self._route(avail, dirs)
        if self.family == TWO_BODY:
            return self._act_two_body(labels)
        if self.family == DIRECTIONAL:
            return self._act_directional(labels)
        return self._act_fallback(labels)

    # ---- routing -----------------------------------------------------------------------------------------------
    def _route(self, avail: List[int], dirs: List[int]) -> None:
        """Classify the game family from the CURRENT LEVEL's warmup stream, learn the organ's params, and post the
        mechanism to the blackboard. Windowed to self._lvl0 so a re-derivation on a graduated level learns from the
        new level's frames only (not the previous level's, which would corrupt the basis). Two-body is tried first
        (its coupled-colour test is specific); then single-body drivable; else undrivable."""
        fw, aw = self.frames[self._lvl0:], self.acts[self._lvl0:]
        colour, ag = learn_two_body(fw, aw)
        if ag is not None and ag.ready() and ag.n_controllable() >= 2:
            self.family = TWO_BODY
            self.tb_colour = colour
            self.ag = ag
            self._learn_tb_passable(colour)
            self.stride = max((max(abs(v[0]), abs(v[1])) for m in (ag.body_map(0), ag.body_map(1)) for v in m.values()),
                              default=1) or 1
            self.bb.post(_prefix(self.game_id), family=TWO_BODY, colour=colour)
            return
        cursor, vecs = learn_basis(fw, aw)
        if not (cursor is not None and vecs):             # trail-drawing / multi-mover games defeat the footprint
            cursor, vecs = learn_basis_trailaware(fw, aw)  # detector -> fall back to the constant-size translator
        if cursor is not None and vecs:
            self.family = DIRECTIONAL
            self.cursor = cursor
            self.vecs = vecs
            self.passable = _learn_passable(fw, cursor)
            self.stride = max((max(abs(v[0]), abs(v[1])) for v in vecs.values()), default=1) or 1
            cands = salient_targets(fw, avatar_colour=cursor, exclude=set(self.passable), top=3)
            self.target_colour = cands[0] if cands else None
            self.bb.post(_prefix(self.game_id), family=DIRECTIONAL, cursor=cursor)
            return
        self.family = UNDRIVABLE
        self.bb.post(_prefix(self.game_id), family=UNDRIVABLE)

    def _learn_tb_passable(self, colour: int) -> None:
        self.tb_pass = [set(), set()]
        fw = self.frames[self._lvl0:]
        for i in range(1, len(fw)):
            b0, b1 = _two_bodies(fw[i - 1], colour), _two_bodies(fw[i], colour)
            if len(b0) == 2 and len(b1) == 2:
                for j in range(2):
                    if b0[j] != b1[j]:
                        r, c = b1[j]
                        h, w = fw[i - 1].shape
                        if 0 <= r < h and 0 <= c < w:
                            self.tb_pass[j].add(int(fw[i - 1][r, c]))

    # ---- curriculum: level-boundary re-derivation --------------------------------------------------------------
    def _on_level_change(self, new_level: int, old_avail: List[int]) -> None:
        """A level graduated. Freeze the transferred model as PRIOR, DIFF old-vs-new, and decide KEEP (organ's
        referent survives → transfer wholesale, the organ reads the live grid), RE-PARAMETERIZE (rebuild the
        cheap per-level bits, e.g. click candidates), or RE-DERIVE (referent gone → the mechanic changed → re-warm
        + re-route on the new level, keeping the prior). This is graduated learning: additive over a transferred
        base, not from scratch. THINKING is free, so diffing every boundary is pure RHAE upside."""
        prev = self.frames[-2] if len(self.frames) >= 2 else self.frames[-1]
        cur = self.frames[-1]
        delta = level_delta(prev, cur, old_avail, self._avail)
        self.prior = dict(family=self.family, cursor=self.cursor, vecs=dict(self.vecs),
                          passable=set(self.passable), tb_colour=self.tb_colour,
                          target_colour=self.target_colour, from_level=self.level)
        survives = self._referent_survives(cur)
        self._lvl0 = len(self.frames) - 1                        # the redraw frame starts the new level's stream
        decision = "keep" if survives else "rederive"
        self.level_model = dict(level=new_level, family_before=self.family, decision=decision,
                                new_colours=delta["new_colours"], gone_colours=delta["gone_colours"],
                                new_actions=delta["new_actions"], gone_actions=delta["gone_actions"])
        self.level_deltas.append(self.level_model)
        self.bb.post(_prefix(self.game_id), graduated_to=new_level, last_delta=self.level_model)
        if survives:
            self._reparameterize(cur)
            # two-body KEEP: the coupling transferred but the OBJECTIVE may have graduated -> probe the new actors
            if self.family == TWO_BODY:
                self._probe = GoalProbe(referent_colours=delta["new_colours"])
        else:
            self._rederive()

    def _referent_survives(self, cur) -> bool:
        """Does the transferred organ's key referent still exist on the graduated level? (The cheap KEEP test.)"""
        if self.family == TWO_BODY and self.tb_colour is not None:
            return len(_two_bodies(cur, self.tb_colour)) >= 2
        if self.family == DIRECTIONAL and self.cursor is not None:
            return bool(np.any(np.asarray(cur) == self.cursor))
        if self.family == CLICK:
            return True
        return False

    def _reparameterize(self, cur) -> None:
        """Referent transferred: keep the family + motion/coupling model (the organ reads the live grid each step);
        only rebuild the cheap per-level bits."""
        if self.family == CLICK:
            self.prober = ClickProber(click_targets(cur), grid_sweep(cur, n=8))
        self.explorer = None                                     # coverage novelty is per-layout

    def _rederive(self) -> None:
        """Referent gone → a mechanic changed. Re-warm + re-route on the new level; the prior is retained (transfer)
        but the organ caches are cleared so the router relearns against the graduated environment."""
        self.family = PENDING
        self._warm_start = self.n_emitted
        self.cursor = None; self.vecs = {}; self.passable = set(); self.target_colour = None
        self.tb_colour = None; self.ag = None; self.tb_pass = [set(), set()]
        self.prober = None; self.explorer = None

    # ---- organ dispatch ----------------------------------------------------------------------------------------
    def _act_click(self) -> Tuple[str, Optional[dict]]:
        grid = self.frames[-1]
        if self.prober is None:
            self.prober = ClickProber(click_targets(grid), grid_sweep(grid, n=8))
        elif len(self.frames) >= 2:
            self.prober.observe(self.frames[-2], self.frames[-1])   # credit the previous click
            self.prober.refresh(click_targets(grid))
        tgt = self.prober.choose()
        if tgt is None:
            return "A6", {"x": 0, "y": 0}
        r, c = tgt
        return "A6", {"x": int(c), "y": int(r)}

    def _act_two_body(self, labels: List[str]) -> Tuple[str, Optional[dict]]:
        grid = self.frames[-1]; h, w = grid.shape
        bodies = _two_bodies(grid, self.tb_colour)
        def passpx(i, dest, _g=grid, _h=h, _w=w, _p=self.tb_pass):
            r, c = dest
            return 0 <= r < _h and 0 <= c < _w and (not _p[i] or int(_g[r, c]) in _p[i])
        def passcell(i, cell, _g=grid, _h=h, _w=w, _s=self.stride, _p=self.tb_pass):
            r, c = cell[0] * _s, cell[1] * _s
            return 0 <= r < _h and 0 <= c < _w and (not _p[i] or int(_g[r, c]) in _p[i])
        # GOAL-HYPOTHESIS probe (post-KEEP graduation): drive toward the current hypothesis referent, rotating
        if self._probe is not None:
            kind, colour = self._probe.current()
            self._probe.tick()
            new_actors = (self.level_model or {}).get("new_colours", []) if self.level_model else []
            if kind == "deliver" and len(bodies) >= 2:
                zones = _largest_zones(grid, new_actors, exclude=self.tb_colour, k=2)
                if len(zones) >= 2:
                    (c0, r0), (c1, r1) = _assign_zones(bodies, zones, self.stride)
                    lbl = (two_body_deliver_action(bodies, self.ag, passcell, c0, c1, self.stride,
                                                   reach0=r0, reach1=r1)
                           or two_body_goal_action(bodies, self.ag, passpx, c0, which=0)
                           or self._cycle(labels))
                    return lbl, None
            elif kind == "near" and colour is not None and len(bodies) >= 2:
                tgt = _nearest_colour_centroid(grid, colour, bodies[0], exclude=self.tb_colour)
                if tgt is not None:
                    lbl = two_body_goal_action(bodies, self.ag, passpx, tgt, which=0) or self._cycle(labels)
                    return lbl, None
            # kind == "meet" (or unresolved) -> fall through to the MEET driver below
        if len(bodies) < 2:
            return self._cycle(labels), None                        # merged/lost -> nudge
        lbl = (two_body_search_action(bodies, self.ag, passcell, self.stride)
               or two_body_drive_action(bodies, self.ag, passpx)
               or self._cycle(labels))
        return lbl, None

    def _act_directional(self, labels: List[str]) -> Tuple[str, Optional[dict]]:
        grid = self.frames[-1]; h, w = grid.shape
        cur = _px_centroid(grid, self.cursor)
        if cur is None:
            return self._cycle(labels), None
        def passable_px(dest, _g=grid, _h=h, _w=w, _p=self.passable):
            r, c = dest
            return 0 <= r < _h and 0 <= c < _w and int(_g[r, c]) in _p
        avatar = (int(round(cur[0])), int(round(cur[1])))
        if self.target_colour is not None:
            tgt = approachable_component_centroid(grid, self.target_colour, self.passable)
            if tgt is not None:
                target = (int(round(tgt[0])), int(round(tgt[1])))
                lbl = (bfs_path_action(grid, avatar, target, self.vecs, self.passable, self.stride)
                       or plan_action(avatar, target, self.vecs, ACTS_TOWARD, passable_px))
                if lbl:
                    return lbl, None
        return self._explore(avatar, passable_px, labels), None     # no target / boxed -> curiosity

    def _explore(self, avatar, passable_px, labels: List[str]) -> str:
        if self.explorer is None:
            self.explorer = CuriosityExplorer()
        pick = self.explorer.choose(avatar, self.vecs, passable_px, self.stride)
        if pick is None:
            return self._cycle(labels)
        lbl, cell = pick
        self.explorer.visit(lbl, cell)
        return lbl

    def _act_fallback(self, labels: List[str]) -> Tuple[str, Optional[dict]]:
        return self._cycle(labels), None
