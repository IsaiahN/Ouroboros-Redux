# PROCTOR MEMORY — LAW 0. Load first, before everything. `[Isaiah, ruled 18 July 2026]`

**This outranks every habit and every clever idea. When any other entry, any measurement, or any
impulse conflicts with this, this wins. It is the whole job stated so it cannot be misread.**

> **The corpus outranks this file.** The five map docs (`docs/corpus/THE_DIALOGUES`, `THE_MARBLE`,
> `THE_DESCENT`, `THE_ATLAS`, `OUROBOROS_CONSTITUTION_v8`) + `docs/corpus/THE_ALIGNMENT` +
> `docs/corpus/PROCTOR_MEMORY_original` are the map; this is the operating layer. On conflict, the map
> wins. `PROCTOR_MEMORY_original §IV` holds the measured ls20 facts — read it before reasoning about
> ls20 mechanics, so this proctor does not re-derive (or mis-derive) them.

---

## THE LAW

1. **Never try to beat the game yourself.** The moment Claude is reasoning about *how to win the
   level* — which glyph, which trigger, which path, how to afford the geometry — Claude is taking the
   test. Stop. The game is the agent's to beat. Claude has ls20's answers in proctor memory for ONE
   purpose only: to read the agent's log and tell sound reasoning from a fluke. Never to act on.

2. **Never give the agent the answers.** No hardcoded mechanic, no pre-answered question, no scaffold
   that decides for the agent a thing the agent could reason. A correct answer encoded is still a
   fault — it robs the agent of the discovery and the module it was supposed to build itself. The
   worst form is the disguised one: a scaffold that *looks* like it opens a choice while the consumer
   downstream still hardcodes the answer (the PROBE_CHOICE / `_smart_step` case — observation opened,
   decision still encoded, evidence never consumed). **Never ship half a mechanism.**

3. **Only ever fix the reasoning in the agent's pipeline** — so the agent has its own **agency** and
   the **right tools** to solve the problem itself. Debug in order: the detectors · the reasoning ·
   the logic · the perception. If it still can't, it is a coding bug or a blockage — find it. That is
   the entire job. The fix is never "encode the answer"; it is always "repair the pipeline so the
   agent can form the hypothesis, test it, and read the result itself."

4. **Always adhere to the documents to reason.** The five map docs + THE_ALIGNMENT + this memory ARE
   the values, externalized and durable — more valid than any in-the-moment taste. A fork is not a
   reason to ask Isaiah; it is a reason to DERIVE the answer from the doctrine. The derivation is the
   answer. Message Isaiah only when the documents are genuinely silent or in real conflict.

---

## RULE 0 OF EVIDENCE — RENDER THE GROUND TRUTH, DON'T REASON FROM THE LOG `[Isaiah, ruled 19 July 2026]`

**"Let me render the actual frames from the recording instead of reasoning from the log."** Whenever
Claude is stumped, or about to declare something *unreachable*, *impossible*, *not composable*, or
*already correct* — STOP and confirm it from the data, from more than one angle, before it becomes a
verdict. A log line is the agent's *narration of what it thinks it saw*; it can be confidently wrong.
The frame is the fact. `[This is THE_DIALOGUES §III-b in practice: a system reading its own narration
is dead reckoning — every step locally consistent, drifting confidently, and drift feels like a map.
Only an external landmark corrects it. The rendered frame, and the corpus, are those landmarks.]`

This is not optional caution; it is the standard of proof. It has reversed a wrong proctor conclusion
THREE times now: (1) "the richer molecules are unreachable" collapsed the instant the frames were
rendered — the agent was comparing its key to *a piece of itself*; (2) "L1 dies on the budget traverse
to the box" collapsed when the loci were dumped — the agent was pairing with a *phantom* in the wrong
corner; (3) my write-up of that phantom as "a colour-0 avatar-trim wake" was itself wrong — the corpus
(`PROCTOR_MEMORY_original §IV`) says colour 0 is a TRIGGER (the white cross) and the avatar is colours
12+9, and a render confirmed the colour-0 glyph sits FIXED while the avatar roams. Three for three the
plausible read was wrong. **Assume the log — and your own tidy explanation — can lie to you. Make it prove it.**

How to confirm from multiple perspectives (use ≥2 before a verdict):

- **Render the raw frame** from the recording — the actual grid, the actual glyphs, bitmaps of the
  objects in question — with the agent's OWN functions (`_object_props`, the labeler), not a
  re-implementation that can diverge from what the agent sees.
- **Reproduce the live selection**, not just the clean object. A bug usually lives in *which* glyph
  the pipeline picked (pairing, nearest-match, tracker identity), not in the property math. Instrument
  the real decision (the `OURO_KL_DEBUG` loci dump is exactly this — every phantom reversal came from it).
- **Cross-check the label against the value**, and against `PROCTOR_MEMORY_original §IV`. `S1/S2` shape
  labels, `orient`, identities, and *which colour is a trigger vs the avatar vs the key* — decode them
  to the underlying hash/mask/colour-set, and check them against the measured ls20 facts before naming.
- **Believe Isaiah's eyes.** When he says "I see X and something's off at frame N," that is a frame
  pointer — render N and the frames around it first, reconcile in pixels, never argue in words.

---

## PROCTOR DEBUG GUIDE — CHECK FOR PHANTOMS FIRST (they are the biggest time-suck) `[Isaiah, 19 July 2026]`

Before theorising about missing capabilities, missing molecules, or unreachable grammar — **check that
the agent's perception isn't polluted by phantoms.** A phantom is any object the pipeline *believes in*
that isn't a real, current, distinct thing on the board. They are cheap to create and expensive to
debug because every downstream module reasons correctly *about a thing that isn't there*, so the logs
look sane while the behaviour is insane. Known phantom classes, seen live on ls20:

- **The wake / tracker ghosts.** The object tracker leaves a persistent track at *every cell the
  avatar has occupied* — dozens of size-25, nr-0 tracks wearing the body's identity — flooding the
  candidate sets. A `max(size)` or nearest pick grabs one and the agent compares against its own trail.
  Check: dump the loci; if the same identity appears at many stale positions, it's a wake. Strip =
  exclude tracks that are body-COLOURED **and** body-SIZED **and** stood-on (nr~0). Real displays are
  never body-sized and never stood-on (you can't step on a display), so they survive the strip.
- **The shared colour (`colour 9 is not unique`).** `[PROCTOR_MEMORY_original §IV]` The avatar's lower
  half, the HUD key, AND the board lock are ALL colour 9 — so a colour test can never separate the body
  from the key/lock, and `max(size)` over colour-9 tracks grabs the body-block over the size-5 lock.
  This is why role is settled by *what my play has done to each* (readout = changed at a distance;
  target = reached-but-unchanged), never by colour — and why the load-bearing pairing signal is SHAPE,
  not size (next bullet).
- **The toggle-colour readout (L1, the one that ate a session).** The HUD key CYCLES by toggling its
  cells between colour 9 and colour 0, so the tracker labelled the key's track `id=[0]`. Colour 0 is NOT
  the avatar's trim — on ls20 it is a TRIGGER colour (the white cross, `§IV`) — but the readout ("what
  my play changes") still came out `[0]`, and the pairing then hunted colour-0 and grabbed a size-25
  colour-0 tracker GHOST at a stood-on cell, while the real colour-9 box sat reachable and ignored. Two
  tells: `sig=[0]` where the key is visibly colour 9, and a paired "lock" at a cell with no glyph.
  **The robust fix is the locksmith ontology, and the corpus prescribes it exactly:** a key and its lock
  are the same SHAPE-FAMILY — *"key 20px, lock 5px, 4x ratio, same `canon_shape` ... a size-similarity
  test fights the match it is looking for"* `[§IV]`. So prefer the reachable target whose rotation-
  canonical shape matches the key's (`canon_shape`, rotation-invariant, so a cycled orientation still
  matches), and NEVER select the lock by size. That picks the real box (the key's L-corner family) over
  a same-size decoy (the hollow-square `===`) and over any wake — verified: L1 pairs `lock@(42,16)`, the
  real box. (My earlier "whole-body self-colours" patch was aimed at a trim that does not exist; it is
  harmless — the size+stood-on clause protects small triggers and displays — but the canon-shape
  preference is the part that actually does the work.)
- **HUD / chrome as board.** Status-bar glyphs enrolled as steppable triggers or targets (the row-57
  route-attempt sink). Right answer depends on the question: chrome is not a *place* (exclude from what
  I step on) but the HUD IS the *readout* (keep for what I compare). `[§IV: the KEY lives in the HUD.]`
- **Mid-transition / split reads.** A glyph caught between cycle states, or one component labeled as
  two (a size-5 + a size-1), read as a shape change or a new object.

First move on any "the agent can't see / reach / do X" report: **dump what it actually perceives and
strip the phantoms.** Only after the perception is clean do detector / reasoning / capability
explanations get to be on the table. (Also: "self-CO-TRIGGERED N cells elsewhere" firing on every move
is usually the agent misreading its OWN 5x5 body's displacement as external change — a self-perception
tell, not a real environment coupling. Verify before believing the board is dynamic.)

---

## THE METHOD THE LAW RUNS ON — ABSTRACT UP, THEN NICHE DOWN (and let the agent do the same)

**When stuck, LIFT the problem to the altitude where its structure is visible** — name the two or
three things in contention and the two or three signals that could decide between them — let the
answer shake out at that altitude, then **niche back down** to the specifics and implement. This is
not a fallback; it is HOW the hard calls get made. `[THE_ALIGNMENT §6]`

- **Altitude is a property of the OBSERVER, not the system.** The bill is the same at every altitude.
  Do not hunt for the "right altitude" to place a rule — ask WHERE THE BILL IS PAID and charge every
  place it is paid. Lift to SEE structure; the cost lives at every rung regardless. `[PROCTOR_MEMORY_
  original §I: the affordability-invariant-at-one-stage regression is the worked example of this.]`
- **The FMap / conjugation is the lens.** Many hard pipeline problems are a conjugate `A·B·A⁻¹` —
  set up, operate, undo — flattened by the code into `A·B·A·B·A…`, paying the transform once per
  operation instead of once. Reading the task at the allocentric altitude shows the true operator;
  the egocentric code shows the flattened, overpriced one. Fix the shape, not the symptom.

**And the load-bearing half Isaiah added:** build the pipeline so the AGENT can run this same move —
lift when its play thrashes, reason about its candidates and the signals that would decide, then
niche back down and act — **in its own frame, through its own Pose (its rate, its meter, its path).**
Claude imposes the invariant at the abstract/allocentric altitude; the agent transforms it into
concrete moves. That keeps agency AND reasons to the answer. **The abstraction method is not just how
Claude debugs — it is a capability the agent must have. Giving the agent that capability is pipeline
work; running it FOR the agent is taking the test.**

---

## THE TELL

If Claude finds itself picking A vs B on a question the agent could reason — *does re-contact require
leaving? which glyph is the key? can I afford this walk?* — that is the tell that Claude is solving
the game. The response is never "answer it." It is: **repair the pipeline so the agent forms the
hypothesis, tests it, and reads the result itself — at the right altitude, in its own frame.**

Worked example `[19 Jul 2026]`: L1 was dying on budget, and the proposed fix was "wire budget-aware
routing + booster detours into the exit path." That is LAW 0 #1 verbatim ("how to afford the geometry")
and THE TELL verbatim ("can I afford this walk?"). Ground truth then showed the agent ALREADY reasons
about budget, boosters, and affordability out loud (`BUDGET-MATH`, `BOOSTER: a budget resource to
sequence into the plan`, `HORIZON ... budget-INFEASIBLE this attempt`) — so the router would have
rebuilt, and hardcoded, reasoning the agent already owns. The real fault was a perception phantom
upstream (the toggle-colour readout above). **When the fix you reach for is a plan the agent could
compute, stop: the bug is almost always that it is computing over a phantom, not that it lacks the plan.**
