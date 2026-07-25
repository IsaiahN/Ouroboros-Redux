"""abort_code.py -- the per-stall TETHER STAGE code.

Winning was never the bar; the bar is ONE firing of the whole loop: a task FAILS -> an operator is MINTED from the
residual -> that operator is REUSED on a task it was NOT minted for -> the reuse CLEARS a break. Until that fires once,
the architecture has not been TESTED: almost every stall so far is stage-one (perception inert, the diff never runs) or
stage-three (a residual is there but the mint gate doesn't fire), and a stage-one/three stall must NEVER be written up as
a verdict on the architecture. Only the reuse stage indicts the architecture, and only when reuse was genuinely ATTEMPTED.

This module makes "how far down the chain a stall got" a MEASURED code instead of a narrative, so implementation /
library / gate / architecture / drive failures are never confused for one another. It is a general instrument: it reads
booleans about the chain state, names no game, encodes no answer.

The chain (each stage subsumes the one before -- a later stage cannot be reached without every earlier signal):

    diff never ran                     -> DIED_PRE_DIFF   (implementation)
    diff ran, residual empty/degenerate-> RESIDUAL_EMPTY  (library -- wrong grain)
    residual there, no mint            -> MINT_UNFIRED     (gate calibration / implementation)
    minted, reuse never ATTEMPTED      -> REUSE_UNWIRED    (implementation -- the loop isn't connected / no 2nd task)
    minted, reuse tried, not explained -> MINTED_UNUSED    (ARCHITECTURE -- the ONLY code that indicts the tether)
    reused (transfer), no break cleared-> USED_NOCLEAR     (drive layer, not the tether)
    reused AND a break cleared         -> CLEARED          (the tether fired once)

The split of "minted but never reused" into REUSE_UNWIRED vs MINTED_UNUSED is load-bearing: a mint whose product was
never offered to a fresh task's residual is a WIRING gap, not an architecture verdict. Only MINTED_UNUSED -- reuse
genuinely attempted on a fresh task and the promoted library failed to explain it -- is allowed to indict the tether.

A break cleared by SEARCH or the drive layer (a level simply advancing) is NOT a tether firing (spec §7.2b) and can
never set CLEARED: `cleared` here means specifically that acting on a TRANSFERRED operator closed the break, which
requires `reused` first. Callers must not pass a raw level-advance as `cleared`.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Optional


class Stage(IntEnum):
    DIED_PRE_DIFF = 0
    RESIDUAL_EMPTY = 1
    MINT_UNFIRED = 2
    REUSE_UNWIRED = 3
    MINTED_UNUSED = 4
    USED_NOCLEAR = 5
    CLEARED = 6


# What a stall at each stage indicts. ONLY MINTED_UNUSED indicts the architecture.
_INDICTS: Dict[Stage, str] = {
    Stage.DIED_PRE_DIFF: "implementation",
    Stage.RESIDUAL_EMPTY: "library",
    Stage.MINT_UNFIRED: "gate/implementation",
    Stage.REUSE_UNWIRED: "implementation",
    Stage.MINTED_UNUSED: "architecture",
    Stage.USED_NOCLEAR: "drive",
    Stage.CLEARED: "none",
}

_NOTE: Dict[Stage, str] = {
    Stage.DIED_PRE_DIFF: "died before the diff -- residual never computed",
    Stage.RESIDUAL_EMPTY: "diff ran but the residual was empty/degenerate -- library grain",
    Stage.MINT_UNFIRED: "residual present but no operator minted -- gate calibration",
    Stage.REUSE_UNWIRED: "minted but reuse was never attempted on a fresh task -- loop not connected",
    Stage.MINTED_UNUSED: "minted and reuse attempted, but the library did not explain a fresh task -- architecture",
    Stage.USED_NOCLEAR: "transferred to a fresh task but acting did not clear a break -- drive layer",
    Stage.CLEARED: "fail -> mint -> reuse-where-not-minted -> break cleared: the tether fired",
}


def indicts(stage: Stage) -> str:
    """The layer a stall at `stage` implicates. 'architecture' appears for exactly one stage (MINTED_UNUSED)."""
    return _INDICTS[Stage(stage)]


def note(stage: Stage) -> str:
    return _NOTE[Stage(stage)]


@dataclass
class ChainSignals:
    """Booleans about how far one stall walked the tether chain. Later signals imply earlier ones; `classify`
    normalises so an inconsistent caller (e.g. reused=True, reuse_attempted=False) is coerced, not mislabelled.
    `cleared` means a TRANSFERRED operator closed a break -- never a raw level advance (spec §7.2b)."""
    diff_ran: bool = False
    residual_nonempty: bool = False
    minted: bool = False
    reuse_attempted: bool = False          # a FRESH task's residual was offered to the promoted library
    reused: bool = False                   # the library EXPLAINED that fresh task WITHOUT re-minting (transfer)
    cleared: bool = False                  # acting on that transfer cleared a break


def classify(s: ChainSignals) -> Stage:
    """The furthest stage this stall reached. Monotonic: each stage requires every earlier signal; implications are
    coerced (transfer implies attempt; a clear implies a transfer) so a partial/loose signal set can never over-credit."""
    reused = bool(s.reused or s.cleared)
    reuse_attempted = bool(s.reuse_attempted or reused)
    if not s.diff_ran:
        return Stage.DIED_PRE_DIFF
    if not s.residual_nonempty:
        return Stage.RESIDUAL_EMPTY
    if not s.minted:
        return Stage.MINT_UNFIRED
    if not reuse_attempted:
        return Stage.REUSE_UNWIRED
    if not reused:
        return Stage.MINTED_UNUSED
    if not s.cleared:
        return Stage.USED_NOCLEAR
    return Stage.CLEARED


@dataclass
class TetherProbe:
    """Accumulates the FURTHEST stage reached across a stream of stalls, and how often each stage was the outcome.
    `furthest` is the honest headline: it is the only stall that could ever say anything about the architecture, and it
    says 'architecture' only if it is MINTED_UNUSED. Everything below that is an implementation/library/gate report."""
    furthest: Optional[Stage] = None
    counts: Counter = field(default_factory=Counter)

    def record(self, s: ChainSignals) -> Stage:
        st = classify(s)
        self.counts[st] += 1
        if self.furthest is None or st > self.furthest:
            self.furthest = st
        return st

    def verdict(self) -> str:
        """The layer the FURTHEST stall implicates, or 'none' before any stall / on a full firing."""
        return "none" if self.furthest is None else indicts(self.furthest)

    def indicts_architecture(self) -> bool:
        """True ONLY if the deepest stall genuinely attempted reuse and the library failed -- the sole architecture
        verdict. A run that never wired/attempted reuse returns False (its ceiling is an implementation stage)."""
        return self.furthest == Stage.MINTED_UNUSED

    def report(self) -> Dict[str, object]:
        f = self.furthest
        return {
            "furthest_stage": None if f is None else f.name,
            "furthest_rank": None if f is None else int(f),
            "indicts": self.verdict(),
            "note": None if f is None else note(f),
            "counts": {st.name: n for st, n in sorted(self.counts.items())},
        }
