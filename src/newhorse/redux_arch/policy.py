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
from .replay import learn_basis
from .goal import salient_targets, approachable_component_centroid
from .planner import plan_action, bfs_path_action
from .explore import CuriosityExplorer
from .coupled import learn_two_body, two_body_search_action, two_body_drive_action
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


def _prefix(game_id: str) -> str:
    return (game_id or "").split("-")[0]


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
    def observe(self, grid, available: List[int]) -> None:
        """Record the freshly observed frame (result of the previously emitted action) + its available actions."""
        self.frames.append(np.asarray(grid))
        self.acts.append(self._pending if len(self.frames) > 1 else "RESET")
        self._avail = [int(a) for a in available]

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
        # minimal warmup: observe each directional action ~once (THINKING is free; ACTIONS are squared-costly)
        warmup_needed = 0 if not dirs else min(self.warmup_cap, max(len(dirs), 2))
        if self.n_emitted < warmup_needed:
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
        """Classify the game family from the warmup stream, learn the organ's params, and post the mechanism to the
        blackboard. Two-body is tried first (its coupled-colour test is specific); then single-body drivable;
        else undrivable."""
        colour, ag = learn_two_body(self.frames, self.acts)
        if ag is not None and ag.ready() and ag.n_controllable() >= 2:
            self.family = TWO_BODY
            self.tb_colour = colour
            self.ag = ag
            self._learn_tb_passable(colour)
            self.stride = max((max(abs(v[0]), abs(v[1])) for m in (ag.body_map(0), ag.body_map(1)) for v in m.values()),
                              default=1) or 1
            self.bb.post(_prefix(self.game_id), family=TWO_BODY, colour=colour)
            return
        cursor, vecs = learn_basis(self.frames, self.acts)
        if cursor is not None and vecs:
            self.family = DIRECTIONAL
            self.cursor = cursor
            self.vecs = vecs
            self.passable = _learn_passable(self.frames, cursor)
            self.stride = max((max(abs(v[0]), abs(v[1])) for v in vecs.values()), default=1) or 1
            cands = salient_targets(self.frames, avatar_colour=cursor, exclude=set(self.passable), top=3)
            self.target_colour = cands[0] if cands else None
            self.bb.post(_prefix(self.game_id), family=DIRECTIONAL, cursor=cursor)
            return
        self.family = UNDRIVABLE
        self.bb.post(_prefix(self.game_id), family=UNDRIVABLE)

    def _learn_tb_passable(self, colour: int) -> None:
        self.tb_pass = [set(), set()]
        for i in range(1, len(self.frames)):
            b0, b1 = _two_bodies(self.frames[i - 1], colour), _two_bodies(self.frames[i], colour)
            if len(b0) == 2 and len(b1) == 2:
                for j in range(2):
                    if b0[j] != b1[j]:
                        r, c = b1[j]
                        h, w = self.frames[i - 1].shape
                        if 0 <= r < h and 0 <= c < w:
                            self.tb_pass[j].add(int(self.frames[i - 1][r, c]))

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
        if len(bodies) < 2:
            return self._cycle(labels), None                        # merged/lost -> nudge
        def passcell(i, cell, _g=grid, _h=h, _w=w, _s=self.stride, _p=self.tb_pass):
            r, c = cell[0] * _s, cell[1] * _s
            return 0 <= r < _h and 0 <= c < _w and (not _p[i] or int(_g[r, c]) in _p[i])
        def passpx(i, dest, _g=grid, _h=h, _w=w, _p=self.tb_pass):
            r, c = dest
            return 0 <= r < _h and 0 <= c < _w and (not _p[i] or int(_g[r, c]) in _p[i])
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
