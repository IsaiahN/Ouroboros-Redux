"""
harness_adapter.py -- redux-triality: bridge ReduxPolicy to the OFFICIAL ARC-AGI-3 Agent contract
(arcprize/ARC-AGI-3-Agents). The harness calls `choose_action(frames, latest_frame) -> GameAction` and
`is_done(frames, latest) -> bool` per step, and runs a SWARM across games. This module holds the PURE, testable
conversion (FrameData ⇄ our grid/label space); the actual `Agent` subclass (newhorse.harness.redux_agent) is a thin
shell that delegates to `PolicyDriver` so the eval-native logic is unit-tested in OUR suite, not the throwaway clone.
"""
from __future__ import annotations
from typing import Optional, Tuple
import numpy as np
from arcengine import GameAction, GameState
from .policy import ReduxPolicy, Blackboard


def grid_from_framedata(fd) -> np.ndarray:
    """The native full-resolution grid = last frame of the FrameData stack (`fd.frame` is a list of 2-D lists)."""
    frame = getattr(fd, "frame", None)
    if not frame:
        return np.zeros((64, 64), dtype=int)
    raw = frame[-1] if isinstance(frame, (list, tuple)) else frame
    arr = np.asarray(raw)
    return arr if arr.ndim == 2 else np.zeros((64, 64), dtype=int)


def available_from(fd) -> list:
    """available_actions as plain ints (they arrive as GameAction enums OR ints depending on SDK layer)."""
    av = getattr(fd, "available_actions", None) or []
    return [int(getattr(a, "value", a)) for a in av]


def state_name(fd) -> str:
    """The game state as a bare NAME string ('WIN'|'GAME_OVER'|'NOT_FINISHED') -- what ReduxPolicy.observe expects
    for death detection (it compares `str(state) == 'GAME_OVER'`, and GameState.GAME_OVER stringifies with a prefix)."""
    st = getattr(fd, "state", None)
    return getattr(st, "name", str(st))


def to_game_action(label: str, data: Optional[dict]) -> GameAction:
    """Map our ('A<n>', data) to a GameAction; ACTION6 (click) carries data={'x':col,'y':row} via set_data."""
    v = int(label[1:])
    ga = getattr(GameAction, "ACTION%d" % v)
    if v == 6 and data:
        ga.set_data({"x": int(data["x"]), "y": int(data["y"])})
    return ga


class PolicyDriver:
    """Wraps a ReduxPolicy behind the harness's per-step contract. Stateful across calls (the policy accumulates
    frames/acts internally); `choose(latest_frame)` observes then returns a ready-to-submit GameAction."""

    def __init__(self, game_id: str = "", blackboard: Optional[Blackboard] = None, warmup_cap: int = 8,
                 retry_cap: int = 6):
        self.policy = ReduxPolicy(game_id=game_id, blackboard=blackboard, warmup_cap=warmup_cap)
        self.retry_cap = int(retry_cap)
        self.retries = 0

    def is_done(self, latest_frame) -> bool:
        """WIN ends the game. GAME_OVER ends it ONLY once the death-retry budget is spent -- while retries remain the
        agent is NOT done: choose() will emit RESET to restart the level (the don't-die organ, beat H) so a single
        death does not terminate the episode in the official-harness loop the way it would if is_done were True here."""
        st = getattr(latest_frame, "state", None)
        if st == GameState.WIN:
            return True
        if st == GameState.GAME_OVER:
            return self.retries >= self.retry_cap
        return False

    def choose(self, latest_frame) -> GameAction:
        grid = grid_from_framedata(latest_frame)
        avail = available_from(latest_frame)
        level = int(getattr(latest_frame, "levels_completed", 0) or 0)
        state = state_name(latest_frame)
        self.policy.observe(grid, avail, level, state=state)          # state -> death recorded on GAME_OVER
        if state == "GAME_OVER" and self.retries < self.retry_cap:    # legitimate post-death RESET, then retry
            self.retries += 1
            self.policy.note_reset()
            return GameAction.RESET
        label, data = self.policy.choose()
        return to_game_action(label, data)

    @property
    def family(self) -> str:
        return self.policy.family
