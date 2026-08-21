# PREREG — W2c: THE PLANNER RETAINS WHAT IT LEARNS (2026-08-21) — BRIEFED

Seat 3: *"Every call discovers things about the environment, the objects, and what applies
where — and discards all of it on return. That is the spent-discriminator shape again...
Retention means the next call starts from what the last one found rather than from nothing."*

**THE GENUS this closes: produced-and-destroyed-at-production.** The binder re-earned every
binding per cycle until `binding_stale`; the planner computes `memo[(aid, key)]` (planner.py:234)
and drops it on return; the composer re-scans anchors, re-simulates seams and rebuilds the
enabler index per attempt. Same shape, same fix: retention with a level-scoped clear. The
storage-layer twin (window 5: produced-once, parsed-many in `fabric._read_stream`) is the
ADJACENT genus and is NOT this build — `_candidate_ids`' and the composer's pool queries stay
as they are; this prereg retains only what `apply_effect`-grade work produces.

## THE NUMBERS (windows 1–5, `F1_VERDICT_AND_SHADOW_TEST.md`) — what the bounds derive from
- applications per planner call: 9.5k (w1) → 5.0k (w2, index) → 8.3k (w3, widened back).
- planner calls per 420s window: 5 → 10 → 17 pre-W2b; **4 per full generation** post-W2b (w4,
  56s); absent from the top in w5. `_MAX_NODES` = 2000, `_MAX_DEPTH` = 8 (unchanged here).
- Every memo entry is one application, so a call inserts ≤ 8.3k entries; a generation ≤ ~33k.
- Why (a) alone does not pay live: GATE B already skips the exact repeat of an unchanged world.
  The live repeat is a CHANGED board — the old root's child, or the old root plus one action's
  cell diff — so the payoff is the shared subtree and the band negative (b), not a replay.

## THE BUILD — one store, `engines/egocentric/retention.py`, OWNED by the scheduler
The store is a field of `PlannerScheduler` (`loop._w2b_sched`, cognitive_loop.py:422) and is
cleared INSIDE `on_level_change` / `on_fission` — the two clears the scheduler already has
(cognitive_loop.py:462 is the level site). One clear site per event; none to forget. The
planner and composer receive it as an optional argument (`retained=None` → today's per-call
behaviour, byte-identical — that absence IS the undo). Every entry is tagged (game, level);
a lookup under any other (game, level) is a miss AND clears (belt under the event's braces).
**Validity lives in the KEY, the level clear is the BOUND:** `apply_effect` is a pure function
of (atom content, state), so every key below carries an ATOM CONTENT KEY (sha1 over the fields
apply_effect reads: kind, ttype, params, context, transform, condition/then/else, parts) computed
once per atom per call — a superseded atom (minimised context, `conflict_component` reinstate,
settle) misses by construction, never by a clear someone remembered to call.

**(a) THE APPLICATION MEMO.** `(atom content key, state key) → None | result state key`, with a
separate `state key → array` store (results dedup: many pairs reach one state). Arrays are
stored and served `writeable=False` — a consumer that mutates raises rather than poisons. An
evicted state turns every memo entry pointing at it into a counted miss (recompute, re-store).
Served to `_run` in the planner and to `_simulate` in the composer — ONE memo: a seam the
planner applied is a hit for the composer, and vice versa.
**(b) THE PER-STATE NEGATIVE + BAND.** A None entry is the matched-nowhere record for that exact
state (tier 1: exact key). Tier 2 carries it ACROSS a board change when the change set C is known
— inside the search every child is parent + C (one array compare per child, counted as its own
instrument term); across cycles the loop passes (previous root key, argwhere(prev ≠ cur)). A
negative for (X, K) plus C licenses, on K' = K + C, a scan of ONLY the anchors whose window
covers a changed cell (the band: dilation of C by the patch dims): off-band anchors were
all non-matching on K and K' equals K there. First-in-row-major is preserved (every off-band
anchor is a known non-match, so the first in-band match is the first overall) — the outcome
equals the full scan's, which is the scope guard W2a set (how `apply_effect` judges is untouched).
Entry: `effects._context_anchors(b, ctx, band=...)` — the ONE dispatch (effects.py:451) gains a
restriction, with the full scan kept as the equivalence oracle. **Scope, stated:** tier 2 ships for
RAW-path atoms only (no ttype / "NONE"), whose only scan is the context window; typed atoms
(`_apply_typed` has its own anchor search) stay tier 1 — the typed extension is the named follow-on
if the profile shows typed atoms carry the remaining scans. EFFECT_IF and COMPOSITE: tier 1 only.
**(c) DEAD-ENDS.** A state at which EVERY candidate application returned None (forward), or
every invertible atom's inverse failed or failed its forward replay (backward), is marked under
`(direction, state key, candidate-set key)` where the candidate-set key hashes the sorted
(id, content key) pairs of the call's pruned `ids`. Target-independent by construction; a mint or
import changes the set key and the mark simply misses. A re-encountered dead-end skips the
candidate loop but STILL spends its `expanded` count — budget and depth semantics unchanged, so
retention changes work, never the answer (R4). (c) is (a) compressed: one entry that survives
after its |ids| memo rows have been evicted.
**(d) THE COMPOSER'S SEAMS.** `_simulate`'s per-seam applications go through memo (a). `_anchors`
results are retained as `(content key, frame key) → anchor list` — a SEPARATE structure (an empty
anchor list is raw-path-only knowledge; it does not imply a typed None, and is never read as one).
The enabler index (`enables_edges` over the pool) is retained keyed by (change mark, frame
signature dims+palette), FIFO of 8. `frames`/`frame0` in the drive stash are untouched.

## BOUNDS (caps STATED, per level, insertion-order eviction — deterministic, no clock)
MEMO_CAP 65,536 entries (≈ 8 calls at the widest observed breadth, 2× a post-W2b generation;
the pre-W2b regime at 17 × 8.3k = 141k exercises eviction, by design). STATE_BYTES_CAP 64 MiB
(at 64×64 in the planner's received dtype, ≥ 2,048 frames at int64). DEAD_CAP 16,384 (≤ 4 calls ×
`_MAX_NODES` = 8k observed ceiling, 2×). ANCHORS_CAP 8,192. ENABLERS 8. Evictions and store-misses
are counted, never raised. **Never the sole holder:** every entry is rebuildable from Gamma +
`apply_effect`; deleting the store mid-level changes cost only. The composer's `atoms` are the
stream's per-attempt pool as today — nothing in the store is an atom.

## FALSIFIERS (gate: tests/gate/test_planner_retention.py unless marked proctor)
- **F1 · THE SECOND CALL DOES LESS WORK — COUNTED, NOT TIMED (the wall-clock rule).** A new
  out-of-band instrument (planner's `reason_counts` pattern, fixed keys): per call `applied_cold`
  (apply_effect invocations), `memo_hits`, `band_anchors` vs `full_anchors`, `dead_end_skips`,
  `store_misses`, `evictions`, plus the delta-compare count. (i) Exact repeat with retention:
  `applied_cold` = 0 on the second call and the returned dict + reason are identical. (ii) Shifted
  repeat (second root = a state the first call expanded): `applied_cold` strictly lower than the
  first call's, `memo_hits` ≥ 1. (iii) Composer: a second `compose_attempt` on the same frame fires
  zero `_context_anchors` scans and zero cold seam applications.
- **F2 · RETENTION NEVER SURVIVES A LEVEL CHANGE OR A FISSION (the leak check).** After
  `on_level_change()` / `on_fission()` every substructure reports 0 entries; a state key seen in
  level L is a MISS in level L+1 even when the board is byte-identical; an entry written under
  (game, L) is unreadable under (game, L+1) with NO clear called (the belt). The mark cannot
  outlive the world it describes.
- **F3 · MEMORY BOUNDED.** Constructed overflow: entry counts never exceed their caps, oldest
  evicted first, `evictions` counted; oversized frames exhaust STATE_BYTES_CAP and the pointing
  memo entries become counted `store_misses`; with MEMO_CAP = 1 the planner's output is identical.
- **F4 · THE BAND NEGATIVE, BOTH WAYS.** (i) Sensitivity: a retained negative for X on K must not
  suppress a match the change creates — construct K' = K + C where X now anchors inside the band;
  the band scan returns that anchor and equals the full scan's first match. (ii) Specificity: a
  change whose band excludes a would-be anchor position re-examines only the band
  (`band_anchors` < `full_anchors`, counted) and records a fresh negative for K' when none matched.
  Plus the oracle: band scan ≡ full scan ∩ band on random frames/patches (the vectorisation gate's
  pattern). A typed atom never enters tier 2 (asserted).
- **R4 · RETENTION CHANGES WORK, NEVER THE ANSWER.** Constructed cold-vs-warm sequences
  (including across mints, aborts and eviction) return identical plans, reasons and `expanded`.
- **KNOWN-NEGATIVES.** KN1 a superseded atom (same id, minimised or reinstated context) misses
  the memo and the anchors store — the new result is returned, never the stale one. KN2 a mint
  between calls: the dead-end mark misses, the new atom's successor is found. KN3 `retained=None`
  → byte-identical to today's planner and composer. KN4 a consumer mutating a served array raises;
  the store's copy is unchanged. KN5 the composer's empty anchor list is not read as a typed None.

## THE PRE-COMMITTED MEASUREMENT AND ITS LOSING CONDITION (proctor's window six)
Same protocol as windows 1–5 (one worker, dump-on-timer, g50t or cn04). The metric is NOT the
share — the reabsorption law holds a ratio at any per-call speed, and the planner is already
off w5's top. The metric is per-call, counted: `applied_cold` per planner call and per
compose attempt, split FIRST-engagement-in-level vs REPEAT-engagement-in-level. **Wins if**
repeat engagements' `applied_cold` per call is below first engagements' by ≥ 30%, and the
retention overhead (content keys + delta compares + store ops, as a profile term) stays below 5%
of planner cumulative (the index's 0.2% is the precedent). **Loses if** the repeat ratio is ≥ 1.0
within the window's noise, or the overhead exceeds 5% — then the remaining cost is breadth (new
states every call, nothing to reuse), the build is UNDONE, and the successor is named now:
candidate selection (the re-point's second hearing), not more caching.

## UNDO
`retained=None` at the two call sites restores per-call behaviour exactly; the band restriction
reverts by dropping the `band` argument (the full scan is the kept oracle); the module deletes.
