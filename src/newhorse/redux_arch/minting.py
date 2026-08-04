"""
minting.py -- redux-arch P2: RESIDUAL-DRIVEN PREDICATE MINTING (Region III, the novel core).

When the grammar's prediction fails, the residual hands us an EXCEPTION LIST: (before-state context, outcome)
pairs the grammar couldn't predict. The minter searches the typed DSL (dsl.py, before-state only) for a predicate
φ that PARTITIONS the exceptions into individually compressible sub-streams, and accepts it by the exact two-part
MDL code [Rissanen 1978; Quinlan & Rivest 1989]:

        L(φ) + L(R | φ)  <  L(R enumerated)          # mint iff φ costs fewer bits than the exceptions it removes

L(R) is the ideal code length of the outcomes under their empirical distribution (binary entropy × count); a
predicate that splits the exceptions into pure sub-streams drives L(R|φ) toward 0, and is accepted iff that saving
beats its own description length L(φ). This is one decision-stump split scored by MDL -- the smallest honest mint.

Guards (charter): (1) TAUTOLOGY is impossible by construction -- the DSL sees only the before-state, so no φ can
peek at the outcome. (2) NOISE mints nothing -- on random outcomes no split reduces entropy enough to beat its
cost, so the minter returns None. (3) φ is evaluable on the before-state -> a regularity, not a post-hoc fit.

This module is the fast LOCAL mint (in-episode). The slow ECHO->PROMOTE consolidation (P3) is cross-episode.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Iterable
import math
from .dsl import Context, Predicate, enumerate_predicates, LIB_ATOM_KIND

Exception_ = Tuple[Context, bool]                        # (before-state, outcome the grammar mispredicted)


def _entropy_bits(n: int, k: int) -> float:
    """Ideal code length (bits) to encode n outcomes with k positives under their empirical distribution.
    A pure set (k=0 or k=n) costs 0 -- nothing left to explain."""
    if n == 0 or k == 0 or k == n:
        return 0.0
    p = k / n
    return -n * (p * math.log2(p) + (1 - p) * math.log2(1 - p))


def _parametric_bits(n: int) -> float:
    """PARAMETRIC COMPLEXITY of one Bernoulli sub-stream: the bits it costs to encode the estimated parameter
    itself, ≈ (1/2)·log2(n·π/2) [Rissanen 1996 stochastic complexity; Grünwald 2007 §7 NML for the Bernoulli].

    WHY IT IS HERE AND WHY IT WAS NOT. `_entropy_bits` is the PLUG-IN code: it charges the data under the
    empirical distribution and charges NOTHING for having fitted that distribution to this very data. That code is
    optimistic by construction, and a split is optimistic TWICE (two sub-streams, two fitted parameters) where the
    baseline is optimistic once. The old code masked the gap with an oversized selection cost -- log2 of every
    CONSTRUCTED candidate, including ones that could not partition this residual at all. Removing that inflation
    without paying the real parameter cost let chance splits through: measured on matched noise, false mints went
    0.75% at n=30 to 2.25% at n=80 -- RISING WITH SAMPLE SIZE, which is the one direction that matters here,
    because pooling residuals is precisely a machine for raising n. With this term the rate is 0.25% / 0.55% /
    0.20% at n=30/80/200: flat, not climbing. The correction is exact-in-form rather than a tuned constant; there
    is no free parameter in it to tune."""
    return 0.5 * math.log2(n * math.pi / 2.0) if n > 0 else 0.0


@dataclass
class Mint:
    predicate: Predicate
    saved_bits: float                                    # L(R) - [L(φ) + L(R|φ)]  (>0 = a real compression)
    support: int                                         # how many exceptions it explained


def two_part_mdl(exceptions: List[Exception_], max_size: int = 2,
                 report: Optional[dict] = None, library: Iterable[Predicate] = ()) -> Optional[Mint]:
    """Search the DSL for the φ that best compresses the exception list by the two-part MDL code. Returns the
    accepted Mint (φ strictly beats the enumerated baseline) or None (nothing worth minting -- e.g. noise).

    `report`, if given, is filled in place with the candidate accounting (constructed / eligible / selection
    cost / baseline) so a caller can SEE the gate rather than infer it. The return type is unchanged.

    `library` (C21.15) admits ALREADY-PROMOTED φ into the atom universe as single conjuncts, so what the agent
    learned can be BUILT ON rather than only re-applied. Default EMPTY -> the pre-C21.15 search space and the
    pre-C21.15 score, exactly. There is NO price break for a library atom, so a library win is a real
    compression win and not a lowered bar; and a bigger Γ raises `n_eligible`, which raises `selection_cost`,
    so the library pays for its own size in the same currency as everything else."""
    n = len(exceptions)
    if n < 2:
        return None
    k = sum(1 for _, o in exceptions if o)
    entropy = _entropy_bits(n, k)                        # L(R enumerated): encode outcomes with the marginal…
    baseline = entropy + _parametric_bits(n)             # …plus the cost of having fitted that marginal (one param)
    if report is not None:
        report.update(n_exceptions=n, n_positive=k, baseline_bits=baseline,
                      n_constructed=0, n_eligible=0, selection_cost_bits=0.0)
    if entropy == 0.0:
        return None                                      # already pure -> no residual structure to mint from
    colours = set()
    for ctx, _ in exceptions:
        colours.add(ctx.focus_colour)
        if ctx.intended_colour is not None:
            colours.add(ctx.intended_colour)             # so INTENDED_COLOUR atoms cover the occupying colours
    preds = enumerate_predicates(colours, max_size=max_size, library=library)
    # ELIGIBILITY, computed from the BEFORE-STATE CONTEXTS ONLY (never the outcomes): a predicate that is
    # constant across this exception list partitions nothing and was structurally incapable of being selected
    # here, whatever the outcomes turn out to be. Such a candidate is not in the hypothesis class we actually
    # searched, so charging for it inflates the selection cost against a mint that never competed with it.
    # Because eligibility reads ctx and not o, the TAUTOLOGY guard survives as a type property: nothing in this
    # filter can leak the outcome into φ's admission.
    eligible = []
    for pred in preds:
        holds = [pred.holds(ctx) for ctx, _ in exceptions]
        if any(holds) and not all(holds):                # a non-trivial split of the CONTEXTS
            eligible.append((pred, holds))
    # L(φ) must pay to NAME which predicate we picked out of that class -- log2|H_eligible| bits (the
    # multiple-hypothesis / search-cost correction). Without it, with enough candidates SOME split reduces
    # entropy by chance on finite noise; with it, a chance saving of a few bits can't clear the selection cost,
    # while a real rule (tens of bits) clears it easily. This is what makes NOISE mint nothing.
    selection_cost = math.log2(len(eligible)) if eligible else 0.0
    if report is not None:
        report.update(n_constructed=len(preds), n_eligible=len(eligible),
                      selection_cost_bits=selection_cost)
        # THE LIBRARY'S OWN DENOMINATOR. `n_eligible` alone cannot say whether the library reached the contest:
        # a Γ that is offered but whose every φ is constant across these contexts is filtered out by the
        # eligibility test above and leaves no trace. Counted only when a library was actually passed, so the
        # key's ABSENCE means "no library offered" and a 0 means "offered and none of it could split".
        if library:
            report["n_eligible_library"] = sum(
                1 for pred, _h in eligible if any(a.kind == LIB_ATOM_KIND for a in pred.atoms))
            # ...AND THE RUNG BELOW IT. `n_eligible_library = 0` has TWO causes that look identical from here:
            # the library φ entered the universe and were CONSTANT across these contexts (a fact about the
            # residual), or they never entered it at all because `atom_universe`'s duplicate guard dropped every
            # one (a fact about the WIRING). Counted from the size-1 predicates, where each admitted library
            # atom appears exactly once, so the two causes are separable on the record instead of by argument.
            report["n_library_admitted"] = sum(
                1 for p in preds if len(p.atoms) == 1 and next(iter(p.atoms)).kind == LIB_ATOM_KIND)
    best: Optional[Mint] = None
    best_total = baseline                                # total (incl. selection cost) must STRICTLY beat baseline
    for pred, holds in eligible:
        pos = [o for (_, o), h in zip(exceptions, holds) if h]
        neg = [o for (_, o), h in zip(exceptions, holds) if not h]
        # L(R|φ): each sub-stream pays its own data cost AND its own fitted parameter. A split buys two
        # parameters where the baseline bought one -- that difference is what a real rule must earn back.
        l_given = (_entropy_bits(len(pos), sum(pos)) + _parametric_bits(len(pos))
                   + _entropy_bits(len(neg), sum(neg)) + _parametric_bits(len(neg)))
        total = pred.cost() + selection_cost + l_given   # L(φ)=intrinsic+selection , plus L(R|φ)
        if total < best_total - 1e-9:
            best_total = total
            best = Mint(predicate=pred, saved_bits=baseline - total,
                        support=sum(1 for (ctx, o), h in zip(exceptions, holds) if h == o))
    if report is not None:
        report.update(minted=best is not None,
                      best_saved_bits=(best.saved_bits if best is not None else 0.0))
    return best


@dataclass
class MintingEngine:
    """The fast local mint wired to the residual: buffer the exceptions, mint when enough have accrued.
    A record with a consumer -- `minted` is the in-episode grammar growth Γ ← Γ ∪ φ (writeback is P3's job)."""
    min_exceptions: int = 20
    max_size: int = 2
    buffer: List[Exception_] = field(default_factory=list)
    minted: List[Mint] = field(default_factory=list)
    log: List[str] = field(default_factory=list)

    def observe(self, ctx: Context, outcome: bool) -> None:
        """Bank one residual exception (a transition the grammar could not predict)."""
        self.buffer.append((ctx, bool(outcome)))

    def maybe_mint(self, report: Optional[dict] = None) -> Optional[Mint]:
        """Trigger: enough exceptions accrued and R won't compress under Γ -> attempt an MDL mint."""
        if len(self.buffer) < self.min_exceptions:
            return None
        mint = two_part_mdl(self.buffer, max_size=self.max_size, report=report)
        if mint is not None:
            self.minted.append(mint)
            self.log.append("MINT  φ=(%s)  saved=%.1f bits  support=%d/%d"
                            % (mint.predicate, mint.saved_bits, mint.support, len(self.buffer)))
        else:
            self.log.append("NO-MINT  %d exceptions won't compress (noise or already pure)" % len(self.buffer))
        return mint
