# PREREG — COMPOSER STAGE 4: THE SETTLEMENT WIRE (2026-08-21)

Cleared in full by Seat 3. Stages 1–3 live (`a494cda`). Stage 3 left nothing to undo:
composites mint as CANDIDATES with no claim fields, asserted structurally. This stage adds
ONE transition and its failure routes. After it, g7 reads.

## THE WIRE
1. **Driving a candidate is the test, not a citation.** A CANDIDATE composite may be
   DRIVEN under the existing plan-drive gates (the wheel's drive path, W2b's scheduling —
   no new engagement). Driving an unsettled composite is a BET being tested — allowed by
   proposable-not-standable; what it may never be is GROUND in a derivation.
2. **The settle**: on the live frame after the driven chain completes, the composite's
   predicted final state must match the observed frame on the WANT cells AND contradict
   nothing it predicted elsewhere. Exact match → superseding append, same id,
   `settled: true` — **citable from that record onward**. Simulation never settles
   (stage 3's rule, restated as this stage's F1).
3. **Failure routes through machinery that already exists**: the abort router names it —
   *world-moved* (state changed under the chain → no penalty, chain remains candidate) vs
   *plan-wrong* (state as expected, prediction failed → `ctx_conflict` fires on the
   MISPREDICTING COMPONENT, tightening it from context_full; the composite stays
   unsettled). Divergence tightens; nothing is deleted.
4. **g7**: a driven composite IS the plan rung firing. The drive increments the same g7
   counter the plan gates already carry (name the exact counter at build time from the
   g1–g7 narration wiring; do not mint a parallel counter — one counter, or the falsifier
   measures the wrong thing).

## FALSIFIERS (tests/gate/test_composer_stage4.py, house style)
- **F1 · live-frame-only settle**: a simulation-perfect chain does NOT settle; the same
  chain matching a constructed LIVE outcome does. Both directions.
- **F2 · unsettled never GROUND**: the citation path refuses an unsettled composite as
  GROUND and accepts it in a BET; settled flips exactly the former.
- **F3 · failure routed both ways**: world-moved → candidate intact, no ctx_conflict;
  plan-wrong → ctx_conflict on the mispredicting component (and only it), composite
  unsettled. Constructed both ways.
- **F4 · g7 increments exactly on the drive**: compose-only → g7 unchanged; driven → +1;
  the counter is the existing one (asserted by identity, not by name-alike).
- **R4**: constructed drive→settle and drive→fail sequences reproduce expected records
  exactly.
- **Known-negatives**: a settle attempt with no drive record → refused; a second settle on
  an already-settled composite is idempotent.

## UNDO
Remove the wire's call sites; candidates remain candidates; settled records remain
readable history. Nothing stored is destroyed.

## AFTER THIS STAGE
Sprint ends: supervisor + full fleet resume; the swarm run opens (purpose: g7's window +
completing the split-half set; stop: scoreable games at derived 2k). **The design
falsifier then reads**: driven composite settlements raise g7 above zero on some L1+ game
within the window, or the promotion failed and the finding routes to the WANT supply —
both outcomes pre-named, neither rescuable.
