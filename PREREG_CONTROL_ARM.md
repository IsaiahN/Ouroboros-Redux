# PREREG: THE CONTROL ARM — does the egocentric stack beat what it replaced?
DATE: 2026-08-17. AUTHORITY: Isaiah/reviewer — "run it, and run it before wave 1's
verdict; it outranks the queue." REGISTERED BEFORE THE RUN.

## THE QUESTION
Every wave shipped has improved OBSERVABILITY and left CAPABILITY UNMEASURED. Nothing
has been demonstrated to cause a level. One paired run answers what three weeks of
instrumentation cannot.

## THE PAIRING (stated in advance)
ARM A (STRIPPED): 4474dace2e28f2e30ecb707ca8c4ca318394edee — the commit immediately BEFORE 493f96c "PHASE 1 LANDS:
  egocentric substrate". Stock v4: no fabric, no mint, no consumer, no planner, no
  priors. Sequence banking/replay is stock v4 and STAYS (it is not part of the stack
  under test).
ARM B (FULL): HEAD — the complete egocentric stack.
GAMES: ar25, r11l, sp80 — chosen because all three DEMONSTRABLY REACH LEVELS, so the
  metric cannot be degenerate-zero on both arms.
EPISODES: 12 per game per arm (36 per arm, 72 total). Same games, same episode count,
  same per-episode action budget (the runner's default, unchanged), separate boxes.
  WALL-CLOCK IS RECORDED per arm so levels-per-hour is derivable without being the
  bound (episode-bounded keeps capability and throughput separable).
THE SWARM IS STOPPED for the duration: 25 workers would contend for CPU and API rate
  limits and confound the wall-clock leg.

## METRICS (both, reported separately — never averaged)
1. CAPABILITY: levels reached per episode, and max level per game.
2. THROUGHPUT-ADJUSTED: levels per wall-clock hour.

## THE LOSING CONDITION, PRE-COMMITTED (deciding after the number arrives is how a null
## gets absorbed)
- STRIPPED WINS ON BOTH -> the stack is not paying for itself. Response: strip to the
  winner and re-add organs ONE AT A TIME, each with its own paired verdict (the
  ablation discipline applied at the architecture level). Not "the architecture is
  right and unfinished."
- STRIPPED WINS ON LEVELS-PER-HOUR ONLY (ties/loses on levels-per-episode) -> the stack
  is capability-neutral and costs throughput. Response: the runtime-tax investigation
  (read B), NOT architectural retreat.
- FULL WINS ON EITHER -> the stack pays; the queue resumes as sequenced.
- BOTH SCORE ZERO -> the run was too short to decide. That is a NULL WITH A REMEDY
  (more episodes / more games), NOT evidence for either side.

## BASELINE CAVEAT, CORRECTED
The reviewer's caveat named replay-into-death at 71% of budget. THAT DEFECT IS FIXED AT
HEAD (corpse guard, 9505156, deployed 18:28) — so arm B is NOT the 1bec793 baseline.
Honest qualification: the corpse guard is UNMEASURED by the coverage layer (tool scope
gap — cognitive_game_player.py is outside its measured scope), so I can confirm it
shipped but not that it executes. A loss for arm B is therefore damning; a win is
informative but rests on an unverified fix.

## AMENDMENT 1 — PARTIAL VERDICT AUTHORISED (2026-08-18, Isaiah's ruling)

AUTHORITY: Isaiah, 2026-08-18: "you can rule on a partial if its taking literal hours."
FACTS AT RULING: r11l full arm 13h08m elapsed at generation 10 of 12; stripped arm
finished the same game in 4m49s (ratio ~163x and still open). ar25 complete. Game 3 never
started. Everything on the board frozen behind it.

**RULING: THE ARM TERMINATES AFTER r11l. GAME 3 IS NOT RUN. THE VERDICT IS TAKEN ON TWO
GAMES.** r11l is allowed to finish (2 generations remain) because killing it now discards
game 2 entirely for ~2 hours of saving.

**WHAT THIS COSTS, STATED BEFORE THE NUMBER ARRIVES rather than after.** n=2 games, not 3.
The prereg's own clause already covers it: "a SPLIT VERDICT is a reason to widen the
experiment (more episodes / more games), NOT evidence for either side." That clause now
binds harder, not less: **with two games a split cannot be resolved by this run and must be
reported as unresolved.** The pre-committed branches are otherwise UNCHANGED — no branch is
being redefined after seeing ar25's numbers.

**AND THE THROUGHPUT ARM IS ALREADY DECIDED ON THE GROUND, INDEPENDENT OF THE VERDICT.**
A configuration that takes 13h+ where its comparator takes 4m49s has answered the
levels-per-hour question by exhausting the operator, which is itself the measurement.
