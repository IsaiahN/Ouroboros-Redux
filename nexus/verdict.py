"""nexus.verdict -- the closed price->generation circuit (DESIGN_the_distillation_loop...).

The distillation loop's load-bearing organ: EVERY ground verdict is a force on the next proposal, not
a record filed and forgotten. The Nexus death loop proved that a price the generator doesn't feel is
not distillation -- it's book-keeping. So there is one object that turns each step's ground outcome
into a shaping of what the generator may emit next:

  CONFIRM (progress: a level / reward)      -> the (board, action) is preferred when seen again.
  REFUTE  (death / proven-fatal)            -> the (board, action) is VETOED (the death-loop fix, generalised).
  MUTE    (ground silent: nothing changed)  -> EMPOWERMENT: don't repeat a move the ground said nothing on;
                                               prefer one that might discriminate. This is the spec's
                                               resolution insight (a mute ground must be made to speak,
                                               never negotiated around) turned into control flow.
  MOVED   (the world changed, no reward yet) -> live exploration; neither preferred nor vetoed.

Scoped to no-data (directional) actions for override, exactly like the earlier fatal veto: a click's
unit is (board, coord) and picking an alternative coordinate is the policy's job, so click verdicts are
counted but not overridden here.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple


class Verdict:
    CONFIRM = "confirm"
    REFUTE = "refute"
    MUTE = "mute"
    MOVED = "moved"


def classify(before_board: int, after_board: int, level_delta: int, done: bool, state) -> str:
    """Read the ground's verdict on the step just taken. Progress and death dominate; otherwise the
    ground spoke iff the world changed (MOVED), and was silent iff it did not (MUTE)."""
    if level_delta > 0:
        return Verdict.CONFIRM
    if done and state != "WIN":
        return Verdict.REFUTE
    if before_board == after_board:
        return Verdict.MUTE
    return Verdict.MOVED


class VerdictCircuit:
    def __init__(self):
        self.fatal: set = set()      # (board, action) -> ended the run
        self.mute: set = set()       # (board, action) -> revealed nothing (ground silent)
        self.confirm: set = set()    # (board, action) -> produced progress
        self.counts: Dict[str, int] = {}

    def record(self, before_board: int, action: str, data: Optional[dict], verdict: str) -> str:
        self.counts[verdict] = self.counts.get(verdict, 0) + 1
        if data:                     # click/data actions: count only (coord-keyed shaping is the policy's job)
            return verdict
        key = (before_board, action)
        if verdict == Verdict.REFUTE:
            self.fatal.add(key); self.mute.discard(key)
        elif verdict == Verdict.CONFIRM:
            self.confirm.add(key); self.mute.discard(key)
        elif verdict == Verdict.MUTE:
            if key not in self.confirm and key not in self.fatal:
                self.mute.add(key)
        # MOVED: the ground spoke via the world -- live exploration, no shaping
        return verdict

    def _rank(self, cur_board: int, a: str, avoid_mute: bool) -> int:
        key = (cur_board, a)
        if key in self.fatal:
            return -100
        s = 0
        if key in self.confirm:
            s += 3                                          # a move that already produced progress here
        novel = key not in self.mute and key not in self.confirm
        if novel:
            s += 2                                          # untried here -> most likely to discriminate
        if avoid_mute and key in self.mute:
            s -= 1
        return s

    def shape(self, cur_board: int, action: str, data: Optional[dict],
              available: List[int]) -> Tuple[str, Optional[dict], Optional[str]]:
        """Turn the accumulated verdicts into a shaping of THIS proposal. Returns (action, data, note).
        Veto a refuted move; on a mute move, apply empowerment (prefer a discriminating alternative);
        otherwise pass through. Only overrides when a strictly better non-fatal alternative exists."""
        if data:
            return action, data, None
        key = (cur_board, action)
        refuted = key in self.fatal
        muted = key in self.mute
        if not refuted and not muted:
            return action, data, None
        alts = ["A%d" % int(v) for v in available if int(v) != 6 and "A%d" % int(v) != action]
        alts = [a for a in alts if (cur_board, a) not in self.fatal]
        if not alts:
            return action, data, None                       # forced: no non-fatal alternative
        best = max(alts, key=lambda a: self._rank(cur_board, a, avoid_mute=muted))
        note = ("veto:refuted->%s" % best) if refuted else ("empower:mute->%s" % best)
        return best, None, note
