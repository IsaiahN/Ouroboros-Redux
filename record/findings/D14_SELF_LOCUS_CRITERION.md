# D-14 — THE SELF-LOCUS IS CHOSEN BY ACTION-CONTINGENCY, NOT ACTION-SPECIFICITY (2026-08-21)

Finding only. No fix attached (GM: the fix, when drafted, is a PRIOR the agent applies
everywhere — "a locus that does not move under a movement action is not a body" — never an
identification; no game, colour or object is named here).

## The criterion, verbatim (engines/egocentric/self_locus.py)
- `observe` :40-52 — per before-object, candidates = any after-object sharing its colour
  (:44), match = max cell-overlap (:48), and records `disp = euclid(centroid_after −
  centroid_before)` under `by_colour[col][action]` (:49-51). **Scalar magnitude; direction
  discarded on the same line it is computed.**
- `_contingency` :57-69 — per-action MEAN magnitude; `moved < move_eps (0.5)` → 0; fewer
  than two actions → 0; else `max(means) − min(means)`. The docstring's "Goodhart guard" IS
  this spread and nothing else.
- `controllable_colour` :71-79 — argmax of the spread over colours with ≥ 2 events.
Not used: per-action vector, within-action consistency, size, colour stability, any
"never changes autonomously" test.

## Why it mis-fires (structural, from the code)
(a) the observer is created once (cognitive_loop.py:1784, 1915) and `by_colour` never
resets across levels or games — lifetime accrual; (b) a zero-overlap same-colour match is
admitted (:44/:48), so one spurious jump inflates an action's mean for the worker's life;
(c) `move_eps = 0.5` is met by a half-cell centroid shift — an object that merely loses an
end cell; (d) a body translating the same magnitude under every arrow has spread 0 across
arrows — its spread comes only from actions under which it does NOT move. An indicator that
changes on every action therefore out-scores a body that moves consistently.

## No consumer checks that the locus moves per action
Composer avatar (cognitive_loop.py:4792-4803 → composer.py:476-479), enables.cross_shelf_reach
(:178-207, BFS from the given avatar), the frontier book (deltas = spine.established(), fed
by the locus's own centroid delta at :1989-1992 and re-seeded from the harvest at :2633 —
circular), the bank's BODY slot (:2176-2180 → bank.py:119-134), the W3 drive (spine.py:222-
241). The binder's BODY rule (binder.py:199-201) HAS a contingency+non-autonomy test, keyed
per colour class — and is not fed back to SelfLocus.

## The per-action vector already exists, locus-independent, unread
The W4c per-colour cell-set classifier (cognitive_loop.py:2141-2163) computes per-colour
centroid moved/mutated per step from the first post-action frame, in memory, for the binder.
SelfLocus never reads it. Every other delta source (spine evidence, bank body evidence,
harvest deltas) is DOWNSTREAM of the locus.

## Size, by count (stored book, latest record per box; no board reads)
25 boxes: a locus named on 16, None on 9. Of the 16: mover (≥ 2 distinct stored deltas) 6;
all-zero deltas under every action 4; no harvest record with deltas 6. **10 of 16 named
loci carry no stored per-action mover evidence.** The 9 locus-less boxes store empty maps.
On the measured box the chooser's own table is never persisted (SelfLocus.log is never
written), so its inputs are not answerable from records.

## Four amplifiers — SEPARATE items (Seat 4), each independently sufficient, none fixed
by the criterion change; named so it is never credited with them
- A1 NO RESET: `by_colour` accrues for the worker's lifetime across levels and games (the
  223-then-676 switch in the log, never reversed).
- A2 ZERO-OVERLAP MATCH admitted (:44/:48): one spurious long jump under one action inflates
  that action's mean permanently.
- A3 `move_eps = 0.5`: met by an object losing a single end cell.
- A4 On a box where every action's `frame_change_rate` is 1.0, "changes when I act"
  discriminates nothing at all.
Consequence of the criterion itself (note d): a real body with uniform step size under every
arrow is INVISIBLE to it — the score is structurally biased against the thing it seeks.

## Smallest criterion change (the builder's sentence, carried as-is, NOT dispatched)
Keep the (dr, dc) vector per action and score by the number of actions with a distinct,
repeatable non-zero vector (direction-specific, consistency-gated), instead of the spread
of scalar magnitude means. A prior; no identity enters.

Queued behind the infrastructure queue and Seat 3's seat-specific work. Ruling required
(it changes what "the body" IS to every consumer above).
