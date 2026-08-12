# PRE-REGISTRATION — mastery-lite: replay probability is EARNED from replay reliability

**Written 2026-08-11, at `792ae2b`. Supersedes the flat 0.8 with the v2 mastery principle
(inspected GENERIC at 3ad9f14) scoped to available evidence: replay reliability. Full mastery
(ablation robustness, diversity scoring) is a later prereg once ablation machinery exists.**

## THE CHANGE THAT IS AUTHORISED
> `engines/egocentric/mastery.py` — `MasteryLite(fabric)`: `record_replay_outcome(game, ok)`
> appends to collective "replay_outcomes" (ok = the replay reproduced its banked levels);
> `replay_probability(game, has_bank)` returns 0.2 without a bank; with a bank: 0.8 with no
> recorded history (the current lever as optimistic prior), else `0.2 + 0.6 * success_rate`
> over the last 10 outcomes (seeds+local). Earned, and DECAYING: failing replays (stale bank,
> changed board) drop the game back toward exploration automatically.
> Wiring: the player calls `record_replay_outcome` after every replay (ok = levels_completed
> >= 1 and no [REPLAY-ABORT]); `_replay_probability(has_bank)` becomes
> `mastery.replay_probability(game, has_bank)` with the static method retained as fallback
> when the fabric is unavailable.

## THE GATE — binding
1. TESTS FIRST: MasteryLite contract (no bank 0.2; bank+no-history 0.8; rates 1.0→0.8, 0.5→0.5,
   0.0→0.2; last-10 window; seeds counted); wiring scans (outcome recorded post-replay; the
   probability call routes through mastery when available).
2. ⭐ FALSIFIER (containment): all six control shas byte-identical (fresh box: no bank → 0.2
   path; one RNG draw unchanged).
3. ⭐ FALSIFIER (capability, on the compounding runs): replay_outcomes records accumulate; and
   on any game whose replays fail repeatedly, the logged replay rate visibly drops (re-derived
   from logs+fabric). No records → the wire is dead → revert.

## THE UNDO
`git revert`.
