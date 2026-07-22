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
from typing import List, Tuple, Optional
import math
from .dsl import Context, Predicate, enumerate_predicates

Exception_ = Tuple[Context, bool]                        # (before-state, outcome the grammar mispredicted)


def _entropy_bits(n: int, k: int) -> float:
    """Ideal code length (bits) to encode n outcomes with k positives under their empirical distribution.
    A pure set (k=0 or k=n) costs 0 -- nothing left to explain."""
    if n == 0 or k == 0 or k == n:
        return 0.0
    p = k / n
    return -n * (p * math.log2(p) + (1 - p) * math.log2(1 - p))


@dataclass
class Mint:
    predicate: Predicate
    saved_bits: float                                    # L(R) - [L(φ) + L(R|φ)]  (>0 = a real compression)
    support: int                                         # how many exceptions it explained


def two_part_mdl(exceptions: List[Exception_], max_size: int = 2) -> Optional[Mint]:
    """Search the DSL for the φ that best compresses the exception list by the two-part MDL code. Returns the
    accepted Mint (φ strictly beats the enumerated baseline) or None (nothing worth minting -- e.g. noise)."""
    n = len(exceptions)
    if n < 2:
        return None
    k = sum(1 for _, o in exceptions if o)
    baseline = _entropy_bits(n, k)                       # L(R enumerated): encode outcomes with the marginal
    if baseline == 0.0:
        return None                                      # already pure -> no residual structure to mint from
    colours = set()
    for ctx, _ in exceptions:
        colours.add(ctx.focus_colour)
        if ctx.intended_colour is not None:
            colours.add(ctx.intended_colour)             # so INTENDED_COLOUR atoms cover the occupying colours
    preds = enumerate_predicates(colours, max_size=max_size)
    # L(φ) must pay to NAME which predicate we picked out of the hypothesis class -- log2|H| bits (the
    # multiple-hypothesis / search-cost correction). Without it, with enough candidates SOME split reduces
    # entropy by chance on finite noise; with it, a chance saving of a few bits can't clear the selection cost,
    # while a real rule (tens of bits) clears it easily. This is what makes NOISE mint nothing.
    selection_cost = math.log2(len(preds)) if preds else 0.0
    best: Optional[Mint] = None
    best_total = baseline                                # total (incl. selection cost) must STRICTLY beat baseline
    for pred in preds:
        pos = [o for ctx, o in exceptions if pred.holds(ctx)]
        neg = [o for ctx, o in exceptions if not pred.holds(ctx)]
        if not pos or not neg:
            continue                                     # a trivial split partitions nothing
        l_given = (_entropy_bits(len(pos), sum(pos)) + _entropy_bits(len(neg), sum(neg)))
        total = pred.cost() + selection_cost + l_given   # L(φ)=intrinsic+selection , plus L(R|φ)
        if total < best_total - 1e-9:
            best_total = total
            best = Mint(predicate=pred, saved_bits=baseline - total,
                        support=sum(1 for ctx, o in exceptions if pred.holds(ctx) == o))
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

    def maybe_mint(self) -> Optional[Mint]:
        """Trigger: enough exceptions accrued and R won't compress under Γ -> attempt an MDL mint."""
        if len(self.buffer) < self.min_exceptions:
            return None
        mint = two_part_mdl(self.buffer, max_size=self.max_size)
        if mint is not None:
            self.minted.append(mint)
            self.log.append("MINT  φ=(%s)  saved=%.1f bits  support=%d/%d"
                            % (mint.predicate, mint.saved_bits, mint.support, len(self.buffer)))
        else:
            self.log.append("NO-MINT  %d exceptions won't compress (noise or already pure)" % len(self.buffer))
        return mint
