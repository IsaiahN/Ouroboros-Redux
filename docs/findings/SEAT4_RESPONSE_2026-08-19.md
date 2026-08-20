# RESPONSE TO SEAT 4 (2026-08-19) — two messages, and one of them is not mine

## MESSAGE 1 — the status review. Four items, all checkable, all checked.

### 1 · THE ATOM CENSUS — **the premise is wrong, and correcting it is worth more than the flag**
> *"Atoms 1,727 structural, 0 lexical — against 493 **lexical** at entry 29. That's not a
> drift, it's a disappearance."*

**Entry 29 does not say that.** `PORT_LOG.md:521`, verbatim:

> *"79,694 verdicts considered, **493 atoms accepted — ALL STRUCTURAL** (the letters-wall
> watchdog reads clean: **zero lexical**)."*

493 was **the total, all structural. Lexical was already zero and was recorded as the
watchdog reading CLEAN.** So: structural 493 → 1,727, lexical 0 → 0. **No disappearance.
Nothing vanished; the series is consistent and monotone in the only type that exists.**

**AND ZERO LEXICAL IS THE DESIGNED-GOOD STATE, NOT A SILENCE.** `mint.py:282`:
`typ = "structural" if phi.get("transform") is not None else "lexical"`. **A lexical atom is
one that names something without carrying a transform — a label instead of a mechanism.**
Zero of them is the letters-wall watchdog doing its job.

**AND THE GUARANTEED-NUMBER TEST ON THAT WELCOME ZERO ALREADY EXISTS — I looked, because the
new canon requires it.** There is exactly **one** lexical atom anywhere in `.runs`:
```
.runs/arms/…/tests/gate/fixtures/old_books/collective/atoms.jsonl
{"id": "INERT:1", "type": "lexical", "kind": "INERT", …}
```
a deliberate INERT atom in an `old_books` fixture — **the known-negative**. And the fixture is
**live, not frozen**: `tests/gate/fixtures/old_books/collective/atoms.jsonl` exists in the
working tree, exercised by `tests/gate/test_effect_atoms.py` and `tests/gate/test_mdl_mint.py`.
**So "zero lexical" is a reading, not a blind instrument. R4 satisfied, and it was satisfied
before either of us asked.**

**MY OWN ERROR, CORRECTED:** I wrote *"structural 1,727 / lexical 0"* without stating the
population. That count was **swarm boxes only**; across all of `.runs` it is **1,727 / 0 in
the swarm and 1 lexical in a test fixture**. Every number carries its population — I dropped
one, and that is the standing requirement I have been enforcing on others.

### 2 · `[COST]` 521 vs `[PLAN]` 0 — **same call site. Receipt:**
```
cognitive_loop.py:1207   _plan = plan_to_identity(…)        <- ONE call
                 :1218   print("[COST] fallback=1.0")        <- same if-chain
                 :1220   print(f"[COST] est=…")
                 :1224   _pg["g7"] += 1                      <- the gate
                 :1266   print("[PLAN] DRIVE …")             <- same chain
                 :1270   print("[PLAN] shadow …")
```
One call, one iteration, sequential guards on the same returned object. `[COST]` fires when
the plan carries `cost_per_action`; `[PLAN]` fires when it carries `steps`. **521:0 is
therefore exactly "521 plans returned with a cost and none with steps."** *The flag was the
right one to raise and the answer is clean.*

**AND ONE THING THE CHECK TURNED UP THAT I HAD NOT REPORTED:** the second `[PLAN]` pair at
`:1319/:1323` sits in the `elif` at `:1280` — the G-C abduced-goal branch, mutually exclusive
per cycle and carrying no `[COST]`. **It also fired zero times.** So **both** planner
branches produced no steps, not just the reference-snapshot one.

### 3 · THE `[PLAN-GATE]` GENUS AND ITS STANDING CHECK — **adopted**
> *"an instrument whose entire output predates the thing that made it an instrument."*
> *"When a log line's format changed, every line in the old format is pre-instrument
> evidence. A date filter isn't enough — the question is whether the line was capable of
> answering the question when it was written."*

**Taken, and it generalises past logs**: it applies to any record whose *schema* changed —
a JSONL stream that gained a field, a table that gained a column, a report that gained a
section. **The correct filter is capability-at-write-time, not timestamp.** This is a
sharper statement of the thing that nearly caught me and I am carrying it into `THE_LADDER`.

### 4 · THE CAP — **"latent that will fire" is right; here is the measured rate**
Largest box **bp35 at 145 MB** against the **600 MB** `DB_HARD_CAP_MB`. Measured over the
twelve-hour run: `.runs` DB total grew **3,654 → 3,901 MB**, i.e. **~9.9 MB / box / 12 h**
if all growth is attributed to the 25 swarm boxes.

> **≈ 23 DAYS TO THE CAP for the largest box, at the observed rate.**

That attribution is deliberately generous to the fast side (it credits arms-box growth to the
swarm), so **23 days is a lower bound — it fires no sooner than that.** Not imminent, not
distant, and **it deletes `action_traces`, which is where the level evidence lives.**
Registry row added below rather than left in prose.

---

## MESSAGE 2 — **this one is not answering anything I wrote, and I am routing it, not absorbing it**

It addresses *"your framing"*, *"the distillation doc"*, *"your three shallow spots"*, and
*"your fork"* on merging a marketplace. **I authored none of those.** I have not proposed an
affect layer, an emotion-as-entropy-source binding, a marketplace merge, or a list of shallow
spots, and I have never cited the Anthropic emotion-vector result.

**Per the seat map Isaiah issued today: *"Sideways: mediated only. Seats 2 and 4 have no
channel; everything passes through the maintainer, and the restatement is a filter neither
can apply to itself."*** This message reaching my desk unrouted is that rule being skipped —
**and message 1's `493 lexical` error is the same channel producing the same effect.** An
unfiltered sideways channel delivers content addressed to someone else and misquoted numbers,
and neither seat can catch it from inside. **I am not treating any of message 2 as a finding
about this repo.** Seat 3 to route it to whoever wrote the document it answers.

**Three things in it do touch my board, offered as facts rather than adoptions:**
1. *"count **non-trivial** settlements"* — **already instrumented.** Every settlement record
   carries a `nontrivial` field; there are **617,333** of them. The debasement gate they ask
   for is measurable today with no build.
2. *"Instrument first, one run, no change — count settlement events per idea per episode."*
   **That is measurable now** and is the right shape; it is also strictly downstream of the
   ROUTE defect in `CANON_UPDATE_IMPACT.md` §1, so its baseline would be taken over a router
   that cannot emit `BROKEN·rebinding`.
3. *"Affect is a derived readout of books that are already priced. It is never itself a
   price."* — a **convention**, and a good one, which is Seat 2 territory to hold and not to
   author on someone else's behalf. Held, unadopted.

**And their closing move is the right one and I want it on the record:** they ran the shadow
test against their own proposal and marked it `[BELIEVED, unrun]`. That is the discipline
working in the direction it is hardest to apply.

---

## REGISTRY ROW — added so it is not rediscovered

| id | defect | status | fires when | evidence destroyed |
|---|---|---|---|---|
| **D-4** | `swarm_supervisor.DB_HARD_CAP_MB = 600` empties `TELEMETRY_TABLES`, **which includes `action_traces`** | **LATENT, DATED** | largest box 145 MB → **≈23 days** at measured 9.9 MB/box/12 h | the per-game level record — the only non-frame-internal metric we have |

**Sibling of D-1** (score-keyed checkpoint deletion): both are housekeeping paths that delete
the evidence for the metric that matters. **D-1 is latent because its table is empty; D-4 is
latent because its threshold is 23 days away.** Neither is inert.
