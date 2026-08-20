# PRE-REGISTRATION — level-scoped ideas (the frontier pollution fix)

**Written 2026-08-12. The consumer case: seeds load once at episode start (level-1 ideas);
after a handoff the agent stands at level N holding level-1 goals, which get pursued, fail,
and burn budget being falsified. With handoffs at ~0.8 the pollution cost is now dominant.
(Also logged: the proactive-reset port is KILLED by consumer analysis — the fabric already
survives death, and a mid-episode reset strands the agent at L1 without replay assistance.)**

## THE CHANGE THAT IS AUTHORISED
> Mint records gain `"level"`: the levels_completed value the reward produced (an idea that won
> level 1 carries level=1). `priors(game, level=None)` filters when level is given (records
> missing the field default to level 1 — historically true). The loop RE-SEEDS on level change:
> entering playing-level N+1 loads priors(game, N+1) at inherited price and demotes the previous
> level's inherited seeds (their gate closes; pariah status untouched). [EGO-SEED] lines carry
> the level.

## THE GATE — binding
1. TESTS FIRST: mint stores level; priors level-filter + missing-field default; re-seed wiring
   scan (level-change branch reloads; previous inherited seeds demoted); backward-compat
   (priors(game) unfiltered keeps existing tests green).
2. ⭐ FALSIFIER (containment): six control shas byte-identical.
3. ⭐ FALSIFIER (capability, compounding runs): [EGO-SEED] lines appear WITH level tags at
   handoffs; and frontier episodes stop falsifying level-1 ideas (the "falsified inherited"
   count at frontier levels drops vs the pre-fix runs, re-derived from logs).

## THE UNDO
`git revert`.
