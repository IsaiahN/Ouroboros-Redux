# PREREG — COMPOSER STAGE 2: THE ENABLES INDICES (2026-08-21)

Cleared in full by Seat 3. Stage 1 (the factoring) is live at `ce84040`. This stage builds
the two edges that make composition *findable* rather than merely priceable.

## THE POSITION→ANCHOR TRANSLATION, SPECIFIED BEFORE CODE
(Seat 4's guard: the cross-shelf reach is a design question wearing construction's clothes
until this is written down. It is written down here, and the representation choice is
stated, not buried.)

**The three facts and their types:**
- BODY delta: `(dr, dc)` — a change in the AVATAR's position. Frame-relative, not absolute.
- Γ atom precondition: a context patch that must match **somewhere**; its anchor is a
  frame CELL `(r, c)` where the patch's top-left sits. Absolute, per-frame.
- The avatar's own position `v = (r_v, c_v)`: read from the self-locus/BODY slot, which is
  the ONLY component that knows where "here" is.

**The translation, stated:** a BODY chain `Σ(dr_i, dc_i) = (Dr, Dc)` moves the avatar from
`v` to `v + (Dr, Dc)`. A Γ atom is *reachable-and-anchored* iff there exists an anchor
`a ∈ A` (its matching anchors in the current frame) and a BODY chain such that the atom's
**click/act cell** lands on `a`. **The composer therefore needs the atom's ACT-RELATIVE
OFFSET: for a click atom, the offset from the anchor to the clicked cell** — which is
derivable at mint time from the recorded action's coordinates minus the matched anchor's
origin, and which today is NOT stored.

**THE REPRESENTATION CHOICE, NAMED:** we store, per atom, `act_offset = (act_cell −
anchor_origin)` when the minting action carried coordinates; absent otherwise. This is a
new derived field (same discipline as psig: total, backfill-on-read, never a migration).
**Without it the cross-shelf edge cannot be computed at all** — this is the design question
the guard was watching for, and its answer is a stored offset rather than a new algorithm.
*If `act_offset` proves underivable for most atoms (coordinates not recorded on the mint
path), stage 2 ships the within-Γ edge only and the cross-shelf edge is reported BLOCKED
with the missing-writer named — a finding, not a workaround.*

## THE BUILD
1. **The within-Γ ENABLES edge**: A→B iff A's `written` colours (psig) intersect B's
   required palette AND B's requirement is not satisfiable in the current frame without A.
   A sparse directed graph, computed from stored signatures, no execution.
2. **`act_offset` derivation + stamping** (the translation above).
3. **The cross-shelf reach query**: given a Γ atom, its matching anchors `A`, and the
   avatar at `v`, return the cheapest BODY chain landing the act-cell on some `a ∈ A` —
   shortest path over the BODY delta algebra (per-action `(dr,dc)` from the bank/action
   book), **masked by the frontier book's fatal cells**. Returns the chain and its cost, or
   None (unreachable), never a guess.

## FALSIFIERS
- **F1 · the translation is exact**: constructed atom + known avatar position + known
  anchors → the returned chain, applied as deltas, places the act-cell exactly on the
  anchor. Off-by-one in either axis fails.
- **F2 · the mask is honest** (design F4, promoted): an anchor whose only path crosses a
  frontier-book fatal cell yields None; clearing the mark yields the chain.
- **F3 · the algebra proposes, simulation decides** (Seat 4's amendment): the returned
  chain is marked UNVERIFIED; a constructed world where a wall blocks a delta-sum path
  shows the chain proposed and the simulation rejecting it — the cheap shelf never returns
  a verified-looking wrong chain.
- **F4 · the within-Γ edge prunes and never lies**: an atom whose requirement A cannot
  manufacture is absent from A's edge list; one that A does manufacture is present; an
  underivable pair produces NO EDGE (never a false edge).
- **R4**: constructed graphs reproduce expected edge sets and cheapest chains exactly.
- **KNOWN-NEGATIVE on the index**: an empty Γ yields an empty graph, not an exception.

## THE MULTI-PRIOR-UNION LIMITATION (carried from stage 1, per Seat 4)
Establishment credits only single-prior full-containment alignments; two steps jointly
establishing a third's context are uncredited, so the tightest three-step chains are
systematically overpriced. **Trigger to revisit: circulating composites clustering just
above admission bars.** Stated here so it is watched, not rediscovered.

## UNDO
Both indices are derived state, rebuildable from Γ + the bank; the reach query is a pure
function. Remove the call sites; nothing stored is lost.
