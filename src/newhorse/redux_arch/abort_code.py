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

A break cleared by SEARCH or the drive layer (a level simply advancing) is NOT a tether firing (the membrane rule §3.6/§5.1 + sole-metric §0) and can
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
    `cleared` means a TRANSFERRED operator closed a break -- never a raw level advance (the membrane rule §3.6/§5.1 + sole-metric §0)."""
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
    minted = bool(s.minted or reused)      # you cannot reuse what was never minted: a transfer implies a mint
    if not s.diff_ran:
        return Stage.DIED_PRE_DIFF
    if not s.residual_nonempty:
        return Stage.RESIDUAL_EMPTY
    if not minted:
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


@dataclass
class ChainLedger:
    """PER-SEGMENT chain accounting -- the instrument that turns "which link breaks" from a guess into a measured
    distribution.

    A SEGMENT is one span of play between two break events. It ends in exactly one of three ways:
      * ADVANCE  -- a level was cleared. This is a clear by SEARCH/DRIVE, never by transfer, so by the membrane rule
                    (§3.6/§5.1 + sole-metric §0) it is NOT a tether firing and is NOT scored as a stage at all. It is
                    counted separately so it can never inflate the stall distribution in either direction.
      * DEATH    -- a stall. Scored.
      * RUN_END  -- a stall (action cap / wall clock / GAME_OVER with no earned reset). Scored.

    Signals are scoped to the segment, not cumulated over the run: the chain claim is "THIS task failed -> mint from
    THIS residual -> reuse elsewhere", so a mint in segment 3 must not credit the stall in segment 7. Cumulative
    signals would silently ratchet the reported stage upward and make a wiring gap look like progress.

    Nothing here infers a signal from a proxy. Each note_* is called from the exact site where the event happens, and
    a signal with no call site stays False -- which is the honest report that the organ is not wired, and is precisely
    what this instrument exists to surface."""
    probe: "TetherProbe" = field(default_factory=lambda: TetherProbe())
    advances: int = 0                                  # segments ended by a level advance (drive/search, not tether)
    stalls: int = 0
    _sig: ChainSignals = field(default_factory=ChainSignals)
    _reasons: Counter = field(default_factory=Counter)
    _steps: int = 0                                    # frames observed inside the CURRENT segment
    # ★ THE REUSE FUNNEL. MINTED_UNUSED is the ONE code that indicts the architecture, and for thirteen beats it has
    # been a bare count: "reuse was attempted and the library did not explain". That sentence names no branch. An
    # attempt can fail because no promoted φ even SPLITS the fresh contexts (Γ was never applicable -- a grain
    # verdict), because eligible φ existed and none of them paid their cost (Γ was tested and lost -- the only
    # reading that is actually about the architecture), or, at the directive site, because nothing was evaluable /
    # nothing was endorsed / two candidates tied. Those have four different fixes and one name. So every reuse
    # ATTEMPT is charged to a STRING LITERAL written at the branch that resolved it, and the identity
    # `sum(reuse_branch) == reuse_attempts` is published rather than assumed -- an attempt with no branch, or a
    # branch with no attempt, is a defect this counter is able to state.
    _att: int = 0                                      # reuse attempts inside the CURRENT segment
    _seg_reuse: Counter = field(default_factory=Counter)   # ...and which branch resolved each of them
    reuse_attempts: int = 0                            # run-level total (never reset by a segment close)
    reuse_branch: Counter = field(default_factory=Counter)
    # ...and ONE LEVEL FINER, because `explains_no_eligible` turned out to be the branch that resolves almost every
    # MINTED_UNUSED and it is itself two states with opposite fixes. This tally is PER φ, not per attempt, so it is
    # deliberately NOT part of the `sum(reuse_branch) == reuse_attempts` identity -- an attempt scans the whole
    # library and contributes as many rows here as the library has ineligible members. Its own denominator is the
    # library scan, which is why it is published as a bare split and never as a rate against attempts.
    _seg_phi: Counter = field(default_factory=Counter)
    no_eligible_phi: Counter = field(default_factory=Counter)

    @property
    def steps_in_segment(self) -> int:
        """Frames observed inside the CURRENTLY OPEN segment. Callers that want to do work at a break event (build a
        residual, offer it to the library) must skip an EMPTY segment for exactly the reason `end_segment` does: it
        is an accounting artefact, not a task that failed, and scoring it would manufacture evidence."""
        return int(self._steps)

    def note_step(self) -> None:
        """One observation landed in the current segment. An EMPTY segment (no frame between two break events -- e.g.
        a run that ends on the same frame as the death that closed the previous segment) is not a stall and must not
        be scored: it would manufacture a DIED_PRE_DIFF out of an accounting artefact."""
        self._steps += 1

    def note_diff(self, residual_nonempty: bool = False) -> None:
        """A boundary diff (§3.5) actually ran for THIS segment. `residual_nonempty` iff it left structure the
        transferred model does not account for -- NOVEL/GONE identities or a rebinding."""
        self._sig.diff_ran = True
        if residual_nonempty:
            self._sig.residual_nonempty = True

    def note_mint(self) -> None:
        """A minter returned a real Mint from this segment's residual. NOT the human gate: a mint that is parked for
        confirmation still MINTED, and conflating the two would report a gate decision as a library failure."""
        self._sig.minted = True

    @property
    def reuse_attempts_in_segment(self) -> int:
        """Reuse attempts made inside the CURRENTLY OPEN segment -- the denominator the branch tally must close
        against. Read before `end_segment`, which zeroes it: a count carried across a segment boundary would charge
        this segment's failures to the next segment's stage, which is the exact defect `_sig` is scoped to avoid."""
        return int(self._att)

    @property
    def reuse_branch_in_segment(self) -> Dict[str, int]:
        return {k: int(n) for k, n in sorted(self._seg_reuse.items())}

    def note_reuse_attempt(self) -> None:
        """A FRESH task's residual was offered to the promoted library (Consolidator.explains). Until some call site
        exists this stays False and the ceiling is REUSE_UNWIRED -- an implementation verdict, never an architectural one."""
        self._sig.reuse_attempted = True
        self._att += 1
        self.reuse_attempts += 1

    def note_reuse_exit(self, where: str) -> None:
        """The branch that RESOLVED one reuse attempt, named by a string literal written at that branch. Callers pass
        this method itself (not a dict) so the count lands in the ledger from the site where the thing happens --
        never re-derived from another organ's number, and never carried by a second object that could be constructed
        somewhere the wiring does not reach. Every attempt must reach exactly one of these; the residue says so."""
        self._seg_reuse[str(where)] += 1
        self.reuse_branch[str(where)] += 1

    @property
    def no_eligible_phi_in_segment(self) -> Dict[str, int]:
        return {k: int(n) for k, n in sorted(self._seg_phi.items())}

    def note_no_eligible_phi(self, kind: str) -> None:
        """ONE library φ was rejected by the eligibility test, and WHY. `phi_absent` = it held on no fresh context
        at all (the vocabulary does not describe this board -- link 1, grain). `phi_universal` = it held on every
        fresh context (true but vacuous -- the contexts are degenerate, which is upstream in the residual). The two
        are exhaustive and exclusive for a rejected φ, so a kind outside them is a new branch added without a
        reading and the printer names it. Passed as a bound method for the same reason `note_reuse_exit` is: a
        second carrier is a second construction site, and one of them gets orphaned."""
        self._seg_phi[str(kind)] += 1
        self.no_eligible_phi[str(kind)] += 1

    def note_reuse(self) -> None:
        """The promoted library EXPLAINED a fresh task without re-minting -- transfer."""
        self._sig.reused = True

    def note_transfer_clear(self) -> None:
        """Acting on a TRANSFERRED operator cleared a break. Callers must never pass a raw level advance here."""
        self._sig.cleared = True

    def end_segment(self, reason: str) -> Optional[Stage]:
        """Close the current segment and open a fresh one. Returns the stage if this was a scored STALL, or None if
        the segment ended in an advance (deliberately unscored) or was empty (no frame observed -- an accounting
        artefact, not a stall)."""
        if self._steps == 0:
            return None                                # nothing was played in this segment; closing it is a no-op
        self._reasons[str(reason)] += 1
        st: Optional[Stage] = None
        if reason == "advance":
            self.advances += 1
        else:
            self.stalls += 1
            st = self.probe.record(self._sig)
        self._sig = ChainSignals()                     # signals belong to a segment, never to the run
        self._steps = 0
        self._att = 0                                  # ...and so does the reuse tally that explains the signals
        self._seg_reuse = Counter()
        self._seg_phi = Counter()
        return st

    def report(self) -> Dict[str, object]:
        r = dict(self.probe.report())
        r.update(stalls=self.stalls, advances=self.advances,
                 segment_ends={k: n for k, n in sorted(self._reasons.items())},
                 reuse_attempts=int(self.reuse_attempts),
                 reuse_branch={k: int(n) for k, n in sorted(self.reuse_branch.items())},
                 reuse_residue=int(self.reuse_attempts) - int(sum(self.reuse_branch.values())),
                 no_eligible_phi={k: int(n) for k, n in sorted(self.no_eligible_phi.items())})
        return r
