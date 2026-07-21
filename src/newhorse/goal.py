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
from typing import List, Optional
from .perception import Object


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
