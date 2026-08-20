# PRE-REGISTRATION — the stock `random`-shadow crash fix (Isaiah-approved)

**Written 2026-08-10, at `8bc6527`. Approved by Isaiah ("Fix it"). BUILD HELD until the scored
run (both 10-gen parts, one code state) completes — the fix lands immediately after.**

## THE BUG (located, this beat)

`cognitive_loop.py` line 40: module-level `import random`. Line ~2524, inside `_act` (begins
~2422): a redundant LOCAL `import random` in a fallback branch — which makes `random` local to
the whole of `_act`, so any earlier `random.` use in `_act` raises
`cannot access local variable 'random'`, the loop dies, and the player silently falls back to
the old stack. Measured blast radius: `ls20 tu93 tr87` crash EVERY episode (games whose `_act`
path hits an earlier `random.` use); 109 crashes across the sealed baseline.

## THE CHANGE THAT WILL BE AUTHORISED

> Delete the redundant local `import random` (one line). Nothing else.

## THE GATE

1. Unit: gate suite green; a new test asserts no local `import random` inside any method that
   also uses `random.` earlier (the shadow class, generically).
2. ⭐ FALSIFIER (the fix bites): hermetic runs on the three crash games show ZERO `[PTMA-ERR]`
   crash lines and `P:[...]` reasoning lines appear (the loop actually plays).
3. ⭐ FALSIFIER (containment): `su15 ka59 dc22` control shas byte-identical (their `_act` never
   hit the shadow). `ls20`'s sha is EXPECTED to change (it joins the cognitive loop for the
   first time) — its new sha becomes the stored control.
4. **SCORING SEPARATION (Isaiah's condition):** the three healed games are scored SEPARATELY
   from the 22-game port scoreboard; any L2 on them is reported under its own line with the
   crash-fix caveat.

## THE UNDO

`git revert` of the fix commit.
