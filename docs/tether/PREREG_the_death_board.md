# PRE-REGISTRATION — what the death BOARDS are expected to show (written BEFORE the sweep)

Instrument commit: this one. Previous run commit: `2651230` (arm L). Bank: **WARM** — `.residual_bank/` is not
deleted before this run. No chain/`fired`/`mint`/`resid` count from this sweep may be compared to any arm that
ran cold, or to any arm whose roster digest differs.

## The claim under test

CLASSIFIER 12 found that restarts bought the agent no depth on four of six multi-life games in arm L, and left
two readings of that flatness unseparated:

* **H1 — a per-game death clock.** Something ends the run at a fixed depth more or less regardless of what the
  agent does; the "new causes" §XIX kept crediting are cosmetic differences on a board that happens to differ.
* **H2 — a replayed route.** The agent re-walks the same path back to the same situation and dies there again.

Nothing on any receipt separated them, because the §XIX branch held the board identity it was judging and threw
it away. This beat's instrument writes it down: every earned and terminal death line now ends
`‖ DEATH-BOARD board=<digest> act=<action> pstep=<policy frame index>`, and the terminal death stamps its own
`@N` instead of having its depth derived. Nothing in the agent reads any of it, the §XIX key is unchanged, and
the death memory is unchanged.

## The predictions

**Instrument self-checks — these must hold or nothing below may be read at all.**

1. For every game with a terminal death, the **printed** terminal `@N` equals the **derived** depth (the game's
   final `steps`). `tools/death_depth.py` computes both and shouts by name if they differ.
2. For every game exiting `death_no_new_cause`, the terminal death's digest **appears among that game's earlier
   death digests, with the same action**. This is forced by the branch condition — that literal is chosen
   because the memory already holds this exact `(board, action)`, and the memory is per-game. If it does not
   appear, the digest is not the identity the gate keyed on and the whole column must be discarded.
3. Every earned and terminal death line carries the clause; no line carries a `board=` with no `act=`/`pstep=`.

**The measurement.**

4. The three `death_no_new_cause` games (`s5i5-18d95033`, `vc33-5430563c`, `su15-1944f8ab`, if they report and
   exit the same way) label their terminal death `[by defn]` and are reported as **by-defn, not replay**. That
   label is a tautology and is not evidence for H2.
5. `tu93-0768757b` (50/50) and `sp80-589a99af` (30/30/30) — the flat games whose deaths ALL registered as new
   causes — show **pairwise distinct** death boards.
6. `bp35-0a0ad940`, the one game whose lives varied (16 then 64), shows **distinct** boards.

## What each outcome licenses, stated before the number is seen

* **Prediction 5 holds (distinct boards under flat life counts): H1 survives, H2's strong form is dead.** Dying
  at the same depth on different screens is what a clock looks like and is not what a replay looks like. The
  next question then becomes *what* is counting — and it is a question about the environment or the action mix,
  not about the death memory's key.
* **Any EARNED death repeats an earlier board of the same game (`★REPEAT`): H2 survives and is the finding.**
  The gate ruled that death a NEW cause, so the agent returned to a screen it had already died on and found a
  second way to die there. That is a replayed route, and the argument it makes is that the memory's key is too
  strict — an argument for changing the KEY, not for changing the gate.
* **Life lengths stop being flat once the boards are logged: the CLASSIFIER 12 table is withdrawn.** It would
  then have been an artefact of that roster or that bank state, and every sentence resting on it goes with it.

## What this sweep may NOT be used for

* **A digest can only say identical or not.** It induces exactly the equivalence `board_fingerprint` induces —
  that is what licenses reading it as the gate's identity, and it is also its ceiling. The "near-identical under
  a weaker key" version of H2 (same avatar cell, same fatal cell, differing only in a counter or an animated
  tile) is **NOT testable from this capture**, because the boards themselves are not logged. So prediction 5
  holding kills the *pixel-exact* replay only. Recording `distinct` from a game whose screen ticks every frame
  is weak evidence and the tool prints that warning rather than counting it.
* **No pooled comparison to arm K** (digest `b93d1c615657`) or to arm L (`793049198616`) unless the roster
  digest printed by this run matches. Per-game observations are per-game.
* **Digests are comparable WITHIN this sweep only in the sense that matters here** — same process, same
  function, stable across processes by construction (`blake2b`, unlike the salted `hash()` the gate uses). A
  cross-arm digest comparison is *arithmetically* valid and is still not licensed as a pooled claim.
* **Nothing here licenses a behaviour change.** Changing the §XIX key or the death memory is the FIX, and it may
  not ship in the beat that measured its motivation.
