"""spine.py -- Phase 2's goal spine: confirmed reward earns the wheel; everything else is None.

`GoalSpine` wraps the verbatim-ported `GoalManager` (goal.py) with the two things the wheel rule
needs (PREREG_PHASE2.md, EGOCENTRIC_PORT_PLAN.md sec. 7):

  * a per-action VECTOR delta map of the controllable's centroid, learned live from
    `note_move(action, delta)` -- an action is ESTABLISHED once its dominant delta has been seen
    `min_evidence` times (the means);
  * the confirmation gate: `drive(self_cell)` returns an action ONLY when a goal holds CONFIRMED
    price (>= confirm_bonus -- a real reward happened) AND an established action strictly reduces
    Manhattan distance to it. Otherwise None -- byte-inert.

Discipline (as Phase 1): deterministic (no RNG, no I/O), and EVERY exception is swallowed to the
`errors` counter -- the spine must never crash the loop it advises.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from engines.egocentric.goal import GoalManager


def _sign(v: float) -> int:
    return (v > 0) - (v < 0)


class GoalSpine:
    """cue-proposes, reward-disposes, and only a confirmed goal may drive."""

    def __init__(self, min_evidence: int = 3):
        self.min_evidence = int(min_evidence)
        self.manager = GoalManager()
        # action -> {exact delta tuple -> observation count}
        self.evidence: Dict[str, Dict[Tuple[int, int], int]] = {}
        self.confirmations: int = 0   # how many credits landed (the gate's memory)
        self.errors: int = 0          # exceptions land here, never in the caller's lap

    # ── the means: per-action delta evidence ──────────────────────────────────

    def note_move(self, action: str, delta: Tuple[int, int]) -> None:
        """Accrue one observed (dr, dc) centroid delta for `action`."""
        try:
            counts = self.evidence.setdefault(str(action), {})
            key = (delta[0], delta[1])
            counts[key] = counts.get(key, 0) + 1
        except Exception:
            self.errors += 1

    def established(self) -> Dict[str, Tuple[int, int]]:
        """action -> sign-normalised dominant delta, for every action whose dominant exact delta
        has been seen >= min_evidence times (ties: lexicographic smallest tuple)."""
        try:
            out: Dict[str, Tuple[int, int]] = {}
            for action, counts in self.evidence.items():
                if not counts:
                    continue
                # most frequent exact tuple; ties broken by the lexicographic smallest tuple
                best = min(counts, key=lambda d: (-counts[d], d))
                if counts[best] >= self.min_evidence:
                    out[action] = (_sign(best[0]), _sign(best[1]))
            return out
        except Exception:
            self.errors += 1
            return {}

    # ── the market: candidate goals priced by reward ──────────────────────────

    def propose(self, cells: Iterable[Tuple[int, int]]) -> None:
        """Seed candidate target cells; rank = enumeration order (0 = most marker-like)."""
        try:
            self.manager.propose(((int(c[0]), int(c[1])), rank) for rank, c in enumerate(cells))
        except Exception:
            self.errors += 1

    def credit(self, cell: Tuple[int, int]) -> None:
        """A REAL reward happened at `cell` -- confirm the market's winner (reward-disposes)."""
        try:
            self.manager.credit((int(cell[0]), int(cell[1])))
            self.confirmations += 1
        except Exception:
            self.errors += 1

    def has_confirmed(self) -> bool:
        """True iff some candidate's price reached confirm_bonus -- i.e. a reward confirmed it."""
        try:
            return any(p >= self.manager.confirm_bonus for p in self.manager.price.values())
        except Exception:
            self.errors += 1
            return False

    # ── the wheel: only signal AND means together drive ───────────────────────

    def drive(self, self_cell: Tuple[int, int]) -> Optional[str]:
        """The established action that most reduces Manhattan distance to the CONFIRMED goal.
        None unless BOTH hold: a confirmed goal exists and some action strictly helps."""
        try:
            if not self.has_confirmed():
                return None
            key = self.manager.active_goal()
            target = self._target_cell(key)
            if target is None:
                return None
            r, c = int(self_cell[0]), int(self_cell[1])
            if (r, c) == target:
                return None
            base = abs(r - target[0]) + abs(c - target[1])
            best: Optional[Tuple[int, str]] = None    # (-reduction, action) -> min = best
            for action, (dr, dc) in self.established().items():
                reduction = base - (abs(r + dr - target[0]) + abs(c + dc - target[1]))
                if reduction > 0 and (best is None or (-reduction, action) < best):
                    best = (-reduction, action)
            return best[1] if best is not None else None
        except Exception:
            self.errors += 1
            return None

    @staticmethod
    def _target_cell(key) -> Optional[Tuple[int, int]]:
        """Goal keys are bare (r, c) cells (from propose) or ('BE_AT', (r, c)) tuples (from
        credit) -- resolve either; anything else (e.g. quantified ALL) is out of v1's scope."""
        if key is None:
            return None
        if isinstance(key, tuple) and len(key) == 2:
            if isinstance(key[0], int) and isinstance(key[1], int):
                return (key[0], key[1])
            cell = key[1]
            if isinstance(cell, tuple) and len(cell) == 2 \
                    and isinstance(cell[0], int) and isinstance(cell[1], int):
                return (cell[0], cell[1])
        return None
