# PREREG — W2 FIRST DELIVERABLE: THE APPLICABILITY INDEX (2026-08-20)

**STATUS: DRAFTED, AWAITING SEAT 3's CLEARANCE.** W1 is cleared; W2 is not yet. This exists so
the clearance starts a build, not a meeting. **Agent code — a firewalled builder writes it.**
Brief is mechanics-only.

## THE BEFORE-NUMBER (from `D5_PROFILE_RESULT.md`, the reason this prereg can exist)
420-second window on cn04: **97.6% of runtime in `plan_to_identity`, 95.3% in `apply_effect`
(47,418 calls), 77.7M `numpy.ndarray.all` comparisons** — every atom applied at every anchor,
no pruning. Five planner calls, ~80s each, zero plans returned, ever (g7 = 0).

## THE BUILD
An **applicability index over Γ**, written at mint/compose time (the same write-sites the
provenance tags will use — build once, two consumers):
- per atom: an **anchor signature** — context-patch dimensions, palette set, and a cheap
  content key (e.g. the patch's nonzero mask hash at its native size)
- per planner query: compute the frame's signature grid ONCE, then **prune to the candidate
  set whose signatures can possibly match** before any `apply_effect` call
- the index is **derived state**: rebuildable from the atoms stream at any time, so it can
  never be the sole holder of anything (retention rules untouched)

**Scope guard:** no change to `apply_effect`'s semantics, no change to which plans are legal —
**only to which candidates are evaluated.** An atom the index prunes that WOULD have applied
is the defect class to gate against (F3).

## FALSIFIERS
- **F1 · THE SHARE COLLAPSES.** Re-run the same 420s dump-on-timer window on cn04
  post-index: the `apply_effect` cumulative share drops from ~95% to a minority share, or the
  same five planner calls complete in seconds. *Fails if the share holds* — and the failure
  **names its successor**: the cost is per-application work, the fix is vectorisation, a
  different build (pre-committed, not a post-hoc save).
- **F2 · NOTHING LEGAL IS LOST.** On a recorded set of planner queries, the pruned candidate
  set contains **every** atom the unpruned search would have applied (superset check, exact).
  *Fails if one applicable atom is pruned* — an index that loses legal candidates is worse
  than no index.
- **F3 · KNOWN-NEGATIVE.** An atom whose context cannot occur in the frame (wrong palette,
  wrong dims) is pruned; an atom hand-placed to match is retained. Both directions on
  constructed cases before the first live read.
- **F4 · THE INDEX IS HONEST ABOUT ITS OWN COST.** Index build + query time is measured in
  the same profile; if index overhead exceeds the savings, that is a result, not a tuning
  problem.

## UNDO
The index is derived and consulted at one call site in the planner. Remove the consult; the
search reverts to exhaustive. Nothing stored is destroyed; the stream records remain.

## WHAT THIS DOES NOT CLAIM
It does not make g7 fire. **It makes the search cheap enough that its emptiness becomes a
readable fact instead of a 95% tax** — whether the planner then finds plans, or is shown to
be structurally unable to, is the next question and it will finally be affordable to ask.
