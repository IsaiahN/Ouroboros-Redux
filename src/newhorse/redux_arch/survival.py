"""survival.py -- the DON'T-DIE organ (Tether: the reward residual R_ρ's *negative* pole). The win-ceiling probe
(beat G) found 13/25 dev games are lost to DEATH (GAME_OVER), several long before the action cap -- the agent walks
into a game-over transition it never learns to avoid. The environment allows a post-death RESET that restarts the
level and lets play continue within the same action budget (empirically verified), so death is a LEARNABLE event:
die once, remember what killed you, and on the deterministic retry take a different action from that exact board.

This organ is that memory. It is domain-general -- it names no game; a "death cause" is just "this action, taken
from a board that looked like THIS, ended the run." On retry, when the same board recurs, that action is vetoed and
a still-available alternative is taken instead. Games are deterministic, so the retry re-encounters the same boards
until the agent diverges onto a survivable path; each fresh death adds its own cause, and the safe path is threaded
one veto at a time.

Fingerprint = exact board hash: zero false vetoes (never blocks an action in a board where it was NOT fatal). The
cost is that it only generalizes across identical boards -- which is exactly the deterministic-retry case it is for.
Coarser, avatar-centric generalization is a deliberate follow-up, not smuggled in here.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set
import numpy as np


def board_fingerprint(grid) -> int:
    """A cheap, exact signature of a board: hash of its bytes + shape. Two boards share a fingerprint iff they are
    pixel-identical. Domain-general (no colours/positions are privileged)."""
    a = np.ascontiguousarray(np.asarray(grid, dtype=np.int64))
    return hash((a.shape, a.tobytes()))


@dataclass
class DeathMemory:
    """Records (board fingerprint -> set of actions that ended the run from that board) and vetoes those actions when
    the board recurs. Purely mechanical; carries no game knowledge."""
    _fatal: Dict[int, Set[str]] = field(default_factory=dict)   # fingerprint -> fatal action labels
    n_deaths: int = 0                                           # total deaths recorded
    _causes: Set = field(default_factory=set)                  # distinct (fingerprint, action) causes

    def note_death(self, context_grid, action: str) -> bool:
        """Record that `action`, taken from `context_grid`, ended the run. Returns True if this is a NEW cause (an
        (board, action) not seen before) -- a repeat means the veto failed to prevent a known death."""
        if action in ("RESET", "?", None) or context_grid is None:
            return False
        fp = board_fingerprint(context_grid)
        self.n_deaths += 1
        new = (fp, action) not in self._causes
        self._causes.add((fp, action))
        self._fatal.setdefault(fp, set()).add(action)
        return new

    def is_fatal(self, context_grid, action: str) -> bool:
        """True iff `action` is known to end the run from a board pixel-identical to `context_grid`."""
        if context_grid is None:
            return False
        return action in self._fatal.get(board_fingerprint(context_grid), ())

    def would_be_new(self, context_grid, action: str) -> bool:
        """Would recording (context_grid, action) as a death be a NEW cause (not seen before)? Pure -- mutates
        nothing. Used by the reset-earned gate to decide, BEFORE recording, whether this death teaches something new
        (a fresh avoidable cause = evidence that a retry has a reasoned basis for a different outcome)."""
        if action in ("RESET", "?", None) or context_grid is None:
            return False
        return (board_fingerprint(context_grid), action) not in self._causes

    def fatal_here(self, context_grid) -> Set[str]:
        """The set of actions known-fatal from this exact board."""
        if context_grid is None:
            return set()
        return set(self._fatal.get(board_fingerprint(context_grid), set()))

    def safe(self, context_grid, labels: List[str]) -> List[str]:
        """Filter `labels` to those NOT known-fatal from this board. Never returns empty while any label exists: if
        EVERY available action is known-fatal here, all are returned (better to act than to freeze -- the board is a
        dead end and the divergence must have happened earlier)."""
        bad = self.fatal_here(context_grid)
        keep = [l for l in labels if l not in bad]
        return keep if keep else list(labels)

    @property
    def distinct_causes(self) -> int:
        return len(self._causes)
