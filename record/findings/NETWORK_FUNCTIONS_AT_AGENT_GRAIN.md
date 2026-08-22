# THE FOUR NETWORK FUNCTIONS, READ AGAINST THE TREE (2026-08-22)

The GM's frame: the network layer buys **variation, selection, retention, independence**.
The first three need multiple ATTEMPTS, not multiple agents — and a restart is an attempt.
So the economy runs across restarts within one agent, and the generation boundary becomes
the restart. This is that read, per function, with sites.

---

## 1 · VARIATION — BUILT, and one arm of it was dead until last night

| organ | site | state |
|---|---|---|
| hypothesis rungs | `decision_rung_system.py:174/288/414/457` → `rungs/hypothesis.py` | **WIRED — and its contradiction branch was UNREACHABLE until the Protocol repair last night.** `rungs/hypothesis.py:47` fell back to the literal `'exploring'` every call, so "theory contradicted" could never fire. Fixed in `c2e7b99`; it has never run in a fleet. |
| drive arms | `engines/egocentric/lp_drive.py` (`assign_arm` → fixed / random / lp) | WIRED, but the arm was assigned **per box per recycle** — a FLEET-grain knob. At agent grain it becomes "which drive this attempt uses", which is exactly the variation the GM wants and needs re-homing, not rebuilding. |
| exploration / starvation | `starvation.py`, the explore-boost path | WIRED; `persist` now feeds it (the persistence monitor). |
| the planner's own search | `planner.py` | WIRED. |

**Verdict: variation is built.** The honest caveat is that its most interesting arm — the
contradiction branch — has literally never executed, so we have no evidence about what it
produces.

## 2 · SELECTION — MOSTLY BUILT, and the one purpose-built organ is UNWIRED

| organ | site | state |
|---|---|---|
| frontier pariah paths | `engines/egocentric/frontier.py` — *"each frontier death permanently removes an opening"* | **WIRED and persists.** This is the closest thing to a working refutation memory. |
| standing / eviction | `engines/egocentric/standing.py` — S ranks retrieval, Tukey-fence eviction, `M_d > 0` so silence never evicts | **WIRED, built last night, never run in a fleet.** |
| plan-wrong routing | `scheduler.plan_wrong`, `mint._conflict_clause` (ctx_conflict) | WIRED. |
| **FalsifiedLedger** | `engines/egocentric/falsified_ledger.py` — *"weighted, defeasible reject-memory"*, its own docstring: *"This is the component Redux structurally cannot hold... here the reject-memory is first-class"* | **EXISTS AND IS UNWIRED.** Its ONLY references tree-wide are the package `__init__.py` re-export and its own file. **Nothing constructs it.** |

**Verdict: selection works, and the organ written specifically to be the refutation ledger
has never been connected.** That is the GM's "pariahs become what has been ruled out",
already written, sitting inert. It is the single highest-value unwired thing found in the
whole examination — and it is what the examination classified `preserve` for exactly this
reason, then nearly moved out of the tree.

## 3 · RETENTION — BUILT AND PERSISTS, with one hole at exactly the restart boundary

Survives a process death (on disk, per game): Γ/atoms, the frontier book, the action book,
mint verdicts, settlements, narration, mastery's replay reliability, and standing (S is
re-derived from the books, so two processes over the same books compute identical S).

**THE HOLE:** `engines/egocentric/retention.py` (W2c — the application memo, the band
negatives, dead-ends, the composer's seams) is **in-memory only and cleared on level change
and fission.** Everything a run learns about *where its own operators apply* dies at the
restart. Under the GM's frame — the economy runs across restarts — this is precisely the
wrong thing to discard, because the restart is the generation boundary.

**Verdict: retention is built for within-run and absent across-run for the one structure
that most represents "what this attempt worked out".**

## 4 · INDEPENDENCE — ABSENT, BY CONSTRUCTION, AND THE GM'S ARGUMENT HOLDS

Nothing at agent grain supplies it. One agent across restarts is one frame; its attempts
correlate by construction — Figure 2's collapse 1 at the agent grain.

The GM's counter is the right one and it is Figure 2's own: **the anchor does the work.** The
game refuses, and refusal does not care that every attempt came from the same head. We lose
triangulation between frames and keep the ground. Figure 2 says independence is what makes
*agreement* meaningful — and we are not asking two frames to agree; we are asking one frame
to be refused by something that does not update.

**One caveat worth carrying, not a rebuttal:** independence is what lets you tell "my
hypothesis is wrong" from "my whole framing is wrong". A single frame refused a thousand
times learns the first and cannot see the second. Figure 6's outward question — *does another
frame already hold it* — has no instrument at agent grain. That is a real loss and it should
be stated rather than dissolved.

---

## 5 · THE ACCIDENTAL ABLATION, STATED AS A MEASUREMENT
The network layer has been **OFF for the entire life of this fleet**, and the evidence is
the examination's, not an argument:
- 28,886 agents, **ONE distinct genome fleet-wide** — no variation to select from
- `discovery_prestige` **0 on every agent, and written by nothing in production** — no
  selection signal; the 60/20/20 lottery degenerates to uniform random
- `best_single_game_score` **0 on every agent** — the other selection field, also unwritten
- 2 of 4 operating modes ever used; `agent_archive` **0 rows fleet-wide** (the archive raised
  `no such column` into `logger.debug` for weeks)

So: **1,496 level crossings, best level 2, 0 games won — all produced with the network layer
inert.** That is the ablation, taken accidentally over months, and it says the fleet's entire
output is attributable to the single-agent stack. Nothing is lost by retiring the population
because nothing was ever gained from it.

## 6 · THE MAP STEP — THE GM IS RIGHT, IT IS NOT A STAGE
Perceive and act exist as stages. **The board model is implicit**: it lives scattered across
`Γ` (what edits are possible), the frontier book (where death is), the binder (what objects
are), the self-locus (where I am) and the bank's slots — with no single place that says
*this is my current model of this board, and here is how it changed*.
The reasoning gate's **PERCEIVE utterance** is the nearest thing built: it makes the agent
state what it sees before it bets. It is currently in shadow mode, blocking nothing, and its
completeness check (`differing` vs `reported`) is exactly a map-fidelity measure that nobody
reads as one. **That is the more valuable half of the gate work, and it is already half-built.**

## 7 · WHAT THE PORT SHOULD BUILD TOWARD — the question the GM asked
Three items, in dependency order, and none of them is "rebuild the network layer":
1. **Wire the FalsifiedLedger.** It is the refutation memory, written, tested by nothing,
   connected to nothing. Selection across restarts is what it is for.
2. **Persist retention across the restart** (or decide explicitly that it should not).
   Today the one structure representing "what this attempt worked out" dies at the boundary
   the economy now runs on.
3. **Make the map a stage.** Promote the gate's PERCEIVE from shadow to a first-class board
   model with an explicit revision step, and read its completeness numbers as map fidelity.
