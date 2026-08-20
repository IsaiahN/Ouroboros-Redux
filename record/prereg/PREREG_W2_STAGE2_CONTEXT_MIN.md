# PREREG — W2 STAGE 2 LEAD: CONTEXT MINIMISATION (2026-08-20)

**AUTHORITY:** the π-replay null (`PI_REPLAY_RESULT.md`) + Seat 4's "take it" on the
ordering. The library cannot apply anywhere: median context 976 cells licensing a 26-cell
change, minted right up against the binary half-board cap. **The repair: extent pays rather
than passes.**

## THE MECHANISM — and why it is provably conservative

**A cell that VARIED across successful firings of the same rule cannot be a precondition of
that rule.** The mint already requires multi-observation support before minting
(`SUPPORT_FULL`); each atom's key was seen on several frames. The minimised context is the
**intersection**: cells constant across all observed firings (plus the changed cells, plus
a stated neighbourhood ring). Dropping a varying cell is safe **by construction** — the
rule demonstrably fired with different values there. This is ablation with the evidence we
already have, not ablation needing new runs.

## THE BUILD (three parts, one builder)
1. **Mint-side, going forward:** at re-observation of an existing key, intersect the stored
   context with the new observation's context (same write-site family as the signature
   stamp). The stored context only ever shrinks.
2. **The extent premium, in the inequality:** `cost = 1.0 + changed + EXTENT_RATE ×
   retained_unchanged_cells` — extent moves from a binary clause into the bargain, so a
   precondition pays per cell it insists on. The half-board clause stays as the outer wall.
   EXTENT_RATE named, documented, module constant.
3. **Retro pass over the 2,009:** where the stream holds multiple observations of one key,
   minimise the stored atom by the same intersection; where it holds one, the atom keeps its
   context (no invented minimisation) and is marked `singleton` so the read can see the
   split. **Builder reports what evidence the stream actually holds before the retro pass
   runs — if observations are not recoverable, part 3 is stated absent, never approximated.**

## FALSIFIERS
- **F1 (absolute):** every minimised atom still matches and correctly predicts **every one
  of its own recorded observations**. One failure = that minimisation reverted.
- **F2 · KNOWN-NEGATIVE both ways:** a constructed rule whose effect depends on a distant
  constant cell RETAINS it (intersection keeps constants); a constructed rule observed with
  a varying distant cell DROPS it and still predicts.
- **F3 · THE PREMIUM PRICES:** with EXTENT_RATE > 0, a constructed wide-context candidate
  that previously minted is now rejected while its narrow twin mints; with EXTENT_RATE = 0
  behaviour is byte-identical to today (the dial proves the axis).
- **F4 · THE POINT (proctor's, not builder's):** re-run the π-replay with the pinned design
  (cohorts split, lp85 control) on the minimised library — match rates move off zero, and
  the fourth profile window shows breadth falling. Then and only then does the colour claim
  get its second hearing.
- **R4:** constructed multi-observation sets reproduce expected intersections exactly.

## UNDO
Original contexts are retained alongside minimised ones (`context_full` field) until Seat 3
rules on their disposal; the premium reverts by EXTENT_RATE = 0; the intersection-at-mint
reverts by removing one call site.

## THE FIFTH-LAYER EXPECTATION, held loosely
API cap → fabric read → commits → brute-force application → over-specified preconditions.
Each fix was real and relocated the bottleneck. **This one may be the floor — an atom that
can apply is the thing we actually wanted — but the expectation has been wrong four times,
and the fourth profile window gets the verdict, not the expectation.**


---

# THE RE-POINT AMENDMENT (2026-08-20, Seat 3: APPROVED with two conditions)

> *"The identity is the rule, not the situation it was seen in — a man is the same man
> across his roles, and keying on the surroundings makes one person into five."*

**THE BUILD:** map the mint's coarse signature (`mint._signature` — change-only, support
already accrues on it) → minted atom id. At every re-observation whose coarse signature
matches a minted atom, intersect the stored context with the observation's context. Forward
minimisation goes live at deploy; atom ids and the full-key dedup stay as they are — the
merge is of EVIDENCE onto one atom, not a rewrite of stream history.

**CONDITION 1, stated explicitly with the case that proves it (Seat 3: outcome-divergence
is information, not noise):**
- By construction, same-signature observations share the same change pattern — the
  signature hashes the change. So divergence cannot appear WITHIN a signature; it appears
  BETWEEN them: after intersection, atom A's loosened context can come to match a frame
  where a DIFFERENT outcome occurred (a different signature's territory).
- **The determinant-retention guarantee, two halves:**
  (a) A cell that is CONSTANT across A's firings is retained by intersection automatically
  — a determinant that never varied survives without any special case.
  (b) A cell that VARIED across A's firings (correctly dropped — A fired under several of
  its values) but whose OTHER values belong to a different rule is caught by the **CONFLICT
  CLAUSE**: when a minimised context matches an observation whose outcome differs from the
  atom's recorded change, the cells distinguishing the two FULL contexts (recoverable from
  `context_full` — this is what it is FOR) are REINSTATED in the minimised context, and the
  event is recorded (`ctx_conflict` marker). Divergence tightens; it never loosens.
- **THE PROVING CASE (gate test, constructed):** two rules with byte-identical change
  patterns distinguished only by a distant cell X — rule A fires at X∈{3,4}, rule B's
  different change occurs at X=5. Intersection over A's observations drops X (varied across
  firings, correctly). A conflicting observation at X=5 then arrives: the clause fires, X
  is reinstated from `context_full` with A's observed values, and A no longer matches X=5.
  *Sensitivity and specificity both asserted: the reinstatement happens on conflict, and
  does NOT happen on a same-outcome re-observation.*

**CONDITION 2 (the undo, affirmed):** `context_full` is retained on every touched atom
until minimised atoms have **circulated and paid** — the disposal ruling stays outstanding
at Seat 3 and nothing below it may delete the field.

**Seat 4's care note, adopted:** this is the first build in the sequence where the OBJECT
changes rather than the loop around it. The merge is recoverable (context_full + ctx_conflict
markers) and the falsifiers above are the deletion-path-grade guard it deserves.
