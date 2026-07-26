"""
consolidate.py -- redux-arch P3: ECHO -> PROMOTE (the slow, cross-episode clock).

A local mint (P2) is provisional: a predicate that compresses ONE task's residual might be an overfit hack. The
guard is ECHO-before-PROMOTE -- a minted φ is admitted into the grammar Γ only after it recurs on a DIFFERENT
task (it echoes). Then Γ ← Γ ∪ φ, and on the next task Γ already predicts the regularity, so the residual is
zero and no search is needed -- the self-modifying loop closes and transfer is realized.

This in-house consolidation (key predicates by their atom set; promote at echo_threshold distinct tasks) is the
minimal version of DreamCoder/Stitch library learning [Ellis 2021; Bowers 2023]. Stitch is the production backend
for the harder job -- refactoring a LARGE set of minted predicates to find shared sub-structure and abstract it;
for the echo-before-promote guard and small libraries, reuse-count promotion suffices. Nothing silent: every
promotion is logged with the tasks that echoed it.
"""
from __future__ import annotations
import math
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, FrozenSet
from .dsl import Predicate, Context
from .minting import Mint, two_part_mdl, Exception_, _entropy_bits
from .receipt import game_of


def _key(pred: Predicate) -> FrozenSet[str]:
    """Canonical identity of a predicate: its set of atom names (equal predicates share it)."""
    return frozenset(a.name for a in pred.atoms)


@dataclass
class Consolidator:
    """The grammar's growth gate: promote a minted predicate into Γ only once it ECHOes on a different task.

    THREAD-SAFE ON PURPOSE. Γ is now SHARED ACROSS GAMES (`policy.SHARED_ECHO`) and the swarm runs eight games
    concurrently in one process, so `observe_mint` is called from many threads at once. Without the lock two
    threads minting the same φ can both read `len(seen)` before either writes, and BOTH return True -- two
    promotions of one predicate, which would put a duplicate in Γ and double the `promoted` count in the pooled
    receipt. That is a measurement corrupted by a race, which is worse than a low number.
    Readers snapshot `library` under the same lock: `explains_scored` iterating the list while another thread
    appends is undefined, and a transfer verdict must never depend on scheduling."""
    echo_threshold: int = 2
    library: List[Predicate] = field(default_factory=list)      # Γ's promoted predicates (the grown vocabulary)
    _tasks_by_key: Dict[FrozenSet[str], Set[str]] = field(default_factory=dict)
    _pred_by_key: Dict[FrozenSet[str], Predicate] = field(default_factory=dict)
    log: List[str] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    def observe_mint(self, task_id: str, mint: Mint) -> bool:
        """Register that `task_id` minted this predicate. Promote it into Γ once it has echoed on
        `echo_threshold` distinct tasks. Returns True iff this call caused a promotion."""
        key = _key(mint.predicate)
        with self._lock:
            self._pred_by_key[key] = mint.predicate
            seen = self._tasks_by_key.setdefault(key, set())
            seen.add(str(task_id))
            already = any(_key(p) == key for p in self.library)
            if len(seen) >= self.echo_threshold and not already:
                self.library.append(mint.predicate)
                self.log.append("PROMOTE  φ=(%s) into Γ -- echoed on tasks %s"
                                % (mint.predicate, sorted(seen)))
                return True
            if already:
                self.log.append("RE-MINT  φ=(%s) minted again on %s -- already in Γ (%d tasks)"
                                % (mint.predicate, task_id, len(seen)))
            else:
                self.log.append("HOLD  φ=(%s) minted on %s (%d/%d tasks -- not yet echoed)"
                                % (mint.predicate, task_id, len(seen), self.echo_threshold))
            return False

    def echo_tasks(self, pred: Predicate) -> List[str]:
        """The distinct task ids this predicate has been minted on. The RECEIPT needs these, not just a count: a φ
        that echoed across two GAMES is a strictly stronger transfer claim than one that echoed across two segments
        of one run, and a receipt that reports only "it echoed" hides that difference (§5.1 source amnesia)."""
        with self._lock:
            return sorted(self._tasks_by_key.get(_key(pred), set()))

    def echo_games(self, pred: Predicate) -> List[str]:
        """The distinct GAMES this predicate has been minted on. `echo_tasks` cannot answer this: task ids carry
        the game, so a φ minted on four segments of ONE game returns four tasks and one game -- and a shared Γ
        judged by task count alone would read that as strong cross-game evidence."""
        return sorted({game_of(t) for t in self.echo_tasks(pred)})

    def foreign(self, game_id: str) -> List[Predicate]:
        """The promoted φ in Γ that `game_id` did NOT mint -- the only φ whose firing here would be a transfer
        ACROSS GAMES. THIS IS THE CROSS-GAME LIBRARY'S REAL SIZE for this game: a Γ of four φ that this same game
        minted is, for transfer purposes, empty, and `len(library)` cannot tell the two apart. The shared Γ's
        pre-registered undo is written against this, not against library size."""
        gid = str(game_id)
        with self._lock:
            lib = list(self.library)
        return [p for p in lib if gid not in self.echo_games(p)]

    def reset(self) -> None:
        """Empty Γ and the echo clock. FOR TEST ISOLATION ONLY (see tests/conftest.py). Γ is a process-wide
        singleton now, so without a per-test reset one test's synthetic promotion becomes another test's library
        and `explains` starts answering from a φ that test never minted -- the residual bank's contamination
        failure, one layer up. There is no call site for this in the build, and there must never be one: a Γ that
        the agent can clear is a Γ the agent can launder."""
        with self._lock:
            self.library.clear()
            self._tasks_by_key.clear()
            self._pred_by_key.clear()
            self.log.clear()

    def explains_scored(self, exceptions: List[Exception_], report: Optional[Dict[str, float]] = None):
        """`explains`, but returning (φ, bits saved) so the firing receipt can record the MDL delta the transfer
        actually bought instead of merely asserting that one happened.

        ★ THE SELECTION COST IS CHARGED HERE TOO -- THE SAME HOLE THE MINT GATE HAD, ONE LAYER UP. Picking the
        BEST-compressing φ out of a library of N is a multiple-hypothesis selection, and naming which one costs
        log2(N) bits. While Γ was per-policy and held 0-1 predicates that cost rounded to nothing, so the omission
        was invisible. Sharing Γ across games is a machine for growing N -- exactly as pooling was a machine for
        growing n -- and an uncharged best-of-N would have made the shared library manufacture its own firings and
        then reported them as the strongest transfer claim the chain can make. Charged over ELIGIBLE library
        predicates only (those that non-trivially split THESE contexts); eligibility reads ctx and never the
        outcome, so the tautology guard stays a type property, identically to `two_part_mdl`.
        THE ASYMMETRY THAT REMAINS, MEASURED AND NOT FIXED HERE: `two_part_mdl` also charges `_parametric_bits` on
        the baseline and on both sides of a split, and this scorer does not, which leaves transfer a slightly
        LAXER test than minting. That is backwards and is owed a fix, but it is a SECOND change and would make this
        one unattributable."""
        n = len(exceptions)
        if n == 0:
            return None
        k = sum(1 for _, o in exceptions if o)
        base = _entropy_bits(n, k)
        if base == 0.0:
            return None                                      # already pure -> nothing to explain
        with self._lock:
            lib = list(self.library)                         # snapshot: Γ is shared and another game may be appending
        eligible = []
        for pred in lib:
            holds = [pred.holds(ctx) for ctx, _ in exceptions]
            if any(holds) and not all(holds):                # a non-trivial split of the CONTEXTS -- outcome-blind
                eligible.append((pred, holds))
        selection_cost = math.log2(len(eligible)) if eligible else 0.0
        if report is not None:
            report.update(library_size=len(lib), n_eligible=len(eligible), selection_cost_bits=selection_cost)
        best, best_gain = None, 1e-9                         # must STRICTLY compress
        for pred, holds in eligible:
            pos = [o for (_, o), h in zip(exceptions, holds) if h]
            neg = [o for (_, o), h in zip(exceptions, holds) if not h]
            l_given = _entropy_bits(len(pos), sum(pos)) + _entropy_bits(len(neg), sum(neg))
            gain = base - (l_given + pred.cost() + selection_cost)   # no SEARCH cost: φ is already in Γ
            if gain > best_gain:
                best, best_gain = pred, gain
        if report is not None:
            report["gain_bits"] = float(best_gain) if best is not None else 0.0
        return None if best is None else (best, float(best_gain))

    def explains(self, exceptions: List[Exception_]) -> Optional[Predicate]:
        """Does Γ (a promoted predicate) already account for these exceptions? If so, the new task is solved
        WITHOUT re-minting -- the transfer payoff. A promoted φ 'explains' the residual by the SAME two-part MDL
        criterion the minter uses -- it COMPRESSES it (L(R|φ)+L(φ) < L(R)) -- not by perfect purity (real
        residuals are noisy; the minter itself accepts imperfect splits that compress). No DSL search happens
        here: we only score the already-promoted library predicates, so this is transfer, not a re-mint. Returns
        the best-compressing promoted predicate, or None if none compresses this residual. Thin wrapper over
        `explains_scored` -- ONE scoring body, so the receipt's bits and the verdict can never disagree."""
        r = self.explains_scored(exceptions)
        return None if r is None else r[0]


def _pure(outcomes: List[bool]) -> bool:
    return len(set(outcomes)) <= 1
