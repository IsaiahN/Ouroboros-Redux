# PRE-REGISTRATION — PHASE 2 v1: the goal spine (confirmed reward earns the wheel)

**Written 2026-08-10 BEFORE the build, on `v4-cold` at `9b7ceab`. Baseline: 6 games L1, ZERO L2.
Phase 1 (the self) passed both falsifiers.**

## 1. THE CHANGE THAT IS AUTHORISED

> Verbatim ports of `goal.py`, `relations.py`, `navigation.py` into `engines/egocentric/`
> (present and importable; v1 consumes GoalManager only — GridNav walls are Phase 2b, scoped out
> honestly). A new `GoalSpine` wrapper: per step it (a) accrues a per-action VECTOR delta map of
> the controllable's centroid (from the Phase-1 observer — learned live, answer-free), (b)
> proposes candidate target cells (small distinct non-self objects) into `GoalManager`; on a
> level-up the loop calls `spine.credit(<controllable's cell>)` — reward confirms the market's
> winner. `spine.drive()` returns an action ONLY when BOTH hold: a goal has CONFIRMED price
> (≥ confirm_bonus — i.e. a real reward happened) AND the action-delta map has an established
> action that reduces distance to it; otherwise None. ONE pre-empt site in the loop's action
> path: a non-None drive replaces the chosen action; None changes nothing, ever.

**HARD CONSTRAINTS:** deterministic, no RNG; failures swallowed to counters; the wheel rule is
structural — no confirmation ⇒ `drive()` is None ⇒ byte-inert; `cognitive_loop.py` gets the
pre-empt site + the credit wire and nothing else.

## 2. THE GATE — binding

1. **TESTS FIRST, SHOWN TO FAIL:** the wheel-rule gate (candidates + established deltas but NO
   confirmation → None, always); credit-then-drive (returns the delta-established action that
   reduces distance); unestablished deltas → None even when confirmed; determinism; wiring scans
   (pre-empt site consults `drive` and uses only non-None; `level_changed` wires to `credit`;
   `[EGO-GOAL]` logged on state changes).
2. **⭐ FALSIFIER (containment):** the four stored control shas (seed 5) reproduced byte-identically
   — those episodes contain no level-up, so the gate never opens and NOTHING may differ. Any
   drift = the spine drove without signal = wheel-rule violation → revert.
3. **⭐ FALSIFIER (consumption, cut-wire):** harness-injected `OURO_CW_EGOCONFIRM=N` (sitecustomize
   wrapper, instrument-side only) force-confirms the top candidate at step N. Forced arm vs
   control arm on 4 movement-capable, non-vacuous games: the action sequence must DIFFER on ≥2
   — a drive that engages and steers nothing is decorative → revert.

## 3. THE UNDO

`git revert` of the Phase-2 commit(s); baseline `9b7ceab`.

## 4. WHAT THIS DOES NOT CLAIM

No claim that confirmed goals EXIST in ordinary episodes (single hermetic episodes rarely level
— the gate may stay shut for whole runs, and that is correct wheel-rule behaviour, not failure).
No L2 claim — that is Phase 3's number. The three PTMA-crash games (`ls20 tu93 tr87`) are out of
scope until the [OPEN] fix question is answered.
