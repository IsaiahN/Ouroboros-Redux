# PREREG — THE D-8 FALLBACK INSTRUMENT (2026-08-21). One field, no behaviour change.

**The defect it measures (D-8):** the cognitive router's selected rung produces no usable
action on ~4 of 5 cycles on sk48/ar25 (lower bound 78.7/78.4%, from the `weighted_random`
label leak) and falls through to `_decide_weighted_non_emergency`, which checks no rung's
`confidence_threshold` (D-7). The true fallback rate is HIGHER by an unknown amount: when
the fallback's best score ≥ 0.15 the label becomes the real winner's name.

**THE BUILD (taken by Seat 3 + Seat 4):**
1. `decision_rung_system.py:1437` — immediately before `_decide_weighted_non_emergency` is
   called, set `self.last_decision_metadata['weighted_fallback'] = True` (and `False` on
   the non-fallback path at the same level, so absence never means "unknown").
2. The ACT narration record carries `fallback: bool` read from that metadata (the same
   path `rung` already travels: `cf.rung_name` ← `last_decision_metadata`).
3. Nothing else changes — no threshold check added (pinned: honouring thresholds on the
   fallback will READ AS A REGRESSION — more weighted_random — and is a separate decision
   taken only after this measurement).

**FALSIFIERS (tests/gate/test_d8_instrument.py):**
- F1 both directions: a constructed decide() where the router yields an available action
  → ACT `fallback=False`; one where it yields none → `fallback=True`, and the fallback's
  winner name is whatever it was (the label leak is NOT removed — the field is additive).
- F2 the field is never absent on an ACT record post-build (structural: every ACT emission
  path reads it).
- F3 byte-identity of decisions: with the field present, the chosen action for a
  constructed corpus is identical to today's (no behaviour change).
- R4: a constructed 10-cycle sequence with a known fallback pattern reproduces the exact
  fallback bitmap on the ACT stream.
- Known-negative: a decide() that never reaches the cognitive router (ladder strategy)
  records `fallback=False`, never True.

**THE READ IT ENABLES (the beat):** true fallback rate per game (exact, not a lower
bound), and the winning-rung distribution ON the fallback path — which decides whether the
threshold fix's blast radius (3 rungs silenced, 6 partial) is acceptable, and sizes the
real repair: why the router yields nothing. For the gate's coverage census: actions with
`fallback=True` are PROBES by mechanism, counted as such.

**UNDO:** remove the two assignments and the field; records already written keep it as
history.
