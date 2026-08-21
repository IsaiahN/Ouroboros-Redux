# PREREG — STAMP FACTORING: self-motion out of world-edits (DRAFT for Seat 3 ruling, 2026-08-21)

Status: CLEARED (Seat 3 + Seat 4 ruling, 2026-08-21). This changes what an EFFECT atom IS
(same class as the re-point amendment).

## THE RULING (verbatim in substance)
1. ACCEPTED — Γ records world-edit only. BODY holds self-motion; the shelves become
   actually separate (today the cross-shelf reach had nothing genuinely cross-shelf to
   reach across).
2. LOCUS + BODY DELTA, with ONE GENERAL RULE replacing the exception list:
   **the delta explains the subtraction, or the cells stay.** Subtract exactly the avatar's
   cells in `before` plus those same cells displaced by the KNOWN delta, and nothing else.
   Avatar-coloured cells in the diff the delta does not account for are WORLD events and
   remain (death, recolour, overwrite fall out of the rule; they are not a list).
   Fail-closed: no locus, no delta -> no subtraction -> byte-identical to today. Strictly
   additive on the paths where the information exists.
3. LEAVE THE VINTAGE. No offline re-derivation: it would produce ~461 x 25 superseding
   appends nobody watched being made, checkable only against the derivation that made
   them. The library heals forward — the near-twins stop being minted the moment the stamp
   changes, and the re-point's own machinery merges them as new observations arrive under
   the coarse signature. If the near-twins persist in the way after a few sessions, that is
   a measurement; re-derivation can be reconsidered with evidence.
On F6: the stamp fix owes READABILITY; the composer owes the NUMBER. Two claims, finally
separated.

## The defect (D-12, PORT_LOG 2026-08-21)
`effects.learn_effect` (effects.py:360-390) derives the bbox, the context crop and the key
from the RAW diff mask `b != a`. The avatar's own cells are in that mask (its previous cell
14->0, its new cell x->14), so:
- the context crop is as wide as avatar-position + world-edit together (the over-
  specification finding, seen from the other side);
- the mint's coarse signature (change-only, mint.py `_signature`) is position-specific, so
  the same world-edit from another avatar position never matches, the minimiser
  (`_merge_context` -> `minimise_atom`) never fires, and a NEW atom is minted;
- sp80: 17 near-twin 40x28..48x30 atoms, 0 DONT_CARE cells, 0/17 anchor on any of 461
  stored level-2 frames; the composer's two-shelf premise (Γ = world-edit, BODY = self-
  motion) is false at the stamp, and g7's falsifier is unreadable.

## The object change
An EFFECT atom's context, transform and key are computed over the diff mask MINUS the
BODY's own cells for that action. Self-motion is the BODY shelf's fact; Γ stops recording it.

## Mechanism (the builder verifies each pointer)
1. `learn_effect(before, action, after, self_cells=None)` — a new optional argument: the set
   of (row, col) cells that are the BODY's own motion for this action (its cells in `before`
   and the same cells displaced by the action's BODY delta). `diff = (b != a)` has
   `self_cells` cleared BEFORE rows/cols/bbox/ctx/out/key/changed are derived. Inside the
   remaining bbox, any self_cell is written DONT_CARE in `context` and `transform.before/
   after` (the value there is observer-dependent, exactly what DONT_CARE means).
2. The mint's coarse signature (`MDLMint._signature(b, a, action)`) and `_atom_signature`
   must use the SAME subtraction, or the re-point never matches the factored atoms. One
   helper, both callers — name it, cite it, one wiring row.
3. Callers supply `self_cells` from what the ego layer already holds: the self-locus
   (`avatar` as the composer receives it) and `book_deltas`/the BODY atom for the action.
   No new perception. `self_cells=None` (no locus known, no BODY delta for the action)
   leaves the stamp BYTE-IDENTICAL to today — absence is not a signal.
4. If every changed cell is a self cell, the event is INERT for Γ (the BODY shelf already
   holds it). `changed` counts world cells only; pricing follows.
5. Existing atoms are NOT rewritten (archive law). Vintage stays vintage: the shelf is mixed
   and STATED (a record field `factored: true` on new mints — the marker discipline, read
   through one total reader, never inferred from absence).

## Falsifiers (pre-registered)
- F1 (offline, the diagnosis data): re-stamping sp80's action_traces (461 level-2 frame
  pairs) with self_cells collapses the 17 near-twin signatures to <= 3 distinct coarse
  signatures. If it does not, the trail is not the (only) contaminant — stop and report.
- F2: the factored atoms anchor on > 0 of the 461 stored level-2 frames (today: 0/17),
  and the `[[14]]`-class atoms' anchor counts are unchanged (the matcher is untouched).
- F3: `self_cells=None` -> learn_effect output byte-identical to today's on a recorded
  corpus of >= 200 events (the default path is a no-op).
- F4: byte-identical fabric streams across identically-seeded runs (test_system_determinism)
  — self_cells must come from the loop's deterministic state, never from timing.
- F5 (live, after deploy): sp80's compose-none reason distribution leaves `unreachable`
  (notes name `no-anchor` at composer.py:571 and `no-reach` at :543 — those two `_note`
  tokens ship with this build, the smallest instrument D-12 lacked).
- F6: g7 becomes READABLE: on some L1+ game within the run window, the composer proposes
  >= 1 chain (proposed > 0). g7 > 0 is NOT this prereg's claim — that is the composer's own
  falsifier, finally runnable.

## Known-negatives (must stay as they are)
- An avatar cell that changes to a colour the BODY delta did NOT predict (the avatar
  dies, recolours, is overwritten) is a WORLD event: it stays in the diff. The mask
  removes only the BODY-predicted motion cells, nothing else.
- An effect whose bbox is entirely inside the avatar's footprint but is not its motion
  (a tile under it changing) stays minted.
- No self-locus -> no subtraction -> today's atom, exactly.

## Residue stated
- Vintage atoms remain single-use near-twins on every box until Seat 3 rules their
  disposal (leave; or re-derive offline from action_traces under the factored stamp —
  possible: F1's data shows the frames are stored).
- The BODY shelf's own stamp is untouched by this prereg.

## Ruling questions for Seat 3
1. Is the object change accepted: an EFFECT atom records world-edit only?
2. Self-cell identification: locus + BODY delta (tight, fails closed to None) vs avatar
   colour anywhere in the bbox (wide, wrong when the colour recurs in the world). Draft
   takes the first.
3. Vintage disposal: leave, or offline re-derivation into a superseding append per id?
