# THE MINIMAL LIVE SET — a subtraction, measured (2026-08-22)

Method: transitive import closure (static AND in-function), parse-only, over the 215 modules
outside `tests/`, `preserve/`, `considered_dead/` and the data dirs. Seeded from the
cognitive path — the loop, the gate, the composer, the mint, Γ, the fabric, the planner, the
narration log — and compared against the closure of the full production entrypoints.

## THE NUMBERS
| | modules |
|---|---|
| in scope | **215** |
| **THE MINIMAL COGNITIVE SET** | **46** |
| the same, counting package `__init__` re-exports | 101 |
| live but NOT on the cognitive path | 97 |
| reachable from neither | 72 |

**FIFTY-FIVE MODULES ARE PULLED IN ONLY BY PACKAGE RE-EXPORT.** The cognition needs 46; the
`__init__.py` files more than double it to 101 without a single call site. That is the same
mechanism that made five files come back within a minute of the examination's move, now
quantified: `engines/egocentric/__init__.py` alone re-exports 16 modules, so importing ONE
of them imports all of them. **The cheapest subtraction available is not deleting anything —
it is stopping the packages from re-exporting.**

## THE 46

> **⚠ LOWER BOUND ONLY — the instrument that produced this list is BLIND TO
> DEPENDENCY INJECTION.** See the falsification banner at §4. Do not delete from this
> evidence.

- **5 root/config**: `cognitive_loop`, `abstraction_config`, `config.cognitive_parameters`,
  `data_root` (new, from the de-cwd build), `database_interface`
- **32 `engines.egocentric.*`**: affect, agency, applicability, bank, betting, binder,
  composer, consumer, discrepancy, effects, enables, fabric, frontier, gate, goal,
  goal_abduction, latents, mastery, mint, narration, navigation, observer, perception,
  persistence, planner, router, self_locus, spine, starvation, swallow, verdicts (+ the package)
- **5 `engines.cognition.*`**: blackboard, causal_map, cognitive_frame, phenomenology_layer,
  valence_tagged_slot
- **4 `engines.perception.*`**: object_detector, perceiver, perceptual_field, visual_cortex

That is the set that runs perceive → think → act through the gate, mints, composes, and
writes the narration log. **The map stage is the gap: there is no module in the 46 whose job
is the board model** — `causal_map` and `blackboard` are the nearest, and neither is a
revised model of *this* board (see §4).

## WHAT EVERYTHING ELSE DOES — the 97 live-but-not-cognitive

> **⚠ LOWER BOUND ONLY — the instrument that produced this list is BLIND TO
> DEPENDENCY INJECTION.** See the falsification banner at §4. Do not delete from this
> evidence.

**THE DECISION LADDER IS NOT ON THE COGNITIVE PATH.** `cognitive_loop.py` imports NEITHER
`decision_rung_system` NOR `rungs` — zero references. The ladder is reached only from
`evolution_runner`, `engines/registry.py` and its own internals. So the 77-rung ladder, its
four rungs that cannot fire, its 21 `hasattr` guards and the eleven Protocols with undefined
methods are **a second decision machine wired into the RUNNER, beside the loop rather than
inside it.** The Protocol repair last night was real and necessary; it repaired a machine the
cognitive path does not consult.
The rest of the 97, by family:
- **the population machinery** — `agent_lifecycle_manager`, `agent_operating_mode_system`,
  `evolutionary_engine`, the lottery, prestige. Retired by the shape change.
- **the routing / rung layer** — `decision_rung_system`, `rungs.*` (7), `cognitive_router`,
  `edge_inference`, `eisenhower_layer`, `catastrophic_fallback`.
- **the network / social layer** — measured inert (one genome, prestige never written).
- **the fleet tooling** — `tools.swarm_supervisor`, `fleet_env`, `watermark`. Retired.
- **the player** — `cognitive_game_player`, `game_player`, `arc_api_adapter`: replay, mastery
  wiring, the toolkit boundary. Replaced by the `Agent` subclass in the port.

## THE THREE THINGS THIS SAYS
1. **The subtraction is real and it is bigger than expected.** 46 of 215. Even keeping the
   ladder and the player, the port's core is a fifth of what is live.
2. **The largest single win is the `__init__.py` re-exports** — 55 modules, no call sites,
   and they are why moving a file breaks four entrypoints instantly.
3. **The ladder needs a ruling of its own.** It is not on the cognitive path, it carries the
   known defects, and it is wired to the runner being replaced. Keeping it means porting it
   deliberately; dropping it means the loop is the whole decision system. Either is
   defensible; drifting into one is not.

---

# 2 · MODE CYCLING ACROSS RESTARTS (the GM's second ask)
The four modes exist — pioneer / generalist / optimizer / exploiter — in
`agent_operating_mode_system.py`, **which is in the REMAINDER, not the minimal set.** So
this is precisely one rescue from the discard pile, not a build.

Measured today: of 31,253 mode assignments fleet-wide, **generalist 19,789, pioneer 11,419,
optimizer 45, exploiter 0.** Two of four have never meaningfully run. The assignment was
per-agent-per-generation inside one process; at agent grain it becomes **one mode per
restart**, which is exactly the variation-with-one-agent transform.

To make the choice informed rather than round-robin it needs one record the tree does not
have: **(mode, board-state-at-start) → what it produced**, persisted across restarts. The
mode table already stores `mode_effectiveness` and it is written on all 31,253 rows — but
against the population's own scoring, which was uniformly zero. The field exists; its
meaning has to be re-derived against the ground (levels crossed, novel atoms minted) rather
than against prestige.
**Falsifier when it is built:** across N restarts on one game, mode selection must become
non-uniform in a direction the ground justifies — and a mode that has never produced a
crossing on this board must lose share. If selection stays uniform, the record is not being
read and the wire is dead.

# 3 · NOT SPECIATION — AGREED, AND NOTHING IS BUILT FOR IT
Accepted without qualification. Thoughts inside one agent share Γ, the priors and the
history by construction; there is no isolation, so there is no speciation. What is available
is variation from one frame, which mode cycling already supplies. **Nothing in the plan
builds for divergence between thoughts, and this note exists so that nobody re-adds it
later reasoning from the word.**
The one thing that genuinely does not transfer from the network layer is independence
(Figure 2), and the answer stands: the ground is the anchor and does not care that every
attempt came from the same head.

---

> # ⛔ SECTIONS 4, 4b AND 4c ARE FALSIFIED — DO NOT ACT ON THEM
> **Falsified 2026-08-22 by `tests/gate/test_ladder_removal.py`, which was built to test
> them and which they failed.** The ladder was ruled dead and queued for `considered_dead/`.
> The pre-registered prediction was that the loop's action sequence would be IDENTICAL with
> the ladder absent. It is not. **13 of 14 cycles diverge, first divergence at cycle 1**, and
> without the ladder the agent degenerates to one repeated action at one coordinate.
> **NOTHING WAS MOVED. The ruling is withdrawn.**
>
> **WHY THE TRACE WAS WRONG — and the load-bearing sentence is TRUE:** `cognitive_loop.py`
> really does import neither `decision_rung_system` nor `rungs`. **The ladder is not imported
> by the loop. It is INJECTED into it.**
> `evolution_runner.py:321` constructs it → `cognitive_game_player.py:116` passes it →
> `cognitive_loop.py:824` stores it → **`cognitive_loop.py:4338` CALLS `.decide()`**, inside
> SPEED 2: REASONED, on the live path, for strategies `exploit` and `experiment`.
> **An import-closure trace cannot see dependency injection.** This is rung 0c's finding with
> the polarity inverted: that was a symbol referenced and never reached; this is a module
> never referenced and always reached.
>
> **THE LIVE COUNT (proctor's INDEPENDENT recount, own predicate, 2026-08-22, all 25 boxes,
> 3,788 `narration.jsonl`, 2,336,716 records — reproduced the builder's figures exactly):**
> 537,424 ACT records · 298,601 carry a `rung` label · 32,031 of those are the loop's own
> `explore` speed, which is **not** a rung name → **266,570 actions decided by a NAMED RUNG.**
> Labels: wall_aware_navigation 112,988 · weighted_random 76,145 · survey 38,767 ·
> grid_exploration 23,610 · controlled_movement_planning 7,476 · exploration_phase 6,959 ·
> smart_action_selection 625. All seven resolve into the modules §4 proposed to delete.
> The `rung` field rides on ACT and on no other point.
>
> **§4c's ZERO IS REAL AND MEASURES THE WRONG DOOR.** The `evolution_runner` exception
> fallback genuinely never fired in 952,951 traces — that is the ladder's BACK door. The
> FRONT door is the constructor argument, open every cycle.
> **§4b's "CONDITION 1 DISCHARGED" ALSO FAILS.** `_consecutive_no_change` is read at
> `rungs/exploitation.py:128, 627, 660` (`decay = self._consecutive_no_change * 0.08`) inside
> rung evaluation. §4b says correctly that this runs "only when the ladder decides" and then
> equates that with the exception handler. The ladder decides on the LIVE path, so the feed's
> consumer is found and it is live: it moves rung confidence → moves which rung wins → moves
> the action. The ~80 frame comparisons per action are not buying nothing.
>
> **THIS IS NOT A DEFENCE OF THE LADDER.** It is load-bearing, which is weaker and different
> from good. Four rungs that cannot fire, and one falling back to a literal, are all still
> true — and they are true ON THE LIVE PATH, which is worse than this section supposed.
>
> **⚠ THE CONTAGION, AND IT IS THE REAL FINDING:** §THE 46 and §THE 97 above were produced by
> the SAME import-closure instrument that missed this. **Every constructor-injected dependency
> in this tree is invisible to it.** The 46 is a LOWER BOUND, and the 97 "live but not
> cognitive" list is UNSAFE TO ACT ON until re-derived with an instrument that can see
> injection. This move was the first withdrawal against that number and it would have removed
> the agent's action variety.

# 4 · WHAT THE LADDER CONTRIBUTES — TRACED, AND THE ANSWER IS: NOTHING TO THE DECISION
The GM asked what the 77-rung ladder contributes that the loop does not. Traced end to end:

**THE LIVE PATH CHOOSES WITH THE LOOP.** `cognitive_game_player.py:383`:
```
action_num, action_data, cf = loop.cycle(frame=..., obs=..., ...)
```
That is the whole of action selection. `decision_rung_system` appears in that file exactly
three times and NONE of them chooses an action:
- `:116` — passed through at construction
- `:479` — `if hasattr(self._gp.decision_system, 'notify_action_complete'):`
- `:501` — `self._gp.decision_system.notify_action_complete(action=..., frame_before=...,
  frame_after=..., context=...)`
**The ladder is NOTIFIED, AFTER THE FACT, OF AN ACTION THE LOOP ALREADY CHOSE** — and the
notification is behind a `hasattr` guard, the exact genus that hid four dead rungs.

**THE LADDER CHOOSES ONLY WHEN THE COGNITIVE LOOP HAS CRASHED.** `evolution_runner.py`
`play_game` routes to `self._cognitive_player.play_game(...)` and falls back to
`self._game_player.play_game(...)` — the legacy player, which is where `decision_system` was
handed at `:502` — inside `except Exception`. So the 77 rungs are the EXCEPTION HANDLER'S
decision system.

## WHAT THIS RE-READS
- **The weighted-fallback measurement (D-8, 78–85% on sk48) is the LADDER'S fallback**, not
  the loop's. It measured how a machine behaves that only chooses when the loop has already
  failed.
- **`primitive_suggester` never winning** is a fact about a machine the live path does not
  consult for decisions.
- **The four rungs that cannot fire, the 21 `hasattr` guards, the eleven Protocols** — all
  in the exception handler.
- **The 315 unexercised primitives may be unexercised twice over**: unreached in the ladder,
  and the ladder itself unreached on the live path.

## THE RECOMMENDATION (the ruling is the GM's)
On this evidence: **the loop is the whole decision system, and the ladder plus everything
downstream of it goes to `considered_dead`.** It is 77 rungs of which four cannot fire, one
cannot pass its own gate, one falls back to a literal every call — and none of them decides
anything unless the loop has thrown.
**WHAT MUST BE PRESERVED FIRST, and it is the one real cost:** `notify_action_complete` is a
genuine per-action outcome feed (frame before, frame after, goal cells, pixels changed). If
anything downstream reads it and matters, that consumer must be found before the ladder goes
— otherwise this repeats the archive defect, where a real feed pointed into an empty room.
**Falsifier for the removal:** with the ladder absent, the loop's action sequence on a
constructed board is UNCHANGED, and the only thing lost is the notification. If the sequence
changes, the ladder was contributing and the trace above is wrong.

## 4b · CONDITION 1 DISCHARGED — THE FEED HAS NO CONSUMER OUTSIDE THE LADDER
I said the ladder could not be removed until `notify_action_complete`'s consumer was found,
because a real feed pointing into an empty room is the archive defect. Traced:

1. **The confidence-adjustment half is DEAD ON THE LIVE PATH.** It is gated on
   `last_rung_name = context.get('last_rung_name') or self._last_winning_rung.name`.
   Nothing in the tree ever sets the context key — the only three references to
   `last_rung_name` are inside `decision_rung_system` reading it. And
   `_last_winning_rung` is assigned ONLY at `:889` and `:996`, inside the ladder's own
   decide path, which does not run when the loop chose. It is initialised to None (`:559`)
   and reset to None (`:856`, `:912`). **So `if last_rung_name:` is never entered.**
2. **The hook half DOES fire.** `for rung in self.rungs: if hasattr(rung,
   'on_action_complete'): rung.on_action_complete(...)` — and 5 files implement it.
3. **But every hook writes only to `self`.** The bodies set
   `self._consecutive_no_change`; **no hook writes the fabric, the DB, or any book** —
   checked across every `on_action_complete` body.
4. **And those counters are read only by the rungs' own decay** (`rungs/exploitation.py:128,
   627, 660: `decay = self._consecutive_no_change * 0.08`), inside rung evaluation — which
   runs only when the ladder decides, i.e. only in the exception handler.
   (`cognitive_loop.py:1889/3104/3134` reads a counter of the SAME NAME — that is the
   LOOP's own attribute on a different object, not the rungs'. Checked, because the name
   collision is exactly how a false consumer gets claimed.)

**THE LADDER IS A CLOSED LOOP WITH ZERO OUTWARD EFFECT ON THE LIVE PATH.** It is handed real
per-action data, updates counters only it reads, and those counters feed a decision that only
happens once the loop has thrown.

**AND IT IS NOT FREE.** `notify_action_complete` runs `(frame_before == frame_after).all()`
— a full numpy frame comparison — ONCE PER RUNG PER ACTION, across ~80 rungs, on the live
path, to update counters nothing reads. That is a measurable per-action cost on precisely the
path the speed mandate is about, buying nothing.

**RULING (recommended, and now fully evidenced): the loop is the whole decision system.** The
ladder, `rungs.*`, `cognitive_router`, `edge_inference`, `eisenhower_layer` and
`catastrophic_fallback` go to `considered_dead`. The falsifier stands and is now a PREDICTION
rather than a hope: with the ladder absent, the loop's action sequence on a constructed board
must be IDENTICAL, because nothing it computes reaches the loop. If the sequence changes, this
trace is wrong and the move reverts.
**THE ONE THING THAT MUST SURVIVE THE MOVE:** the legacy `GamePlayer` fallback path. Today a
cognitive-loop exception silently falls back to a ladder-driven player. If the ladder goes,
that fallback must become a LOUD failure rather than a quieter one — a crash that reports,
not a crash that quietly plays worse. That is a build item, not a move item.

## 4c · THE FALLBACK HAS NEVER FIRED — SO THE LADDER HAS NEVER DECIDED ANYTHING
The GM asked how often the cognitive loop crashed into the ladder-driven legacy player,
because if it were often, the fleet's readings would be pooled across two different agents.
**MEASURED: ZERO.** `[PTMA-ERR] CognitiveLoop failed, falling back` appears **0 times in
every worker log on all 25 boxes**, across **952,951 action traces**. And the message is
reachable — it prints under `--verbose`, which is exactly how the supervisor spawned every
worker. Had it fired, it would have printed.
TWO CONSEQUENCES:
1. **The readings are NOT pooled.** Every measurement this project has taken is of one
   agent — the cognitive loop. That is a relief and it should be stated, because the
   alternative would have invalidated the split-half baseline, the level ceilings and the
   D-8 read all at once.
2. **THE LADDER HAS NEVER CHOSEN AN ACTION IN THE PROJECT'S HISTORY.** It is not "the
   decision system used on the exception path" — the exception path has never been taken.
   77 rungs, priority-ordered, four of which cannot fire, one of which cannot pass its own
   gate, one of which falls back to a literal every call — and the whole assembly has never
   once decided anything. It has only ever been notified, and updated counters nobody reads.
The ruling stands and is now stronger than when it was made: there is no live path, no
historical path, and no consumer. Only the per-action numpy cost, ~80 frame comparisons per
action, paid on every one of those 952,951 actions.
