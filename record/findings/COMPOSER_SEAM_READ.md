# THE CROSS-STAGE SEAM READ (2026-08-21, Seat 3's request) — FOUR SILENT SUCCESSES FOUND

Stages 1-4 each passed their own falsifiers; their COMBINATION had never been checked.
1. **verified=False contract — HOLDS structurally** (every proposal funnels through _simulate
   + endpoint check before the one compose() site, composer.py:390-406) — but
   `reach["verified"]` is never READ: honoured by construction, not checked. And the final
   Gamma seam applies at apply_effect's FIRST anchor regardless of avatar position — **a
   BODY prefix's necessity is never tested** (silent success #4).
2. **csig-less composites mint — FAILS SILENTLY**: composite_signature→None → price=inf →
   still ranks, still mints (composer.py:398-406), index-invisible (NO-REQUIREMENT) — and
   admission_price is reached only from the IMPORT door, so a locally minted composite is
   never priced at all. Stage 1's hole never applied to local mints. (silent #2)
3. **One price — HOLDS** (composer ranks by the same composite_signature derivation;
   inf is the only local sentinel). The claimed "third consumer, the gate's PAY" does not
   exist yet.
4. **Multi-prior union — systematic overpricing on every multi-step chain**, loud in the
   prereg, silent at runtime: BODY after-patches can never contain the core's context, so
   the core's whole requirement bills as residue; ranking prefers the shortest chain —
   biasing AGAINST the multi-step chains stages 2-3 exist to find. Palette credits a
   union; cell count does not (internal inconsistency).
5. **Degradations combine silently**: act_offset None is read as "no positioning needed"
   and the drive site is then GUESSED from the patch centre (silent #3); NO-REQUIREMENT/
   unpriced composites still drive and settle.
6. **Handoff gaps**: centroid (float mean, rounded) vs exact anchor+offset equality — a
   multi-cell body may never satisfy it; the reach targets its own anchor while simulation
   and drive use anchors[0]; gamma.get returns rec["atom"] which cannot carry `settled`, so
   is_citable has nothing to read in production.

**THE WORST (silent #1):** predicate mode — plan_to_identity returns steps=[] when the
abduced predicate ALREADY HOLDS, abduced_plan returns None, the composer is invoked with a
satisfied WANT, `_advances` tests satisfies(pred, result) with NO BASELINE, every applying
chain "verifies", the cheapest mints, drives, and live_settle writes settled:True for a
composite that advanced nothing — **g7 would increment for no work.**

**DISPOSITION:** HOLD stays; the fleet does not resume on this code. Stage 4.5 (seam
repairs) preregged and built BEFORE the run. The read was cheap; the run on unread seams
would not have been.
