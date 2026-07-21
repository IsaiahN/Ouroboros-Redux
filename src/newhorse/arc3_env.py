"""
arc3_env.py -- THE MAP §9.6 loop closure against the REAL world (brick 9): a thin session over the
live ARC-AGI-3 online API. One scorecard, one game, ONE session-open reset (the game-open, NOT the
banned in-play reset). Frames are returned at NATIVE full resolution -- never downsampled.

The API key is read from ARC_API_KEY and is NEVER written to disk by this module (env-only, per the
standing security constraint). This module holds NO game knowledge -- it only moves frames and actions
across the wire; all reasoning lives in AgentLoop. (Keeping it thin is the point: never encode the answer.)
"""
from __future__ import annotations
import os, time
from typing import Optional, List, Dict, Any
import numpy as np
import arc_agi
try:
    from arc_agi.base import OperationMode
except Exception:                                    # pragma: no cover - SDK layout drift
    from arc_agi import OperationMode
from arcengine import GameAction, GameState

_ACTIONVAL = {i: getattr(GameAction, "ACTION%d" % i) for i in range(1, 8)}   # 1..7 (6 = click)


def _grid_from_obs(o) -> np.ndarray:
    """The native full-resolution frame as a 2-D int grid (last frame of a stack, if stacked)."""
    f = np.array(getattr(o, "frame", None))
    if f.size == 0:
        return np.zeros((64, 64), dtype=int)
    raw = f[-1] if f.ndim == 3 else f
    return np.asarray(raw)


def _retry(fn, tries=4, base=0.8):
    o = None
    for i in range(tries):
        try:
            o = fn()
        except Exception:
            o = None
        if o is not None:
            return o
        time.sleep(base * (2 ** i))
    return o


class Arc3Session:
    """One online session over ONE game. Interface (also what the offline FakeSession mirrors):
        open()  -> snapshot dict
        step(action_value, data=None) -> snapshot dict
        close() -> final scorecard (or None)
    snapshot = {grid, available:[int], levels_completed:int, state:str, done:bool}."""

    def __init__(self, game_id: str, *, tags: Optional[List[str]] = None, save_recording: bool = True,
                 min_interval: float = 0.13, logger=None):
        key = os.environ.get("ARC_API_KEY", "")
        if not key:
            raise RuntimeError("ARC_API_KEY not set -- the key is env-only, never written to disk")
        self.game_id = game_id
        self._arc = arc_agi.Arcade(operation_mode=OperationMode.ONLINE, arc_api_key=key, logger=logger)
        self.scorecard_id = self._arc.open_scorecard(tags=tags or ["new-horse", "brick9", game_id])
        self.view_url = "https://arcprize.org/scorecards/%s" % self.scorecard_id
        self._env = self._arc.make(game_id, scorecard_id=self.scorecard_id, save_recording=save_recording)
        self._min_interval = float(min_interval)
        self._last = 0.0
        self._obs = None

    def _throttle(self):
        dt = time.time() - self._last
        if dt < self._min_interval:
            time.sleep(self._min_interval - dt)
        self._last = time.time()

    def _snapshot(self) -> Dict[str, Any]:
        o = self._obs
        state = getattr(o, "state", None)
        return dict(grid=_grid_from_obs(o),
                    available=[int(a) for a in (getattr(o, "available_actions", None) or [])],
                    levels_completed=int(getattr(o, "levels_completed", 0) or 0),
                    state=getattr(state, "name", "?"),
                    done=state in (GameState.WIN, GameState.GAME_OVER))

    def open(self) -> Dict[str, Any]:
        self._throttle()
        self._obs = _retry(lambda: self._env.reset(), tries=5, base=1.2)   # the ONE session-open reset
        if self._obs is None:
            raise RuntimeError("online reset returned None after retries (rate limit / server)")
        return self._snapshot()

    def step(self, action_value: int, data: Optional[dict] = None, reasoning: Optional[dict] = None) -> Dict[str, Any]:
        self._throttle()
        ga = _ACTIONVAL[int(action_value)]
        o = _retry(lambda: self._env.step(ga, data=data, reasoning=reasoning), tries=3, base=0.6)
        if o is not None:
            self._obs = o
        return self._snapshot()

    def close(self):
        try:
            return self._arc.close_scorecard(self.scorecard_id)
        except Exception:
            return None
