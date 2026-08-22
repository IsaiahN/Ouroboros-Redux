# PREREG — NARROW AT MINT: context = changed + one ring, tightened on conflict (DRAFT for Seat 3, 2026-08-21)

Status: RULED 'take it' (Seat 4, 2026-08-21) and SEQUENCED by Seat 3 behind the
infrastructure queue (fabric I/O, W2c, standing_half_life, persistence monitor, symbol
receipts). Drafting history: withdrawn by the proctor the same evening as overreach (a
proposal reasoned from game-specific facts), then re-admitted on the reviewer's ruling with
the game-specific language REMOVED -- falsifiers below are stated by BEHAVIOUR only.
FIREWALL: no game, colour, or object identity appears in this document or may appear in
its brief, code, or fixtures. Was: NOT CLEARED. Object change (what an EFFECT atom's context IS at first mint); same
class as the re-point amendment and PREREG_STAMP_FACTORING. Drafted so the ruling has an
object. Supersedes the composer-starvation claim of PREREG_STAMP_FACTORING (F1 fired there).

## What the composer's starvation actually is (D-12 corrected, PORT_LOG)
On the measured box, the WANT-writing atoms the composer could not anchor are DISTINCT
large world-edits (64-128 cells), each observed ONCE, each minted with context = the full bbox crop of the
before-frame (effects.learn_effect, effects.py:360-390). The minimiser (W2-S2 re-point:
`_merge_context` -> `effects.minimise_atom`, "varying cells become DONT_CARE, changed +
one ring always retained") needs a SECOND observation of the SAME coarse signature to
fire. A large edit that happens once never gets one. So: full crop, exact-match anchoring,
no later frame matches, single-use forever. Over-specification proper. Self-motion
factoring does not touch it (measured: 17 -> 16 even under the widest subtraction).

## The object change
At first mint, an EFFECT atom's stored `context` is the minimiser's RETENTION SET applied
immediately: changed cells + one ring retained at their observed values, every other cell
of the bbox crop DONT_CARE. `context_full` (the raw crop) is stored on the same record as
the undo, exactly as the minimiser does on first touch today. The key, the coarse
signature and pricing are unchanged (they are change-only already).
Direction reversed, machinery unchanged: today = start exact, LOOSEN on repeat (never
happens for large edits); proposed = start loose, TIGHTEN on conflict via the re-point's
existing conflict clause (`_conflict_clause`: a before-frame that matches the loosened
context but produces a different signature REINSTATES distinguishing cells from
context_full, pinned via ctx_conflict_cells -- "divergence tightens, never loosens").

## Mechanism (the builder verifies each pointer)
1. `learn_effect(..., narrow=False)`: with `narrow=True`, after the bbox crop, compute
   `retain = changed | ring1(changed)` within the crop; `context[~retain] = DONT_CARE`;
   `context_full` = the raw crop; `transform.before` follows context; `transform.after`
   unchanged at changed cells and DONT_CARE where context is DONT_CARE (the minimiser's own
   invariant: DONT_CARE lands in context and after TOGETHER, never at a changed cell --
   mint.py `_atom_signature` docstring). `narrow=False` -> byte-identical to today.
2. The flag is set by the ONE stamp call site in cognitive_loop and is PINNED on (KNOBS
   row, prereg-bound); `narrow=False` exists only for F3.
3. The minimiser and the conflict clause need no change: a narrowed atom is already in the
   form they produce. Verify `_refresh_sig_index` treats `context_full`-bearing records as
   minimised (mint.py:548) so the conflict clause covers them from birth.
4. Vintage atoms untouched (archive law; the library heals forward, per the ruling on
   PREREG_STAMP_FACTORING q3). New mints carry `narrowed: True` on the record envelope, read
   through one total reader (exemplar effects.origin_of).

## Falsifiers
- F1 (offline, BEHAVIOURALLY DEFINED population -- no game or colour named): take every
  stored EFFECT atom on one box that currently anchors on ZERO of that box's stored frames
  (the agent's own trace records; the builder reads counts, not boards). Re-stamp them with
  narrow=True and anchor against the same frames with the UNCHANGED matcher. Pass: at least
  30% of that population anchors on > 0 frames. Stop-and-report below that: the ring is not
  the discriminator and the object change is not the fix.
- F2: atoms whose crop is a single cell have UNCHANGED anchor counts (the ring of a 1-cell
  change on a 1x1 crop is the crop itself).
- F3: narrow=False -> byte-identical learn_effect on >= 200 recorded events.
- F4: tests/gate/test_system_determinism.py stays green.
- F5 (the risk, pre-registered): over-application. On the same stored frames, count atoms
  that anchor on a frame where the ACTUAL next frame (action_traces) shows the effect did
  NOT occur -- false applicability. Report the rate; the conflict clause is the designed
  corrective and its firing count is reported beside it. No bar is set on this number; it
  is the measurement the ruling on "start loose" is made against.
- F6 (live, after deploy): on the measured box, compose-none notes stop being all `no-anchor`
  (PREREG_STAMP_FACTORING F5's instrument, shipped as F-alone). Readability of g7 is this
  prereg's debt now; the number is still the composer's.

## Known-negatives
- A 1-cell effect keeps a 3x3 context (changed + ring) -- not narrower than today's 1x1
  crop, so single-cell atoms are unaffected.
- An effect gated by a distant cell (a switch elsewhere) is over-applied until the first
  conflict reinstates the switch cell -- stated; F5 measures it.

## Ruling questions for Seat 3
1. Accept start-loose/tighten-on-conflict as the context's default direction?
2. Is "one ring" the retention set, or the minimiser's exact set (changed + ring + conflict-
   pinned)? Draft: identical to the minimiser's, so one definition lives in one place.
3. F5 has no bar: is a measurement-first deploy acceptable for the over-application risk,
   given the conflict clause is already live?
