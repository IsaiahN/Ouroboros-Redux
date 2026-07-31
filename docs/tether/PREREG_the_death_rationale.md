# PRE-REGISTRATION — what the death rationale is expected to say (written BEFORE the sweep)

Commit at time of writing: `7e37f83`. Bank: **WARM** — `.residual_bank/` holds 14 family files (728K) and was
NOT deleted before this run. No chain/`fired`/`mint`/`resid` count from this sweep may be compared to any arm
that ran cold, or to any arm whose roster differs.

## The claim under test

CLASSIFIER 11 attributed the three short games of arm K — `s5i5-18d95033` (101 steps), `vc33-5430563c` (101),
`su15-1944f8ab` (117) — to `death_no_new_cause`: the terminal death repeated a cause the death-memory already
held, so §XIX refused the restart and the session ended. That attribution is an **INFERENCE** from code plus a
receipt that carried only the pooled `GAME_OVER` literal. It has never been printed.

## The prediction

1. Each of `s5i5`, `vc33`, `su15` — if it reports at all — exits `death_no_new_cause`, **not** `death_retry_cap`
   and **not** `death_no_reset_support`.
2. Each carries exactly one TERMINAL rationale containing `repeats a cause already in game-memory`.
3. `retries` on each is strictly below the harness `retry_cap = 6`.
4. `deaths - retries == 1` on each (the terminal death is the one that earned nothing).

## The falsifier, stated before the number is seen

* **Any of the three printing `death_retry_cap`** moves the finding from the agent's memory to the builder's
  constant, and **CLASSIFIER 11's §XIX paragraph must be rewritten before it is cited again.**
* **Any of the three printing `death_no_reset_support`** would mean the live session lost `reset_after_death`,
  which would invalidate the whole §XIX reading of this sweep, not just these games.
* **A ★ MISSING terminal rationale on a `death_*` exit** means the log did not cross the boundary and the run
  proves nothing either way — it is a defect in this beat's instrument, not evidence about the agent.

## What this sweep may NOT be used for

A game that errors in `open()` is not evidence for or against any of the above; it is a lost denominator. The
roster digest is printed and any pooled comparison to arm K (digest `b93d1c615657`) is refused unless the digests
match. Nothing here licenses a behaviour change: the fix, if the falsifier fires, is a rewritten paragraph.
