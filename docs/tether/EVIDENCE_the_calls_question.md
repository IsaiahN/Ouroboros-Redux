# EVIDENCE: is `decide_calls` code-determined or wall-clock-determined?

Banked 2026-07-30. This file is EVIDENCE, not a conclusion. It records what was predicted, what was
measured, and what would overturn it. Nothing here licenses a change to the agent.

## THE CLAIM UNDER TEST

`FINDINGS_the_members_behind_the_price.md` §5 observed that the decide funnel was bit-identical across
three consecutive sweeps (`calls=2943`, `priced=2841`, `veto=58`, `unpriced=44`) while the chain moved by
±2, and recorded it as a HYPOTHESIS WITH NO RECEIPT. The named check was "two sweeps with `.residual_bank/`
cleared between them."

`_play_policy` (swarm.py:66) terminates on `steps < max_actions and (time.time() - t0) < wall_cap_s`.
TWO bounds, and `outcome` is initialised to `"action_cap"` and only ever overwritten by `"WIN"` or
`"GAME_OVER"` -- so a game truncated by the WALL CLOCK reports `outcome="action_cap"`. That is an exit name
covering two states, and it means `outcome` cannot answer the question it looks like it answers.

## WHAT THE SAVED RECEIPTS ALREADY SAID (no live cost)

The members block publishes a per-game step count per exit. Summed per game it equals the pooled
`decide() calls` line EXACTLY on every sweep that has the block. Per-game decide steps, eight sweeps:

| game | A | B | D | members | C(=F) | E | esc | 0726 | **G** |
|---|---|---|---|---|---|---|---|---|---|
| ar25-0c556536 | 119 | 119 | 119 | 119 | 119 | 119 | 119 | 119 | **119** |
| bp35-0a0ad940 | 118 | 118 | 118 | 118 | 118 | 118 | -- | -- | **118** |
| cd82-fb555c5d | 119 | 119 | 119 | 119 | 119 | 119 | 119 | 119 | **119** |
| cn04-2fe56bfb | 119 | 119 | 119 | 119 | 119 | 119 | 119 | 119 | **119** |
| dc22-fdcac232 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | **120** |
| ft09-0d8bbf25 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | **120** |
| g50t-5849a774 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | **120** |
| ka59-38d34dbb | 119 | 119 | 119 | 119 | 119 | 119 | 119 | 119 | **119** |
| lf52-271a04aa | 119 | 119 | 119 | 119 | -- | 119 | 119 | 119 | **119** |
| lp85-305b61c3 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | **120** |
| ls20-9607627b | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | **120** |
| m0r0-492f87ba | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | **120** |
| r11l-495a7899 | 119 | 119 | 119 | 119 | 119 | 119 | 119 | 119 | **119** |
| re86-8af5384d | 119 | 119 | 119 | 119 | 119 | 119 | 119 | 119 | **119** |
| s5i5-18d95033 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | **100** |
| sb26-7fbdac44 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | **120** |
| sc25-635fd71a | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | **120** |
| sk48-d8078629 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | **120** |
| sp80-589a99af | 117 | 117 | 117 | 117 | 117 | -- | 117 | 117 | **117** |
| su15-1944f8ab | 118 | 118 | 118 | 118 | 118 | 118 | 118 | 118 | **118** |
| tn36-ef4dde99 | 119 | 119 | 119 | 119 | 119 | 119 | 119 | 119 | **119** |
| tr87-cd924810 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | **120** |
| tu93-0768757b | 118 | 118 | 118 | 118 | 118 | 118 | 118 | -- | **118** |
| vc33-5430563c | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | **100** |
| wa30-ee6fef47 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | **120** |
| **pooled `calls`** | 2943 | 2943 | 2943 | 2943 | 2824 | 2826 | 2825 | 2707 | **2943** |

ZERO mismatches on every pair, across three commits (`9c00271`, `f38c9ee`, `059118a`), two dates, cold bank
and warm bank, all under 8-way concurrency. **Every difference in the pooled `calls` is game-set MEMBERSHIP**
-- 2943 − 2824 = 119 = lf52's row; 2943 − 2826 = 117 = sp80's row; 2943 − 2825 = 118 = bp35's row;
2943 − 2707 = 236 = bp35 + tu93. The pooled number moved because a game errored out, never because the agent
or the schedule did something different.

## THE ONE CONFOUND THE SAVED RECEIPTS COULD NOT EXCLUDE

All eight ran at `wall_cap=200`. If the wall clock bound, it bound identically every time -- implausible under
network latency, but not measured. So ONE arm was run varying only that parameter.

## PRE-REGISTERED, WRITTEN BEFORE SWEEP G PRODUCED OUTPUT

Arm: `tools/sweep_chain.py 120 900`. HEAD `059118a`. Bank WARM, 14 files. Control: the eight sweeps above.

- **P1** per-game vector unchanged from the table. → **HELD**, 25/25 games, 0 mismatches.
- **P2** pooled `calls` = 2943 minus any errored game's row. → **HELD**, `calls=2943`, 0 games errored.
- **P3** `UNCOUNTED=0`. → **HELD**.
- **P4** wall time ≈ the same ~7–9 min despite a 4.5× wall cap; materially longer would mean the wall clock
  WAS binding and P1 fails. → **HELD**, ~8 min.
- **P5** `MINTED_UNUSED|explains_no_compress` predicted 0 or 1. → **MISSED**, it printed 2. See below.

## WHAT IS NOW ON A RECEIPT

`decide_calls` is **code-determined**: the ACTION budget binds and the wall clock does not, at least out to
`wall_cap=900`. The per-game deficits below 120 are restart frames (a retry costs a `steps` increment but no
`_decide` entry) -- 1, 2, and 3 frames for the 119/118/117 rows. The two 100s (s5i5, vc33) are a 20-frame
deficit that is stable across all nine sweeps and is NOT explained here; it is the open remainder.

## HOW TO OVERTURN THIS

Any sweep printing a per-game decide-step count that differs from the table above by more than 0, on a game
that did not error. That would make step counts run-dependent and put the wall clock back in play. The
identity the whole attribution rests on (`sum over games of per-game exits == calls`, no residue) is now
locked by `test_the_per_game_split_sums_to_CALLS_and_not_merely_to_the_pooled_exits`.

Not overturned by: a change in the pooled `calls` alone. Ask WHICH GAMES REPORTED first -- that has been the
answer every time so far.
