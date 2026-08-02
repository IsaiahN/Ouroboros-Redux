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
    def __init__(self, sig_echo: int = 2):
        self.fatal: set = set()      # (board, action) -> ended the run (exact)
        self.mute: set = set()       # (board, action) -> revealed nothing (ground silent)
        self.confirm: set = set()    # (board, action) -> produced progress
        self.counts: Dict[str, int] = {}
        # --- ground-verified refutation GENERALIZATION over an INJECTED signature (open vocabulary) ---
        self.sig_echo = sig_echo             # distinct grounded instances before a generalization is CONFIRMED
        self.sig_fatal_boards: Dict = {}     # (signature, action) -> set of distinct boards it was fatal at
        self.sig_confirmed: set = set()      # (signature, action) confirmed fatal by echo (>= sig_echo boards)
        self.sig_refuted: set = set()        # (signature, action) that a counterexample proved OVER-general

    def _counterexample(self, action: str, signature) -> None:
        """The action was taken at a board matching `signature` and did NOT end the run -> refute any
        'signature+action is fatal' claim (verify against the ground, never trust the correlation)."""
        if signature is None:
            return
        sk = (signature, action)
        if sk in self.sig_confirmed or sk in self.sig_fatal_boards:
            self.sig_confirmed.discard(sk); self.sig_fatal_boards.pop(sk, None); self.sig_refuted.add(sk)

    def record(self, before_board: int, action: str, data: Optional[dict], verdict: str,
               signature=None) -> str:
        self.counts[verdict] = self.counts.get(verdict, 0) + 1
        if data:                     # click/data actions: count only (coord-keyed shaping is the policy's job)
            return verdict
        key = (before_board, action)
        if verdict == Verdict.REFUTE:
            self.fatal.add(key); self.mute.discard(key)
            if signature is not None:                        # generalize the refutation, ground-verified
                sk = (signature, action)
                if sk not in self.sig_refuted:
                    self.sig_fatal_boards.setdefault(sk, set()).add(before_board)
                    if len(self.sig_fatal_boards[sk]) >= self.sig_echo:   # echo: fatal at >= N distinct boards
                        self.sig_confirmed.add(sk)
        elif verdict == Verdict.CONFIRM:
            self.confirm.add(key); self.mute.discard(key)
            self._counterexample(action, signature)          # survived here -> not reliably fatal
        elif verdict == Verdict.MUTE:
            if key not in self.confirm and key not in self.fatal:
                self.mute.add(key)
        else:                                                # MOVED: the world changed and the run continued
            self._counterexample(action, signature)          # survived here -> refutes over-general fatality
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

    def _blocked(self, board: int, a: str, signature) -> bool:
        """An action is blocked at this board if it is exact-fatal OR its signature-generalization is a
        CONFIRMED fatal (ground-verified by echo). Generalization lets a fatal learned on similar boards
        veto a NEW, never-seen board that shares the signature."""
        return (board, a) in self.fatal or (signature is not None and (signature, a) in self.sig_confirmed)

    def shape(self, cur_board: int, action: str, data: Optional[dict],
              available: List[int], signature=None) -> Tuple[str, Optional[dict], Optional[str]]:
        """Turn the accumulated verdicts into a shaping of THIS proposal. Returns (action, data, note).
        Veto a refuted move (exact OR confirmed-general); on a mute move, apply empowerment; otherwise
        pass through. Only overrides when a strictly better non-blocked alternative exists."""
        if data:
            return action, data, None
        key = (cur_board, action)
        refuted = key in self.fatal
        muted = key in self.mute
        general = signature is not None and (signature, action) in self.sig_confirmed
        if not refuted and not muted and not general:
            return action, data, None
        alts = ["A%d" % int(v) for v in available if int(v) != 6 and "A%d" % int(v) != action]
        alts = [a for a in alts if not self._blocked(cur_board, a, signature)]
        if not alts:
            return action, data, None                       # forced: no non-blocked alternative
        best = max(alts, key=lambda a: self._rank(cur_board, a, avoid_mute=muted))
        note = ("veto:refuted->%s" % best) if refuted else \
               ("veto:general->%s" % best if general else "empower:mute->%s" % best)
        return best, None, note


def local_signature(grid, available):
    """ONE candidate signature axis -- an OPEN, REPLACEABLE placeholder, NOT a fixed feature vocabulary
    (per the scrutiny: the debugger's vocabulary must itself be mintable, or it re-smuggles the
    presupposition one door down). Groups boards by their available-action set + the multiset of colours
    present. Coarse ON PURPOSE: over-grouping is SAFE here because the ground refutes an over-general
    signature -- a matching board that survives the action relaxes it (VerdictCircuit._counterexample).
    Replace/extend with kernel-perceived features; never hardcode a closed list."""
    import numpy as np
    try:
        colours = tuple(sorted(int(c) for c in np.unique(np.asarray(grid))))
    except Exception:
        colours = ()
    return (tuple(sorted(int(v) for v in available)), colours)
