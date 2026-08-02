"""nexus.ground.live_arc -- the REAL ground: the ARC-AGI-3 live public-set API.

This is not a stub. It delegates to the kernel's OWN live harness (`src/newhorse/live_run.py`),
which already opens a real Arc3Session from ARC_API_KEY (env-only, never written to disk), plays a
game through the egocentric AgentLoop, and returns `levels_completed` -- "the only real metric"
(paper §16.7). Nexus does not reimplement an ARC client; the kernel is the egocentric half and it
already knows how to play.

Two entry points:
  * `play(game_id)`      -- online, needs ARC_API_KEY + network. Returns the kernel's result dict.
  * `run_offline(session)` -- drives the same loop against any session object (a FakeSession),
                              so the wiring is testable with no key and no network.

Status: the live run is the validation step done next, with the key in-env. What this branch ships
is the runnable PATH (and an offline-tested reach into the kernel loop), not a claimed live score --
a firing is a receipt, not a claim.
"""
from __future__ import annotations
import os, sys
from typing import List, Optional, Dict, Any

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SRC = os.path.join(_REPO, "src")


def _live_run_module():
    if _SRC not in sys.path:
        sys.path.insert(0, _SRC)
    from newhorse import live_run          # kernel's real harness (relative imports resolve as a package)
    return live_run


class LiveArcGround:
    """The live gate. `palette` is accepted for interface-parity with SyntheticGround, but the live
    ground needs none -- the environment supplies frames at native resolution."""

    def __init__(self, palette=None):
        self.palette = palette

    def has_key(self) -> bool:
        return bool(os.environ.get("ARC_API_KEY"))

    def play(self, game_id: str, *, max_actions: int = 400, wall_cap_s: float = 90.0,
             tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Play one live public-set game. Requires ARC_API_KEY in env and network. Returns the
        kernel's result dict incl. `levels_completed` and `view_url` (the scorecard)."""
        if not self.has_key():
            raise RuntimeError("ARC_API_KEY not in env -- export it (env-only) before a live run.")
        return _live_run_module().run_online_game(
            game_id, max_actions=max_actions, wall_cap_s=wall_cap_s, tags=tags or ["nexus"])

    def run_offline(self, session, *, max_actions: int = 50, wall_cap_s: float = 30.0) -> Dict[str, Any]:
        """Drive the kernel loop against a provided session object (for tests: a FakeSession). No key."""
        return _live_run_module().run_live(session, max_actions=max_actions, wall_cap_s=wall_cap_s)
