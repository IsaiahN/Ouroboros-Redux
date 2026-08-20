# PRE-REGISTRATION — the handoff-rate lever (the ticket multiplier)

**Written 2026-08-11, at entry-16 state. The arithmetic: replay fires at p=0.2, so games with a
banked L1 spend 80% of episodes blindly re-fishing a level that is already solved, instead of
standing at the frontier with the harvest.**

## THE CHANGE THAT IS AUTHORISED
> In the player's replay branch: the probability becomes bank-aware — `_replay_probability(
> has_bank)` returning 0.8 when the game has banked sequences, 0.2 otherwise (the stock value,
> byte-equivalent path). Bank presence is checked BEFORE the draw; exactly ONE `random.random()`
> draw happens either way (the RNG stream cannot shift). Nothing else changes: replay content,
> handoff, harvest all as-is.

## THE GATE — binding
1. TESTS FIRST: `_replay_probability` unit contract (0.8 banked / 0.2 unbanked); source scan —
   one draw, bank check precedes it.
2. ⭐ FALSIFIER (containment): all six control shas byte-identical (fresh boxes: no bank →
   p=0.2 path, same single draw).
3. ⭐ FALSIFIER (capability, next population run): on games with banked L1s, the per-generation
   handoff count rises vs the harvest-judge run (same shape, p=0.2), re-derived from logs. No
   rise → the lever is decorative → revert.

## THE UNDO
`git revert`.
