# THE AGENT ACCESS MAP (2026-08-20) — everything consultable during one gameplay decision

Seat 3: *"Every source it can consult, every tool it can call, what each costs, and what it
returns. The planner consuming 95% of runtime is exactly what a map would have made obvious."*
**Costs are MEASURED where a number exists and marked UNMEASURED where none does** — an
unmeasured cell is a specification of what to measure, not a guess.

## The decision path, in firing order

| # | source / tool | what it returns | measured cost | notes |
|---|---|---|---|---|
| 1 | **Frame** (env observation) | 64×64 grid(s) | ~free | multi-frame payloads normalised to last (the `post` fix) |
| 2 | **Perceiver / object extraction** | objects, palette, regions | UNMEASURED | inside the 2.7–10 act/min envelope for L0 workers |
| 3 | **Context dict** (`ContextBuilder.to_dict`) | **83 keys provided; 34 consumed by rungs** | ~free | 55 provided-and-unread; 2 read-and-never-written (`game_state_mode` dead branch) |
| 4 | **75 decision rungs** (registry-ordered) | candidate action + confidence each | UNMEASURED per-rung | priority table diverges from class defaults (known defect) |
| 5 | **Banked routes** — `winning_sequences` | replayable sequences | **~136–730 s at startup** (replay tail) | recordings; mastery-lite gated; the "handed" item under W3 earn-through |
| 6 | **Salient prefixes** | banked prefix + divergence detection | UNMEASURED | consumption-recorded (corpse guard) |
| 7 | **Frontier book** | avoid-set of fatal cells | cheap (set lookup) | earned, per-level |
| 8 | **Γ atoms** (fabric `atoms` stream) | learned EFFECT/COMPOSITE atoms | query per call: UNMEASURED; **application: the 95% term** | 1,829 structural; no applicability index yet (W2a) |
| 9 | **The planner** (`plan_to_identity`) | steps or nothing — **has only ever returned nothing** | **~80 s/call; 95.3% of slow-worker runtime** | goal-blind candidate selection (PLANNER_ALGORITHM_READ); W2a/b/c aimed here |
| 10 | **Goal hypotheses** (abduction stream) | structural predicates from own level-ups | cheap (tail read) | earned; feeds pred-mode planning |
| 11 | **Import queue / collective fabrics** | other agents' residual records | tail-read WINDOW=32: cheap | **cross-mounted at boot (OURO_FABRIC_SEEDS)** — the Stream-B-as-A defect, W3 removes auto-load |
| 12 | **Seed primitives registry** (~4,000 lines) | executable primitives via `PrimitiveSuggesterRung` | UNMEASURED | the handed-capability mass; W3 sorts priors from capabilities |
| 13 | **Engine registry** (32 dynamic modules) | per-engine analyses on demand | UNMEASURED per engine | import-time side effects fixed (D-6); per-engine decision-time cost is the map's biggest blind spot |
| 14 | **SQLite** (box `core_data.db`, 284 tables) | histories, patterns, lessons | UNMEASURED per query | per-worker box; the shared-root defect closed |
| 15 | **Affect gains** | risk modulation (explore boost) | cheap | book-derived only, per ruling; never a price |
| 16 | **Narration stream** *(W1, building)* | the agent's own bet + reasoning, pre-action | budget ≤5% wall-clock | becomes source 0 once consuming |

## What the map makes obvious (the reason it was asked for)
1. **One row is 95% of the budget** (row 9) and it has never returned a value. No other row
   is within two orders of magnitude — the next candidate terms (2, 4, 13, 14) are all
   unmeasured, which is the map's to-do, not its conclusion.
2. **Three rows are inherited, not earned** (5, 11, 12) — exactly the ladder's three
   forbidden moves, now visible as rows rather than findings.
3. **The biggest blind spot is row 13**: 32 registry engines whose per-decision cost has
   never been measured individually. The D-5 wrapper can profile them the same way — queued
   as the map's follow-up read.
4. **Rows 3 and 9 carry the same genus** — produced-and-not-consumed (55 unread context
   keys; a computed diff unused for candidate selection).

*Sources: D5_PROFILE_RESULT, PLANNER_ALGORITHM_READ, scan_context_keys run, F8A/LINK3 reads,
the live-closure computation, and the startup-tail measurement. Each number carries its
origin; each UNMEASURED is a named gap.*
