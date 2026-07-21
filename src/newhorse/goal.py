"""
goal.py -- brick 13 (minimal): abduce a NAVIGATION TARGET from the goal's APPEARANCE, not the action space
(harvested from Redux `goal_cues`, re-expressed). The win-relation is proposed from what the board LOOKS
like -- a unique small distinct object is a plausible destination (BE_AT it). This is a PROVISIONAL cue:
cue-proposes, reward-disposes (brick 14 will demote a target that navigating to never advances a level).

NEVER ENCODE THE ANSWER: this looks for a generic shape (a unique small non-self object), not ls20's
specific target. If the board has no such cue, it returns None and the agent keeps exploring. Nothing silent.
"""
from __future__ import annotations
from collections import Counter
from typing import List, Optional, Dict, Tuple, Iterable
from .perception import Object


class GoalManager:
    """A MARKET OF CANDIDATE GOALS priced by REWARD (brick 14). ls20's goal is not a single appearance cue,
    so we propose several candidate targets from the board and let the sparse reward arbitrate.

    FMap: hayek_price_system (d=0.154) -- reward is the PRICE that selects among competing candidate goals;
    adaptive_immune_system (d=0.137) -- remember specific candidates and DEMOTE defeasibly (a demoted target
    keeps a residual price and can be reconsidered, never a hard drop). cue-proposes, reward-disposes.

    Cycle: propose() seeds candidate target CELLS (marker-like first); active_goal() returns the
    highest-priced one to pursue; observe() CONFIRMS it (price up) on a reward while pursuing it, or DEMOTES
    it (price down, rotate) when the cursor reaches it with no reward or stalls. Nothing silent."""

    def __init__(self, *, stall_steps: int = 50, demote_factor: float = 0.4,
                 confirm_bonus: float = 10.0, min_price: float = 0.05):
        self.stall_steps = int(stall_steps)
        self.demote_factor = float(demote_factor)
        self.confirm_bonus = float(confirm_bonus)
        self.min_price = float(min_price)
        self.price: Dict[Tuple[int, int], float] = {}      # candidate target cell -> price
        self.active: Optional[Tuple[int, int]] = None
        self.pursuit = 0
        self.log: List[str] = []

    def propose(self, candidates: Iterable[Tuple[Tuple[int, int], int]]) -> None:
        """Seed NEW candidate cells. `candidates` = (cell, rank); rank 0 = most marker-like -> higher price."""
        for cell, rank in candidates:
            if cell not in self.price:
                self.price[cell] = 1.0 / (1.0 + rank)

    def active_goal(self) -> Optional[Tuple[int, int]]:
        """The candidate to pursue now: the highest-priced one (a confirmed target stays highest and is
        re-selected; an untested/demoted one is tried in turn)."""
        if self.active is not None:
            return self.active
        if not self.price:
            return None
        self.active = max(self.price, key=self.price.get)
        self.pursuit = 0
        self.log.append("GOAL  pursue %s (price %.2f)" % (self.active, self.price[self.active]))
        return self.active

    def observe(self, cursor_cell: Optional[Tuple[int, int]], reward: bool) -> None:
        """Feedback for the active goal: a reward while pursuing it CONFIRMS (price up, keep it); reaching it
        with no reward, or stalling, DEMOTES it (price down) and rotates to the next candidate."""
        if self.active is None:
            return
        self.pursuit += 1
        if reward:
            self.price[self.active] = self.price.get(self.active, 0.0) + self.confirm_bonus
            self.log.append("GOAL  CONFIRM %s (reward) -> price %.2f" % (self.active, self.price[self.active]))
            self.pursuit = 0
            return
        reached = (cursor_cell is not None and cursor_cell == self.active)
        if reached or self.pursuit >= self.stall_steps:
            self.price[self.active] = max(self.min_price, self.price[self.active] * self.demote_factor)
            self.log.append("GOAL  demote %s (reached=%s stall=%d) -> price %.2f"
                            % (self.active, reached, self.pursuit, self.price[self.active]))
            self.active = None                              # rotate: next active_goal() picks the new best


def candidate_targets(objs: List[Object], cursor_colour: Optional[int], stride: int,
                      *, max_candidates: int = 6) -> List[Tuple[Tuple[int, int], int]]:
    """Candidate goal CELLS for the GoalManager: each distinct non-self object's logical cell, ranked
    marker-like first (smallest/rarest = most likely a goal marker; Redux `_distinct_cell_targets` shape).
    Returns [(cell, rank), ...]. Generic -- no game identity; reward disposes."""
    s = max(1, stride)
    non_self = [o for o in objs if cursor_colour is None or cursor_colour not in o.colours]
    non_self.sort(key=lambda o: o.size)                    # smallest first = most marker-like
    out: List[Tuple[Tuple[int, int], int]] = []
    seen = set()
    for rank, o in enumerate(non_self[:max_candidates]):
        cell = (int(round(o.centroid[0] / s)), int(round(o.centroid[1] / s)))
        if cell not in seen:
            seen.add(cell); out.append((cell, rank))
    return out


def abduce_target(objs: List[Object], cursor_colour: Optional[int], *, max_size: int = 30) -> Optional[Object]:
    """The provisional destination: a UNIQUE small non-self object (Redux `detect_distinct_exit` shape) --
    a colour that appears as exactly ONE small component is a distinctive landmark / exit. Returns the
    Object to navigate to (BE_AT), or None if the board shows no such cue."""
    non_self = [o for o in objs if cursor_colour is None or cursor_colour not in o.colours]
    if not non_self:
        return None
    colour_counts = Counter()
    for o in non_self:
        for c in o.colours:
            colour_counts[c] += 1
    # a colour that appears in exactly ONE small object -> a unique landmark (candidate destination)
    uniques = [o for o in non_self
               if o.size <= max_size and all(colour_counts[c] == 1 for c in o.colours)]
    if not uniques:
        return None
    # prefer the smallest, most glyph-like unique landmark (a compact exit marker)
    return min(uniques, key=lambda o: o.size)
