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
from typing import Callable, Dict, List, Optional, Set, FrozenSet, Tuple
from .dsl import Predicate, Context, atom_family, predicate_family
from .minting import Mint, two_part_mdl, Exception_, _entropy_bits
from .residual_bank import family_key as _family
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
    sign_min_families: int = 2                                  # corroboration bar for a TRANSFERABLE sign (see `sign`)
    library: List[Predicate] = field(default_factory=list)      # Γ's promoted predicates (the grown vocabulary)
    _tasks_by_key: Dict[FrozenSet[str], Set[str]] = field(default_factory=dict)
    _pred_by_key: Dict[FrozenSet[str], Predicate] = field(default_factory=dict)
    # key -> family -> [n_true_side, k_true_side, n_false_side, k_false_side]. THE SIGN LIVES HERE, NOT IN Γ's list.
    _split_by_key: Dict[FrozenSet[str], Dict[str, List[int]]] = field(default_factory=dict)
    log: List[str] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    def observe_mint(self, task_id: str, mint: Mint,
                     exceptions: Optional[List[Exception_]] = None) -> bool:
        """Register that `task_id` minted this predicate. Promote it into Γ once it has echoed on
        `echo_threshold` distinct tasks. Returns True iff this call caused a promotion.

        `exceptions` is the residual φ was minted from. It is OPTIONAL and it is the only way a SIGN ever gets into
        Γ. Without it a promotion carries a partition and no preference: "these two groups of steps differ" is not
        "prefer this group", and an audit of the promoted library (`tools/audit_gamma.py`) measured that a shared Γ
        built without it cannot yield a single decision no matter what else is wired. Passing it banks the outcome
        SPLIT per FAMILY -- evidence, not a conclusion; the sign is derived on read, under a corroboration bar."""
        key = _key(mint.predicate)
        with self._lock:
            self._pred_by_key[key] = mint.predicate
            if exceptions:
                fam = _family(str(task_id))
                slot = self._split_by_key.setdefault(key, {}).setdefault(fam, [0, 0, 0, 0])
                for ctx, o in exceptions:
                    i = 0 if mint.predicate.holds(ctx) else 2
                    slot[i] += 1
                    slot[i + 1] += 1 if o else 0
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

    # ---- THE SIGN: which side of a promoted split is the side to ACT ON ---------------------------------------
    def _delta(self, key: FrozenSet[str], family: str) -> Optional[float]:
        """P(outcome | φ) - P(outcome | ¬φ) on ONE family's banked split, or None if either side is empty."""
        s = self._split_by_key.get(key, {}).get(family)
        if not s or s[0] == 0 or s[2] == 0:
            return None
        return (s[1] / s[0]) - (s[3] / s[2])

    def sign(self, pred: Predicate, exclude_game: Optional[str] = None,
             min_families: Optional[int] = None) -> Optional[int]:
        """+1 / -1 if the families that minted φ AGREE on which side of its split carries the outcome; None if they
        do not agree, or if too few of them can vote.

        ★ WHY THIS IS NOT JUST "TAKE THE POOLED AVERAGE", AND WHY THE BAR IS TWO FAMILIES.
        The offline audit found exactly one promoted φ that both ranks actions and echoed across two families --
        INTENDED_FREE -- and its sign REVERSES between them: on wa30 a free cell ahead means the focus moves
        (+0.70), on re86 it means the focus does NOT move (-0.98). Pooled, those average to a confident-looking
        number that is right on one game and maximally wrong on the other. So the echo gate certifies that a
        DISTINCTION recurs; it does not certify that the distinction MEANS the same thing, and the sign is where
        that difference becomes a wrong action instead of a wrong sentence. In the one case we could check, a
        single-family sign was demonstrably unreliable -- hence corroboration, not majority vote: every voting
        family must agree, and one dissent kills it. A killed sign is the honest output, not a failure.

        `exclude_game` drops the family of the game being ADVISED, so a rule can never be transferred to itself:
        φ signed only by the game it is about is not transfer, it is memory."""
        need = self.sign_min_families if min_families is None else int(min_families)
        key = _key(pred)
        with self._lock:
            fams = sorted(self._split_by_key.get(key, {}))
            drop = _family(str(exclude_game)) if exclude_game else None
            deltas = [d for f in fams if f != drop
                      for d in (self._delta(key, f),) if d is not None and d != 0.0]
        if len(deltas) < need:
            return None                                  # not corroborated -- too few families can speak
        signs = {1 if d > 0 else -1 for d in deltas}
        return signs.pop() if len(signs) == 1 else None  # any dissent -> no transferable sign

    def directives(self, game_id: str, min_families: Optional[int] = None) -> List[Tuple[Predicate, int]]:
        """The promoted φ this game did NOT mint, that carry a corroborated sign: (φ, +1/-1). THIS IS THE ONLY
        THING IN Γ THAT AN ACTION-SELECTION SITE MAY READ. `foreign` guarantees the transfer is across games;
        `sign` guarantees the advice has a direction and that the direction survived every family that could
        check it. Returns [] when Γ has nothing to say, which is the expected answer for a long time yet."""
        out: List[Tuple[Predicate, int]] = []
        for p in self.foreign(game_id):
            s = self.sign(p, exclude_game=game_id, min_families=min_families)
            if s is not None:
                out.append((p, s))
        return out

    def sign_report(self, game_id: str) -> Dict[str, int]:
        """What Γ would offer this game at each corroboration bar -- for the receipt, so a sweep that produces ZERO
        directives still says WHY it was zero (nothing foreign / nothing signed / signs reversed) instead of being
        a silence that reads the same as an unwired organ."""
        foreign = self.foreign(game_id)
        at1 = self.directives(game_id, min_families=1)
        at2 = self.directives(game_id, min_families=2)
        with self._lock:
            have_split = sum(1 for p in foreign if self._split_by_key.get(_key(p)))
        return dict(library=len(self.library), foreign=len(foreign), foreign_with_split=have_split,
                    signed_at_1_family=len(at1), signed_at_2_families=len(at2))

    def reset(self) -> None:
        """Empty Γ, the echo clock, and the banked splits. FOR TEST ISOLATION ONLY (see tests/conftest.py). Γ is a process-wide
        singleton now, so without a per-test reset one test's synthetic promotion becomes another test's library
        and `explains` starts answering from a φ that test never minted -- the residual bank's contamination
        failure, one layer up. There is no call site for this in the build, and there must never be one: a Γ that
        the agent can clear is a Γ the agent can launder."""
        with self._lock:
            self.library.clear()
            self._tasks_by_key.clear()
            self._pred_by_key.clear()
            self._split_by_key.clear()
            self.log.clear()

    def explains_scored(self, exceptions: List[Exception_], report: Optional[Dict[str, float]] = None,
                        branch: Optional[Callable[[str], None]] = None,
                        phi_branch: Optional[Callable[[str], None]] = None,
                        kind_branch: Optional[Callable[[str], None]] = None):
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
        one unattributable.

        ★ `branch` IS THE REUSE FUNNEL'S PEN, AND IT IS A CALLABLE ON PURPOSE. Every way out of this function is a
        different verdict on Γ, and a caller that only sees `None` cannot tell "no promoted φ even applies to these
        contexts" from "φ applied and did not pay". Those are a grain failure and an architecture failure. Each way
        out therefore writes its OWN string literal at its OWN branch. It is passed the ledger's bound method rather
        than a dict so there is no second carrier that could be built somewhere the wiring does not reach -- the
        defect that made the click branch read a residue of 126 for a beat. Scoring is untouched: this writes a
        name and returns exactly what it returned before.

        ★ `explains_no_eligible` IS ITSELF AN EXIT NAME SPANNING MORE THAN ONE STATE, AND THIS BEAT SPLITS IT.
        Ten of ten MINTED_UNUSED segments across three sweeps resolved here, so "no promoted φ splits these
        contexts" is now the load-bearing sentence in the whole chain -- and it covers two states with OPPOSITE
        fixes. A φ is ineligible either because it holds on NO fresh context (it is ABSENT here: the predicate
        describes something this board does not contain, which is a GRAIN fault at link 1, in perception's
        vocabulary) or because it holds on EVERY fresh context (it is UNIVERSAL here: the predicate is true but
        vacuous, which says the CONTEXTS are degenerate and points UPSTREAM into the residual builder). Those are
        mutually exclusive and jointly exhaustive for an ineligible φ, because `any(h) and not all(h)` is false
        exactly when `not any(h)` or `all(h)`. So the attempt is charged to one of four literals -- empty library,
        all-absent, all-universal, mixed -- at four separate returns, and `phi_branch` additionally tallies the
        PER-φ classification so a `mixed` attempt is not a dead end. Deciding dominance by a threshold was
        rejected: a threshold is a name somebody chose, which is the defect this whole funnel exists to undo.

        `kind_branch` goes one level finer still, on the SAME denominator as `phi_branch` (a φ scanned and
        rejected) but answering WHICH VOCABULARY was absent rather than WHETHER it was. It writes two orthogonal
        splits over the absent φ -- the COMPOSITION of the dead predicate (`absent_kind_*`: colour literals only,
        relational atoms only, or a conjunction spanning both) and the CAUSE of its death (`absent_cause_*`:
        which family's atom was ITSELF dead on these contexts, or `none` when every atom lives and only the
        conjunction fails) -- plus the composition of the UNIVERSAL φ as the base rate the absent split has to be
        read against. It is a bookkeeping split of the existing atom registry; no atom, gate, threshold or
        detector is added, and nothing in the search or the MDL score reads any of it."""
        _b = branch if branch is not None else (lambda _name: None)
        _p = phi_branch if phi_branch is not None else (lambda _name: None)
        _k = kind_branch if kind_branch is not None else (lambda _name: None)
        n = len(exceptions)
        if n == 0:
            _b("explains_no_exceptions")
            return None
        k = sum(1 for _, o in exceptions if o)
        base = _entropy_bits(n, k)
        if base == 0.0:
            _b("explains_already_pure")
            return None                                      # already pure -> nothing to explain
        with self._lock:
            lib = list(self.library)                         # snapshot: Γ is shared and another game may be appending
        eligible = []
        n_absent = n_universal = 0                           # WHY each rejected φ was rejected, charged at the loop
        for pred in lib:
            holds = [pred.holds(ctx) for ctx, _ in exceptions]
            if any(holds) and not all(holds):                # a non-trivial split of the CONTEXTS -- outcome-blind
                eligible.append((pred, holds))
            elif not any(holds):                             # φ is ABSENT on this board -- a grain fault at link 1
                n_absent += 1
                _p("phi_absent")
                _k("absent_kind_" + predicate_family(pred))  # COMPOSITION: what the dead φ was MADE OF
                # ...and CAUSE, which is a different claim. A conjunction can hold nowhere even though every one
                # of its atoms holds somewhere -- the atoms simply never co-occur. That state ('none') is an
                # INTERACTION absence and its repair is the conjunction arity, not the vocabulary. Charging the
                # composition alone would silently rename it as a vocabulary fault. Each atom is evaluated over
                # the SAME contexts, which is the only place the fact exists; nothing else is consulted.
                dead = {atom_family(a) for a in pred.atoms
                        if not any(a.holds(ctx) for ctx, _ in exceptions)}
                if not dead:
                    _k("absent_cause_none")                  # every atom lives; the CONJUNCTION never co-occurs
                elif dead == {"colour"}:
                    _k("absent_cause_colour")
                elif dead == {"relational"}:
                    _k("absent_cause_relational")
                elif "unregistered" in dead:
                    _k("absent_cause_unregistered")          # a wiring fault, named rather than folded in
                else:
                    _k("absent_cause_both")
            else:                                            # φ holds EVERYWHERE -- true but vacuous; look upstream
                n_universal += 1
                _p("phi_universal")
                _k("universal_kind_" + predicate_family(pred))   # the BASE RATE the absent split is read against
        selection_cost = math.log2(len(eligible)) if eligible else 0.0
        if report is not None:
            report.update(library_size=len(lib), n_eligible=len(eligible), selection_cost_bits=selection_cost,
                          n_phi_absent=n_absent, n_phi_universal=n_universal)
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
        # THE TWO WAYS TO LOSE ARE NAMED SEPARATELY, AT THEIR OWN BRANCHES. One `return None` covering both would be
        # an exit name spanning two branches, which is not an attribution. `explains_no_eligible` means Γ held
        # nothing that non-trivially splits THESE contexts -- the library never got to compete, so the stall is
        # about grain/applicability and NOT about the architecture. `explains_no_compress` means eligible φ existed
        # and none strictly compressed after paying its own cost plus log2(eligible) -- that one is the reading
        # MINTED_UNUSED has always claimed to be. The no-eligible side is split FOUR ways, each at its own return,
        # because "nothing applied" covers an empty library, a library that is absent here, a library that is
        # vacuously true here, and a library that is some of each -- and those have different fixes in different
        # links. No threshold and no dominance rule: the four are exhaustive and exclusive by construction.
        if best is None:
            if eligible:
                _b("explains_no_compress")
            elif not lib:
                _b("explains_no_eligible_empty")             # not reachable from the live site, which guards on Γ
            elif n_absent and n_universal:
                _b("explains_no_eligible_mixed")
            elif n_absent:
                _b("explains_no_eligible_absent")            # GRAIN: the vocabulary does not describe this board
            else:
                _b("explains_no_eligible_universal")         # UPSTREAM: the fresh contexts do not vary
            return None
        _b("explains_transfer")
        return (best, float(best_gain))

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
