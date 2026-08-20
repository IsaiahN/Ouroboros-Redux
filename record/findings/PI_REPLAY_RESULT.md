# THE π-REPLAY RESULT (2026-08-20): THE FALSIFIER DID NOT FIRE — AND THE REASON IS BIGGER THAN COLOUR

Run on recordings only; HOLD held; no swarm involved. Design pinned before the run
(cohorts split, lp85 as control) per Seat 3.

## Part 1 · The pinned result, reported as pinned

Atoms replayed against the NEXT level's recorded boards, identity-match vs permutation-match,
cohorts separate:

| game | role | tested | T: id → π | A: id → π | π-only gain |
|---|---|---|---|---|---|
| cn04 | RECOLOUR | 18 | 0 → 0 | 0 → 0 | **0** |
| m0r0 | RECOLOUR | 151 | 0 → 0 | 0 → 0 | **0** |
| sp80 | RECOLOUR | 1 | — | 1 → 1 | **0** |
| lp85 | **CONTROL** | 11 | 0 → 0 | 0 → 0 | **0** |
| ar25 / cd82 / ft09 / r11l | — | 190 | 0 → 0 | 0 → 0 | **0** |

**THE FALSIFIER DID NOT FIRE.** Zero π-only gain in every game, both cohorts, including all
three recolouring games. **The control did its job**: no differential between lp85 and the
recolouring games means no mechanism confirmation — exactly the pre-rejection condition Seat
3 pinned, applied to a null rather than to a false positive.

**Per the pre-commitment, the relational signature does NOT become stage 2's lead.** The
colour census (`COLOUR_INVARIANT_READ`) stands as true and remains unspent: palettes really
do rotate in three games, and `colour_delta` really is recorded-and-unread on 100% of atoms.
But colour repair is **downstream of a binding constraint discovered by this replay**.

## Part 2 · Why nothing matched — the constraint under the constraint

The replay's null forced the question *why does an atom never match any board but its own?*
Measured over all 2,009 atoms:

- **Median context: 976 cells. 75% of atoms carry contexts ≥512 cells** (a quarter-board or
  more); max 2,035.
- **Median change: 26 cells — a 3.9% density inside that context.**
- The change's own bounding box **equals** the context (1×): changes are **sparse and
  scattered across the whole region**, not a small edit with padding.
- **96% of changes are position-dependent** (only 4% are fully explained by a colour rule),
  so the extent is not compressible into a colour law.
- And `apply_effect` requires **every context cell to match**, zeros included.

> **An atom demands that ~976 cells be identical in order to license a change to ~26 of
> them. It is a dense snapshot of a sparse rule. It can therefore match essentially nothing
> but the frame it was minted from.**

**This is the answer to the question that has been open since g7 first read zero.** The
planner never returns a plan because the library is structurally unable to apply anywhere:
not a search bug, not a cost problem, not a colour problem — **an over-specified
representation**. It also explains the 65% rederivation bill directly (nothing transfers
because nothing can match) and it explains why the index's pruning was safe but small (few
candidates are excluded by palette/dims when nearly all are excluded by extent anyway).

**And it names the guard precisely — I checked the code before claiming, and the first
version of this claim was too strong.** Extent IS gated, but in two separable pieces
(`mint.py:255-265`):
- **The MDL inequality is extent-blind**: `cost = 1.0 + changed` against
  `R = RESIDUAL_CELL_COST × changed + UNEXPLAINED_PREMIUM`. **Context extent appears on
  neither side.** A 9-cell precondition and a 2,000-cell precondition for the same effect
  cost exactly the same.
- **A separate binary clause does cap it**: `bbox_area < MAX_BBOX_BOARD_FRACTION (0.5) ×
  board_area` — so a precondition may occupy **up to half the board** and still mint.
  Observed max context is **2,035 cells against a 2,048 ceiling** — the cap is binding at
  the top end, and atoms are being minted right up against it.

**So the defect is not an absent guard but a loose one on a blind axis:** the inequality
that does the pricing cannot see extent, and the clause that can see extent only asks a
yes/no question at half the board. **The repair is to make extent PAY rather than merely
PASS** — put it in the inequality, where the same margin logic that prices changed cells can
price required-but-unchanged ones.

## Part 3 · What stage 2 should be instead

**CONTEXT MINIMISATION becomes stage 2's lead** — the MDL bargain applied to the
precondition rather than to the atom count. Shape: retain only the cells the change
demonstrably depends on (plus a stated neighbourhood), verified by the ablation pattern the
mastery gate already uses — *an atom that still predicts with cells removed did not need
them.* The colour work (relational signature + `colour_delta` anchor) stays queued behind
it, where its value can actually be tested: **once contexts are small enough to match at
all, colour labels become the next binding constraint in the three recolouring games — and
lp85 remains the control for that test.**

Order proposed to Seat 3: (1) context minimisation prereg + its falsifier, (2) re-run this
exact π-replay afterward — the same script, the same cohorts, the same control. If the
colour gain appears then, the colour claim is confirmed by a read whose design was pinned
today, before any of this was known.

## Method note
Three instrument corrections en route, all caught by zero-owes-a-constructed-presence:
record nesting (`atom` sub-object), per-agent path segment, and whole-frame vs windowed
matching. The sensitivity check that unblocked it — *an atom must match its own source
frame* — passed, which is what licensed reading the remaining zeros as data.
