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
import hashlib
import numpy as np


def board_fingerprint(grid) -> int:
    """A cheap, exact signature of a board: hash of its bytes + shape. Two boards share a fingerprint iff they are
    pixel-identical. Domain-general (no colours/positions are privileged)."""
    a = np.ascontiguousarray(np.asarray(grid, dtype=np.int64))
    return hash((a.shape, a.tobytes()))


def board_digest(grid) -> str:
    """★ THE SAME IDENTITY AS `board_fingerprint`, WRITTEN DOWN SO A RECEIPT CAN CARRY IT. ★

    `board_fingerprint` is built on `hash()`, which Python salts per process: the integer the death-memory compares
    is correct WITHIN a run and meaningless BETWEEN runs. A fingerprint printed into a log and then compared across
    two arms would therefore be a mis-labelled receipt of exactly the kind the discipline forbids -- it would look
    like a board identity and behave like a session nonce.

    So this returns a STABLE, reproducible digest of the same bytes and the same shape. It induces THE SAME
    EQUIVALENCE the gate uses (two boards share a digest iff they are pixel-identical, collisions aside), which is
    what licenses reading it as the gate's identity; `tests/test_survival.py` pins that agreement rather than
    asserting it here. It is used for LOGGING ONLY. Nothing in the agent reads it, and it is NOT a second key --
    substituting it for `board_fingerprint` in the death memory would change nothing except the cost."""
    a = np.ascontiguousarray(np.asarray(grid, dtype=np.int64))
    h = hashlib.blake2b(a.tobytes(), digest_size=6)
    h.update(repr(tuple(int(x) for x in a.shape)).encode("ascii"))
    return h.hexdigest()


@dataclass
class AvatarHazard:
    """Avatar-centric hazard generalization (Tether: R_ρ negative pole, generalized). The exact-board DeathMemory
    vetoes only a pixel-identical board, so the agent must die ONCE at EACH new fatal board. But a death often has a
    LOCAL cause: the cursor MOVED ONTO a particular colour (a lava/wall/pit cell). Learning that fatal DESTINATION
    COLOUR lets the veto generalize across DIFFERENT boards -- after one death the agent avoids every move onto that
    colour. Domain-general: it names no game; the fatal colour is read live from where the cursor died.

    PRECISION: the BACKGROUND colour is NEVER a hazard (moving across bg is normal traversal) -- recording bg would
    freeze the agent, since bg is everywhere. So note() excludes bg. A colour that is only *sometimes* fatal is a
    (rare) false positive bounded by the same 'never freeze' fallback the caller applies."""
    _fatal: "Set[int]" = field(default_factory=set)         # colours the cursor died entering (bg excluded)

    def note(self, dest_colour, bg) -> bool:
        """Record that entering `dest_colour` ended the run. Excludes the background. Returns True if newly learned."""
        if dest_colour is None or int(dest_colour) < 0 or int(dest_colour) == int(bg):
            return False
        c = int(dest_colour)
        new = c not in self._fatal
        self._fatal.add(c)
        return new

    def is_fatal_colour(self, colour) -> bool:
        return colour is not None and int(colour) in self._fatal

    def fatal_colours(self) -> "Set[int]":
        return set(self._fatal)


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
