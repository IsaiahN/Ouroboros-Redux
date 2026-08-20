# THE HORIZON — mostly RETRACTED within the hour, by a caveat this document wrote
2026-08-18. TAG: **APPARATUS**. Prompted by Isaiah: *"what if a game has no end point? you
should be able to tell that by the code and you would see the failure, right?"*

> ## RETRACTION, AT THE TOP WHERE IT BELONGS
> **PART 2 BELOW IS WRONG AND IS RETRACTED.** I claimed 15 of 28 games exceed the agent's
> action cap. **THE BUDGET IS NOT A FLAT 500 PER GAME. IT IS PER-LEVEL AND IT EXTENDS ON
> EVERY LEVEL-UP**, with unused actions carrying forward — `cognitive_game_player.py:238-251`:
> *"Per-level action budget: starts at max_actions, extends by actions_per_level on each
> level-up. Unused actions carry forward as a speed bonus for fast solvers."*
> So an 8-level game has an allowance up to ~8x, not 1x. Against that, **EVERY REFERENCE
> COST FITS COMFORTABLY**: wa30's 1843 over 9 levels averages ~205 per level, and the
> largest single-level reference cost anywhere (ar25 level 7, 233 actions) is well inside
> one allowance. **THE HORIZON PROBLEM I REPORTED DOES NOT EXIST.**
>
> **WHAT I DID WRONG, NAMED:** I read `MAX_ACTIONS = 500` at `cognitive_loop.py:415` and
> treated it as the episode's action allowance. It is the LOOP's internal budget variable.
> **THE ALLOWANCE IS COMPUTED SOMEWHERE ELSE, BY DIFFERENT LOGIC, IN A DIFFERENT FILE.**
> Two quantities, one name, and I compared the reference cost against the wrong one — a
> metamer, which is a genus already in the catalogue and which I have now supplied an
> instance of.
>
> **HOW IT WAS CAUGHT:** by caveat (ii), which I wrote into this document *before* asserting
> the finding, and then ran. **THE CAVEAT WAS THE INSTRUMENT.** Recorded because a
> pre-registered caveat that actually fires is the only reason this did not reach Seat 3 as
> a live claim about the mission being unachievable.
>
> **WHAT SURVIVES IS PART 1 AND PART 3.** Part 1 stands unchanged: no game lacks an
> endpoint, all 28 of 28 carry a completed reference run. **PART 3 STANDS ENTIRELY AND IS
> NOW THE WHOLE FINDING** — the loop cannot distinguish *ran out of budget* from *endpoint
> beyond reach* from *no endpoint*, and no field separates them. That gap is real, is
> independent of the arithmetic I got wrong, and is the actual answer to the question asked.

## PART 1 — CAN I TELL? YES, BUT NOT FROM THE CODE

**Not from the game's code — we do not have it.** ARC-AGI-3 is a remote API; the loop sees
observations, never the game's source. So "read the code and see" is unavailable in
principle, not merely unbuilt.

**From the reference metadata, yes, and the answer is clean.** All **28 of 28**
`environment_files/*/*/metadata.json` carry a non-empty `baseline_actions` — a reference
run's per-level action counts. **ITS EXISTENCE IS PROOF SOMEONE FINISHED THOSE LEVELS.**
Zero games lack one. Levels per game: 6 (×9), 7 (×5), 8 (×6), 9 (×4), 10 (×1).
**SO NO GAME ON THIS ROSTER LACKS AN ENDPOINT.** The literal worry is answered and closed.

## PART 2 — AND THAT IS NOT THE PROBLEM. THE PROBLEM IS THE HORIZON.

`MAX_ACTIONS = 500` per episode (`cognitive_loop.py:415`, `:475`, `:294`), consumed as
feasibility at `:1168-1169` and `:1250-1251`. Against the reference cost to finish each
game:

**15 OF 28 GAMES EXCEED THE CAP AT REFERENCE-RUN EFFICIENCY:**
```
  wa30 1843 (3.7x)   lf52 1339 (2.7x)   re86 1255 (2.5x)   dc22 1228 (2.5x)
  m0r0 1107 (2.2x)   sk48 1070 (2.1x)   g50t  879 (1.8x)   cn04  789 (1.6x)
  ls20  776 (1.6x)   ar25  748 (1.5x)   ka59  730 (1.5x)   bp35  651 (1.3x)
  s5i5  638 (1.3x)   sp80  518 (1.0x)
```
**MEDIAN REFERENCE COST ACROSS ALL 28 IS 638 — ABOVE THE CAP.**
And the 13 that "fit" mostly fit *barely, at flawless play*: tu93 92% of cap, vc33 89%,
tr87 83%, lp85 78% — **with zero budget left for the exploration that learning requires.**

**AND THE CAP MUST ALSO PAY FOR REPLAY.** A GAME_OVER resets `levels_completed` to 0 —
which is precisely why the replay machinery exists at all. So the 500 covers
re-reaching the current level PLUS new progress, and the effective exploration budget is
500 minus the replay cost. On ar25 the banked prefix spends **197 of the 500** just
returning to level 2.

## PART 3 — "WOULD YOU SEE THE FAILURE?" **NO. AND THAT IS THE REAL FINDING.**

**THE LOOP CANNOT DISTINGUISH THREE STATES THAT PRODUCE IDENTICAL RECORDS:**
  (a) I ran out of MY budget.
  (b) The endpoint is FURTHER THAN my budget.
  (c) The game has no endpoint at all.
All three end an episode with `levels_completed < total` and **NO FIELD SEPARATES THEM.**
There is no regime variable, no target-distance estimate, no "further than I can reach"
representation — this is the same defect as KNOBS A13/G24: the quantity feasibility divides
by is a literal, and nothing compares it to anything. **SO THE FAILURE IS NOT MERELY
UNNOTICED, IT IS UNREPRESENTABLE**, and 25/25 has been the standing mission while 15 of the
28 were outside the horizon the whole time, unreported because nothing could report it.

## PART 4 — THREE CAVEATS, BECAUSE THIS IS TOO LOAD-BEARING TO OVERSTATE

**(i) `baseline_actions` IS ONE REFERENCE RUN, NOT THE OPTIMUM.** It carries the efficiency
read's own label: *distance to THAT player, one run, NOT THE BAR.* A better player might
finish some of the 15 inside 500, so **"exceeds the cap at reference efficiency" is the
exact claim and "unwinnable" is NOT.** Cutting the other way: the agent currently runs at
MULTIPLES of reference cost, so it is far worse placed than the reference, not better.

**(ii) WHETHER A FULL-GAME WIN REQUIRES ALL LEVELS INSIDE ONE EPISODE IS INFERRED, NOT
PROVEN.** The inference rests on two observations — `levels_completed` resets to 0 on
GAME_OVER, and the replay machinery exists to re-reach a banked level — which together
only make sense if levels do not persist. **IF SOME MODE PERSISTS LEVELS ACROSS EPISODES,
THIS FINDING WEAKENS SHARPLY.** That is the single check that would settle it and it is
NOT YET RUN.

**(iii) THE ARC API MAY IMPOSE ITS OWN LIMIT** independent of ours, higher or lower.
Unchecked. If the server's limit is the binding one, `MAX_ACTIONS=500` is not the horizon —
it is a self-imposed floor beneath it, which is a different defect with the same symptom.

## PART 5 — WHAT THIS DOES NOT LICENSE
**IT DOES NOT EXCUSE 0/25.** The agent has never won a game it *could* fit inside the cap
either — lp85 needs 388 reference actions and has never been finished. **A horizon defect
on 15 games does not explain the 13, and the framework must not be allowed to excuse the
anchor.** This is registered as a constraint on what the mission can mean, not as a reason
the counter is stuck.

## THE ONE-LINE VERSION
**No game lacks an endpoint. 15 of 28 have one further away than the agent is configured to
reach, the median game is further than the cap, and the loop has no way to represent
"further than I can reach" — so it has been failing at that for the entire project without
a single record saying so.**

---

## APPENDIX — THE ONE THING THE RETRACTED PASS DID TURN UP, AND IT IS SMALL BUT REAL

`cognitive_game_player.py:238` says *"starts at max_actions (150)"*. `cognitive_loop.py:458`
sets `self._max_actions: int = 500`. **THE COMMENT SAYS 150 AND THE CODE PATH IT DESCRIBES
DRAWS FROM A DEFAULT OF 500.** One of the two is stale. It does not affect the retraction —
the budget extends per level either way — but it is a live disagreement between a comment
and its code on the quantity that sets the action allowance, and comments are what the next
reader trusts. **TAG: SUBJECT / GROUND-GATED** (a grep settles which value the live path
uses). Queued, not started.

## AND THE CORRECTED ANSWER TO THE QUESTION, IN ONE LINE

**No game lacks an endpoint — all 28 carry a completed reference run, and the budget
extends per level so every reference cost fits. But the loop still cannot represent
"further than I can reach," so if a game DID have no endpoint, or an endpoint past the
allowance, THE RECORD WOULD LOOK EXACTLY THE SAME AS A NORMAL LOSS.** The failure you asked
about is not currently happening. It is also not currently detectable, and those are two
different facts.
