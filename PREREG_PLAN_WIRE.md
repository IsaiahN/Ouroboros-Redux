# PREREG: THE [PLAN] WIRE TEST — which gate starves the planner?

DATE: 2026-08-13 (beat 30). STATUS: registered before build.

## The condition
Atoms exist (504 structural, 22 game/level pairs) and [PLAN] narration = 0 across all 25
worker logs for two+ beats. Per the beat protocol this is a starvation bug. Per C33 §15
(imported-witness law) log SILENCE is not a verdict on WHICH gate starves — the mechanism
has seven conjunctive gates that all fail silently, plus a silent empty-plan path:

  G1 _gamma/_role_binder/_refsnap constructed      (cognitive_loop.py:907-910)
  G2 _reference_snapshot non-None at plan time      (reset on level change :1932;
                                                     rebuilt only via stable-split :2016)
  G3 _ego_level >= 1                                (:911)
  G4 a REFERENCE-bound class exists                 (:914-916)
  G5 frame shape == refsnap shape                   (:918-919)
  G6 atoms exist for THIS game                      (:920-923)
  G7 plan non-None AND steps non-empty              (:934 — empty plan prints NOTHING)

## The build (narration only — zero behavior change)
Per-gate pass counters inside the EGO-PLAN block; every 200 W4c cycles emit ONE line:
  [PLAN-GATE] g1=.. g2=.. g3=.. g4=.. g5=.. g6=.. g7=.. shadow=.. drive=..
Constraints: (a) do NOT touch record_result (the 8000-char .credit window has ~60 chars
slack); (b) counters live on self, printed from the cycle path; (c) no new actions, no
changed action_data — narration only.

## Falsifier (shown failing first)
tests/gate/test_plan_wire.py: a loop instance driven with all gates forced open emits
[PLAN-GATE] with nonzero g-counts; source contains the counter block. Fails before build.

## Verdict rule
One full worker episode on a fabric that already holds atoms: the [PLAN-GATE] line names
the first gate whose count collapses to ~0. That gate is the starvation site; the NEXT
prereg (the fix) targets it specifically. No fix in this build — instrument first.

## Undo
Delete the counter block + test; cognitive_loop.py reverts by git checkout.

## Containment
Narration-only: the 6-control byte-identity check applies to ACTION STREAMS and must stay
green (stdout lines are exempt; action_data untouched).
