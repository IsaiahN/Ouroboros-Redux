# Ouroboros Redux — CPU version + the Ouroboros evolutionary port (marketplace of predictions, one lifetime)

Snapshot `void_fix` · 62 modules · no API key · no game mechanics/grids persisted.

**Metric: `levels_completed = 1`. The port runs; it has not cleared the hurdle.**

---

## The port: v1–v4's network, one shell down

The macro system evolved a *population of agents* trading ideas priced by measured `score_change`. This ports that
invariant into ONE agent, where the traders are *perceptual carvings* and the currency is *whether the next frame
confirms what they staked*.

| macro (network) | micro (this agent) |
|---|---|
| agent | a perceptual carving + its reasoning chain |
| genome / role | stage specialisation (pioneer / exploiter / optimizer / generalist) |
| game episode | one decision cycle (frame → action → frame) |
| **score_change** | **prediction confirmed by the frame** |
| generation | **an epoch = a death** (or an action ceiling where a game has no loss signal) |
| propose→vote→resolve | identical protocol, actors swapped |
| viral package | a confirmed predicate promoted to the molecule registry |
| HGT (3 layers) | 3 timescales inside one head |

`marketplace.py` — the invariant, parameterised by `(actor, currency, arena)`. In-memory; no SQL.
`micro_market.py` — the micro binding: chains, predictions, arena, evolution, roles, pariahs.
`test_marketplace_fidelity.py` — the macro binding checked against v4's transcribed arithmetic. All pass.

### Why prediction-priced, not trial-priced
v4 could afford to price an idea by TRYING it — twenty agents each played a whole game. One agent has ~70 actions
per life. So every chain stakes a falsifiable claim on the frame the agent was going to see anyway: **one action
prices every bid at zero extra cost**. No chain is credited for an idea it would not bet on.

### Transcribed, not retuned
`confidence = min(1.0, 0.3 + delta*2.0)` · `for if proposer_delta >= voter_delta` · `weight = clamp(mean(terms), 0.5, 2.0)`
· `consensus >= 0.6` · HGT rates `0.75 / 0.45 / 0.15` · `ROLE_TOLERANCE {exploiter .8, optimizer .6, pioneer .3,
generalist 0}` · pariah `toxicity = 1 - score/10`, decay `0.05/gen` · paralysis boost `0.3 * min(1, attempts/50)`.

### Findings the fidelity tests forced
- **`WEIGHT_CEIL = 2.0` is dead code in v4**: three terms each capped at 1.5 average to at most 1.5. Effective range
  is **[0.5, 1.5]** — a 3× spread. That clamp is *why a crowd of weak actors beats one strong one*, and it is now a
  passing test (`titan=1.50 vs crowd-of-4=2.00 → crowd prevails`), not a story.
- **Newcomer bug (mine)**: I floored unproven actors at 0.5. v4 gives them 1.0. Flooring is self-fulfilling — never
  win a vote → never gain a record → never win a vote.
- **Cold-start degeneracy (v4's, inherited)**: `0 >= 0` is support, so two evidence-free actors endorse each other
  unanimously. v4 hid this (deliberation only ran among agents with track records); the micro shell *starts* here.
  Fixed by backing the boldest claim and letting the frame settle it.
- **Accuracy ≠ advancement (mine, caught in synthetic)**: pricing chains on predictive accuracy made the market
  converge on hammering a wall at 100% consensus — "nothing will happen" is the easiest true statement on any board.
  Fixed by splitting **advocate** (priced in progress) from **predict** (priced in accuracy → credibility). A chain
  that knows a step is dead now VETOES it instead of winning with it.

### Ported from the published paper (IJCA 187(78))
Roles as *stage* specialisation; pariah store with **toxicity decay** ("without decay, agents become paralyzed by
ancient failures"); **paralysis detection** (many carvings attempting, none succeeding → raise tolerance, because the
accumulated "don't do that" may be the blocker); **resonance** (role-diverse agreement scores 1.61 vs 0.40 for an
echo of clones — the click); **youth bonus** (stops the ratchet where the first thing that worked out-records
everything later); and the **sacred rule** — prestige buys influence, never action budget — ported as a real guard.

---

## THE RESULT: the market made a falsifiable claim and the board refuted it

```
steer_ACTION1   n=1060  hit=0.475   ASSUMED (the composer's own steer map)
q1_ACTION1      n=1059  hit=0.427   INDUCED (learned from scratch by watching)
transfers=1                          first HGT in the port
19 generations | 3111 actions | 49 deaths
```

Two rival carvings of one question -- *what does ACTION1 do?* -- priced on identical frames. **The composer's forward
model is CORRECT** (0.475), and slightly better than a model induced from nothing.

That is not the result the first draft of this file reported. It claimed the assumed model scored 0.000 and had been
retired by selection. That claim was false, and it was false twice over, from two bugs in the TEST rather than in the
system under test:

1. the ctx bridge's `avatar_pos(f)` ignored the frame it was handed and returned the live position, so any chain
   comparing before-vs-after saw the same position twice and inferred that every move was blocked;
2. `SteerChain` multiplied the composer's steer map by the quantum a second time -- the map already stores a PIXEL
   displacement `(-5, 0)`, so it predicted a 25px hop for a 5px step and was refuted on every stake.

A broken rival was built, it lost, and its loss was announced as the incumbent's refutation.

**The port is nonetheless doing its job, and this is the demonstration.** The market stated something falsifiable,
the board tested it, and it was overturned inside two iterations. The same assertion under the previous architecture
-- one hypothesis, no competitor, no price -- would have become another session of navigation rewrites. That is the
failure mode this port exists to remove, and the first thing it removed was one of my own claims.

**The currency now works.** `transfers=1` is the first horizontal transfer: HGT requires a donor measurably better
than a recipient, and until the test bugs were fixed every carving was equally wrong, so there was nothing to move.
A real spread (0.475 / 0.427 / 0.006) is what selection needs to act on at all.

**The one real quantity we now hold:** both models are ~45% accurate. The avatar fails to land where predicted more
than half the time -- not because the model is wrong, but because it is BLOCKED. That is a measured fact about the
board, and it is the first honest number about why ls20 level 2 resists.

## The other findings that matter

**1. Our own diagnostic cap forbade evolution.** `my_agent.py: PER_LEVEL_ACTIONS = 500` ends the game after 500
actions on one level. The Ouroboros technique needs thousands of actions across hundreds of generations *on that
level*; v4 took 276 generations to reach level 4. Every measurement this project has taken was of a system killed at
generation ~1. With the cap lifted: **43 generations, 4250 actions, 62 deaths in 290s** — and ARC allows ~9h/game in
swarm mode, so this is still a rounding error of the available budget.

**2. Our action pipeline does not execute what our planner decides.** 98% of market stakes had to be VOIDED because
the stuck-break redirect substituted a different action than the one bid. Voiding (not refuting) is the right
response -- grading a chain on an action it never proposed is convicting it of our substitution, the same error as
convicting a trigger we never reached.

**3. Two bridge bugs that had made the reasoning engine structurally incapable of learning** -- both found by the
market failing to move rather than by inspection:
- `void()` discarded the *observation* along with the pricing. But PRICING and LEARNING are different questions:
  "was this bet right?" must be voided on substitution; "what does this action DO?" is answered perfectly well by a
  substituted action -- we did it, we watched it. Voiding both is how the induced model stayed ignorant while 98% of
  the agent's experience went past it unexamined.
- The ctx bridge's `avatar_pos(f)` IGNORED the frame it was handed and returned the live position, so any chain
  comparing before-vs-after saw the same position twice, inferred zero displacement, and concluded every move was
  blocked. **Every 0.000 hit-rate measured before this fix was measuring that bug, not the model.**

It also matches the published ls20 signature exactly: ls20 produced **25 hypotheses (10 active)** against as66's
**861**. Hypothesis generation was starved on ls20 for v4 too — the bottleneck was never the executor.

---

## Flags
`OURO_MICRO_MARKET` (0/1) · `OURO_EPOCH_ACTIONS` (60; the artificial epoch where a game gives no loss signal)
· `OURO_AVATAR_RETRIES` (6; raise for evolutionary runs) · `PER_LEVEL_ACTIONS` — **lift for evolution**.
Run: `OURO_MICRO_MARKET=1 OURO_EPOCH_ACTIONS=60 RUN_SECS=... python3 run_evolve.py`

## Honest caveats
- `max_level = 1`, unchanged. The port runs and evolves; it does not yet win.
- 0 HGT transfers — the transfer rule needs a donor better than a recipient, and every carving is equally wrong. The
  market has no currency until the forward model works. Selection cannot select on noise.
- Chains are still thin. The paper is explicit that the **reasoning engine (Q1–Q4) is the contribution** and the
  marketplace is support. The chains do not yet ask *what is changing vs fixed*, *what punishes/rewards*, *what
  happens if I interact with the most salient thing*, *what rule explains this*. That is the next build, and on this
  evidence it is the one that matters.
- Unported: adaptive `w` (private-vs-network trust), the valence engine, maturity-aware matching.


---

# THE MACRO SHELL — where previous attempts inform the next

The micro market decides ACTIONS against FRAMES. That is one shell, and it cannot answer *"last life I found a booster
over there — go get it"*, because a plan of that shape spans a whole life and can only be priced by what the life
achieved. Without the upper shell the agent re-derived the board every epoch: 43 generations of experience, and not
one of them told the 44th where anything was.

    micro:  actor = a perceptual carving,  arena = a frame,  currency = prediction confirmed
    macro:  actor = a PLAN,                arena = an EPOCH,  currency = progress the life measurably made

The macro binding is `EpisodeScoreCurrency` — **v4's own currency, already checked against its arithmetic in the
Phase-1 fidelity tests**. The upper shell is not new code; it is the same `Marketplace` protocol bound to different
actors. Plans bidding for epochs *is* v4's network, one shell up. `CommitmentChain` carries the plan down into the
micro market, where it must win its bids like anything else — a plan that cannot be outvoted is an order.

```
epoch 10  trip@(9, 6)        epoch 15  trip@(8, 7)
epoch 11  trip@(8, 6)        epoch 16  trip@(9, 10)
epoch 12  explore@-          epoch 17  trip@(8, 3)
epoch 13  collect@(2, 7)     epoch 18  trip@(3, 3)
epoch 14  collect@(11, 1)    epoch 19  collect@(10, 8)

plan KINDS: {'trip': 6, 'explore': 1, 'collect': 3}     discovery: 10 sites
```

Each life commits to a discovered site, is priced by what it achieved, marks its failure toxic (decaying 0.05/gen),
and the next life takes the least-recently-refuted option — cycling back once toxicity decays, so nothing is written
off forever.

## The class bug (Isaiah's diagnosis, confirmed line-for-line)

> *"once it grabs the booster it learns a bad lesson, never records the benefit properly, never applies it to other
> objects of the same class, and never does the math to use it when it's nearly out of actions."*

Mechanically correct on every link:

```python
cmap[ttype] = {"effect": "budget", ..., "gain": qb - pb, "inst": insts[0]}
```

The atom is keyed by **TYPE** — a claim about a CLASS — and stored **ONE ADDRESS**. The agent learned the general fact
and could act on exactly one object; retiring that instance left it with no boosters while identical ones sat on the
board. Compounded by `next((a for a in cmap.values() ...))` (one booster, ever), by two consumers iterating the parent
of the dict the cmap actually lives in (`patterns["avatar_cmap"]`) so `_boost` was `None` *every time*, and by the
gain being applied to a single member of a class it is a property of.

The benefit was never a "bad lesson" — it was recorded correctly (`gain: 32`) and could never be read.

**Fixed:** atoms carry `insts` (the whole class); every consumer iterates it; the macro shell reads the molecule
registry. **3 boosters known where 1 was; 3 `collect@` plans committed where 0 were.**

## Budget: the agent now works out its own resources

```
meter colour : 11        lives colour : 8      lives left : 3
q1_hud       : n=833  hit=0.954        (incumbent budget model: 0.006)
ACTIONS LEFT : induced 63.0            assumed: None
```

`_hud_units()` counted ONE colour, which turned out to be the *current life's* meter — so `_budget_actions()` answered
"actions until I respawn" while every decision it fed needed "actions until the game ends". **The agent never knew it
had lives.** `Q1Hud` induces the structure from scratch — no colour named, no game named — finding the lives counter by
the rule that *a life cannot be bought back*.

**Still unwired:** `_budget_actions()` continues to return the old per-life number. The agent knows the truth and is
not yet using it. That is the third link in the diagnosis above and it remains open.

## Honest state

`levels_completed = 1`. `progress=0` on every plan. The port evolves, selects, transfers, commits, and works through
the board — it does not yet win.


---

# PLURAL VANTAGES — the structural fix

## The defect

```
FrameArena.__init__(self, ctx, chains)     # ONE ctx, TEN chains
```

Every chain called the same `ctx.avatar_pos()`, `ctx.is_novel()`, `ctx.rarest_colour()`. **They disagreed about what
to DO and agreed completely about what they SAW.** Ten opinions over one percept is ONE SHELL — and one shell plus
selection is the definition of gradient descent. *"It's not exactly brute force, but it's still too long and is not
intelligent steering — it's gradient-descent-like"* was a structural diagnosis, not a figure of speech, and the code
confirms it.

`I6`: the invariant is never observed directly; it is only ever **integrated from shells, plural**. The shells did not
exist. Diversity has to live at the perceptual front-end, not downstream of a shared percept.

## What now exists

Three vantages, each a different answer to *where is the thing that moves*, each able to be wrong, **each priced by
the board rather than by argument**:

```
p_colour   n=1712  hit=0.268   identity: a fixed colour IS the avatar      <- the incumbent
p_delta    n=768   hit=0.134   causality: what MOVED when I acted is me
p_rarity   n=1712  hit=0.000   salience: the rarest small object is me     <- refuted, correctly
```

The colour percept has been the agent's only way of seeing for the life of the project. **An unopposed percept cannot
be discovered to be wrong.** It now has rivals; it currently wins; that is the first time that sentence has been a
measurement.

## `I2a` — the pose, live

Every chain carries `alpha` (private history vs market consensus, learnable per `w(t+1) = clip(w + b*sign(s-0.5))`)
and its **own encounter history in its own order**, recency-weighted so that order matters. Measured live:

```
steer_ACTION1  alpha=0.10  (trusts the market)
wall_ACTION1   alpha=1.00  (trusts itself)
alpha spread: 0.950  -> DIVERGED
```

**Identical architecture, divergent encounter order, different agents.** Unit-checked directly: same outcomes in
reversed order give private views 0.473 vs 0.527 and alphas 0.80 vs 0.20. Non-identity is now *structured* rather than
resting on entropy — which the corpus rejects everywhere else (*"the randomness is background radiation; the thing
you're still missing is gravity"*).

## Niche separation — the dual economy, not the youth bonus

The immune system has **no youth bonus**. It has niches — naive cells on IL-7, memory on IL-2/15Rbeta — and it *still*
gets memory inflation: old clones crowd out the naive repertoire until the system cannot answer anything new. **This
market had that disease**: one carving won every tie forever, direction mix 122:34. Reserved decisions now belong to
the unproven, where an established carving cannot bid at any price (`naive_wins=214, proven_wins=0`). The youth bonus
stays as the offset nature never evolved.

## Two bugs found by building this

- **`DeltaPercept` was reading the HUD.** The meter drains on every action, so the centroid of "what changed" was
  dragged into the status bar every time — the percept was measuring the budget, not the avatar (0.071 -> 0.134 once
  the play area was isolated).
- **`alpha` was never updated.** The mechanism existed and nothing called it, which made `I2a` unfalsifiable by
  construction rather than true.

## Honest state

`levels_completed = 1`. Within the 6/6 band — no regression, no gain.

- `disagree_rate = 1.0`: the percepts always disagree because they measure *different objects*, not one object three
  ways. That is not yet the informative disagreement `I2a` needs, and it is the next thing to fix.
- `p_colour` reads 0.268 here against `steer`'s 0.485 on the same model: percept stakes are not voided when the
  pipeline substitutes an action. Same bug, new surface.
- **Requirement (iii) — the residual as the aim — remains unbuilt.** Per `§1.3a`'s ledger every fix in this package
  lowers the **coefficient**; only aiming variation with a spec lowers the **exponent**, and that is the frontier.


---

# THE AVATAR IS A COMPOSITE, AND THE ONTOLOGY CUTS IT IN HALF `[MEASURED, live]`

```
composer believes : avatar = colour 12
ground truth      : the avatar is a 5x5 block -- 2 rows of colour 12 OVER 3 rows of colour 9
play area census  : {12: 10, 9: 27}      # 10 px = exactly 2x5 = the avatar's TOP HALF, and nothing else
one ACTION1       : that 5x5 block translates up by exactly one quantum
```

**The agent has been tracking half of its own body.** Its position is the centroid of the top two rows, ~1.5 rows
above the object's true centre.

## Why a year of tests never caught it

**A constant offset cancels in any translation test.** `want = pos+offset+disp`; `after = pos+disp+offset`. The offset
is on both sides and vanishes. Raced live against a percept that tracks the whole connected object:

```
p_colour     n=1898  hit=0.266   (half the avatar)
p_component  n=1898  hit=0.266   (the whole object)   <- IDENTICAL
```

Every instrument this project owns measures displacement, so every instrument is blind to it. It bites in exactly one
place: **absolute-position lookups** -- *what is in the cell ahead of me*, cell assignment, collision. Which is
precisely the context feature a factored world-model needs, and precisely what the row-entropy test could not compute.

## What it actually is

Not downsampling -- the ban passes, and the frame is full-resolution. It is one level in: **the ontology carves by
COLOUR, and the avatar is not a colour.** It is a two-colour composite, so the type boundary runs through the middle
of the object. `f_tau(object, action, context)` cannot be written for a thing whose `tau` bisects it. The carve is
upstream of the rule, and *"the hard part was never the carving -- it was which block."*

## Fixed here

- `ComponentPercept` -- the rival the colour percept never had: grows the whole connected object from a seed, whatever
  colours it wears. It ties today, and the tie IS the finding.
- **The downsample ban did not scan `micro_market.py` or `marketplace.py`** -- the two files perception now lives in,
  both added after the list was written. A ban that does not scan where the percepts are reports clean forever. Widened.


---

# THE BOOSTER: measured, and the diagnosis moves upstream

> `[I]` *"once the agent grabs the booster on the left, it learns a bad lesson and never sees the benefits or records
> the benefits properly, and then it never applies that to the other objects of the same class, and then never
> calculates that math so that it uses it when it runs out of actions nearly while cycling"*

**Link 2 and link 3 were confirmed and fixed** (`"inst": insts[0]`; `_budget_actions()` = 21 when the truth is 42).
**The literal reading of link 1 is REFUTED by measurement, and the substance of it is worse than stated.**

```
900 actions, 11 game-overs
refills that COST A LIFE     : 22   (respawns)
BOOSTERS ACTUALLY COLLECTED  : 9    <- it DOES grab them
   collected at meter = 8, 8, 8, 8, ...  EVERY SINGLE ONE
actions spent at <=3 on the meter : 79
```

**The booster is never a plan. It is only ever a rescue.** Nine collected, every one at eight actions from death,
and the agent died 22 times anyway. The winner takes 4, never drops below ~57% of the meter, and never dies once.

## A third instance of the class bug, in the consumer that decides whether to GO

```python
_boost = next((a for a in cmap.values() if a.get("effect") == "budget" and a.get("inst")), None)
```

One booster, ever. Fixed here to enumerate every instance of every budget class, nearest reachable first. **Kept.**

## The standing rule was built, measured, and LOST

| | panic rule | standing rule |
|---|---|---|
| boosters collected | 9 | **3** |
| meter when collected | 8, 8, 8 | 12, 20, 20 |
| deaths | 22 | **26** |
| actions nearly-dead | 79 | **90** |
| `max_level` | 1 | 1 |

It fires earlier and far rarer: *"still affordable after the detour"* is almost never true once the meter is under
55%, so it made the panic branch pickier without giving it a working alternative. **Reverted rather than tuned — the
reason it fails is not the threshold.**

## The finding, which no booster policy fixes

**At bar=8 with a plan costing more than 8, the agent is already lost, and no rule about when to detour can save it.**
The winner never arrives at bar=8, because it walks a 41-action path on a 42-action meter. Ours wanders. **The booster
is downstream of navigation: a resource policy cannot repay a debt that pathing keeps running up.**

*(And the first detector reported "31 boosters collected" — it was counting respawns, because the meter also refills
when a life is lost. Caught by checking the lives counter. Same shape as every other error this session: an instrument
that agreed with what was expected.)*


---

# THE RESIDUAL IS ROUTED — arrival's mechanism, plugged in `[LIVE]`

> *"Candidate 2 is a routing job, not a minting job. The atoms exist. The work is connecting them."* — `§7.5`

## The disconnection, located

`PASS 4` — the evolvability engine — lives inside `validate()`. The **avatar regime never calls `validate()`**:

```python
# regime_factory.py
def solve(self, budget=260):
    from objective_validator import _avatar_solve
    return _avatar_solve(self.adapter, self.av, budget=budget)   # straight to the solver
```

Measured live before the fix: `_avatar_solve` 2 calls · `validate()` 1 · `new_engine()` 1 · **`on_residual` 0**.

**The engine was constructed on every single run and dropped on the floor.** Not unbuilt — *unreachable*. ls20 is played
by the avatar regime, so the entire residual→mint route has never once executed on the game the project is stuck on.

## The wire

`_route_avatar_residual()` fires from the avatar regime's own MODEL_INCOMPLETE: the composer ran its model to
exhaustion — aligned what it believed the triggers were, walked where it believed the exit was — and the world paid
nothing. That is *"the grammar was satisfied and unrewarded"* stated in this regime's terms.

It authors nothing. Every atom it reaches already existed:

| atom | job |
|---|---|
| `ResidualReporter` | forward-model prediction error over the objective-keyed `transition_buffer` |
| `CUSUM` | only a **reproduced** residual licenses a mint — one-off noise is pareidolia |
| `triangulate` | does the residual cast a **shadow** across existing primitives? |
| `_route_three_way` | shadow → **CO-OPT** · representable → **MINT** · neither → **ESCALATE, never mint** |
| `DirectedMint` | a new **instance** of a tested kind, **parametrised by the residual**. Aimed, not open-atom. |

## First live routing

```
MODEL_INCOMPLETE: objective <route a mover through free space to an exit (maze)> was SATISFIED
  but produced NO reward; residual = a 'change' change over ...
ROUTE -> CO-OPT (§15): the residual casts a shadow on [object(colour ?, size 1451)] -- signals
  ALREADY in the grammar. Recomposing them into a new composite...
  * MINT.BE_AT@(44, 51): <be located at a target position> aimed at the residual -- drive the
    controllable onto where the reward-linked change occurred

residual: ('change', (0,1,3,9,12), (40,49,49,53))    route: co-opt    speciate: False
```

**The route chose CO-OPT, not MINT** — correctly: the residual casts a shadow on a primitive already held. And
`speciate: False` is CUSUM declining to license a mint on a single occurrence. The apophenia guard worked on its
first live outing.

## The bug the route found in its first breath

The first routing returned residual bbox **rows 40..62 carrying colour 11** — the **HUD**. The agent was reporting
*its own meter draining* as "a dynamic my grammar cannot explain", which is the one thing it explains perfectly. **The
status bar is not the world**, and an aim that points at the meter mints a primitive for arithmetic we already have.
Masked. *(Third time today the HUD has poisoned a measurement: `DeltaPercept`, the booster detector, and now the
residual.)*

## Honest state

`levels_completed = 1`. The route fires **once per ~900 actions** — `_avatar_solve` is called rarely because each
solve is long — so the residual is sampled far too sparsely to reproduce, and without reproduction CUSUM will never
license a mint. **The loop is closed and it is not yet turning.** That is the next thing, and it is a cadence problem,
not a mechanism problem.


---

# `residual_router.py` — the loop turns `[LIVE]`

The route was reachable but sampled **once per ~900 actions**, because it fired at the tail of `_avatar_solve`, a
1900-line function, and inherited that function's cadence. CUSUM licenses a mint only on a **reproduced** residual,
and nothing reproduces at one sample per solve. The loop was closed and not turning.

The engine's own docstring said where it belonged, the whole time:

> *"buffer = list of grids for the CURRENT objective (**reset at each decision point**)"*

A decision point is not a solve. It is every `_goto(cell, reason=...)` -- every time the composer commits to a named
objective and finds out whether the world agreed. Broken out into `residual_router.py` and fired there.

## Two failures on the way, both mine, both instructive

**1. I invented a gate the engine already had.** First cut filtered on *"did anything change outside the avatar's
footprint"* and routed **0 of 107** satisfied-but-unrewarded objectives -- the world almost always changes something.
But *"the world responded"* is not *"the model predicted the response"*, and deciding that is exactly what
`ResidualReporter`'s forward-prediction-error is FOR. I re-implemented the mechanism badly and hid it from its own
evidence. Removed.

**2. `on_residual` DRIVES -- it is not an observer.** It proposes candidate organs and then `descend`/`pursue`-s them
with real actions. Fired at every decision point it ate the entire run: objectives **305 -> 3**, `max_level` **1 -> 0**
-- below the band. The report is cheap; the EXECUTION is not; they were welded together.

## The split, which is the actual fix

**Accumulate cheaply on every objective; hand the engine the wheel only when CUSUM licenses.**

```
report -> count -> CUSUM -> triangulate -> route        (cheap: no actions spent, every objective)
    |
    +-- speciate? --> on_residual(): propose + descend/pursue   (expensive: only on a REPRODUCED residual)
```

That is the engine's own rule -- *a one-off residual is pareidolia* -- applied to its own budget. An agent that spends
its whole meter investigating the first surprise it meets is not doing science; it is doing the thing the meter
measures.

## Live

```
objectives committed to  : 10
objectives SATISFIED     : 7
RESIDUALS ROUTED         : 6        (was 1 per ~900 actions)
three-way routing        : {'co-opt': 6}
distinct residual KINDS  : 4
REPRODUCED residuals     : 2        <- what CUSUM needs, and never had
most-reproduced          : x4
mints LICENSED by CUSUM  : 2        <- speciate was False forever; it is not any more
max_level                : 1        (band: 1 -- no regression, no gain)
```

**A residual has now been seen four times and CUSUM has licensed two mints.** The loop turns. `levels_completed = 1`.


---

# FOUR MECHANISMS FREED FROM THE MONOLITH

```
lines  nested-defs  where
 2002           63  objective_validator.py::_avatar_solve
```

**The composer's own source is the monolith its world-model theory warns about.** *"A program that places all
behavior in one type degenerates to a single monolithic transition."* Everything in `_avatar_solve` is load-bearing
for everything else in it. The residual route was not hidden -- it was inside something too big to see into. Freeing
it was one instance, not the class.

## 1. `budget_model.py` — one model, and the burial CAUSED the second one

`_hud_units`/`_rate`/`_budget_actions` were sealed in the closure. When the market needed budget reasoning it could
not reach them, so `Q1Hud` induced the same quantities from scratch. **Two models of one board, neither able to see
the other**, disagreeing (4.0 vs a true 2), each internally consistent, debugged separately for hours -- Mars Climate
Orbiter with the units the other way round. The trap did not merely hide the code; **it caused a duplicate
implementation of it.** Merged: subtractive, and fed from the one choke every action passes through.

```
budget model: meter=11  lives=8  lives_left=2  one_life=42     <- 42 is ground truth
```

## 2. Negative knowledge now outlives the solve

`_dead_boosters`, `_blocked_targets`, `_visited`, `_probed`, `_shape_ids` were closure locals in a host re-entered
many times per game. **I3 ("archives biodegrade") happening INSIDE the episode** -- worse than at the boundary, since
the boundary is at least a place you expect to lose things. An agent that forgets which booster it drained walks back
to the empty one, on a board where a level costs 41 actions of 42. *(Caught on the way: `_shape_ids` referenced
`_persist` 49 lines before it was defined — the run went to `max_level=0` until the ordering was fixed.)*

## 3. `navigation.py` — the pure half, now testable

`path_cost`, `closest_reachable`, `reachable_from`, `act_toward` — all pure, all previously exercisable only by
playing an entire game. They wanted the same nine host names, which was never a closure; it was an interface nobody
had written down (`BoardView`). Now:

```
act_toward(up) -> ACTION1 · path_cost -> 4 actions · closest_reachable -> {gap: 0, reachable: 142}
    ...with no game, no adapter, no network.
```

**Not extracted: `_goto_inner` (88 lines, 15 host names) and `_reach_escalate` (73/10).** They ACT -- they close over
`_stepw`, `_reconcile_state`, the router. That is a different job and pretending otherwise is how the band gets
broken. `apos` is INJECTED rather than computed: which percept answers "where am I" is a live question (colour vs
component), and navigation must not quietly elect a winner the board has not priced.

## 4. `epoch_loop.py` — selection's boundary

`_epoch_check` worked only because it happened to hang its state on `adapter._micro_market` rather than in the
closure -- a coin landing right way up in a file where the same coin landed wrong five times. An epoch is a LIFE: the
boundary must be something the WORLD does, or selection is paid in a currency the author minted, which by ROOT IV is
a Levin-null loop with extra steps.

## The lesson that cost the most, twice in one hour

**A mint is a probe, not a campaign.** CUSUM licensing a mint means *"this residual is real enough to look at"*, not
*"spend the game on it"*. Handing each licensed mint the solve's budget (260) meant three of them consumed the run:
**the market made 6 decisions in 3062 actions** and the macro shell discovered nothing. Capped to a 24-action probe,
max 2 per level:

```
residual: routed=137  reproduced=127  licensed=2  routes={'co-opt': 134, 'escalate': 3}
epochs=4    market top n=241    macro sites=8 plans=3
```

**`escalate: 3`** — the gap-report refusing to mint into a dimension that casts no shadow. The apophenia interlock,
firing on real evidence for the first time.

## State

`MAX_LEVEL=1` — the band. No regression, no gain. Four mechanisms that could only be reached by playing a whole game
can now be called, tested, and be wrong in public.


---

# THE AUDIT: what is built, correct, and unreachable

Every mechanism hunted for today already existed and was not plugged in: `DirectedMint` 0 refs, `dead_frontier_mint`
0, `EvolvabilityEngine` 0, `ObjectTransitionInducer` 0. So: grep the whole tree.

```
DEFINED, AND NEVER CALLED FROM ANYWHERE  (>=12 lines, no dynamic dispatch hiding them)
   34 mechanisms · 994 lines that nothing in this tree can reach
```

*(A first pass said 9279 lines. That filter counted things reached from inside their own file -- `BudgetModel` via
`budget_model.get()`, `_route_avatar_residual` from its own module. Wrong number, retracted before it became a
talking point. 994 is the real one.)*

## The cluster that matters

```
 51  _exploit_triggers             objective_validator.py
 51  _confirm_cycle_live           objective_validator.py
 43  _perceive_cyclic_triggers     objective_validator.py
 22  TriggerChain                  micro_market.py
 22  learn_cycle                   slot_cycle.py
```

**~190 lines of trigger machinery, unreachable, on a game whose entire mechanic is triggers.**

## `TriggerChain` — the purest instance in the tree

Nine chains are enrolled in the arena. `TriggerChain` is not one of them. What it does:

> *"Carving: causal atoms -- **'stepping HERE changes THAT'**. Stakes that the property actually cycles."*

The one carving that reads this board the way the board actually works. And it had **two independent** reasons to be
silent:

1. **Never enrolled** -- one missing `chains.append(...)`.
2. **`ctx.is_trigger_step()` was a stub: `return False`.** Unconditionally. So even enrolled, it could never advocate.

Not missing. Not broken. Not even unreachable. **Built, wired to a stub, and left out of a list.**

## Fixed

`is_trigger_step` now answers from `avatar_cmap` -- which has held trigger -> effect with live-learned instances the
whole time. **The knowledge was in the system and not in the carving**: the same shape as wall-knowledge living in a
veto chain instead of inside the steer rule as context. Same disease, third location today.

```
trigger_ACTION1   n=73   hit_rate=0.0      <- the mechanic bids for the first time
max_level=1 (band)   steer_ACTION1 0.978   q1_hud 0.991
```

**Honest: hit_rate 0.0 is mine.** I enrolled it with `target_at=None`, so it predicts *"the property at None changes"*
and settles against nothing. The chain is now bidding honestly and being priced as wrong for a reason that has nothing
to do with the board. Next fix, not a win.


---

# THE TRIGGER THREAD, FOLLOWED TO THE BOTTOM

Fixing `target_at=None` did not produce a working carving. It produced a **diagnosis**, and it is the level-1
blocker stated mechanically.

## The chain of fixes, each exposing the next

1. **`TriggerChain` never enrolled** -- one missing `chains.append(...)`. Fixed.
2. **`ctx.is_trigger_step()` was `return False`** -- a stub, so even enrolled it could never advocate. Implemented
   against `avatar_cmap`, which has held trigger -> effect with live-learned instances all along.
3. **`target_at=None`** -- it predicted *"the property at None changes"*: a claim that settles against nothing. It
   staked that **73 times at hit_rate 0.0**. A prediction that cannot be refuted is not modest, it is empty. Now
   resolved late (the key is DISCOVERED, not known at construction) and it **abstains** when the key is unknown.
4. **A booster is not a trigger.** `is_trigger_step` matched ANY atom in the causal map -- and every atom the agent
   has ever learned on this board has `effect='budget'`. It would have called every booster a key-trigger and staked
   that the key cycles when it does not. **A carving that fires on the wrong object is worse than one that abstains:
   it manufactures evidence for a rule it invented.**

## And then the bottom of the thread

```
avatar_cmap (trigger -> effect), after 400 live actions:
   (9, ...)  effect=budget   insts=[(11,36), (56,4)]
   (9, ...)  effect=budget   insts=[(48,36)]
   (0, ...)  effect=None     insts=[None]
```

**Every causal atom the agent has ever learned is `budget` or `None`. Not one is "stepping here cycles the key."**

The agent has learned, live and correctly, **where the resources are**. It has never once learned an atom **about the
objective**. So the trigger carving abstains -- and abstaining is the honest thing for it to do, because there is
nothing true for it to say.

> ### That is the level-1 stall, mechanically: the agent cannot plan to cycle the key because it has never learned
> ### that anything cycles the key. Every fix above was downstream of a causal map with no objective in it.

`levels_completed = 1`. The carving is enrolled, aimed, honest, and silent -- waiting on a map that has never had an
objective atom in it.


---

# THE ROOT, TRACED — and the fix that wasn't enough

Following "why does the classifier learn `budget` and never `cycle`" to the bottom:

## The chain

1. The classifier **can** name `orientation` -- the key cycling. The machinery is complete.
2. It **does** find the key: `PERCEIVE property-display := glyph@(12,36) [KEY/LOCK: shape/orientation IS its state]`.
3. It groups floor objects into trigger types **by (colour, shape)** and probes each by walking to it.
4. Live: **INERT 11 · BUDGET 3 · classified 0.** It reaches triggers. The key does not cycle.

## Why

```python
targets = perceive_targets(g, exclude_color=ctrl)      # exclude_color is SINGULAR. One colour.
if ap is not None and max(abs(pos[0]-ap[0]), abs(pos[1]-ap[1])) <= 2:
    continue                                           # "literally ON the avatar"
```

The avatar is a **5x5 composite: 2 rows of colour 12 over 3 rows of colour 9**. `avatar` names colour 12, so `_apos()`
returns the centroid of the **top half**. The lower half's centroid sits **~2.5 rows** from that point. **The test is
`<= 2`.**

> ### The agent's own body missed the "that is me" test by half a row, was enrolled as a trigger candidate, and the
> ### agent spent probes walking to itself and recording that the key did not cycle.

A body is not a radius around a colour. `_self_footprint()` now grows the actual connected object and excludes all of
it.

## Result: real, and not enough

```
trigger types   : 4 -> 3        (the false candidate is gone)
probe outcomes  : INERT 10, BUDGET 2    (was INERT 11, BUDGET 3)
cmap effects    : {'None': 2, 'budget': 2}      <- still not one 'orientation'
max_level       : 1
```

**The agent still has never learned a single atom about the objective.** It has learned, correctly and live, where the
resources are. Ten probes reach something and find it inert. So either the real key-cyclers are never reached
(navigation), or they are not in the candidate set at all (perception). Both are upstream of everything this session
touched.


---

# THE RE-PARTITIONER, ROUTED TO THE RESIDUAL

> *Minting is not creation. It is re-reading. The constraint is the raw material. The residual is the pressure. The
> operation is drawing a new boundary.*

**Followed up. Both gaps were named earlier and neither was fixed. Both are now closed.**

## Gap 1 — the re-partitioner was never fed

```
ObjectTransitionInducer     refs outside its own file: 0
TransitionInductionEngine   refs outside its own file: 0
LogicalTransitionInducer    refs outside its own file: 0
StaticPairInducer           refs outside its own file: 0
```

And what it is: *"per-OBJECT relational transition rules… matches objects by **colour-signature** + nearest centroid,
induces effects keyed by **(colour_sig, size-bucket, action)** -> translate | vanish | recolor | rotate."*

**That is the factored world model — `f_tau(object, action)` — already built, in this tree, referenced by nothing.**
And it matches by colour SIGNATURE rather than a single colour, which is precisely what this codebase lacks: the
avatar is a two-colour composite and every carve-by-colour ontology cuts it in half.

Now fed from the universal choke, play-area only. Live: **297 transitions · 15 confirmed object rules · 19 object
keys · degenerate=False.**

## Gap 2 — the abduction->molecule bridge WAS the argument `atomics=[]`

```python
base = [(h, d) for (h, d) in atomics if h["descriptor"] in names]   # CoOption.propose
ctx = dict(..., atomics=[], ...)                                     # my wire
```

Co-option routed **134 times and composed over an empty list every time** — the route correct, nothing to recruit.
Candidate 2, exactly: *the molecules exist but are not reachable from abduction; the gap is the bridge, not the
inventory.* The bridge was a missing argument.

The avatar regime never calls `abduce()`, but it has two sources of induced structure and both are grammar: the
**causal map** (trigger-type -> effect) and the **object inducer** (`(colour_sig, size, action) -> effect`). Handing
them over is a shape conversion. **18 atomics now, was 0.**

## What the chisel says, pointed at the board

```
obj:(frozenset({5}), 3, 'ACTION1')          -> (('stay',), 'confirmed')
obj:(frozenset({9, 5}), 2, 'ACTION1')       -> (('stay',), 'confirmed')
obj:(frozenset({0,1,3,5,9,12}), 3, ...)     -> (('stay',), 'contradicted')
```

**Every induced law is `stay`**, and one key is *every colour on the board as a single object*, self-marked
**`contradicted`**. The segmentation is gluing the maze into one blob, so nothing moves, so the only law available is
"nothing moves" — and the inducer says so itself rather than inventing one.

> ### The chisel is routed, fed, and pointed at the board. It reports that its own partition is wrong.
> ### That is the first honest reading Region ③'s machinery has ever produced here, and it is a segmentation
> ### problem — which is *the carve*, again, upstream of everything.

`levels_completed = 1`.


---

# THE CARVE — FIXED `[LIVE]`

Six threads today bottomed out here. One cause, in two files, and the same disease as the other four:
**the knowledge was in the system and not in the carving.**

## The bug

```python
@staticmethod
def _bg(g):
    return int(np.bincount(np.asarray(g).ravel()).argmax())   # ONE colour: the modal one
```

The background of a board is not a colour. It is the **TERRAIN**: floor AND walls. `_bg` returns the modal colour --
the floor -- so **the walls stayed foreground**, and a maze's walls are one connected structure. Every segmentation
returned a single **1451-pixel object** spanning 42% of the board, carrying `frozenset({0,1,3,5,9,12})`: every colour
on the board, as one thing.

`segment_objects` has **always** taken `ignore_colors` -- *"large static structure colors to treat as background
too."* Nobody passed it. And the agent has narrated `terrain := floor(colour 3), walls(colours [4,5])` on **every
single run**, out loud, for the whole project.

## What that one wrong partition was causing

| symptom | mechanism |
|---|---|
| every induced object law was `('stay',)` | one blob, and blobs do not move |
| the blob self-marked `contradicted` | the inducer honestly reporting its own partition was wrong |
| **MINT never fired -- 84/84 co-opt, all session** | a 1451px blob correlates with everything above the 0.15 shadow threshold, so `triangulate` ALWAYS found a shadow, so co-opt ALWAYS won, so **the mint branch was structurally unreachable** |
| the avatar read as its top half | carve-by-colour bisects a two-colour composite |

**The mint route was never blocked because minting is hard. It was blocked because the carve was wrong.**

## Fixed, in both places

`ObjectTransitionInducer._segs` and `ResidualReporter._correlates` both now receive the terrain the composer already
knows. Injected, not guessed.

```
LAWS INDUCED          before: ('stay',) x ALL        now: ('stay',) x17
                                                          ('translate', -5, 0) x1     <- up, one quantum
                                                          ('translate',  0, 5) x1     <- right
                                                          ('translate',  5, 0) x1     <- down
keys with 5+ colours  before: 1 (the maze as one)    now: 0
THE SHADOW TEST       before: object(?, 1451)        now: object(?, 25) @ 0.48
                              ^ the maze                   ^ 5x5 = THE WHOLE AVATAR
```

**The first real object laws this system has ever induced** -- translation, by exactly the 5px quantum, under three
actions. That is the avatar, seen whole, as one object, for the first time.

And `co-opt` still wins -- but now **for the right reason**. It used to win because a blob correlated with everything;
the decision was an artifact. It now wins because the residual genuinely correlates with the avatar at 0.48. **The
routing decision is real for the first time.**

`MAX_LEVEL=1`, band held. `levels_completed = 1`.


---

# THE ISOLATION AUDIT — including my own

> *"The knowledge is in the system and not in the carving."*

## The one I committed today

**`navigation.py` — extracted this session, unit-tested with no game attached, celebrated, and never wired.** The
composer went on calling its nested `_path_cost` / `_closest_reachable` / `_act_toward`, and the module was
decoration. **Two implementations of one thing — the exact failure that made the budget model disagree with itself
for hours — created by me, in the same session I spent auditing other people's version of it.**

Fixed: the composer now delegates to `navigation.py`, with the local copies as fallback only. Subtractive.
`MAX_LEVEL=1`, band held, `residual routed=108`.

## The rest, classified — because "nothing isolated" cannot mean "wire everything"

```
ENTRY POINT   run_evolve · ouro_trial · submission_agent      run directly. Correct.
OFFLINE TOOL  primitive_ledger · level_segmenter · frame_delta  the agent SHOULD not import these.
OTHER-GAME    joint_state_push (Sokoban) · slot_cycle (lp85) · dynamics_forecast (P7)
```

**True orphans remaining: 0.**

## The judgement, stated plainly

The three OTHER-GAME modules are real primitives for game families we are not playing, and **nothing can reach them
from any regime** -- so even when the right game appears, they will not fire. That is a genuine gap.

**And wiring them now would be a mistake.** §3.4 measured it: adding capability before fixing upstream perception has
consistently *hurt* -- highest scores (0.21-0.22) predate the elaboration. Reaching for `joint_state_push` while the
agent cannot learn a single atom about ls20's objective is the elaboration trap with a clean conscience. They stay
dormant and NAMED, which is the honest state: a known gap, priced, not silently carried.

**The test is not "is it reachable" -- it is "is it unreachable AND should it be reachable NOW."** By that test the
tree is clean.


---

# `model_search.py` — the missing molecule, and three modules dissolved

## The decomposition

Three unreachable game-specific planners. Strip the game off each and the same sentence remains:

```
joint_state_push   "a move into a crate pushes it"          =  OBJECT LAW: (obj, action) -> translate(dr,dc)
slot_cycle         "contents advance by a pitch"            =  OBJECT LAW WITH A PERIOD
dynamics_forecast  "extrapolate an autonomous mover"        =  OBJECT LAW UNDER A NO-OP
```

**They are not three planners. They are one planner over three learned laws** -- and the laws are not ours to write,
they are the board's to teach. `ObjectTransitionInducer` already induces that shape, keyed by
`(colour_signature, size_bucket, action)`. `simulate()` already rolls it forward. **Both existed. Nothing called
`simulate()`.** This module is the caller.

| molecule | status |
|---|---|
| `induce_object_law` | wired earlier today; producing `translate(-5,0)` |
| `simulate(state, action)` | existed, called by nothing |
| **`search over simulate`** | **built: `ModelSearch.plan()`** |

The three are now **goal_tests, not modules**: Sokoban is `plan(goal_objects_at(...))`, the belt and ls20's key are
both `plan(goal_property_at(...))`, forecasting is `forecast(state, steps)`. **No Sokoban detector, no belt detector,
no regime router** -- the induced model tells you what game you are in. That is kernel-not-library as code rather
than as a position, and it is subtractive: three modules marked dissolved.

## THE LICENCE — and the trap it catches

Searching over a model that does not predict is searching over FICTION, with the meter running, at full confidence.
So the molecule does not decide it is ready. The MODEL decides, via honesty machinery the inducer already carried:

```python
fidelity     = 1 - wrong/predicted
degenerate   = (motion_rules < 2)      # "nothing ever moves"
identifiable = contradiction <= 0.15 and fidelity >= 0.6 and not degenerate
```

Tested in **both** directions, which is the only way a gate means anything:

```
GOOD model                  licensed=True   plan=16 actions   <- optimal (8 down + 8 across)
ls20's ACTUAL model         licensed=False  ABSTAINED
LAZY model (fidelity 1.0!)  licensed=False  ABSTAINED
      refused: DEGENERATE -- it has learned 'nothing moves', which scores well and means nothing
```

> ### A model that predicts "nothing ever changes" scores **perfect fidelity** on a mostly-static board.
> ### `predict_error` alone would be fooled. `predict_error` + `degenerate` is not.

## State on ls20

```
fidelity 0.353 · degenerate True · contradiction 0.2  ->  NOT LICENSED  ->  the molecule abstains
MAX_LEVEL=1 (band held)
```

**That is the molecule working, not failing.** Same shape as TriggerChain abstaining when the key is unknown: an
agent planning over a model it cannot predict with is not planning. The gate now stands between this system and its
most seductive failure -- and it is the carve, not the search, that has to clear it.


---

# THE MIXED ROW WAS A MISSING FEATURE

```python
def _key(self, o, action):
    return (frozenset(o["color_sig"]), self._bucket(o["size"]), _akey(action))     # NO CONTEXT
```

The avatar under `ACTION1` produced **both** `translate(-5,0)` and `stay` -- because sometimes there was a wall
there. Same precondition, different effects -> `contradictory` -> never confirmed -> `motion_rules < 2` ->
`degenerate` -> **fidelity 0.353** and a model nothing may plan over.

**The row was never noisy. It was under-specified.** A mixed row is not evidence that the world is stochastic; it is
evidence that the precondition is missing a feature -- and the fix is to NAME the feature, not widen the tolerance.
The feature is *what the object is about to enter*.

## And the model learns the feature from itself

`_delta_for(action)` reads the action->delta map off **the model's own confirmed translate rules**. Nothing is
supplied. Before any translate confirms it returns None and the key stays context-free: the model does not pretend to
a feature it has not earned.

## Synthetic proof: one mover, a wall in some directions

```
sig={7}  ctx=None -> ('translate',-1,0) [tentative]     before any delta was known
sig={7}  ctx=0    -> ('translate',-1,0) [confirmed]     floor ahead -> MOVES
sig={7}  ctx=5    -> ('stay',)          [confirmed]     wall  ahead -> BLOCKED

contradiction 0.2 -> 0.0        fidelity 0.353 -> 0.7
```

## Live on ls20

```
                       before    now
contradiction_rate        0.2    0.02      <- the row split
degenerate               True    False     <- motion rules confirmed for the first time
object_rules_confirmed      9    22
fidelity                0.353    0.416     <- STILL < 0.6.  LICENCE REFUSED.

laws:  stay ctx=4 x10  (wall ahead -> blocked)      translate ctx=3 x1  (floor ahead -> moves)
       stay ctx=-1 x1  (off-board -> blocked)       stay ctx=3 x8       (floor ahead, but a DECORATION)
```

**Every law it learned is correct.** And the gate still refuses, because 0.416 means it is wrong about the world more
often than it is right, and `ModelSearch` will not plan over that.

Caught on the way: `_delta_for` unpacked a 3-tuple key I had just made 4-wide, and `simulate` built its lookup key
**without the grid** -- which would have matched nothing the model learned, predicted "stay" for everything, and
scored a degenerate fidelity of ~1.0. **The most dangerous bug of the day, caught by the gate it was about to fool.**

`MAX_LEVEL=1`. Three of the four licence conditions now pass. The fourth is the honest one.


---

# THREE RE-EXAMINATIONS, ALL LANDED

## 1. The shadow test was reading the AFTER-state — the tautology direction, live

```python
res.correlates = self._correlates(res, base_before, base_after, traces)
    bg = _bg(g_after);  segment_objects(g_after, ...)      # "which object does the residual sit in"
```

The residual **is** the change. Asking which after-state object contains the changed cells asks the outcome to
explain itself -- the object is partly CONSTITUTED by the residual it is being credited with. That is *"the block
moved because the block moved"* with a segmentation in front of it.

**And the guard caught that my first fix was incomplete.** I changed the body to read `g_before`; the function still
RECEIVED `g_after`. A function handed the outcome can read the outcome, and the next edit will. **The parameter is
gone.** Don't-look became can't-look -- the difference between a convention and a bound.

## 2. The market's price could not re-clear inside a life — this was the big one

```
steer_ACTION1  n=258  hit_rate=0.981          (measured live)
consecutive WRONG frames to drag it below 0.90:  24  |  below 0.60: 164  |  below 0.50: 249
A LIFE IS 42 ACTIONS.
```

**A carving right for 258 frames owned the wheel for the rest of the game.** It needed 164 consecutive errors to lose
its price and it dies at 42. At a regime change the hardened level-1 carving is maximally confident and maximally
wrong, and the price was **structurally incapable of moving** -- not a fixed valuation by design, one by arithmetic,
which is worse because it looks dynamic.

Salience is a claim about THIS FRAME. A vantage does not own the wheel; it rents it, per frame. Price is now a
recency-weighted hit rate (EWMA, half-life ~8). The cumulative rate is KEPT for reporting -- it is a fact about the
past and it must never be a price. `confirmations` capped: a long record is evidence, never a franchise.

```
after 258 frames at 0.981:  cumulative=0.981   PRICE=0.528     <- only one of them noticed the last 5 misses
after 11 wrong frames:      cumulative=0.941   PRICE=0.129
after 24 wrong frames:      cumulative=0.897   PRICE=0.025
                            ^ unmoved          ^ re-cleared, inside a life
```

**164 wrong frames to lose the wheel -> 11.**

## 3. `no_posthoc.py` — a hard bound, at import, beside the downsampling ban

**HARD-BOUND WHERE A DIAL WOULD BE GAMED**, and this is the clearest case in the tree: the exploit is not merely
available, it is *the highest-scoring move on the board*.

```
MDL sweep over a predicate family on a synthetic residual:
  [TAUTOLOGY] "did it move"          |phi|=36   R|phi=0.0   gain +189.7   <- WINS
  ctx: colour at centroid+delta      |phi|=52   R|phi=0.0   gain +173.7   <- the truth, rediscovered UNAIDED
  step parity / step mod 3 / row / col / n-walls              NEGATIVE    <- superstition, rejected by arithmetic
  ctx BEHIND me (identical |phi|=52) 52       225.1          -51.4        <- same cost, wrong cell, rejected
```

Two results. **The search DID rediscover the hand-picked predicate unaided**, by a wide margin over every other real
candidate -- the mechanism is real. **And the tautology beat it.** A predicate reading the after-state compresses the
residual to ZERO bits, so it beats every genuine regularity systematically -- and would promote on echo and predict
nothing on every game we ever run.

So *"phi must be evaluable BEFORE the action"* is not a footnote. **MDL alone does not work.** The before-state
constraint is not what makes the mechanism honest; it is what makes it FUNCTION.

The bound is exact about what it does NOT cover -- `_effect(oa,ob)` is a LABEL, `settle(before,after)` is an OUTCOME,
the residual IS a diff. Those must read the outcome; that is their job.

> **A predicate is a question asked of the world BEFORE you act. A label is what the world answered.
> Nothing may be both.**

Verified in both directions: passes on the live tree, **fires on reintroduction**.

```
MAX_LEVEL=1 (band held) · residual routed=127 · both hard bounds PASS · fidelity tests PASS
```


---

# NARRATION AUDIT — every new feature now speaks

The standing rule: the frame data is the debugging surface, and a feature that does not narrate cannot be debugged
from inside the agent. Audited today's eight additions; **four were mute**, and the worst was the worst kind:

```
model_search.py     emit references: 0     <- it REFUSED TO PLAN and said nothing
budget_model.py     emit references: 0     <- "one life = 42 actions" never narrated
navigation.py       emit references: 0
"ctx="              0 emits                <- the context feature that split the row was silent
```

**`ModelSearch` abstained silently.** The agent decided its own world-model was untrustworthy, declined to plan over
it, and never said so -- an invisible decision, diagnosable only from outside the agent, which is where every wrong
theory in this session came from.

Now, in the agent's own stream:

```
CARVE   terrain := colours [3,4,5] are the BOARD, not objects on it -- I stop growing components through
        them. Every rule learned under the old partition is discarded: a law induced from a wrong carve is
        not evidence.
MODEL   120 transitions -> 23 confirmed object-laws, 3 of them MOTION. fidelity 0.419, contradiction 0.02.
        NOT identifiable -- I will not plan over this.
MODEL   240 transitions -> 24 confirmed object-laws, 3 of them MOTION. fidelity 0.395 ...
BUDGET  the longest meter I have SEEN so far = 34 actions ... This is a floor, not the capacity: it can only
        rise, and it is not settled until I have seen a full refill.
RESIDUAL [probe trigger-type ...] change x1 -> CO-OPT  [first sighting -- watching, not minting]
```

**Corrected on the way:** the budget line said *"one full meter = 34 ACTIONS"* -- stating a floor (the max seen so
far) as a settled capacity. The true value is 42. A narration that overstates its own certainty poisons every later
reading of the stream, which is precisely what the stream exists to prevent.

## Two things the stream said that I did not put there

**1. fidelity is FALLING: 0.419 -> 0.395.** More data, worse predictions. Not a model that needs more time -- a model
whose preconditions are still under-specified, confirming rules that do not generalise.

**2. The agent SEES the objective happen and cannot name it:**

```
PROPRIOCEPT  moved as intended, but 32 cells changed ELSEWHERE too -> my move CO-TRIGGERED something;
             noting it for cause-analysis
PROPRIOCEPT  moved as intended, but 38 cells changed ELSEWHERE too -> ...
```

32 and 38 cells change elsewhere when it moves. It notes them "for cause-analysis". The cause-analysis returns
`effect=None`. **That is the level-1 stall in the agent's own words, and it is a different diagnosis than "the probe
never reaches the key-cyclers":** it reaches them, it detects the co-trigger, and it cannot name what changed.

`MAX_LEVEL=1` · both hard bounds PASS · fidelity tests PASS


---

# "IS 120 TRANSITIONS TOO LONG?" — the interval was the small half

**Yes** -- a LIFE is 42 actions, so reporting every 120 meant the model said nothing about itself for two lives out
of three: a feedback interval longer than the thing it informs. Now **30**.

**But the MEASURE was the bug**, and it is the same one fixed in the market price an hour earlier, sitting in the one
number that gates everything:

```python
fidelity = 1 - self._wrong / self._pred        # CUMULATIVE. Over every transition. Forever.
```

A model NECESSARILY starts wrong -- it has no rules yet -- so the lifetime figure permanently carries the errors of
its own learning period:

```
wrong for first 200, then PERFECT for 100  ->  lifetime 0.333   REFUSED
wrong for first 200, then PERFECT for 300  ->  lifetime 0.600   licensed at last
```

**A model that becomes perfect at transition 200 must be perfect for 300 more just to reach the gate -- and the agent
dies every 42. The carve could be fixed and the licence would still refuse, for reasons entirely about the past.**

The licence asks *"can I plan over this NOW"*. The lifetime figure answers *"how has this done since birth"*. Now:
EWMA fidelity gates; lifetime is reported as history and never as the gate.

```
MODEL  30 transitions -> fidelity NOW 0.344 (lifetime 0.235) ... NOT identifiable
MODEL  60 transitions -> fidelity NOW 0.442 (lifetime 0.344) ... NOT identifiable
MODEL  90 transitions -> fidelity NOW 0.313 (lifetime 0.34)  ... NOT identifiable
MODEL 120 transitions -> fidelity NOW 0.452 (lifetime 0.326) ... NOT identifiable
```

They diverge, and the report now lands 4+ times per run instead of 2. The signal is NOISY (0.34 -> 0.44 -> 0.31 ->
0.45), not trending -- which retires "fidelity is falling" as a reading of the lifetime figure.

## CLAUDE'S OVERCLAIM, RETRACTED

I claimed `predict_error` was whole-board cell error, that "predict nothing" would score ~0.99, and therefore that
fidelity 0.4 meant **the model is worse than doing nothing**. **Wrong, and backwards.**

```python
active = (before != after) | (pred != before)      # cells that CHANGED, or that we PREDICTED would change
return count_nonzero((pred != after) & active) / count_nonzero(active)
```

It scores only the ACTIVE cells. Predicting nothing means `pred == before`, so `active` is exactly the cells that
changed and every one is wrong -> **fidelity 0.0, not 0.99.** A model that says nothing scores ZERO here.

`fidelity 0.395` means *of the cells actually in play, the model gets 39.5% right* -- a real, non-degenerate,
hard-to-fool measure. **The trap I thought I had found had already been thought about by whoever wrote the
function.** Checked before it became a finding; documented so the next reader does not re-discover my error.

`MAX_LEVEL=1` · both hard bounds PASS · fidelity tests PASS


---

# SWEEP: every instance of the day's bug classes

Three cumulative-vs-recent bugs were found today, all the same shape: **a window longer than the life it informs.**
The price (164 frames vs 42). The fidelity (300 transitions vs 42). The narration (120 vs 42). Swept the tree for
the rest.

## CLASS A — a feedback interval longer than a life

```
run_evolve.py:70   steps % 250 == 0 -> dump()      a JSON status write, not feedback. CLEAN.
```
Only instance. Clean.

## CLASS B — a lifetime ratio used as a DECISION

### FOUND: `standing()` — and it is the function that actually decides

```python
def standing(self, actor_id, ledger):
    return (r.get("hits", 0.0) / n) if n > 0 else 0.0        # LIFETIME
```

Called four times, including inside `resolve()`:

```python
p_std = currency.standing(proposer);   v_std = currency.standing(voter)
if p_std >= v_std:  vote "for"
```

**Every vote in the marketplace was cast by comparing two lifetime track records.** `weight_terms` was fixed to price
on recency an hour before this was found -- `standing` is the one that picks the winner, and it was missed. At n=258
hit_rate=0.981 it takes **164 consecutive errors** to fall below 0.6 and a life is **42**: a carving that was right
early could not be outvoted inside a life however wrong it had become. **That is not a marketplace, it is an
incumbency.** Now reads recency; `standing_lifetime()` kept for reporting.

### FOUND: the MACRO price had an uncapped franchise term

`marketplace.py::weight_terms` averages over EPOCHS, and an epoch IS a life -- a short window in the right unit, so
that part was sound. But `wins` was cumulative and **uncapped**: a plan that won early accrued unbounded weight
forever. Same franchise, other shell. Capped at 10, exactly as `confirmations` is in the micro currency.

### CORRECT AS-IS: the cull — and it is now documented so nobody "fixes" it

```
the PRICE asks "who drives THIS frame"                  -> recency. A vantage RENTS the wheel, per frame.
the CULL  asks "has this had a fair run and is still wrong" -> lifetime. Existence is a verdict on the whole run.
```

Culling on recency would delete a carving for being wrong about level 2 when it was the only thing that ever worked
on level 1. **The sliderule point is that both shells stay occupied; a monoculture is a slide rule with one reading.**

### Reporting-only, correctly lifetime: `standings()` x2, `standing_lifetime()`, percept report.

## The class, named

> **A measure's window must be shorter than the life it informs.**
> Price: recency. Existence: lifetime. Narration: inside a life. History: reported, never a gate.

`MAX_LEVEL=1` (band held, epochs=4) · both hard bounds PASS · fidelity tests PASS


---

# CADENCE: MEASURED, NOT CHOSEN

30 was a luckier magic number than 120, and that is all it was. **A life is a property of the GAME, not of the code.**
At 200 actions per life a fixed 30 reports six times per life and drowns the stream; at 12 it reports never, and the
model is mute for exactly the life it was meant to inform. Same defect as pricing a carving on its lifetime hit-rate,
same fix: `budget_model` already measures `one_life()` off the bar -- use it.

`BudgetModel.report_interval()` -- **a fraction of a life, bounded both ways:**

```
REPORT_FRACTION = 0.25     ~4 reports per life: often enough to steer inside one, rare enough to read
REPORT_MIN      = 5        FLOOR   -- a short life must not drown the stream in noise
REPORT_MAX      = 60       CEILING -- an unmeasurable life must not produce an unmeasured model
```

**The ceiling is the one that matters.** If the meter never drains, or there is no meter, or a life is effectively
unbounded, `one_life()` is None or enormous -- and *a fraction of infinity is silence*. A game with no meter would
have produced a model that never reports on itself: the exact failure we started from, reached by correct arithmetic.
So an unmeasured life falls back to the cap and the agent keeps speaking.

## Live — and it self-corrected while running

```
MODEL  [every  8 actions = 1/4 of a 34-action life] ...     <- early: life measured as 34
MODEL  [every 10 actions = 1/4 of a 42-action life] ...     <- later: 42 measured, cadence TRACKED IT

one_life measured: 42  ->  report every 10 actions
41 reports in 420 actions          (120 gave 2 · 30 gave 4)
```

The interval is derived from the bar, and when `one_life` corrected itself 34 -> 42 the cadence followed with nobody
touching it. And it holds on games we have never played:

```
one_life      every   /life   
None            60      -      no meter measured yet -> cap, NOT silence
8                5     1.6     floored
42              10     4.2
200             50     4.0
10,000,000      60      -      capped
```

**The agent now states its own cadence in the stream** -- `[every 10 actions = 1/4 of a 42-action life]` -- so a
reader can see not just the measurement but how often it is being taken, and whether that is fast enough to matter.

`MAX_LEVEL=1` · both hard bounds PASS · fidelity tests PASS


---

# EVERY BUDGET, PRICED IN LIVES

Audited every action-denominated constant against the measured 42-action life:

```
MINT_PROBE_BUDGET   24    57% of a life   *** under a comment reading "a probe, not a campaign" ***
_goto cap           40    95%             ONE navigation call may spend a whole life
epoch DEFAULT_CAP  120   286%             the artificial mortality is 3x the real one
max_depth           40    95%             planning 40 steps ahead when you have 42
max_expansions    4000    n/a             CPU, not actions -- correctly unpriced
EWMA half-life       8    19%             ok
```

**Not wrong by a little. Wrong by the same order as the thing they budget** -- on a board that publishes its own life
on the bar, every frame. I diagnosed "the mint spends like a campaign", capped it at a number I made up, wrote a
paragraph explaining why campaigns are bad, and set it to 57% of a life.

> **A constant in ACTIONS is a claim about how much of a life something deserves. Price it in lives, or it is not a
> budget -- it is a wish.**

`BudgetModel.actions_fraction(frac, lo, hi=one_life)` -- and the ceiling defaults to a life, because *nothing that
spends actions may exceed the life it spends them from.*

| budget | was | now |
|---|---|---|
| mint probe | 24 (57%) | **a quarter of a life** |
| `_goto` cap | 40 (95%) | **half a life** -- no plan makes walking to one cell worth an entire life |
| epoch mortality | 120 (286%) | **one measured life** -- an epoch IS a life |
| plan horizon | 40 (95%) | **one life** -- *you cannot plan further than you can live* |

**The epoch cap is the sharpest.** Where a game kills you, real death fires first and the cap never mattered --
which is exactly why nobody noticed. On a game that does NOT kill you, that number **is** the generation boundary,
and a boundary three lives long means selection runs a third as often as the world allows. The bug was invisible on
ls20 and would have been silent and expensive everywhere else.

**And the plan horizon:** every step past the meter is a step the agent will never take. Searching them is not
caution, it is fiction with a CPU bill. The horizon is a property of the BOARD, not of the planner.

```
   one_life   mint probe   goto cap   epoch cap   plan horizon
   None       8            20         120         40          <- fallbacks, until the bar is read once
   12         4            6          12          12
   42         10           21         42          42
   200        50           100        200         200
```

**Before: 24 / 40 / 120 / 40 on every game ever played, forever.**

`MAX_LEVEL=1` · both hard bounds PASS · fidelity tests PASS


---

# LEGIBILITY — every live DECIDER can speak

46 modules were mute. **"Everything emits" would be the wrong fix:** a module that computes a path cost decides
nothing; the thing that acts on it does. The rule that matters is narrower:

> **A module that makes a decision the agent acts on must be able to say so. A module that computes a value for
> someone else to decide with speaks through its caller. And 24 of the mute modules are unreachable, dissolved, or
> offline tooling -- wiring a voice into unreachable code is worse than leaving it quiet.**

Live-and-mute-and-deciding, now fixed:

| module | the decision it was making silently |
|---|---|
| `budget_model` | how many actions remain -- borrowed the composer's voice, owned none |
| `navigation` | `closest_reachable` returns a GAP: **"I cannot get there"** -- returned as a dict, never spoken |
| `no_posthoc` | a HARD BOUND. It raised on violation and **never said it HELD** |
| `spatial_map` | what is passable |

**`no_posthoc` is the interesting one.** A bound that only speaks when violated is a bound nobody knows is there: on
a healthy tree it is perfectly, permanently silent, and a reader of the frame data cannot tell the agent is operating
under it. **The constraints an agent is bound by belong in its record, not only in its source.**

## The stream, live — house style intact

```
BOUND   no predicate may read the after-state := ENFORCED at import over 4 predicate-builders
        [a predicate that reads the outcome compresses the residual to ZERO bits and scores +189.7 on
         MDL against the truth's +173.7 -- it wins systematically and predicts nothing. Hard-bound
         rather than dialled BECAUSE it is the highest-scoring move on the board]

BUDGET  meter := colour 11  [BECAUSE it is the only colour that ONLY EVER FALLS between refills --
        nothing told me; I watched it]
BUDGET  lives := colour 8   [BECAUSE it NEVER rises and falls at every refill -- a life is the one
        thing on this board that cannot be bought back]

CARVE   terrain := colours [3,4,5] are the BOARD, not objects on it -- I stop growing components
        through them. Every rule learned under the old partition is discarded.

MODEL   [every 10 actions = 1/4 of a 42-action life] 20 transitions -> 14 confirmed object-laws,
        3 of them MOTION. fidelity NOW 0.336 (lifetime 0.188 -- kept as history, never as the gate)

REACH   target (r,c) is UNREACHABLE := nearest cell I can stand on is N steps short
        [M cells reachable under the map I have LEARNED -- unreachable means unreachable under my
         current map, never 'give up']

RESIDUAL [probe trigger-type ...] change x1 -> CO-OPT  [first sighting -- watching, not minting]
```

`KEYWORD claim := value [BECAUSE reason]`, `--` as separator, **once-keyed** so a line repeated every action cannot
turn the record into a log. 26 distinct claims per run. A line repeated every step is noise, and noise is where a
real finding goes to hide.

`MAX_LEVEL=1` · both hard bounds PASS · fidelity tests PASS · 67 modules parse


---

# THE UNREACHED LEDGER — and 276 lines removed

Asked whether anything unreachable SHOULD be reachable, and whether the truly-unused should go. Both — and the answer
to the first was worse than expected.

## `footprint.py` — the sixth hand-rebuild, and my retraction

> *"STANDALONE causal, modality-aware self-footprint extractor. Goal: extract the SET OF CELLS that constitute the
> self's effect, WITHOUT being handed a marker_color (which would just inherit the controllable-ID wall)."*

**I wrote `_self_footprint()` by hand today** to fix the composite-avatar bug — seeded from `avatar` (colour 12),
growing a component. **It is handed a marker colour. It inherits exactly the wall this module's docstring names.**

**But I was too quick, and the truth is more interesting:**

- `footprint.py:33` and `:66` call **`ad.reset()`** — RESET is HARD-BANNED during gameplay; it wipes level progress
  to 0. The module predates the ban.
- `causal_marker_color()` returns the **dominant NON-BACKGROUND colour** — i.e. ONE colour. The same wall.

**The module names the controllable-ID wall in its docstring and then walks into it.** The docstring is aspirational.
So I did NOT reinvent it worse: its IDEA (derive the self causally from discriminative cells) beats my colour-seed;
its IMPLEMENTATION carries my wall AND a banned reset. **The reusable part is `discr_union`** — the discriminative
CELL SET, the whole body whatever colours it wears — and freeing it means deriving it without a reset.

## `proprioception.py` (509) — unreachable, while the composer runs its own

The `PROPRIOCEPT` lines in the stream come from `objective_validator.py:4348`, not from the 509-line module. **Two
implementations of one thing** — the duplication-by-burial that made the budget model disagree with itself for hours.
Seventh instance today.

## REMOVED — 276 lines

`joint_state_push.py` · `slot_cycle.py` · `dynamics_forecast.py`. Superseded by `model_search.py`: each was one
planner over a learned object law; all three are now a `goal_test` plus `plan()`/`forecast()`. The only references
were `model_search`'s own docstring naming what it dissolved. **Band held after the prune** (`MAX_LEVEL=1`,
`epochs=6`). Recoverable from the `molecules` snapshot.

## KEPT — and correctly unimported

Entry points (`run_evolve`, `submission_agent`, `ouro_trial`) · the harness (`online_harness` imports the agent, not
the reverse) · tests · offline tools (`frame_delta`, `level_segmenter`, `primitive_ledger` — the agent SHOULD not
import these).

## `UNREACHED.md` — the countermeasure

Not a TODO list. A **priced ledger**: each entry is a mechanism that exists, works, and cannot fire, WITH the reason
it cannot. Six times this session a mechanism was hand-rebuilt that was already in the tree. A ledger is the only
thing that stops a seventh.

> **Unreachable is not dormant.** Dormant means a route exists and the board has not asked. Unreachable means no
> route exists, so it will not fire when the board DOES ask. The first is design. The second is a defect, and it
> must be named and priced rather than rediscovered by hand.

`MAX_LEVEL=1` · 64 modules · both hard bounds PASS · fidelity tests PASS
