# EVIDENCE — THE ACTION BUDGET, AND WHAT SPENT IT

*Recorded 2026-07-31. Commits `ef88e47` (instrument) and `e7b6db7` (the death split). Live arm K,
scorecard `https://arcprize.org/scorecards/63bc6331-545c-4e09-84a3-a51a0a73ee9f`, run on `ef88e47`.
This is EVIDENCE. It records what the receipt printed and how to overturn it. It does not conclude.*

## What was believed, and on what

CLASSIFIER 7 read `decide_calls` as the ACTION budget: the count reproduced at **2943 on eleven consecutive
sweeps**, no sweep was ever reported wall-clock bound, and the number therefore looked like `25 games × 120
actions` minus a handful of short runs. It moved for the first time in arm J (−123), of which −119 was `tn36`
never playing and **−4 was unexplained** — `su15` −3 and `sc25` −1. NEXT item 1 asked for that residual to be
attributed from the two captures on disk before any live arm was spent on it.

## It is not attributable from those captures, and that is the first finding

`_play_policy` increments `steps` at **two** sites: after a `pol.choose()`, which produces exactly one `decide()`
exit, and at the EARNED RESET, which produces none. So, exactly and always:

```
decide_exits(game) == steps(game) - retries(game)
```

`decide_calls` is therefore **not the action budget**. It is the budget minus a term no receipt had ever printed.
`_play_policy` has returned `steps`, `retries` and `deaths` all along; `tools/sweep_chain.py` never printed any of
them. `grep -c "EARNED RESET"` and `grep '"retries"'` return **0** in both `/tmp/armI_eager.txt` and
`/tmp/armJ_reserve.txt`. The mechanism was identifiable exactly in code; the NUMBER was not recoverable from the
existing receipts. So the beat's deliverable is the receipt, not a claim.

## The second finding, from the same read: the mis-named exit

`outcome` was pre-set to the literal `"action_cap"` **before** a loop with **two** fall-through exit conditions —
`steps < max_actions` and `(time.time() - t0) < wall_cap_s`. One name covered both returns. Every *"no sweep was
wall-clock bound"* reading, which is the clause CLASSIFIER 7 rests on, came from a name nobody chose at the exit
that produced it.

`GAME_OVER` was the same defect one line down: one literal at one `break` guarded by
`not can_retry or not earned or retries >= retry_cap` — three different findings about the agent under one word.

## Arm K — what the new receipt printed

23 of 25 games reported (`cn04` and `r11l` both `open_error:RuntimeError`). Roster digest `b93d1c615657`.

```
  TOTAL steps=2719 decide=2701 retries=18 | BUDGET RESIDUE=0
  OUTCOME:  action_cap 20 games | GAME_OVER 3 games | open_error:RuntimeError 2 games
```

- **The identity closes on every reporting game.** Residue 0, checked by the printer per game, not by a reader
  subtracting. A move in `decide_calls` between two sweeps is now a move in `steps` or in `retries` and in
  nothing else, and the table says which.
- **18 of the sweep's 2719 actions were earned restarts that made no decision.** That term has been invisible for
  twelve sweeps.
- **Twenty games hit the action cap at exactly 120 steps. NOT ONE game was wall-clock bound.** CLASSIFIER 7's
  clause survives — but it is now a measurement rather than a literal pre-set before the loop.

## NEXT item 4 is answered: the 20-frame deficit is DEATH, not the clock

| game | steps | decide | retries | deaths | outcome |
|---|---|---|---|---|---|
| `s5i5-18d95033` | 101 | 100 | 1 | 2 | `GAME_OVER` |
| `vc33-5430563c` | 101 | 100 | 1 | 2 | `GAME_OVER` |
| `su15-1944f8ab` | 117 | 115 | 2 | 3 | `GAME_OVER` |

All three exit on a death, not on the cap and not on the clock. In each, `deaths - retries == 1`: exactly one
death did not earn a restart, and it is the terminal one. Retries were 1, 2 and 1 against `retry_cap = 6`, and the
sessions were live (`reset_after_death` present), so of the three conditions behind that break **only `not earned`
remains**: the terminal death repeated a cause the death-memory already held, and §XIX refused the restart.

Twelve sweeps of "`s5i5` and `vc33` stop 20 short" was the agent's own death-memory rule ending the session, and
no field on the receipt said so. **This attribution is an inference from code plus receipt.** The exit split
(`e7b6db7`) makes the next sweep print `death_no_new_cause` directly instead, and that is the check.

## The 4-step residual did not float back

| game | arm I (`eager`) | arm J (`reserve`) | arm K (`reserve`) |
|---|---|---|---|
| `su15-1944f8ab` | 118 | 115 | **115** |
| `sc25-635fd71a` | 120 | 119 | **119** |

Arm K reproduced both of arm J's values at a third independent run, so the 4 is **not a noise floor**. What arm K
adds beyond the value is the decomposition: `su15` spent 117 actions of which 2 were restarts, `sc25` spent 120 of
which 1 was. Arm J's decomposition is **not** recoverable — that receipt never printed either term — so the
matching value is a reproduction of the NUMBER and not of the ROUTE. `su15` ended on a death in arm K and at the
cap in arm J.

## What may NOT be read off this

- **No pooled arm-K-vs-arm-J comparison.** The rosters differ (`tn36` errored in J, `cn04` and `r11l` in K), and
  the printer now refuses the comparison by digest. Recompute on the intersection or do not compare.
- **The residual bank was WARM** — arm J deposited into it. No chain, `fired`, `mint` or `resid` count crosses
  between these arms.
- **The death split is not live-validated.** Arm K ran on `ef88e47`, which had only the action/wall split. The
  three death literals have synthetic coverage and no live firing yet.
- `reserve_promotions_empty` still has **no live firing** (arm K: `empty=0 inert=1`).

## How to overturn

- A sweep where `BUDGET RESIDUE` is nonzero overturns the identity outright: the two counters are then counting
  different things and `decide_calls` may not be cited as anything.
- A sweep where `DEATH IDENTITY BROKEN` fires overturns the death attribution: a death went unobserved, or a
  restart fired without one.
- A sweep where `s5i5` or `vc33` reports `death_retry_cap` rather than `death_no_new_cause` overturns the §XIX
  reading above and moves the finding from the agent's memory to the builder's constant.
- A sweep reporting `wall_cap` or `action_and_wall_cap` on any game overturns the surviving half of CLASSIFIER 7.
- `loop_exit_unattributed` appearing at all means the post-loop guard is wrong and every outcome on that sweep is
  suspect.
