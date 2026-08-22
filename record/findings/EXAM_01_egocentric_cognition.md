# EXAM 01 — `engines/egocentric/**` + `engines/cognition/**`

Binding rubric: `record/findings/EXAMINATION_RUBRIC.md`. Builds on
`record/findings/CODEBASE_INVENTORY.md` (the automated pass) — every row below was re-checked
against the tree, not copied. **Read-only pass. Nothing moved, nothing deleted, no file edited.**

**Snapshot:** branch `v4-cold`, HEAD `e1cce38`, 2026-08-22. Two files in this slice
(`agent_lifecycle_manager.py` / `evolution_runner.py` are outside it, but the builder owns them)
were not touched; nothing in this slice was written to.

## COUNTS

| | files |
|---|---|
| **TOTAL examined** | **76** |
| `engines/egocentric/` | 43 |
| `engines/cognition/` | 33 |
| **live** | **68** |
| **preserve** | **8** |
| **considered_dead** | **0** |

`preserve` (8): `egocentric/falsified_ledger.py`, `egocentric/janitor.py`,
`egocentric/relations.py`, `cognition/ab_testing.py`, `cognition/cognitive_stages.py`,
`cognition/contradiction_detector.py`, `cognition/edge_trust_manager.py`,
`cognition/shadow_testing.py`.

## METHOD, AND WHERE IT DISAGREES WITH THE INVENTORY

Every `.py` in the slice was opened (module docstring + every top-level `class`/`def`/`CONST`,
parsed with `ast`; no module was imported or executed). Reachability was rebuilt from scratch:
an `ast` pass over every `.py` in the tree outside `.`-directories, recording each import of a
slice module with its **file:line** and whether it sits at module level (STATIC) or inside a
function body (LAZY). Bare module names were then swept as strings across
`.py .json .md .txt .toml .yaml .ini .cfg`, and — the step the inventory did not take —
**every public symbol of each suspicious module was searched for a CONSTRUCTION or CALL, not
just an import.** That step is what separates the eight `preserve` rows from the rest.

Note on the sweep: `.runs/arms/<hash>/` contains a **complete second copy of the repository**
(`.`-prefixed, correctly out of scope). Any name search that does not exclude it doubles every
hit and can make an unreferenced symbol look referenced. All counts here exclude it.

### RUBRIC AMENDMENT 1 — dot-directories searched as invocation sites

Applied to all eight `preserve` rows before they were finalised. Searched: `.github/**`,
`.pre-commit-config.yaml`, `.githooks/**`, `.claude/**`, `.vscode/**` (absent), and every
`.sh`/Makefile (none present). Four results, two of which changed rows:

1. **`.github/workflows/ci.yml:52` runs `pytest tests/gate -q` as a BLOCKING step on every push
   and PR.** `tests/gate/` is therefore an invocation site with CI force. Three preserve rows are
   affected — `janitor.py`, `falsified_ledger.py`, `relations.py` — and their reached-by cells now
   say so. **All three stay `preserve`:** CI executes them, production does not construct them.
   "Exercised by a blocking test" and "on the live path" are different claims and the rows now
   distinguish them.
2. **The same file does NOT run `tests/` root.** Only `tests/gate` and one named file
   (`tests/gate/test_wiring_registry.py`, its own blocking step at `:46`). The four cognition
   preserve rows — `ab_testing`, `contradiction_detector`, `edge_trust_manager`,
   `shadow_testing` — are reached only from `tests/test_phase5_validation.py`,
   `tests/test_epistemic.py`, `tests/test_phase6_production.py` and
   `tests/test_phase75_stabilization.py`, none of which CI runs. `pytest.ini` sets
   `testpaths = tests`, so a bare local `pytest` does collect them; CI never does. **This
   strengthens those four rows rather than weakening them**, and the cells now state it.
3. **`tools/consumption_sweep.py`, `tools/ood_lint.py` and `vulture_whitelist.py` — the three
   scripts the CI and pre-commit steps invoke — name none of the eight modules.** Checked by bare
   name against all three; zero hits.
4. **One inverse case, worth recording because it is the amendment's trap running backwards.**
   `.pre-commit-config.yaml:17` feeds `vulture_whitelist.py` to the vulture hook, and
   `vulture_whitelist.py:10` contains `CognitiveStageSystem  # noqa: F821 - Used in type hint in
   hypothesis_system.py`. A dot-dir config does reach that name — but it reaches it in order to
   **suppress vulture's correct dead-code finding**, on the strength of a `TYPE_CHECKING` hint.
   That is an inventory entry and a silencer, not an invocation, and it is *evidence for* the
   `preserve` classification rather than against it. A sweep that counted config hits as
   reachability would read this file exactly backwards.

`ruff check .` (blocking, `ci.yml:49`; also `.githooks/pre-commit`) and the vulture hook parse
every file in this slice. Parsing is not invocation and no row was changed on that basis.

Four disagreements with `CODEBASE_INVENTORY.md`, each with its receipt:

1. **`cognition/shadow_testing.py` is not on an executable path.** The inventory classes it
   `OBSCURE-E` on the strength of the lazy import at `decision_rung_system.py:1574`. That import
   sits inside `DecisionRungSystem.get_shadow_tester()`, and **nothing in the tree calls
   `get_shadow_tester` or `enable_shadow_mode`** — the only two occurrences of either name are
   their own `def` lines (`decision_rung_system.py:1563`, `:1570`). A lazy import inside a
   never-called method is not reachability. → `preserve`.
2. **`cognition/cognitive_stages.py` is import-reached and never constructed.** `CognitiveStageSystem`
   has **zero construction sites** tree-wide. Its non-definition occurrences are: the
   `engines/cognition/__init__.py:11` re-export, the `engines/__init__.py:122` re-export, a
   `TYPE_CHECKING`-guarded annotation at `engines/social/hypothesis_system.py:26`, and a
   `vulture_whitelist.py:10` entry that exists *because* the annotation makes it look used. This
   is the `sequence_miner` trap exactly. → `preserve`.
3. **`egocentric/falsified_ledger.py` is a second instance of FINDING 2's re-export blind spot,
   already on record and not carried into the inventory's list.** Its only importer is
   `engines/egocentric/__init__.py:24`; `FalsifiedLedger` is never constructed.
   `WIRING_REGISTRY.md:209` already says so: *"S11 never constructed; the `__init__` re-export hid
   it from vulture; triage DELETE (dead weight)."* The registry's verdict is DELETE; this pass
   disagrees and says `preserve`, with the capability named below.
4. **`cognition/metacognition.py` is live by STRING, which no import scan shows.** It is loaded
   by `engines/registry.py:162-167` (`module='engines.cognition'`, `class_name=
   'MetacognitiveReasoningEngine'`) fed to `importlib.import_module` at `registry.py:381`, and
   consumed at `rungs/filter_rungs.py:658`, `:803` and `rungs/hypothesis.py:135`, `:1337`.

---

## `engines/egocentric/` — 43 files

| path | dest | reached-by (with site) | what it does | if preserve: capability, and why it may matter |
|---|---|---|---|---|
| `engines/egocentric/__init__.py` | live | STATIC — package `__init__`, executed by every `engines.egocentric.*` import (e.g. `cognitive_loop.py:49`) | Phase-1..W1a re-export surface; a 12-module bulk `from engines.egocentric import (…)` at :19 plus 15 symbol re-exports | — |
| `engines/egocentric/action_book.py` | live | STATIC `engines/egocentric/gate.py:63`; LAZY `cognitive_loop.py:5399`, `engines/egocentric/enables.py:304`; also `tools/build_action_book.py:74` | the read side of STAGE 0 of the reasoning gate: per-(game, action) semantics derived only from the agent's own records, served from one JSON per game box | — |
| `engines/egocentric/affect.py` | live | STATIC `engines/egocentric/__init__.py:33`; LAZY `cognitive_loop.py:2220` | W4a gains on the deliberation loop (`seed_bias`, `mint_bar`) computed as a pure function of the collective ledger prefix | — |
| `engines/egocentric/agency.py` | live | STATIC `engines/egocentric/__init__.py:19`; LAZY `cognitive_loop.py:2826` | `CursorAgency`: learns the controllable's per-action displacement map, separating it from action-independent background churn | — |
| `engines/egocentric/applicability.py` | live | STATIC `composer.py:137`, `consumer.py:113`, `enables.py:80`, `mint.py:105`, `planner.py:86`; LAZY `cognitive_loop.py:5384` | the W2a applicability index: anchor/postcondition/composite signatures stamped at mint and backfilled on read, plus the `prune_candidates` pre-filter | — |
| `engines/egocentric/bank.py` | live | STATIC `engines/egocentric/__init__.py:34`, `gate.py:66`; LAZY `cognitive_loop.py:2217` | `PredictorBank`: one predictor and one residual per bound slot (BODY / WORKSPACE / REFERENCE / RESOURCE); plus `ClassFissionSocket` | — |
| `engines/egocentric/betting.py` | live | STATIC `engines/egocentric/__init__.py:19`; LAZY `cognitive_loop.py:1795` | `BetBook`: commit a prediction family at choice time, settle it against the executed action's next frame; committed≠executed → VOID | — |
| `engines/egocentric/binder.py` | live | STATIC `engines/egocentric/__init__.py:35`; LAZY `cognitive_loop.py:2216` | `RoleBinder`: one invariance classifier, four role verdicts, with the Goodhart guard (autonomous change disqualifies BODY) | — |
| `engines/egocentric/composer.py` | live | STATIC `engines/egocentric/gate.py:67`; LAZY `cognitive_loop.py:4906`, `:4990`, `:5063`, `:5106`, `:5263` | the compose loop: WANT → Γ candidates by effect-intersects-WANT → exact simulation → composite entered as a CANDIDATE, with the live-frame settle | — |
| `engines/egocentric/consumer.py` | live | STATIC `engines/egocentric/mint.py:106`; LAZY `cognitive_loop.py:92`, `:1030`, `:2502`, `composer.py:625` | the triangulation consumer: signature-first recognition — σ computed candidate-blind inside the home frame, persisted, then matched against mint-time signatures | — |
| `engines/egocentric/discrepancy.py` | live | STATIC `__init__.py:19`, `:36`, `gate.py:68`, `planner.py:87`; LAZY `cognitive_loop.py:1615` | `d`, the self-authored objective: a role-aware axis-wise residual transform between WORKSPACE and REFERENCE, plus its anti-elaboration falsifier | — |
| `engines/egocentric/effects.py` | live | STATIC ×9 in-package (`__init__.py:37`, `applicability.py:53`, `composer.py:138`, `consumer.py:114`, `gate.py:69`, `mint.py:107`, `planner.py:88`, `retention.py:84`); LAZY `cognitive_loop.py:2222` | the EFFECT constructor (arity-two-over-time atoms, position-free canonical keys) and the typed `Gamma` store with `compose`/`narrow` | — |
| `engines/egocentric/enables.py` | live | STATIC `composer.py:139`, `mint.py:108`; LAZY `cognitive_loop.py:4907`, `:4991`, `:5007`, `:5388`, `:5411` | composer stage 2: the two composition edges (`enables_edges`, `cross_shelf_reach`) computed from stored signatures only, plus `act_offset` / `fatal_cells` / `book_deltas` | — |
| `engines/egocentric/fabric.py` | live | STATIC `engines/egocentric/__init__.py:44`; LAZY `cognitive_loop.py:132`, `:261`, `:1939`, `:2060`, `cognitive_game_player.py:105` | `KnowledgeFabric`: pure-stdlib scoped JSONL streams with a per-process seq high-water cache, an anchor-checked read cache, and the idea economy | — |
| `engines/egocentric/falsified_ledger.py` | **preserve** | STATIC `engines/egocentric/__init__.py:24` **only** (re-export). `FalsifiedLedger` has **zero constructions in production**. Its one executable reach is an availability probe at `tests/gate/test_knowledge_fabric.py:174` — which **CI runs on every push** (`.github/workflows/ci.yml:52`, `pytest tests/gate -q`, BLOCKING). So it is imported every push and constructed never. `WIRING_REGISTRY.md:209` = SEVERED | `FalsifiedLedger`: weighted, defeasible reject-memory — refutations decay, `reconsider` re-opens, `bias`/`is_refuted` steer retrieval, `explain` states why | **A refutation is only recorded after a trial actually RAN and the do-operator registered** — "I failed to do X" is a non-trial, never "X is inert". No live organ makes that distinction: `discrepancy.objective_falsified` and the verdict stream record falsification flat, with no weight, no decay and no path back. Also the only reject-memory here that is *defeasible* — the live path either believes an atom or evicts it (`standing`), with nothing in between |
| `engines/egocentric/frontier.py` | live | LAZY `cognitive_loop.py:1667`, `:2662`, `:4158`, `:5149`, `goal_abduction.py:394` | `FrontierBook`: each frontier death banks its first post-frontier click as a fatal opening; `avoid_set` reads the population-wide union back | — |
| `engines/egocentric/gate.py` | live | LAZY `cognitive_loop.py:5362` (`_gate_step`, one void call per step beside the spine's `act()`) | the reasoning gate: an executor and a ledger, never a judge — every utterance clause pays in LEDGER / EXECUTABLE / COMPLETENESS currency, logged on the personal `gate` topic | — |
| `engines/egocentric/goal.py` | live | STATIC `engines/egocentric/spine.py:20`, `__init__.py:19` | `GoalManager`: a market of candidate goals priced by confirmed reward. **Its two module-level functions `candidate_targets` (:122) and `abduce_target` (:140) have zero call sites** — see PAIRS §6 | — |
| `engines/egocentric/goal_abduction.py` | live | STATIC `engines/egocentric/planner.py:89`; LAZY `cognitive_loop.py:143`, `:1722`, `composer.py:232/319/748/834` | mines the level-up frame delta for structural predicates that became true (`region_uniform`, `colour_count_zero`, `regions_equal`) over frame-shape-derived regions | — |
| `engines/egocentric/grammar.py` | live | STATIC `engines/egocentric/gate.py:64` — inherits the gate's lazy-only visibility from `cognitive_loop.py:5362` | the utterance grammar: five world types, 13 typed primes salvaged from `origin/new-horse`, `compose()` raising on ill-typed composition, plus the authored speech-act layer | — |
| `engines/egocentric/janitor.py` | **preserve** | TEST-ONLY, **but CI-blocking** — `tests/gate/test_fabric_janitor.py:32`, `tests/gate/test_record_keeping.py:37`, `tests/gate/test_torn_writes.py:39`, all under `tests/gate`, run by `.github/workflows/ci.yml:52` (`pytest tests/gate -q`, BLOCKING) on every push and PR. So `FabricJanitor` is constructed and swept on every push and **never in production**: `WIRING_REGISTRY.md:206` = SEVERED, *"NEVER CONSTRUCTED in production — compaction has never run (explains 268k-line queues)"* | `FabricJanitor`: size-triggered (never cadence-triggered) stream compaction that is loud (a `[JANITOR]` manifest per sweep) and archives rather than deletes | The falsifier is **byte-equality of every consumer-visible answer pre/post compaction** — the consumer's pending/candidates, affect's gains, the idea economy's priors, harvest merge, mastery rate, the atoms query. That is a compaction discipline nothing else in the tree has: it is the only mechanism able to bound stream growth *while proving it changed no answer*. Bears directly on the read-cost side of mandate item 2 — the streams it was written for are still growing unbounded |
| `engines/egocentric/latents.py` | live | LAZY `engines/egocentric/planner.py:213` (single production site) | REGISTER L: `ActionCostEstimator` — `cost_per_action` measured per (game, level) from the collective `settlements` stream instead of hard-coded 1.0 | — |
| `engines/egocentric/lp_drive.py` | live | STATIC `engines/egocentric/affect.py:50`, `tools/fleet_env.py:24` | C33's three-arm exploration control (`fixed` / `random` / `lp`), arm assigned per worker by `LP_DRIVE_ARM`; `lp` reweights candidates by learning progress | — |
| `engines/egocentric/mastery.py` | live | STATIC `engines/egocentric/__init__.py:45`; LAZY `cognitive_game_player.py:106` | `MasteryLite`: replay probability earned from recorded replay reliability, decaying back toward exploration when replays start failing | — |
| `engines/egocentric/mint.py` | live | STATIC `engines/egocentric/__init__.py:46`, `lp_drive.py:65`; LAZY `cognitive_loop.py:2219`, `:4777`, `consumer.py:915` | the MDL mint: SUPPORT → NOVELTY → MDL as a guard product; accept an atom iff the compression pays, with fixed refusal reason tokens | — |
| `engines/egocentric/narration.py` | live | STATIC `gate.py:65`, `persistence.py:64`; LAZY `cognitive_loop.py:229`, `:252`, `:331`, `:939`, `:1948`, `:4760`, `:4813`, `:4850` | the narration spine: the BET record is emitted *before* the action, and PERCEIVE/ROUTE/MINT/ECHO/ACT close against it by id — narration as the decision, not a log | — |
| `engines/egocentric/navigation.py` | live | STATIC `engines/egocentric/__init__.py:19`; LAZY `cognitive_loop.py:2819`, `:2827` | `GridNav`: walls as *directed edge* facts measured by bumping, defeasible (BLOCKED decays back to unknown), BFS/frontier stepping over known-free cells | — |
| `engines/egocentric/observer.py` | live | STATIC `engines/egocentric/__init__.py:47`; LAZY `cognitive_loop.py:1904`, `:2035` | `EgoObserver`: the read-only wrapper — one (post_frame, action) pair in, a small belief dict out (controllable colour, object count, centroid, exact cell) | — |
| `engines/egocentric/perception.py` | live | STATIC `observer.py:22`, `agency.py:33`, `engines/perception/perceiver.py:30`, `__init__.py:19` | full-resolution segmentation with object permanence by overlap; `check_no_downsampling()` enforces the constitutional never-downsample bound | — |
| `engines/egocentric/persistence.py` | live | LAZY `cognitive_loop.py:5338` | a read-only consumer of the narration stream that counts: the same residual recurring under an unchanged strategy for k steps is one PERSISTENCE finding | — |
| `engines/egocentric/planner.py` | live | STATIC `engines/egocentric/__init__.py:48`, `scheduler.py:68`; LAZY `cognitive_loop.py:1616`, `goal_abduction.py:363` | breadth-first search over applicable EFFECT atoms driving `d → identity`, run bidirectionally under one node budget with every backward step forward-verified | — |
| `engines/egocentric/pricing.py` | live | STATIC `engines/egocentric/betting.py:33`, `__init__.py:19` | `informative_salience` (the live half — `betting.py:98`) plus `Hypothesis`/`Resolution`/`Marketplace`, which `WIRING_REGISTRY.md:212-214` marks SEVERED **by design** (C33 step 1: bets drive nothing) | — |
| `engines/egocentric/relations.py` | **preserve** | STATIC `engines/egocentric/__init__.py:19` **only** — so it is *imported* whenever the package is, including under CI (`.github/workflows/ci.yml:52`). All three public functions (`quantified_candidates`, `class_member_cells`, `candidate_relations`) have **zero call sites tree-wide**. The only other occurrences are inside `tests/gate/test_wiring_registry.py` — a **separate BLOCKING CI step** (`ci.yml:46`) — which at `:547-554` records the gap as an acknowledged exception and at `:669` asserts the reachability scan must not lose the file. No `WIRING_REGISTRY.md` row | a space of **typed** win-relations over objects — `BE_AT` (on the cell), `TOUCH` (adjacent, for a target only reachable at its edge), `COVER` (inside an enclosed interior) — plus ALL-quantified class-member candidates via `class_member_cells` | The live goal path proposes exactly one relation shape: "be on the unique small distinct object". This module's own docstring records the multi-game result that made it: that hypothesis is too narrow, the agent navigates onto the obvious target and does not win. The successor was written, wired into `__init__`, and never called; the predecessor it was meant to replace is the one running. **Quantification is the sharper half**: nothing else in the live stack can express "visit every member of a class" as a goal at all |
| `engines/egocentric/retention.py` | live | STATIC `composer.py:140`, `planner.py:84`, `scheduler.py:66` | `RetentionStore` + `Session`: one level-scoped store so the next planner call starts from what the last one found (memo, negatives, anchors, enablers, lineage) | — |
| `engines/egocentric/rho.py` | live | STATIC `engines/egocentric/consumer.py:115`; also `tools/regen_series.py:60` | ρ: weighted-Jaccard over atom signature classes, pricing the redundancy between cross-mounted fabrics so k photocopies do not count as k witnesses | — |
| `engines/egocentric/router.py` | live | STATIC `engines/egocentric/__init__.py:49`, `gate.py:77`; LAZY `cognitive_loop.py:2218` | `ResidualRouter`: every settled residual lands in exactly one of four bins (TRANSFERRED / NOVEL / BROKEN·rebinding / BROKEN·mechanism). `BROKEN_REBINDING` is SEVERED per `WIRING_REGISTRY.md:207` | — |
| `engines/egocentric/scheduler.py` | live | LAZY `cognitive_loop.py:433`, `:495`, `:5064`, `:5107`, `:5200`, `:5264` | `PlannerScheduler`: two gates (cheap-routes-first, unchanged-world), one guard, one abort router (`world-moved` vs `plan-wrong`) — the decision of *when* to search | — |
| `engines/egocentric/self_locus.py` | live | STATIC `engines/egocentric/observer.py:23`, `__init__.py:19` | `SelfLocus`: identifies the controllable by action *contingency* (displacement must vary with which action), not correlation — the Goodhart guard against spurious correlates | — |
| `engines/egocentric/spine.py` | live | STATIC `engines/egocentric/__init__.py:50`; LAZY `cognitive_loop.py:1907`, `:2050` | `GoalSpine`: wraps `GoalManager` with a learned per-action vector delta map and the confirmation gate — an action only when a goal holds confirmed price | — |
| `engines/egocentric/standing.py` | live | STATIC `composer.py:141`, `planner.py:85`, `scheduler.py:67`; LAZY `cognitive_loop.py:534`, `:551`, `:576` | R3/R4 standing at the atom grain: earn/mispredict events with a half-life, ranking retrieval order and evicting — the demotion `scheduler.plan_wrong` was deliberately not | — |
| `engines/egocentric/starvation.py` | live | LAZY `cognitive_loop.py:1011` | `StarvationBook`: a fixed enum of machinery codes; sockets exercised persistently with zero passes are named at the episode boundary (residual, never grade) | — |
| `engines/egocentric/swallow.py` | live | STATIC `cognitive_loop.py:49` (the only module-level egocentric import in the loop) | `swallow_note` + `SwallowBook`: a ledger for the house law's swallowed exceptions, so a silently starving guarded block is countable | — |
| `engines/egocentric/verdicts.py` | live | STATIC `engines/egocentric/__init__.py:51`; LAZY `cognitive_loop.py:2221` (constructed at `:2232`) | `MuteHandler`: quarantine on a MUTE verdict, answering with the discriminating probe (least-observed candidate cell). `WIRING_REGISTRY.md:205` marks the probe SEVERED — it prints, `release()` is never called | — |

---

## `engines/cognition/` — 33 files

| path | dest | reached-by (with site) | what it does | if preserve: capability, and why it may matter |
|---|---|---|---|---|
| `engines/cognition/__init__.py` | live | STATIC `engines/__init__.py:122`; **STRING** `engines/registry.py:163` (`module='engines.cognition'` → `importlib.import_module` at `registry.py:381`) | package façade re-exporting `CognitiveStageSystem`, `MetacognitiveReasoningEngine`, `RuleInductionEngine` and (from `engines.social`) `AgentHypothesisSystem` | — |
| `engines/cognition/ab_testing.py` | **preserve** | TEST-ONLY — `tests/test_phase5_validation.py:20`, which is in `tests/` root and therefore **not run by CI** (`.github/workflows/ci.yml:52` runs `pytest tests/gate` only); `pytest.ini` `testpaths = tests` means a bare local run does collect it. Bare-name sweep across `.py/.json/.md/.txt/.toml/.yaml/.ini/.cfg` **and `.github/**`, `.pre-commit-config.yaml`, `.githooks/**`, `.claude/**`**: **zero occurrences** outside itself and that test | `ABTestManager`: deterministic variant assignment by game-id hash, phase configs (5a/5b/5c), `PhaseMetrics.meets_thresholds`, **`maybe_promote` AND `rollback`**, plus `kill`/`resurrect`/`is_killed` | The build can *assign* an arm (`lp_drive.assign_arm`) and it can *measure* one. It has no mechanism that promotes an arm or rolls it back on the evidence, and no kill switch — the promote/rollback decision is currently a human reading `PORT_LOG`. This is that loop, already written, with the thresholds as data. Bears on mandate item 5 (a rate that acts) |
| `engines/cognition/algorithms.py` | live | STATIC `cognitive_router.py:38`, `meta_planner.py:25` | the search-algorithm portfolio: topological-DP, bidirectional, landmark-A\*, greedy, beam, information-maximizing, hierarchical-A\*, backtracking-A\*, retrieval, exclusion-aware — selected per domain/quadrant | — |
| `engines/cognition/blackboard.py` | live | STATIC `evolution_runner.py:73` + 9 in-package importers; LAZY `decision_rung_system.py:1390`, `:1402` | the typed-slot knowledge store replacing the raw context dict: per-slot confidence/source/staleness, checkpointing, Rumsfeld counts, valence accessors. **Also carries four inline duplicate classes — see PAIRS §1-5** | — |
| `engines/cognition/catastrophic_fallback.py` | live | STATIC `cognitive_router.py:44` | the router's circuit breaker: quadrant-oscillation loops, empty frontiers, contradiction storms and iteration blowouts trip an escape back to a static ordering | — |
| `engines/cognition/causal_map.py` | live | STATIC `cognitive_loop.py:46`; LAZY `cognitive_loop.py:1195`, `:1261`, `:1298`, `:1357` | typed persistent causal knowledge per game — per-position effects, cross-position rules, goal plans, confidence, surprise checking, delayed observation, BFS pathing (docstring at line 5, after a `PYTHONDONTWRITEBYTECODE` preamble) | — |
| `engines/cognition/cognitive_frame.py` | live | STATIC `cognitive_game_player.py:34`, `cognitive_loop.py:47`, `tools/replay_viewer.py:26` | `CognitiveFrame`: the observable record of one Perceive-Think-Map-Act cycle, renderable to log line / dashboard / dict | — |
| `engines/cognition/cognitive_router.py` | live | STATIC `evolution_runner.py:74`; LAZY `decision_rung_system.py:81` | the central router: holds blackboard + epistemic state, detects quadrant transitions, switches algorithm **on transitions rather than per iteration**, with fallback integration | — |
| `engines/cognition/cognitive_stages.py` | **preserve** | STATIC `engines/cognition/__init__.py:11` (re-export) and `engines/__init__.py:122`. **`CognitiveStageSystem` has zero construction sites.** The only other references are a `TYPE_CHECKING`-guarded annotation (`engines/social/hypothesis_system.py:26`, used at `:46`) and `vulture_whitelist.py:10` — which **is** reached from a dot-dir (`.pre-commit-config.yaml:17` feeds it to the vulture hook), but reaches this name in order to *suppress* vulture's dead-code finding. A silencer, not a caller (amendment §4) | DB-backed Piaget-style developmental stage tracking: competency updates, stage-transition evaluation, per-stage capability sets, and `get_population_distribution` across the swarm | A **population-level developmental read** — where the fleet's agents sit on a competence ladder, and what each stage is permitted to attempt. The live stack measures per-agent standing, reputation and mastery, but has no notion of a *stage* that gates which capabilities are available, and no cross-agent distribution of it. `hypothesis_system` was built to accept one (`cognitive_system=None`) and has never been handed one — the socket exists and is empty |
| `engines/cognition/contradiction_detector.py` | **preserve** | TEST-ONLY — `tests/test_epistemic.py:22`, in `tests/` root, **not run by CI**. The one non-test string hit (`eisenhower_layer.py:381`) is a **rung name** inside a `theory_testing_rungs` list, not this module. Zero hits across `.github/**`, `.pre-commit-config.yaml`, `.githooks/**`, `.claude/**` | severity-graded belief conflict: MILD (KK→KU, confidence weakens and a specific question emerges) vs SEVERE (KK→UU, the belief is invalidated), with exclusion lists, failed-path tracking and a catastrophic threshold | The live stack records *that* something was falsified (`falsified_ledger` — itself unreached, `discrepancy.objective_falsified`, the verdict stream) and never *how badly*. The difference between "this narrows my confidence, and here is the question it raises" and "this belief is void" is the difference between a targeted next probe and a restart; nothing live can express the first |
| `engines/cognition/edge_inference.py` | live | LAZY `decision_rung_system.py:1329` — inside the per-game router initialisation, a genuine production path; also `tests/test_edge_inference.py:32` and the (unreached) `manual_tools/validate_inferred_edges.py:36` | derives rung-graph edges instead of authoring O(n²) of them: static slot-dataflow analysis (writes→reads), category adjacency/fallback heuristics, and runtime transition observation | — |
| `engines/cognition/edge_trust_manager.py` | **preserve** | TEST-ONLY — `tests/test_phase6_production.py:21`, `tests/test_phase75_stabilization.py:24`, both in `tests/` root and **not run by CI**. Bare-name sweep including all dot-dir config: zero occurrences elsewhere. The router's live edge-trust call goes to a *different* class (see PAIRS §2) | `GraphEvolutionManager`: cumulative per-edge trust across games, EMA weight updates, trust→cost and trust→info-gain modifiers, **crystallized** vs **toxic** edge classification, generation advance, DB persistence | Trust accumulated on **transitions**, and persisted across generations. The live path's trust is per-call and per-agent; `standing` scores atoms, `lp_drive` scores arms, and neither carries a judgement about a *move between two states* forward across games. `is_toxic` — a transition that has earned the right never to be tried again — has no live counterpart at all |
| `engines/cognition/eisenhower_layer.py` | live | STATIC `cognitive_router.py:45` | the convergent layer: takes the divergent candidate rungs and prioritises by urgency × importance, with a scheduled queue, ageing, and an all-eliminate handler | — |
| `engines/cognition/epistemic_logging.py` | live | STATIC `cognitive_router.py:105` | structured epistemic trace records (schema + logger + transition matrix + pattern detection) persisted to `epistemic_traces` | — |
| `engines/cognition/epistemic_state.py` | live | STATIC `cognitive_router.py:46`, `epistemic_logging.py:25-26`, `epistemic_tracker.py:21` | the Rumsfeld state-machine data structures: `EpistemicState`, `EpistemicTransition` (progression/regression/stagnation), `TransitionResponse`, and the default per-quadrant algorithm table | — |
| `engines/cognition/epistemic_tracker.py` | live | STATIC `cognitive_router.py:47`, `evolution_runner.py:79`; LAZY `decision_rung_system.py:82` | tracks the current KK/KU/UK/UU quadrant, detects transitions, keeps history for pattern/stagnation detection, and names the algorithm the transition implies | — |
| `engines/cognition/hysteresis.py` | live | STATIC `cognitive_router.py:48` | prevents quadrant thrashing: confirmation counts before a transition, per-quadrant cooldowns, signal decay, and a thrashing score | — |
| `engines/cognition/meta_planner.py` | live | STATIC `cognitive_router.py:49` | algorithm selection with bucketed cache keys (so a 0.73→0.74 confidence move does not invalidate), tiered profile→cache→full-compute lookup, and targeted invalidation | — |
| `engines/cognition/metacognition.py` | live | **STRING** — `engines/registry.py:162-167` (`class_name='MetacognitiveReasoningEngine'`) instantiated at `registry.py:381`; consumed at `rungs/filter_rungs.py:658`, `:803`, `rungs/hypothesis.py:135`, `:1337`. Also STATIC `engines/cognition/__init__.py:12` | prediction before acting, assumption registration/challenge, failure-pattern insight, action and click-coordinate elimination, post-win reflection | — |
| `engines/cognition/path_crystallization.py` | live | LAZY `engines/cognition/cognitive_router.py:590` — constructed in `CognitiveRouter.__init__`, read at `:880`, written at `:1606` | a path traversed enough times becomes a direct lookup: domain-relative thresholds, de-crystallisation on decay, DB persistence | — |
| `engines/cognition/phenomenology_layer.py` | live | STATIC `cognitive_loop.py:48`, `cognitive_router.py:50`, `valence_tagged_slot.py:42`, `engines/reasoning/graph_evolution.py:27` | compresses blackboard state to a 5-D `FeltState` (valence, arousal, certainty, agency, salience, momentum), stabilises it, and injects it back as urgency/importance bias | — |
| `engines/cognition/precomputation.py` | live | STATIC `cognitive_router.py:55`; LAZY `shadow_testing.py:330` | offline preprocessing for O(1) query: landmark distances, topological order, category clusters, reverse edges, plus an incremental updater with cycle detection | — |
| `engines/cognition/process_knowledge.py` | live | STATIC `cognitive_router.py:121` | extracts abstract role patterns (ENTRY→LEVERAGE→COMPOUNDING) from successful concrete paths and re-instantiates them for a new domain | — |
| `engines/cognition/question_manager.py` | live | STATIC `cognitive_router.py:89` | the KU question lifecycle: raise (free or from template) → active → answered / demoted after failed attempts / abandoned, with priority and resolution rate | — |
| `engines/cognition/routing_metrics.py` | live | STATIC `cognitive_router.py:97` | decision-level telemetry against named targets (rungs per decision, latency, first-win rate, backtracking, contradiction detection) with per-metric status and a rollout-readiness check | — |
| `engines/cognition/routing_traces.py` | live | STATIC `evolution_runner.py:80` | persists each routing decision's path, algorithms, epistemic transitions, action and later outcome, with a query layer and outcome correlation | — |
| `engines/cognition/rule_induction.py` | live | LAZY `rungs/exploitation.py:3973` (constructed at `:3975`); STATIC `engines/cognition/__init__.py:13` | extracts transferable rules from winning sessions — action-effect analysis, precondition extraction, visual signature, then match-to-new-game for transfer (docstring at line 5) | — |
| `engines/cognition/rung_roles.py` | live | STATIC `engines/cognition/process_knowledge.py:43` | the four-role taxonomy (ENTRY / LEVERAGE / COMPOUNDING / RESOLUTION) with valid- and backtrack-transition tests and path-structure analysis | — |
| `engines/cognition/search_context.py` | live | STATIC `algorithms.py:35`, `cognitive_router.py:56`, `meta_planner.py:43` | the injectable context that keeps algorithms stateless: algorithms *request* mutations (checkpoint, backtrack, exclude, contradiction) and the router applies them | — |
| `engines/cognition/shadow_testing.py` | **preserve** | LAZY `decision_rung_system.py:1574` — but that import is inside `get_shadow_tester()`, and **neither `get_shadow_tester` nor `enable_shadow_mode` is called anywhere in the tree, dot-dirs included** (their `def` lines at `:1570` / `:1563` are the only occurrences; zero hits in `.github/**`, `.pre-commit-config.yaml`, `.githooks/**`, `.claude/**`). Otherwise TEST-ONLY (`tests/test_phase5_validation.py:34`, in `tests/` root, **not run by CI**) | `ShadowTester`: runs two deciders on the same input, keeps the **safe** one authoritative, types and stores every divergence, and reports agreement statistics | A **general** shadow harness — decider-agnostic, with divergence typing and a persistence schema. `gate.py` has a shadow mode, but it is bespoke to the gate, speaks the gate's vocabulary, and cannot be pointed at anything else. Any future "does the new selector agree with the old one before we switch" question has this answer already written, and it pairs with `ab_testing` (§2 above) to make a complete promote-on-evidence loop that the build currently lacks both halves of |
| `engines/cognition/slot_registry.py` | live | STATIC `cognitive_router.py:81` | `SLOT_DEFINITIONS` — the 87 blackboard slots with category, expected type, writers and readers, plus a coverage validator | — |
| `engines/cognition/uk_potential_index.py` | live | STATIC `cognitive_router.py:113` | O(1) "do we have cached knowledge?" for the UK quadrant: a bloom filter for definite-no, a detail dict, and a cold-start structural fallback | — |
| `engines/cognition/valence_tagged_slot.py` | live | STATIC `blackboard.py:51`, `cognitive_router.py:61`; LAZY `blackboard.py:1155` | urgency and importance as **part of the encoding** rather than metadata looked up separately — O(1) urgency reads, context-varying valence, aggregate urgency/importance | — |

---

## PAIRS AND DUPLICATES

The genus the GM asked for, with both halves named. Nine live findings and one already-resolved
case kept on record so the fix is visible.

### 1. `CrystallizedPath` exists twice; the live half is not the one in the blackboard
`engines/cognition/blackboard.py:393` and `engines/cognition/path_crystallization.py:53` both
define a `CrystallizedPath` dataclass, with **different fields** (blackboard's keys on
`path_id` + `trigger_rumsfeld` + `min_success_rate`; the standalone keys on `domain_signature` +
`traversal_count` + `avg_ticks`). The blackboard additionally carries
`crystallize_path` (:1084), `get_crystallized_path` (:1104) and `get_crystallized_path_by_id`
(:1115) — **all three have zero callers outside `blackboard.py`.** The router uses the standalone
one instead (`cognitive_router.py:591` constructs `PathCrystallizer`, reads it at `:880`, writes
it at `:1606`). So the blackboard holds a complete, never-exercised second implementation of
crystallisation, inside a module that `evolution_runner.py:73` imports on every run.

### 2. Edge trust exists **three** times, and the live one is the thinnest
- `engines/cognition/blackboard.py:302` `EdgeTrustRecord` + `record_edge_traversal` (:1052) +
  `get_edge_trust` (:1073) — zero callers outside `blackboard.py`.
- `engines/cognition/edge_trust_manager.py:64` `EdgeTrustRecord` + `GraphEvolutionManager` (:158)
  — test-only; the richest of the three (EMA, generations, crystallized/toxic classification).
- `engines/reasoning/graph_evolution.py` `GraphEvolution` — **the live one**, imported at
  `cognitive_router.py:65`, constructed at `:585`, called at `:2111`.

Three implementations of "how much do I trust this transition", one live, and the live one is not
the one with cross-game accumulation.

### 3. `RumsfeldAssessment` is defined twice with different shapes and no converter
`blackboard.py:140` (the live assessment object: routing priority, questions, facts, KK
confidence recalculation) and `routing_traces.py:55` (a serialisation dataclass with
`to_dict`/`from_dict`). `routing_traces` builds its own from a plain dict
(`routing_traces.py:317-319`) and never sees the blackboard's. Two objects, one name, no
translation between them — a reader who greps the name lands on the wrong one half the time.

### 4. `EdgeType` is defined twice as two different enums
`blackboard.py:81` and `edge_inference.py:50`. `edge_inference` is the module that *produces*
edges (live via `decision_rung_system.py:1329`); the blackboard is the module that *stores* them.
They do not import each other and the members are not asserted equal anywhere.

### 5. The question and UK-potential lifecycles each exist twice
`blackboard.Question` (:113) / `blackboard.RumsfeldAssessment.add_question`/`answer_question`
against `question_manager.ManagedQuestion` (:45) + `QuestionManager` (:172); and
`blackboard.UKPotentialEntry` (:548) + `register_uk_need`/`clear_uk_need` against
`uk_potential_index.UKEntry` (:32) + `UKPotentialIndex`. In both pairs the router constructs the
standalone manager (`cognitive_router.py:89`, `:113`) and the blackboard's inline lite version is
the one carried but not driven.

**§1-5 are one finding stated five ways: `blackboard.py` (1368 lines, live from
`evolution_runner.py:73`) contains inline lite re-implementations of five subsystems that also
exist as dedicated modules. The dedicated modules are the ones wired to the router; the inline
copies are dead weight that a reader cannot distinguish from the live path by name.**

### 6. `goal.abduce_target` vs `relations.candidate_relations` — the successor is the dead one
`engines/egocentric/goal.py:122/140` proposes goal cells under a single relation
("be on the unique small distinct object"). `engines/egocentric/relations.py:100` was written to
replace exactly that, and says so in its own docstring: the one-relation hypothesis *"is too
narrow"*, so propose several typed relations (`BE_AT` / `TOUCH` / `COVER`) plus ALL-quantified
class candidates and let the reward-priced market arbitrate. **`relations`' three functions have
zero callers; `goal`'s two module-level functions also have zero callers, but `GoalManager` —
the narrow path — is live through `spine.py:20`.** Both halves of the pair are partly unreached
and the narrow half is the one still steering.

### 7. The route-bin table exists in three files, and the drift check guards only one seam
The four bin tokens are defined three times:
- `engines/egocentric/router.py:17-20` — the organ that produces them;
- `engines/egocentric/narration.py:119-122` — commented *"string-stable mirror of router.py; no
  import cycle"*, with **no assertion**;
- `engines/egocentric/persistence.py:78-82` — a mirror of *narration*, with an explicit
  equality check that raises `RuntimeError` on drift (`persistence.py:81-82`).

So `persistence ↔ narration` is protected and `narration ↔ router` is not. This is the
"normaliser applied to one side of a pair" shape precisely: a rename in `router.py` breaks the
narration stream's bin vocabulary silently, and the one assertion in the chain will still pass
because it compares the two mirrors to each other rather than either to the organ.

### 8. The gate re-implements the composer's WANT decoding instead of importing it
`composer.py:198` `_want_cells` / `:222` `_satisfied` against `gate.py:281` `_want_cells_of` /
`:334` `_satisfied`. `gate.py:67` **already imports `composer`**, so the duplication is not an
import-cycle workaround. Two decoders of the same WANT structure, one of which is what the other
is meant to be checking.

### 9. `sigma_of` names two unrelated organs in the same package
`consumer.py:200` `sigma_of(before, after, slot, residual)` returns the candidate-blind residual
signature; `persistence.py:108` `sigma_of(bet, plan, act)` returns the step's *strategy* tuple.
No shared code, no shared meaning, one name inside one package. Not a duplicate implementation —
a findability hazard, recorded because a name search over `sigma_of` reads as one organ.

### 10. Two "routers", two "trackers" — naming collisions across the slice boundary
`engines/egocentric/router.py` (`ResidualRouter`, four residual bins) and
`engines/cognition/cognitive_router.py` (`CognitiveRouter`, rung-graph search) share the word;
`engines/egocentric/perception.py:167` `ObjectTracker` (permanence by overlap) and
`engines/perception/object_tracker.py:50` `ObjectTracker` (outside this slice) share the class
name outright. Also worth noting: `engines/cognition/algorithms.py` `BidirectionalSearch` and
`engines/egocentric/planner.py:plan_to_identity` both implement meet-in-the-middle search over
different graphs with no shared code — the same algorithm written twice for two substrates.

### RESOLVED, kept on record
`state_key` **was** this genus and is no longer: `retention.py:118` now holds the single
definition, `planner.py:152` aliases it (`_state_key = _retention.state_key`), and
`scheduler.py:68` imports that alias — with `retention.py:119-120` stating the reason in the
docstring (*"the definition moved there so planner, scheduler and store share ONE hash"*). Two
functions became one, and the reason is written down at the site. This is what a fixed instance
of §1-9 looks like.

---

## RESIDUE — stated, not resolved

- **`engines/egocentric/relations.py` still has no `WIRING_REGISTRY.md` row.** Every other
  unreached organ found here does (`falsified_ledger` :209, `janitor` :206, `Marketplace` :212).
  Corrected after Amendment 1: the fact is *not* recorded only in prose — `tests/gate/
  test_wiring_registry.py:547-554` carries it as an explicit acknowledged exception and `:669`
  asserts it, and that file is its own **BLOCKING CI step** (`ci.yml:46`). So the gap is pinned by
  CI while remaining absent from the registry it is a gap in. The test itself calls the state
  QUEUED — *"a SEVERED row with the reason, or a deletion"* — and this pass supplies the third
  answer the queue did not have: `preserve`, for the capability named in its row.
- **A blocking CI test suite is not the live path, and this file keeps the two apart.** Three
  preserve rows (`janitor`, `falsified_ledger`, `relations`) are executed on every push by
  `pytest tests/gate -q`. That makes them *maintained* — they cannot silently rot — and it does
  not make them reached in production. Any later move must keep the `tests/gate` import paths
  working or it breaks a blocking gate.
- **Four cognition preserve rows are reached only by tests CI does not run.** `ab_testing`,
  `contradiction_detector`, `edge_trust_manager` and `shadow_testing` live behind
  `tests/test_phase5_validation.py`, `tests/test_epistemic.py`, `tests/test_phase6_production.py`
  and `tests/test_phase75_stabilization.py` — collected by a bare local `pytest` (`pytest.ini`
  `testpaths = tests`), never by `ci.yml`. These four have no gate holding them correct, which is
  the weakest state any file in this slice is in.
- **`WIRING_REGISTRY.md:209` proposes DELETE for `falsified_ledger`.** This pass proposes
  `preserve` instead, for the reason in its row. The two verdicts are in the tree at once; the GM
  decides, and this file does not act.
- **`.runs/arms/<hash>/` holds a full second copy of the repo**, correctly `.`-prefixed and out of
  scope for moves — but any future name-based sweep that forgets to exclude it will double every
  count and can make an unreferenced symbol appear referenced. Note the asymmetry Amendment 1
  creates: dot-dirs must now be **searched** for invocation sites, and this one is the case where
  searching it produces false positives rather than true ones. A mirror is not a caller, exactly
  as a whitelist is not a caller. The rule that survives both is: name the site and say what it
  does, never count hits.
- No file in this slice was unreadable; all 76 parsed. No `considered_dead` row was produced —
  every file here is either on an executable path or holds capability named above.
