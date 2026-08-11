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

    def seed_confirmed(self, cell: Tuple[int, int], price: float) -> None:
        """PHASE 3a: register a candidate at an INHERITED price (a prior from the fabric).
        Writes the price only -- never touches manager.active. An inherited price
        >= manager.confirm_bonus opens has_confirmed(); the CALLER decides the price."""
        try:
            self.manager.price[("BE_AT", (int(cell[0]), int(cell[1])))] = float(price)
        except Exception:
            self.errors += 1

    def demote_inherited(self, cell: Tuple[int, int]) -> None:
        """PHASE 3a: an inherited confirmation was falsified by live play -- drop that
        key's price to min_price (well below confirm_bonus) so the gate closes back."""
        try:
            key = ("BE_AT", (int(cell[0]), int(cell[1])))
            if key in self.manager.price:
                self.manager.price[key] = self.manager.min_price
        except Exception:
            self.errors += 1

    # ── PHASE 3b2: the click-side economy — the same wheel rule on the acted-on cell ──

    def credit_click(self, cell: Tuple[int, int]) -> None:
        """A REAL reward followed a click at `cell` -- manager-credit on the CLICK_AT key
        (price accumulates by confirm_bonus, as GoalManager.credit does). Never touches
        manager.active -- BE_AT pursuit is undisturbed; drive_click() resolves independently."""
        try:
            key = ("CLICK_AT", (int(cell[0]), int(cell[1])))
            self.manager.price[key] = self.manager.price.get(key, 0.0) + self.manager.confirm_bonus
            self.confirmations += 1
        except Exception:
            self.errors += 1

    def seed_confirmed_click(self, cell: Tuple[int, int], price: float) -> None:
        """PHASE 3b2: register a CLICK_AT candidate at an INHERITED price (a prior from the
        fabric) -- symmetric to seed_confirmed; writes the price only."""
        try:
            self.manager.price[("CLICK_AT", (int(cell[0]), int(cell[1])))] = float(price)
        except Exception:
            self.errors += 1

    def demote_inherited_click(self, cell: Tuple[int, int]) -> None:
        """PHASE 3b2: a confirmed CLICK_AT was clicked without reward -- drop that key's
        price to min_price (well below confirm_bonus) so the gate closes back."""
        try:
            key = ("CLICK_AT", (int(cell[0]), int(cell[1])))
            if key in self.manager.price:
                self.manager.price[key] = self.manager.min_price
        except Exception:
            self.errors += 1

    def drive_click(self) -> Optional[Tuple[int, int]]:
        """The highest-priced CONFIRMED CLICK_AT cell (price >= confirm_bonus); ties broken
        by the smallest cell tuple; None otherwise. INDEPENDENT of the movement delta map --
        clicking needs no locomotion (and never consults manager.active)."""
        try:
            best: Optional[Tuple[float, Tuple[int, int]]] = None   # (-price, cell) -> min = best
            for key, price in self.manager.price.items():
                if not (isinstance(key, tuple) and len(key) == 2 and key[0] == "CLICK_AT"):
                    continue
                if price < self.manager.confirm_bonus:
                    continue
                cand = (-float(price), key[1])
                if best is None or cand < best:
                    best = cand
            return best[1] if best is not None else None
        except Exception:
            self.errors += 1
            return None

    def has_confirmed(self) -> bool:
        """True iff some candidate's price reached confirm_bonus -- i.e. a reward confirmed it."""
        try:
            return any(p >= self.manager.confirm_bonus for p in self.manager.price.values())
        except Exception:
            self.errors += 1
            return False

    # ── 3d-i: frontier pariah remap — a banked fatal opening is stepped around ──

    def remap_avoided(self, cell: Tuple[int, int], avoid,
                      shape: Tuple[int, int]) -> Tuple[int, int]:
        """Identity when `cell` is not in `avoid`; else the nearest non-avoided
        in-bounds cell by Chebyshev ring scan r=1.. (ties: ascending (dy, dx)).
        `shape` is (h, w) with cell=(x, y): 0 <= x < w and 0 <= y < h. If every
        in-range cell is avoided, the original stands. Deterministic, no RNG."""
        try:
            x, y = int(cell[0]), int(cell[1])
            if (x, y) not in avoid:
                return (x, y)
            h, w = int(shape[0]), int(shape[1])
            for r in range(1, max(h, w) + 1):
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        if max(abs(dy), abs(dx)) != r:
                            continue         # interior of the ring: already scanned
                        nx, ny = x + dx, y + dy
                        if not (0 <= nx < w and 0 <= ny < h):
                            continue
                        if (nx, ny) in avoid:
                            continue
                        return (nx, ny)
            return (x, y)                    # everything avoided: the original stands
        except Exception:
            self.errors += 1
            return cell

    # ── 3d-ii: the harvest remap — coverage becomes one cumulative sweep ──────

    def remap_to_untried(self, cell: Tuple[int, int], tried, avoid,
                         shape: Tuple[int, int]) -> Tuple[int, int]:
        """The nearest in-bounds cell NOT in tried|avoid, by the same Chebyshev
        ring scan as remap_avoided (r=0.., ties: ascending (dy, dx)) -- N
        episodes stop being N independent blind draws. If every in-range cell
        was tried, retry preferring merely not-avoided (fatal cells must still
        be escaped); if that too exhausts, the original stands. Deterministic."""
        try:
            x, y = int(cell[0]), int(cell[1])
            h, w = int(shape[0]), int(shape[1])
            for banned in (set(tried) | set(avoid), set(avoid)):
                if (x, y) not in banned:
                    return (x, y)
                for r in range(1, max(h, w) + 1):
                    for dy in range(-r, r + 1):
                        for dx in range(-r, r + 1):
                            if max(abs(dy), abs(dx)) != r:
                                continue     # interior of the ring: already scanned
                            nx, ny = x + dx, y + dy
                            if not (0 <= nx < w and 0 <= ny < h):
                                continue
                            if (nx, ny) in banned:
                                continue
                            return (nx, ny)
            return (x, y)                    # everything banned: the original stands
        except Exception:
            self.errors += 1
            return cell

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
