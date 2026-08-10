# PRE-REGISTRATION — PHASE 3c: THE L2 ATTACK (the handoff at the frontier)

**Written 2026-08-10, on `v4-cold` at `e29ba00` + 3b prereg. DRAFT until 3b's circulation
verdict lands; the build does not start before that. Baseline: ZERO L2 in 1800 episodes / 20
generations.**

## 1. THE MEASURED GAP THIS FIXES (from source, this beat)

`play_game` returns at replay completion (`cognitive_game_player.py:236`): a replayed episode
THROWS AWAY its remaining budget. Stock v4's only reliable route to level 2's doorstep ends the
episode on arrival. Additionally the replay executor bypasses the loop entirely, so the
replayed level-up never reaches the spine — even if play continued, the wheel would not know
the reward happened.

## 2. THE CHANGE THAT WILL BE AUTHORISED (after 3b)

> After a successful, non-terminal replay (levels_completed ≥ 1, state not WIN/GAME_OVER,
> budget remaining): DO NOT return. Fire the reward into the egocentric layer (the replayed
> level-up is THIS episode's real level-up: spine.credit at the current controllable cell +
> fabric mint/echo, same code path as a live level-up), then hand control to the ordinary
> cognitive play loop with the current observation and the REMAINING budget. No other change:
> episodes without replays are untouched byte-for-byte.

## 3. THE GATE — binding (finalised post-3b)

1. TESTS FIRST: handoff unit tests (return-shape preserved; remaining-budget arithmetic; the
   credit fires exactly once per replayed level; no handoff on WIN/GAME_OVER/exhausted budget).
2. ⭐ FALSIFIER (containment): the four stored control shas byte-identical (fresh boxes have no
   banked sequences → no replay → nothing may change).
3. ⭐ FALSIFIER (the handoff is real): in a population run, replay episodes show post-replay
   cognitive actions in their logs (action count > replayed count) on ≥3 games with banked L1s.
4. **THE SCORED NUMBER (the port's whole scoreboard): any `level_completions ≥ 2` episode
   within 20 generations of population run, against the baseline of ZERO in 20.** No A/B
   ambiguity: the baseline is fixed, sealed, and 1800 episodes deep.

## 4. THE UNDO

`git revert` of the 3c commit(s).
