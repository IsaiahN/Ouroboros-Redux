"""nexus.reset_policy -- when does a LIFETIME end (and a new generation begin)?

The reset boundary is natural to the game, not a magic number (Isaiah, 2026-08-02):
  * GAME_OVER  -> death IS the reset. Natural, immediate.
  * WIN        -> stop the whole run; solved.
  * STALL      -> an infinite game that stops REVEALING anything (no new board state and no level for
                  `patience` steps) has told us this lifetime is exhausted -> reset into a fresh one.
  * CAP        -> a hard ceiling (default 500) for a game that runs infinitely AND keeps changing, so
                  one lifetime never eats the whole budget.

The thresholds are not fixed: the "agent society" adjusts them in-game via `adapt()`. If lifetimes keep
STALLING without ever gaining a level, patience GROWS (maybe the game needs longer exploration before
it reveals its mechanic); the moment a level is gained, patience resets to base. Every adjustment is a
receipt written to the ledger, so the tuning is visible, not silent.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any


class ResetPolicy:
    def __init__(self, base_patience: int = 60, hard_cap: int = 500, patience_ceiling: int = 300):
        self.base = base_patience
        self.patience = base_patience
        self.hard_cap = hard_cap
        self.ceiling = patience_ceiling
        self.history: List[str] = []

    def lifetime_over(self, *, done: bool, state: Optional[str], steps_in_life: int,
                      steps_since_progress: int) -> Optional[str]:
        """Return the reason this lifetime should end now, or None to continue."""
        if done and state == "WIN":
            return "win"
        if done:
            return "death"                       # GAME_OVER: the game's own natural reset
        if steps_since_progress >= self.patience:
            return "stall"                       # infinite game that stopped revealing anything
        if steps_in_life >= self.hard_cap:
            return "cap"                          # infinite + still changing: ceiling so budget survives
        return None

    def adapt(self, reason: str, gained_level: bool) -> Dict[str, Any]:
        """The society tunes the reset threshold from what the last generation did. Returns the change."""
        self.history.append(reason)
        old = self.patience
        if gained_level:
            self.patience = self.base                                   # progress -> back to base
        elif reason == "stall":
            self.patience = min(self.ceiling, int(round(self.patience * 1.25)))  # exhausted w/o progress -> more room
        return {"reason": reason, "gained_level": gained_level,
                "patience": self.patience, "patience_was": old}
