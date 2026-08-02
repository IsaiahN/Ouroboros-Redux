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


def _mod(name: str):
    if _SRC not in sys.path:
        sys.path.insert(0, _SRC)
    import importlib
    return importlib.import_module(name)


class LiveArcGround:
    """The live gate. `palette` is accepted for interface-parity with SyntheticGround, but the live
    ground needs none -- the environment supplies frames at native resolution.

    IMPORTANT (reconciliation 2026-08-02): the play path is the kernel's FAMILY-DETECTING ReduxPolicy
    (`redux_arch.live_goal_run.run_policy_live` / `redux_arch.swarm.run_swarm`), which routes click /
    two-body / directional games itself and CAN act on click-only games (vc33, ft09, lp85, ...). The
    earlier baseline mistakenly used the minimal mover-only `live_run.run_online_game`, which drops
    action 6 (click) and so forfeited every click game at step 0. That was a wiring error in this
    adapter, NOT a capability regression in the kernel."""

    def __init__(self, palette=None):
        self.palette = palette

    def has_key(self) -> bool:
        return bool(os.environ.get("ARC_API_KEY"))

    def play(self, game_id: str, *, max_actions: int = 120, wall_cap_s: float = 120.0,
             tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Play one live game through the family-detecting ReduxPolicy (handles click). Returns the
        kernel's rich result dict (levels_completed, family, view_url, tether_stage, probe, ...)."""
        if not self.has_key():
            raise RuntimeError("ARC_API_KEY not in env -- export it (env-only) before a live run.")
        return _mod("newhorse.redux_arch.live_goal_run").run_policy_live(
            game_id, max_actions=max_actions, wall_cap_s=wall_cap_s, tags=tags or ["nexus"])

    def play_set(self, game_ids: List[str], *, max_actions: int = 120, wall_cap_s: float = 120.0,
                 max_workers: int = 8, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Play a roster concurrently under ONE scorecard via the kernel's swarm (family-detecting,
        shared rate limiter + blackboard). Returns {view_url, results{game->dict}, families}."""
        if not self.has_key():
            raise RuntimeError("ARC_API_KEY not in env -- export it (env-only) before a live run.")
        return _mod("newhorse.redux_arch.swarm").run_swarm(
            game_ids, max_actions=max_actions, wall_cap_s=wall_cap_s, max_workers=max_workers,
            tags=tags or ["nexus"])

    def run_offline(self, session, *, max_actions: int = 50, wall_cap_s: float = 30.0) -> Dict[str, Any]:
        """Drive the kernel's brick-9 loop against a provided session (for tests: a FakeSession). No key."""
        return _mod("newhorse.live_run").run_live(session, max_actions=max_actions, wall_cap_s=wall_cap_s)
