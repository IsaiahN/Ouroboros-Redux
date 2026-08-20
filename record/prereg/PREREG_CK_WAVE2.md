# PREREG: CORE-KNOWLEDGE WAVE 2 — efference copy, inverse closure, surprise weighting

DATE: 2026-08-13. AUTHORITY: Isaiah ("proceed" on CK-2). Measured grounds: g4=0
(REFERENCE never binds — attribution too noisy), g7 residual (plans need backward
reach), lp85/ft09 debasement (flat evidence inflates support).

## CK-2a: EFFERENCE-COPY SUBTRACTION (von Holst; Wolpert) — attacks g4=0
The binder attributes world-vs-self changes by a crude click-proximity check. Build:
predict the sensory consequence of own action (the bank's committed prediction and/or
best matching atom applied at the action site), SUBTRACT predicted changes from observed
changes; the remainder is world-caused and feeds changed_without_agent. Heavy logic in
engines/egocentric/binder.py (new method taking a predicted-change mask); cognitive_loop
W4c-1 calls it in ONE-TWO compact lines (the .credit-within-8000-chars-of-record_result
gate has ~60 chars slack and MUST stay green).
FALSIFIER (failing first): synthetic episode where the agent's click changes cells AND an
independent mover changes others — old path misattributes (changed_without_agent fires on
self-caused cells or vice versa); new path attributes correctly; REFERENCE binds where it
previously could not.
VERDICT: [PLAN-GATE] g4 rises in games where g3 passes, within two beats.

## CK-2b: INVERSE CLOSURE + BACKWARD CHAINING (Klein group structure; Newell & Simon)
Typed transforms (CK-1a) make inverses computable: TRANSLATE(dx,dy)^-1=(-dx,-dy),
ROTATE(k)^-1=ROTATE(4-k), REFLECT self-inverse, COLOUR_PERM inverse mapping (injective by
construction), SCALE up<->down. Build: invert_transform() in effects.py; planner
plan_to_identity gains bidirectional search (forward from current, backward from
reference via inverses, meet in the middle) under the same budget.
FALSIFIER (failing first): a synthetic board where the goal is reachable in 2k steps but
forward-only BFS under budget k finds nothing and bidirectional finds the meet.
VERDICT: g7 moves on games with typed atoms; plan lengths reported in [PLAN] narration.

## CK-2c: PREDICTION-ERROR WEIGHTING (Rescorla-Wagner) — attacks debasement
Mint evidence currently counts; it should SURPRISE. Build: in mint.py, weight SUPPORT by
novelty of the transition (a before/after/action already predicted by an existing atom or
repeatedly seen contributes diminishing support; a surprising one contributes full
support). Pure bookkeeping inside consider(); bar/threshold semantics unchanged.
FALSIFIER (failing first): N identical repeated evidence items no longer reach the
support threshold that N distinct ones reach; a novel transition is unaffected.
VERDICT: lp85/ft09 mint acceptance rate on trivial evidence falls; structural share holds.

## CONTAINMENT (all): gate suite (191+) green; failing-first shown; separate commits,
separately revertible; no game specifics; the four-year-old/universality test per
CK_LEDGER v2. The wheel rule untouched: DRIVE still needs 2x TRANSFERRED.
