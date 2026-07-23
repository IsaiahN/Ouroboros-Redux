"""
ReduxAgent -- the redux-triality agent AS an official ARC-AGI-3-Agents `Agent` subclass. Drop this file into the
harness clone's `agents/` dir (and import it in agents/__init__.py before the AVAILABLE_AGENTS comprehension, which
auto-registers every Agent subclass), then run:  uv run main.py --agent reduxagent [--game <id>]

It is deliberately thin: all eval-native logic lives in newhorse.redux_arch.harness_adapter.PolicyDriver (unit-
tested in the redux-triality suite). The `Agent` base import is GUARDED so this module still imports in our repo /
tests where the official harness is not on the path.
"""
from __future__ import annotations

try:                                    # the official harness base (present only inside the clone)
    from agents.agent import Agent
    _HAVE_AGENT = True
except Exception:                       # our repo / unit tests: no official harness on path
    Agent = object                      # type: ignore
    _HAVE_AGENT = False

from newhorse.redux_arch.harness_adapter import PolicyDriver
from newhorse.redux_arch.policy import BLACKBOARD


class ReduxAgent(Agent):               # type: ignore[misc]
    """One routed, curriculum-aware ReduxPolicy per game, behind the harness's per-step contract."""

    MAX_ACTIONS: int = 80

    def __init__(self, *args, **kwargs) -> None:
        if not _HAVE_AGENT:
            raise RuntimeError("official Agent base not importable -- run inside the ARC-AGI-3-Agents clone")
        super().__init__(*args, **kwargs)
        # shared blackboard -> cross-game transfer when the harness swarm runs many ReduxAgents
        self.driver = PolicyDriver(game_id=self.game_id, blackboard=BLACKBOARD, warmup_cap=8)

    def is_done(self, frames, latest_frame) -> bool:
        return self.driver.is_done(latest_frame)

    def choose_action(self, frames, latest_frame):
        return self.driver.choose(latest_frame)
