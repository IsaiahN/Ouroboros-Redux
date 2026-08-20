# PREREG — ATTRIBUTE THE EMPTY PLAN (2026-08-19, beat improvement slot)

**STATUS: PREREG ONLY. NOT BUILT.** The change is inside `engines/egocentric/` and
`cognitive_loop.py` — **agent code, which is a builder's to write, not the proctor's.**
This is the brief, with its falsifier and undo fixed before anyone touches it.

## THE FINDING THAT PUTS IT IN THE SLOT
The whole planner DRIVE path is dark, and the project's own instrument names the step:

```
[PLAN-GATE] cyc=200 g1=198 g2=194 g3=194 g4=194 g5=194 g6=194 g7=0 shadow=0 drive=0
```
**g1–g6 pass ~97%. g7 collapses to zero.** `g7` is `plan_to_identity(...)` returning a plan
**with steps**. Both `drive` and `shadow` increment *inside* the g7 branch, which is why both
read 0 — and why **the 2× TRANSFERRED verification never executes at all.**

**THE 2× GATE IS NOT THE BLOCKER. IT IS NEVER REACHED.** Measured this beat:
**5,644 TRANSFERRED settlements, 59 distinct atoms, 32 of them clearing the ≥2 bar.**
Those 32 are irrelevant while no plan with steps arrives to be checked against them.
*(Ladder stop rule: a step whose input never arrives cannot be diagnosed, only its
predecessor can. The predecessor is `plan_to_identity`.)*

**CONFIRMED ON CURRENT CODE, NOT ON THE STALE LINE.** The `[PLAN-GATE]` readings above are
from **2026-08-13/14** and predate `ad441c0` (2026-08-15), which added `gate_summary()` to
that line — so they could not be used to diagnose today's build. The live confirmation is
different evidence: in the minutes after this beat's relaunch, across 25 workers,
**`[COST]` fired 521 times and `[PLAN]` fired 0 times.** `[COST]` prints *inside* g6 once
`plan_to_identity` has returned; `[PLAN]` prints only at g7. **So the planner is returning a
plan object that carries a cost and no steps, every time.**

## THE GAP, AND IT IS ONE FIELD WIDE
Two instruments each hold half the answer and **nothing joins them**:
- `starvation.jsonl` records **which socket starved** — `{"socket":"plan_steps",
  "code":"EMPTY_PLAN","game":...,"level":2,"budget_spent":175}` — **68 records, no reason.**
- `planner._REASON_COUNTS` records **why** — one of `NO_APPLICABLE_ATOMS`,
  `BUDGET_EXHAUSTED`, `NO_MEET`, `ANCHOR_MISS`, `INFEASIBLE_COST` — but it is a **module
  global that dies with the worker**, surfaced only on a `[PLAN-GATE]` line printed every
  200 planner cycles. **That line has emitted ZERO times since 2026-08-14** — 27 lines
  total, ever, from 2 of 25 boxes. *The instrument built on 08-15 to answer exactly this
  question has never once reported.* (Rung 0e, again.)

## THE BUILD (minimal — one field, no behaviour change)
Carry the planner's empty-plan reason onto the `EMPTY_PLAN` starvation record:
`{"socket":"plan_steps","code":"EMPTY_PLAN","reason":"<NO_APPLICABLE_ATOMS|BUDGET_EXHAUSTED|
NO_MEET|ANCHOR_MISS|INFEASIBLE_COST>", ...}`.
**NO DECISION CHANGES. NO GATE MOVES. NO PLAN IS MADE OR SUPPRESSED.** This is narration
reaching disk, nothing else. **The wheel rule and the answer-firewall are untouched: the
reason is a mechanism enum, never game content.**

## FALSIFIERS — both directions, fixed now
- **F1 · IT ATTRIBUTES.** After one episode on a box that starves at `plan_steps`, **every
  new `EMPTY_PLAN` record carries a non-null `reason` drawn from the five enums.**
  *Fails if:* any new record has a null/absent/`"?"` reason.
- **F2 · IT CHANGES NOTHING ELSE.** Over a fixed-seed episode, `g1..g7`, `drive`, `shadow`
  and the action sequence are **identical before and after**. *Fails if:* any gate count or
  any action differs. **A narration change that moves a decision is a defect, not a fix.**
- **F3 · KNOWN-NEGATIVE.** A box that starves at a *different* socket (`mint`,
  `bank`, `plan_reference`, `plan_binding`) must **not** gain a planner reason —
  the field is specific to `plan_steps`, not sprayed on every record.
  *Fails if:* a `MINT_STARVED` record acquires a planner reason.

## UNDO
Delete the added field and its one call site. **The stream is append-only JSONL and readers
ignore unknown keys, so records written under the change stay readable if it is reverted.**
No schema migration, no state, nothing destroyed.

## WHAT THIS DOES NOT CLAIM
It does not fix the empty plan. **It makes the empty plan attributable**, which is the
precondition for fixing it and is currently missing. If the reason turns out to be
`NO_APPLICABLE_ATOMS` while 1,727 atoms exist, that is a second finding and a separate brief.
