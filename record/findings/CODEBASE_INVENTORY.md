# CODEBASE INVENTORY — every `.py` outside `.`-directories, classified

**Read against FIGURE 11 — "the habitat is enumerated, never composed."** The habitat is not
argued into existence; it is listed. So this read starts at the residual (the six production
entrypoints), lists everything in contact with it, then everything in contact with those, and
walks outward until the cascade stops mattering — 524 files, no sampling, no "and similar".
Where the cascade stopped is stated, not implied: the outermost ring here is a file whose name
appears nowhere in the tree but its own.

**Read against FIGURE 6 — "an instrument is improved from a worse instrument already
returning something."** Two consequences, both binding on this document. First, capability that
already exists and is unreached is a **proto-instrument, not a nice-to-have** — the HELD list
below is written on that basis. Second, this inventory is itself an improved instrument, and the
worse one it improves is in the tree: `tools/repo_assess.py`, which already encodes the
lazy-import lesson in its own docstring and is classified DEAD by its own criteria (no mention
anywhere outside itself). The wall did not move by composition; it moved by importing a method
from a source that was already there.

Binding mandate: `record/corpus/THE_PROCTOR_MANDATE.md` item 7. Digest:
`record/corpus/FIGURES_TEXT_DIGEST.md`.

**THE REQUIREMENT (GM):** *be able to verify nothing is hiding.* Every failure this week —
a module reachable only by a lazy import, five composer-lineage modules nobody remembered, a
grammar in two repos under two names — was a **findability** failure, not a correctness one.
This document is therefore built so a reader can check it, not believe it: every non-LIVE row
names the ONE site that reaches it, `file:line`, with the mechanism.

**Snapshot:** branch `v4-cold`, HEAD `41886d6`, 2026-08-22 ~02:40 UTC. The tree was **in
flight during this read** — `engines/egocentric/standing.py` and `tools/beat_rates.py` both
appeared mid-run and are included; 25 tracked files were dirty. Re-run before acting on any row.

---

## COUNTS

| | files |
|---|---|
| **TOTAL `.py` outside `.`-dirs** | **524** |
| **LIVE** — transitively, statically imported from an entrypoint | **160** |
| **OBSCURELY REACHABLE** | **331** |
| &nbsp;&nbsp;· `OBSCURE-E` — an executable path reaches it (lazy import, registry/importlib string, subprocess, pytest, a test) | 251 |
| &nbsp;&nbsp;· `OBSCURE-N` — **nominal only**: its name occurs elsewhere but nothing invokes it | 80 |
| **DEAD** — no import, no invocation, no test, no mention outside its own file | **33** |
| **HELD (capability this build lacks)** — a subset of OBSCURE + DEAD, listed below | **26** |

Entrypoints: `evolution_runner.py`, `tools/swarm_supervisor.py`, `tools/sprint_keeper.py`,
`cognitive_game_player.py`, `game_player.py`, `arc_api_adapter.py`.

---

## METHOD, AND WHAT EACH CLASS MEANS

**The import graph is built with `ast` — parse only. No module in this tree was imported or
executed at any point in this read.** Package semantics are modelled: importing `a.b.c` marks
`a/__init__.py` and `a/b/__init__.py` reached, which is how a re-export can carry a module into
the live set (see FINDING 2). Module-level imports build the LIVE graph; imports inside a
function or method body are recorded separately as lazy edges.

- **LIVE** — reachable from an entrypoint through module-level imports only. `depth` = hops from
  the nearest entrypoint (0 = the entrypoint itself).
- **OBSCURE-E** — not statically reachable, but an executable path exists. Mechanisms found, in
  precedence order: a lazy/in-function import; `engines/registry.py`'s `ENGINE_CONFIGS`
  `module='…'` strings fed to `importlib.import_module` (registry.py:381); pytest collection
  (`pytest.ini`: `testpaths=tests`, `python_files=test_*.py`); an import from a test; a
  command line / `sys.executable` / `-m` invocation; `spec_from_file_location`.
- **OBSCURE-N** — the module's bare name appears in other files, but every occurrence is prose,
  a comment, a markdown link, or a bare entry in a filename list. **Nothing runs it.** This tier
  exists because the mandate's literal DEAD test ("no string mention outside its own file")
  would otherwise clear 80 files that nothing executes. Kept out of DEAD to honour the letter;
  named separately to honour the truth.
- **DEAD** — no static import, no lazy import, no dynamic/registry string, no command line, no
  test, and no mention of its name anywhere outside itself.

**Name search.** Every non-live module's bare name was searched as a STRING across
`.py .json .md .txt .toml .yaml .yml .ini .cfg .sh .ps1 .bat` — the search that caught
`manual_tools` (reached only by `evolutionary_engine.py:464`'s function-local import; confirmed
still the only site).

**Verified overrides.** Six rows were re-classified by hand after reading the cited site; each is
labelled `VERIFIED OVERRIDE` in the table with its reason (the `engines/postgame/` package —
its only "references" are usage examples inside its own docstrings, plus a collision with the
`lessons_learned` *database table* name at `context_builder.py:154`).

**Exclusions honoured.** `.`-prefixed directories skipped entirely at every level. Not opened:
`docs/GAME_TRUTH`, `ouroboros_cpu/objective_grammar.py`, the train-set-answers directory, `.env`.
No game frame was decoded. The 28 files under `environment_files/*/*/` are ARC game-environment
source: they are counted and classified from their reachability only — **their contents were not
read** (mandate item 8), beyond an MIT licence header.

---

## WHAT WAS HIDING — the genera, with receipts

### FINDING 1 · The live path itself is 27 modules wider than any import scan shows
Twenty-seven modules are reached **only by an in-function import from a module that is LIVE**.
They run in production every episode; a static scan condemns every one of them. Eleven sit
inside the protected `engines/egocentric/` stack:

| module | the ONE site |
|---|---|
| `engines/egocentric/narration.py` | `cognitive_loop.py:229` |
| `engines/egocentric/scheduler.py` | `cognitive_loop.py:433` |
| `engines/egocentric/starvation.py` | `cognitive_loop.py:1011` |
| `engines/egocentric/frontier.py` | `cognitive_loop.py:1667` |
| `engines/egocentric/composer.py` | `cognitive_loop.py:4906` |
| `engines/egocentric/persistence.py` | `cognitive_loop.py:5338` |
| `engines/egocentric/gate.py` | `cognitive_loop.py:5362` |
| `engines/egocentric/action_book.py` | `cognitive_loop.py:5399` |
| `engines/egocentric/grammar.py` | (static, from `gate.py` — inherits gate's invisibility) |
| `engines/egocentric/latents.py` | `engines/egocentric/planner.py:213` |
| `engines/egocentric/janitor.py` | reached only by `tests/gate/test_fabric_janitor.py` |

and sixteen outside it, including `engines/cognition/edge_inference.py`
(`decision_rung_system.py:1329`), `engines/cognition/shadow_testing.py`
(`decision_rung_system.py:1574`), `engines/cognition/path_crystallization.py`
(`engines/cognition/cognitive_router.py:590`), `engines/reasoning/deliberation_audit.py`
(`decision_rung_system.py:627`), `engines/perception/palette_detector.py`
(`rungs/orientation.py:314`), `engines/perception/sparse_grid.py` (`rungs/orientation.py:517`),
`seed_primitives.py` (`rungs/base.py:47`), `safe_cleanup.py` (`tools/swarm_supervisor.py:178`),
and `manual_tools/analysis/performance_analyzer.py` (`evolutionary_engine.py:464`).
**`manual_tools` was not the exception. It was the first instance of the rule.**

### FINDING 2 · The re-export blind spot has SIX instances, not one
A module whose only importer is a package `__init__.py` is import-reachable and
symbol-unreferenced — the trap that hid `sequence_miner`. Checked across the tree: for each such
module, whether ANY of its public top-level names appears in any other `.py` file. Six fail:

| module | public symbols | referenced anywhere |
|---|---|---|
| `engines/planning/sequence_miner.py` | `SequenceMiner`, `MiningResult` | **0** (the known instance) |
| **`engines/egocentric/relations.py`** | `quantified_candidates`, `class_member_cells`, `candidate_relations` | **0** |
| `engines/postgame/orchestrator.py` | `PostGameProcessor`, `ARCRLVRFramework`, … | **0** |
| `engines/postgame/lessons_learned.py` | `LessonsLearnedEngine`, `DeathCauseHypothesis` | **0** |
| `engines/postgame/replay_learning.py` | (none) | **0** |
| `rungs/exploration.py` | `SmartActionSelectionRung`, … | 0 by symbol — **but live** via its own module-level `RUNGS` dict consumed by `rungs/__init__.py`; a false positive, stated so the check's failure mode is on record |

`engines/egocentric/relations.py` is the one that matters: it is **inside the protected
egocentric package**, it is LIVE by import (depth 3, via `engines/egocentric/__init__.py`), it
has **no row in `record/canon/WIRING_REGISTRY.md`**, and none of its three functions is called anywhere. The
registry gate was written to close exactly this blind spot and it does not cover this file.

### FINDING 3 · `engines/postgame/` is a closed island — six files, zero callers
Fitness calculation, lessons extraction, replay learning and their orchestrator. The intended
caller is named in its own docstring: `game_loop.py` — which lives in `legacy/`. Nothing in the
tree imports `engines.postgame`. This is the largest single unreferenced subsystem found.

### FINDING 4 · 80 files are "reachable" only because two of their own neighbours list them
`manual_tools/utilities/cleanup_temp_files.py`'s `KEEP_FILES` set and
`manual_tools/analysis/analyze_dependencies.py`'s `entry_points` set are **filename inventories**,
not call sites. A naive string sweep reads them as reachability and clears ~20 files. They are
tiered `OBSCURE-N` here. `manual_tools/README.md`, `architecture/traceability/README.md` and
`record/findings/FORGOTTEN_CAPABILITIES.md` do the same for most of the rest. **A prior audit's
"checked as import + dotted path + bare string" test cannot distinguish an inventory from an
invocation; this one does, and the difference is 80 files.**

### FINDING 5 · The cross-repo lineage — the second instance of "two repos, two names"
The five composer-lineage modules named in
`record/findings/PROPOSAL_REASONING_GATE.md:253-256` — `objective_abductor.py`,
`objective_validator.py`, `no_posthoc.py`, `primitive_ledger.py`, `reason_first_agent.py`
(+ `question_tropism.py`) — **are not files in this tree.** Their capability was salvaged into
`engines/egocentric/gate.py` (the no-posthoc wall, the observe ladder, `Discrepancy`, the
`discrimination()` scorer) and `engines/egocentric/grammar.py` (the primes, salvaged from
`origin/new-horse:src/newhorse/grammar.py`). **Both salvage destinations are themselves
lazy-import-only (FINDING 1).** A second live cross-repo edge exists and is a hard-coded absolute
path: `manual_tools/_extract_rungs.py:5` reads
`c:\Users\Admin\Documents\GitHub\BitterTruth-AI\decision_rung_system.py`. The root
`__init__.py` still describes the project as "BitterTruth-AI". **This tree cannot enumerate its
own habitat while part of it is in another repository — stated as the limit of this read, per
FIGURE 11.**

### FINDING 6 · Where the cascade stops
33 files have no mention anywhere outside themselves. Twelve are `manual_tools/*` one-offs and
six are the `postgame` island. Three are load-bearing by intent and unreachable in fact:
`tools/repo_assess.py` (the proto-instrument for this document),
`manual_tools/infer_answerable_by.py`, `manual_tools/validate_inferred_edges.py`. Three are
package markers nothing imports (`__init__.py`, `lab/__init__.py`, `tests/__init__.py`).

---

## HOLDS CAPABILITY THIS BUILD LACKS — **HELD for the GM**

**HELD. No recommendation is made, no move is proposed, nothing here is acted on.** Selection
rule: among OBSCURE and DEAD, files whose first ~60 lines and top-level `def`/`class` names
express something absent from the live `engines/egocentric/` export surface (checked against the
44 live/lazy egocentric modules' public names). Per FIGURE 6, each is read as a **proto-instrument
already returning something**, not as a proposal.

| # | path | what it does | nearest live counterpart | why it may be valuable |
|---|---|---|---|---|
| 1 | `engines/planning/sequence_miner.py` | `compute_level_breakpoints` / `backfill_level_breakpoints`: segments a banked winning sequence by the level each action belonged to | `retention.RetentionStore` tags keys `(game, level)` — a *scope* tag, not a *segmentation* of a stored sequence | The known instance. "These actions solved THIS board" vs "these actions reach where I was" is expressible nowhere else; the schema column `level_breakpoints` exists and has never been written |
| 2 | `engines/perception/event_detector.py` | discrete event vocabulary (MOVEMENT / COLLISION / FUSION) over tracked objects + causal attribution to actions | `effects.classify_transform` / `classify_object_transform` (typed cell deltas) | The live stack types *transforms*; this types *events between objects* and attributes them to an action — a different grain of "what happened" |
| 3 | `engines/perception/spatial_learning.py` | `SpatialEffectLearner` (which position affects which other positions), `MultiObjectGoalTracker`, `PropertyExtractor` | `enables.act_offset` / `fatal_cells` (single-offset) | Action-at-a-distance click maps and multi-object goal configurations; the live enables index is pairwise-atom, not positional-field |
| 4 | `engines/perception/palette_detector.py` | detects legend/palette blocks that *encode a rule*, inside-out vs top-to-bottom mapping direction | NONE | A region of the frame that is instructions rather than state has no representation in the live stack |
| 5 | `engines/perception/sparse_grid.py` | sparse dict frame encoding, `sparse_diff`, `find_common_structure`, `compare_grids_detailed` | `perception.segment` / `label_components` (dense) | Structural comparison across frames without dense scans — bears on mandate item 2 (speed) as well as representation |
| 6 | `engines/reasoning/deliberation_audit.py` | records the top-5 alternative interpretations per decision and what each would have implied | `narration.route_why_not` records ONE alternative bin | A ranked counterfactual set per decision; the live record keeps one runner-up |
| 7 | `engines/cognition/edge_inference.py` | derives graph edges from slot dataflow (writes→reads) by static analysis + runtime observation instead of authoring O(n²) | NONE | A machine that discovers its own wiring — the same problem this inventory solves by hand |
| 8 | `engines/cognition/path_crystallization.py` | a path traversed enough times becomes a direct lookup, skipping the search | `retention` memoises per (state, atom) within a level | Crystallisation is cross-episode and cross-level; retention clears on level change |
| 9 | `engines/cognition/edge_trust_manager.py` | cumulative edge trust across games, EMA updates, trust→cost/info-gain modifiers | `lp_drive` arms, `standing`/reputation | Trust accumulated on *transitions*, not on agents or atoms |
| 10 | `engines/cognition/shadow_testing.py` | runs two deciders in parallel, logs divergences, keeps the safe one authoritative | `gate.py` shadow mode (one layer, its own vocabulary) | A general shadow harness; the gate's is bespoke to the gate |
| 11 | `engines/cognition/ab_testing.py` | deterministic variant assignment + **metrics-driven promotion AND rollback** with phase gates | `lp_drive.assign_arm` (assignment only) | The build can assign arms; it has no mechanism that promotes or rolls one back on evidence |
| 12 | `engines/cognition/contradiction_detector.py` | classifies belief conflicts as mild (KK→KU) or severe (KK→UU) | `falsified_ledger`, `discrepancy.objective_falsified` | Severity-graded contradiction; the live ledger records falsification without grading it |
| 13 | `engines/social/package_compressor.py` | LCS over a cluster of successful sequences → a template with holes | `composer.compose_attempt` (pairwise, simulation-decided) | Composition *induced from many observed sequences* rather than assembled from two atoms |
| 14 | `engines/social/execution_trace_miner.py` **(DEAD)** | mines execution traces for recurring structure | NONE | Trace-level mining; the live path mines frames and atoms |
| 15 | `engines/social/remote_effect_learner.py` **(DEAD)** | learns effects distant from the acted-on cell | `enables.act_offset` (bounded offset) | Unbounded action-at-a-distance |
| 16 | `engines/social/cods_types.py` **(DEAD)** | `BayesianHypothesis`, `OperatorResult`, `CODSGameContext` | `pricing.Hypothesis` (iced) | Already flagged protected-unreferenced in `FORGOTTEN_CAPABILITIES.md` §A4; re-confirmed unreferenced |
| 17 | `engines/regulation/network_exploration_tracker.py` | what the **network** (not the agent) has explored per level; unexplored-region priority; a collective world map | `fabric` collective scope (atoms, not space) | Spatial coverage as a *shared* quantity — the economy has no spatial denominator |
| 18 | `engines/regulation/imagination_budget.py` | `compute_mental_modeling_budget` — how much simulation to afford before acting | `scheduler.PlannerScheduler` (when to engage), `KNOBS` caps | Budgets *thinking*, not *searching*; the scheduler decides whether, not how much |
| 19 | `engines/memory/near_miss_analyzer.py` | analyses episodes that nearly succeeded | `frontier.FrontierBook` (deaths at the frontier) | The frontier books fatal openings; near-misses are the positive-side residual and nothing reads them |
| 20 | `engines/postgame/*` **(DEAD, 6 files)** | fitness calculation, lessons extraction, replay learning, orchestration, single post-game entry point | `outcome_processor.py`, `mastery.py`, `evolutionary_engine` scoring | A whole post-game pipeline with a stated contract and zero callers; bears directly on mandate item 4 |
| 21 | `lab/trend_tracker.py` | a `lab_experiments` table: every experiment, its hypothesis, before/after metrics, outcome; **convergence and plateau detection** | `record/log/PORT_LOG.md` (prose) | Mandate items 3 and 5 in code: a rate, and an automatic "this has been flat for N" — the beat currently does this by memory |
| 22 | `lab/comparative_analyst.py` | splits runs into cohorts and ranks discovered features by **Cohen's d** | `tools/split_half.py` (one statistic, one direction) | Effect-size attribution over *every* discovered feature vs one hand-picked statistic |
| 23 | `lab/code_tracer.py` | discovers which subsystems actually engaged, from traces, with subsystem names discovered at runtime | `tools/live_coverage_diff.py`, `tools/consumption_sweep.py` | Engagement measured from *runs* rather than from source; complements both |
| 24 | `tools/repo_assess.py` **(DEAD — zero mentions)** | the four-verdict repo read (LIVE / CAPABILITY / MISFILED / SUPERSEDED) with the guard product and the lazy-import lesson built into its docstring | **this document** | Per FIGURE 6, the instrument this inventory improves on. It was written for exactly this requirement and has never been cited |
| 25 | `manual_tools/infer_answerable_by.py` **(DEAD — zero mentions)** | inverts the rung read-matrix into "which questions are answerable by whom", with a Rumsfeld taxonomy | NONE | Findability as a derived artefact instead of a periodic manual sweep |
| 26 | `manual_tools/validate_inferred_edges.py` **(DEAD — zero mentions)** | cycle detection, orphan rungs, contradicting edges, confidence distribution over the inferred graph | NONE | The falsifier for #7; the pair is a closed loop and neither half is reachable |

**Adjacent, already on record, re-confirmed unreachable** (not re-argued here):
`manual_tools/scan_context_keys.py` (declared-vs-provided key diff; found a live defect on first
run), `manual_tools/analysis/oracle_stuck_game_diagnostics.py` (per-tier break detector),
`manual_tools/_extract_rungs.py` (rung inventory — and the hard-coded cross-repo path of
FINDING 5), `tools/consumption_sweep.py` (writer-reader pairing + literal-vs-measurement with
the three-outcome honesty rule; cited six times in canon, invoked nowhere),
`manual_tools/profile_baseline.py` (per-rung decision profiler — mandate item 2),
`manual_tools/analysis/pipeline_health_check.py` (seven named pipeline checks; DEAD, zero
mentions), `engines/consciousness/persona_runtime.py` (57 KB, lazy-import-only).

---

## DIRECTORY-DEPTH MAP — for the one-subdirectory rule

All directories deeper than one level below the root, with counts (`.`-dirs excluded at every
level). The rule is *one subdirectory level*; the requirement is *be able to verify nothing is
hiding*. **Where they disagree, the requirement wins — so the collisions and the over-60 cases
are stated, and nothing is proposed.**

| directory | depth | `.py` | all files |
|---|---|---|---|
| `architecture/ARC-API-TOOLKIT-DOCS` | 2 | 0 | 10 |
| `architecture/data-contracts` | 2 | 0 | 2 |
| `architecture/nfrs` | 2 | 0 | 1 |
| `architecture/reliability` | 2 | 0 | 1 |
| `architecture/runtime` | 2 | 0 | 3 |
| `architecture/traceability` | 2 | 0 | 2 |
| `engines/cognition` | 2 | 33 | 33 |
| `engines/consciousness` | 2 | 7 | 7 |
| `engines/egocentric` | 2 | 43 | 43 |
| `engines/memory` | 2 | 5 | 5 |
| `engines/perception` | 2 | 15 | 15 |
| **`engines/perception/terminal`** | **3** | 4 | 4 |
| `engines/planning` | 2 | 5 | 5 |
| `engines/postgame` | 2 | 6 | 6 |
| `engines/reasoning` | 2 | 5 | 5 |
| `engines/regulation` | 2 | 6 | 6 |
| `engines/self_model` | 2 | 16 | 16 |
| `engines/social` | 2 | 12 | 12 |
| `environment_files/<game>` | 2 | 0 | 0 |
| **`environment_files/<game>/<hash>`** (28 dirs) | **3** | 1 each | 2 each |
| `legacy/manual_tools` | 2 | 13 | 13 |
| `legacy/tests_dead_lineage` | 2 | 6 | 6 |
| `manual_tools/analysis` | 2 | 20 | 20 |
| `manual_tools/database` | 2 | 8 | 8 |
| `manual_tools/monitoring` | 2 | 2 | 2 |
| `manual_tools/utilities` | 2 | 13 | 13 |
| `record/corpus` | 2 | 0 | 7 |
| `record/findings` | 2 | 0 | 46 |
| `record/log` | 2 | 0 | 1 |
| `record/prereg` | 2 | 0 | 34 |
| `record/retired` | 2 | 0 | 8 |
| `tests/gate` | 2 | 120 | 120 |
| **`tests/gate/fixtures/old_books/collective`** | **5** | 0 | 5 |
| `tools/verify` | 2 | 1 | 1 |

**Deeper than two levels (the rule's hard cases), 4 sites:**
`engines/perception/terminal` (3), `environment_files/<game>/<hash>` (3, ×28),
`tests/gate/fixtures/old_books/collective` (5 — a fixture path whose *shape* is the fixture).

**WHERE FLATTENING TO ONE LEVEL EXCEEDS 60 FILES IN ONE DIRECTORY — stated, nothing proposed:**

| top-level dir | files after flattening | over 60? | filename collisions that would occur |
|---|---|---|---|
| `engines/` | **161** | **YES — 2.7×** | `__init__.py` ×13 |
| `tests/` | **156** | **YES — 2.6×** | none |
| `record/` | **97** | **YES** | `README.md` ×2 |
| `manual_tools/` | **65** | **YES** | none |
| `environment_files/` | 57 | no | `ft09.py`, `ls20.py`, `vc33.py`, `metadata.json` — **4 collisions**, because three games have two environment hashes each |
| `legacy/` | 38 | no | none |
| `tools/` | 33 | no | none |
| `architecture/` | 25 | no | `README.md` ×2 |

Four directories cannot satisfy the one-subdirectory rule without a >60-file directory, and
`engines/` additionally cannot flatten at all without destroying 13 package `__init__.py` files —
which would break the `engines/registry.py` `importlib` module strings that are the ONLY thing
reaching 5 of its modules. **Stated. Nothing proposed. This is the GM's ruling to make.**

---

## LIMITS OF THIS READ — what it still cannot see

1. **The other repository.** FINDING 5: part of the habitat is not in this tree. FIGURE 11's
   enumeration is incomplete by construction until both repos are walked together.
2. **`getattr`/dispatch tables.** The graph covers `import`, `importlib`, `__import__`,
   `spec_from_file_location`, subprocess argv and config strings. A module selected by a
   dynamically-built name (`"engines." + x`) would not be caught. No such construction was found,
   but absence of a hit is not proof.
3. **Reachable ≠ running.** OBSCURE-E means a path exists, not that it fires. Ten of the eleven
   lazy egocentric modules are behind `try:` blocks; a swallowed `ImportError` would present
   identically to a live import. `record/canon/WIRING_REGISTRY.md`'s SEVERED rows are the complement of this
   document, not a subset of it.
4. **`OBSCURE-N` is a judgement about a line, not about intent.** 80 files are tiered on whether
   the one cited line invokes or merely names. Each cites its line so the call is checkable.
5. **The tree moved during the read** (two new files, 25 dirty). Re-run before acting.

---

## THE FULL INVENTORY — 524 rows

`depth` = hops from the nearest entrypoint (LIVE only). Every non-LIVE row names the ONE site
that reaches it and the mechanism. Paths are relative to each section's directory heading.

#### `(root)/` — 37 files · LIVE 30 · OBSCURE-E 6 · OBSCURE-N 0 · DEAD 1

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | DEAD | — | package marker: nothing in the tree imports this package |
| `abstraction_config.py` | LIVE | 4 | static import chain |
| `agent_lifecycle_manager.py` | LIVE | 1 | static import chain |
| `agent_operating_mode_system.py` | LIVE | 1 | static import chain |
| `arc_api_adapter.py` | LIVE | 0 | static import chain |
| `breakthrough_budget_allocator.py` | OBSCURE-E | — | ENGINE_CONFIGS module string -> importlib.import_module (engines/registry.py:381) — `engines/registry.py:297` |
| `cognitive_game_player.py` | LIVE | 0 | static import chain |
| `cognitive_loop.py` | LIVE | 1 | static import chain |
| `collective_reasoning_engine.py` | LIVE | 1 | static import chain |
| `concept_discovery_engine.py` | LIVE | 1 | static import chain |
| `context_builder.py` | LIVE | 1 | static import chain |
| `database_interface.py` | LIVE | 1 | static import chain |
| `database_logger.py` | LIVE | 2 | static import chain |
| `decision_rung_system.py` | LIVE | 1 | static import chain |
| `event_bus.py` | LIVE | 1 | static import chain |
| `evolution_runner.py` | LIVE | 0 | static import chain |
| `evolution_types.py` | LIVE | 1 | static import chain |
| `evolutionary_engine.py` | LIVE | 1 | static import chain |
| `game_player.py` | LIVE | 0 | static import chain |
| `health_monitor.py` | LIVE | 1 | static import chain |
| `horizontal_transfer_engine.py` | LIVE | 1 | static import chain |
| `mastery_system.py` | LIVE | 1 | static import chain |
| `meta_learning_curriculum.py` | LIVE | 1 | static import chain |
| `multi_stage_matching_pipeline.py` | OBSCURE-E | — | lazy/in-function import — `engines/reasoning/symbolic_reasoning_engine.py:2150` |
| `network_health_responder.py` | LIVE | 1 | static import chain |
| `network_intelligence_engine.py` | LIVE | 1 | static import chain |
| `outcome_processor.py` | LIVE | 2 | static import chain |
| `pipeline_assertions.py` | LIVE | 1 | static import chain |
| `primitive_unlock_manager.py` | LIVE | 1 | static import chain |
| `representation_learner.py` | LIVE | 3 | static import chain |
| `result_recorder.py` | LIVE | 1 | static import chain |
| `safe_cleanup.py` | OBSCURE-E | — | lazy/in-function import — `tools/swarm_supervisor.py:178` |
| `schema_auto_maintenance.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:110` |
| `seed_primitives.py` | OBSCURE-E | — | lazy/in-function import — `rungs/base.py:47` |
| `system_diagnostic.py` | LIVE | 1 | static import chain |
| `system_health_gauges.py` | LIVE | 1 | static import chain |
| `vulture_whitelist.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `tests/gate/test_origin_marker.py:257` |

#### `config/` — 1 files · LIVE 1 · OBSCURE-E 0 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `cognitive_parameters.py` | LIVE | 2 | static import chain |

#### `engines/` — 4 files · LIVE 4 · OBSCURE-E 0 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 1 | static import chain |
| `engine_logger.py` | LIVE | 2 | static import chain |
| `interfaces.py` | LIVE | 2 | static import chain |
| `registry.py` | LIVE | 2 | static import chain |

#### `engines/egocentric/` — 43 files · LIVE 32 · OBSCURE-E 11 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 2 | static import chain |
| `action_book.py` | OBSCURE-E | — | lazy/in-function import — `cognitive_loop.py:5399` |
| `affect.py` | LIVE | 3 | static import chain |
| `agency.py` | LIVE | 3 | static import chain |
| `applicability.py` | LIVE | 4 | static import chain |
| `bank.py` | LIVE | 3 | static import chain |
| `betting.py` | LIVE | 3 | static import chain |
| `binder.py` | LIVE | 3 | static import chain |
| `composer.py` | OBSCURE-E | — | lazy/in-function import — `cognitive_loop.py:4906` |
| `consumer.py` | LIVE | 4 | static import chain |
| `discrepancy.py` | LIVE | 3 | static import chain |
| `effects.py` | LIVE | 3 | static import chain |
| `enables.py` | LIVE | 4 | static import chain |
| `fabric.py` | LIVE | 3 | static import chain |
| `falsified_ledger.py` | LIVE | 3 | static import chain |
| `frontier.py` | OBSCURE-E | — | lazy/in-function import — `cognitive_loop.py:1667` |
| `gate.py` | OBSCURE-E | — | lazy/in-function import — `cognitive_loop.py:5362` |
| `goal.py` | LIVE | 3 | static import chain |
| `goal_abduction.py` | LIVE | 4 | static import chain |
| `grammar.py` | OBSCURE-E | — | static import from an obscurely-reached module — `engines/egocentric/gate.py` |
| `janitor.py` | OBSCURE-E | — | static import from a test — `tests/gate/test_fabric_janitor.py` |
| `latents.py` | OBSCURE-E | — | lazy/in-function import — `engines/egocentric/planner.py:213` |
| `lp_drive.py` | LIVE | 2 | static import chain |
| `mastery.py` | LIVE | 3 | static import chain |
| `mint.py` | LIVE | 3 | static import chain |
| `narration.py` | OBSCURE-E | — | lazy/in-function import — `cognitive_loop.py:229` |
| `navigation.py` | LIVE | 3 | static import chain |
| `observer.py` | LIVE | 3 | static import chain |
| `perception.py` | LIVE | 3 | static import chain |
| `persistence.py` | OBSCURE-E | — | lazy/in-function import — `cognitive_loop.py:5338` |
| `planner.py` | LIVE | 3 | static import chain |
| `pricing.py` | LIVE | 3 | static import chain |
| `relations.py` | LIVE | 3 | static import chain |
| `retention.py` | LIVE | 4 | static import chain |
| `rho.py` | LIVE | 5 | static import chain |
| `router.py` | LIVE | 3 | static import chain |
| `scheduler.py` | OBSCURE-E | — | lazy/in-function import — `cognitive_loop.py:433` |
| `self_locus.py` | LIVE | 3 | static import chain |
| `spine.py` | LIVE | 3 | static import chain |
| `standing.py` | LIVE | 4 | static import chain |
| `starvation.py` | OBSCURE-E | — | lazy/in-function import — `cognitive_loop.py:1011` |
| `swallow.py` | LIVE | 2 | static import chain |
| `verdicts.py` | LIVE | 3 | static import chain |

#### `engines/cognition/` — 33 files · LIVE 27 · OBSCURE-E 6 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 1 | static import chain |
| `ab_testing.py` | OBSCURE-E | — | static import from a test — `tests/test_phase5_validation.py` |
| `algorithms.py` | LIVE | 2 | static import chain |
| `blackboard.py` | LIVE | 1 | static import chain |
| `catastrophic_fallback.py` | LIVE | 2 | static import chain |
| `causal_map.py` | LIVE | 2 | static import chain |
| `cognitive_frame.py` | LIVE | 1 | static import chain |
| `cognitive_router.py` | LIVE | 1 | static import chain |
| `cognitive_stages.py` | LIVE | 2 | static import chain |
| `contradiction_detector.py` | OBSCURE-E | — | static import from a test — `tests/test_epistemic.py` |
| `edge_inference.py` | OBSCURE-E | — | lazy/in-function import — `decision_rung_system.py:1329` |
| `edge_trust_manager.py` | OBSCURE-E | — | static import from a test — `tests/test_phase6_production.py` |
| `eisenhower_layer.py` | LIVE | 2 | static import chain |
| `epistemic_logging.py` | LIVE | 2 | static import chain |
| `epistemic_state.py` | LIVE | 2 | static import chain |
| `epistemic_tracker.py` | LIVE | 1 | static import chain |
| `hysteresis.py` | LIVE | 2 | static import chain |
| `meta_planner.py` | LIVE | 2 | static import chain |
| `metacognition.py` | LIVE | 2 | static import chain |
| `path_crystallization.py` | OBSCURE-E | — | lazy/in-function import — `engines/cognition/cognitive_router.py:590` |
| `phenomenology_layer.py` | LIVE | 2 | static import chain |
| `precomputation.py` | LIVE | 2 | static import chain |
| `process_knowledge.py` | LIVE | 2 | static import chain |
| `question_manager.py` | LIVE | 2 | static import chain |
| `routing_metrics.py` | LIVE | 2 | static import chain |
| `routing_traces.py` | LIVE | 1 | static import chain |
| `rule_induction.py` | LIVE | 2 | static import chain |
| `rung_roles.py` | LIVE | 3 | static import chain |
| `search_context.py` | LIVE | 2 | static import chain |
| `shadow_testing.py` | OBSCURE-E | — | lazy/in-function import — `decision_rung_system.py:1574` |
| `slot_registry.py` | LIVE | 2 | static import chain |
| `uk_potential_index.py` | LIVE | 2 | static import chain |
| `valence_tagged_slot.py` | LIVE | 2 | static import chain |

#### `engines/consciousness/` — 7 files · LIVE 6 · OBSCURE-E 1 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 1 | static import chain |
| `deliberation_engine.py` | LIVE | 2 | static import chain |
| `i_thread.py` | LIVE | 1 | static import chain |
| `i_thread_types.py` | LIVE | 2 | static import chain |
| `persona_runtime.py` | OBSCURE-E | — | lazy/in-function import — `engines/consciousness/__init__.py:30` |
| `sensation_engine.py` | LIVE | 1 | static import chain |
| `weaving_reporter.py` | LIVE | 2 | static import chain |

#### `engines/memory/` — 5 files · LIVE 4 · OBSCURE-E 1 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 1 | static import chain |
| `episodic_memory.py` | LIVE | 1 | static import chain |
| `generation_clock.py` | LIVE | 2 | static import chain |
| `near_miss_analyzer.py` | OBSCURE-E | — | lazy/in-function import — `engines/memory/__init__.py:32` |
| `temporal_integrator.py` | LIVE | 2 | static import chain |

#### `engines/perception/` — 15 files · LIVE 10 · OBSCURE-E 5 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 1 | static import chain |
| `event_detector.py` | OBSCURE-E | — | lazy/in-function import — `engines/perception/__init__.py:28` |
| `object_detector.py` | LIVE | 3 | static import chain |
| `object_tracker.py` | OBSCURE-E | — | lazy/in-function import — `engines/perception/__init__.py:22` |
| `palette_detector.py` | OBSCURE-E | — | lazy/in-function import — `rungs/orientation.py:314` |
| `perceiver.py` | LIVE | 2 | static import chain |
| `perceptual_field.py` | LIVE | 2 | static import chain |
| `player_localizer.py` | LIVE | 1 | static import chain |
| `property_extractor.py` | LIVE | 1 | static import chain |
| `sparse_grid.py` | OBSCURE-E | — | lazy/in-function import — `rungs/orientation.py:517` |
| `spatial_learning.py` | OBSCURE-E | — | lazy/in-function import — `engines/perception/__init__.py:34` |
| `terminal_pattern_detector.py` | LIVE | 2 | static import chain |
| `visual_analyzer.py` | LIVE | 2 | static import chain |
| `visual_cortex.py` | LIVE | 2 | static import chain |
| `visual_reasoning.py` | LIVE | 2 | static import chain |

#### `engines/perception/terminal/` — 4 files · LIVE 4 · OBSCURE-E 0 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 3 | static import chain |
| `dangerous_objects.py` | LIVE | 3 | static import chain |
| `death_zones.py` | LIVE | 3 | static import chain |
| `game_over_theory.py` | LIVE | 3 | static import chain |

#### `engines/planning/` — 5 files · LIVE 4 · OBSCURE-E 1 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 2 | static import chain |
| `replay_learning_engine.py` | OBSCURE-E | — | lazy/in-function import — `engines/planning/__init__.py:10` |
| `sequence_abstraction.py` | LIVE | 2 | static import chain |
| `sequence_miner.py` | LIVE | 3 | static import chain |
| `subgoal_planner.py` | LIVE | 3 | static import chain |

#### `engines/postgame/` — 6 files · LIVE 0 · OBSCURE-E 0 · OBSCURE-N 0 · DEAD 6

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | DEAD | — | VERIFIED OVERRIDE — every automated hit is a usage example inside the package's own docstrings; `lessons_learned` also collides with a DB table name (context_builder.py:154). The named caller, game_loop.py, is in legacy/. Nothing imports engines.postgame. |
| `fitness_calculator.py` | DEAD | — | VERIFIED OVERRIDE — every automated hit is a usage example inside the package's own docstrings; `lessons_learned` also collides with a DB table name (context_builder.py:154). The named caller, game_loop.py, is in legacy/. Nothing imports engines.postgame. |
| `lessons_extractor.py` | DEAD | — | VERIFIED OVERRIDE — every automated hit is a usage example inside the package's own docstrings; `lessons_learned` also collides with a DB table name (context_builder.py:154). The named caller, game_loop.py, is in legacy/. Nothing imports engines.postgame. |
| `lessons_learned.py` | DEAD | — | VERIFIED OVERRIDE — every automated hit is a usage example inside the package's own docstrings; `lessons_learned` also collides with a DB table name (context_builder.py:154). The named caller, game_loop.py, is in legacy/. Nothing imports engines.postgame. |
| `orchestrator.py` | DEAD | — | VERIFIED OVERRIDE — every automated hit is a usage example inside the package's own docstrings; `lessons_learned` also collides with a DB table name (context_builder.py:154). The named caller, game_loop.py, is in legacy/. Nothing imports engines.postgame. |
| `replay_learning.py` | DEAD | — | VERIFIED OVERRIDE — every automated hit is a usage example inside the package's own docstrings; `lessons_learned` also collides with a DB table name (context_builder.py:154). The named caller, game_loop.py, is in legacy/. Nothing imports engines.postgame. |

#### `engines/reasoning/` — 5 files · LIVE 4 · OBSCURE-E 1 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 1 | static import chain |
| `deliberation_audit.py` | OBSCURE-E | — | lazy/in-function import — `decision_rung_system.py:627` |
| `graph_evolution.py` | LIVE | 2 | static import chain |
| `scientific_method_engine.py` | LIVE | 1 | static import chain |
| `symbolic_reasoning_engine.py` | LIVE | 1 | static import chain |

#### `engines/regulation/` — 6 files · LIVE 0 · OBSCURE-E 6 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | OBSCURE-E | — | package __init__ run by the registry importlib load of engines.regulation.frustration_detector — `engines/registry.py:228` |
| `frustration_detector.py` | OBSCURE-E | — | ENGINE_CONFIGS module string -> importlib.import_module (engines/registry.py:381) — `engines/registry.py:228` |
| `imagination_budget.py` | OBSCURE-E | — | ENGINE_CONFIGS module string -> importlib.import_module (engines/registry.py:381) — `engines/registry.py:240` |
| `network_exploration_tracker.py` | OBSCURE-E | — | ENGINE_CONFIGS module string -> importlib.import_module (engines/registry.py:381) — `engines/registry.py:244` |
| `regulatory_signal_engine.py` | OBSCURE-E | — | ENGINE_CONFIGS module string -> importlib.import_module (engines/registry.py:381) — `engines/registry.py:234` |
| `trigger_controller.py` | OBSCURE-E | — | static import from an obscurely-reached module — `engines/regulation/regulatory_signal_engine.py` |

#### `engines/self_model/` — 16 files · LIVE 16 · OBSCURE-E 0 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 1 | static import chain |
| `action6_behavior.py` | LIVE | 2 | static import chain |
| `belief_system.py` | LIVE | 2 | static import chain |
| `click_behavior.py` | LIVE | 2 | static import chain |
| `cognitive_core.py` | LIVE | 2 | static import chain |
| `completion_predictor.py` | LIVE | 2 | static import chain |
| `control_tracker.py` | LIVE | 2 | static import chain |
| `discovery_engine.py` | LIVE | 2 | static import chain |
| `embedding_matcher.py` | LIVE | 2 | static import chain |
| `few_shot_relations.py` | LIVE | 2 | static import chain |
| `grid_analysis.py` | LIVE | 2 | static import chain |
| `network_sharing.py` | LIVE | 2 | static import chain |
| `symbolic_tracker.py` | LIVE | 2 | static import chain |
| `trigger_sequences.py` | LIVE | 2 | static import chain |
| `universal_patterns.py` | LIVE | 1 | static import chain |
| `valence_goals.py` | LIVE | 2 | static import chain |

#### `engines/social/` — 12 files · LIVE 7 · OBSCURE-E 2 · OBSCURE-N 3 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 1 | static import chain |
| `cods_types.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:63` |
| `execution_trace_miner.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/REFACTOR_PLAN_AND_READ.md:27` |
| `hypothesis_system.py` | LIVE | 2 | static import chain |
| `network_contributor.py` | LIVE | 2 | static import chain |
| `package_compressor.py` | OBSCURE-E | — | lazy/in-function import — `engines/social/__init__.py:50` |
| `pariah_manager.py` | LIVE | 2 | static import chain |
| `prestige_engine.py` | LIVE | 2 | static import chain |
| `primitive_suggester.py` | OBSCURE-E | — | lazy/in-function import — `engines/social/__init__.py:44` |
| `remote_effect_learner.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/REFACTOR_PLAN_AND_READ.md:27` |
| `resonance_detector.py` | LIVE | 1 | static import chain |
| `viral_package_engine.py` | LIVE | 1 | static import chain |

#### `rungs/` — 8 files · LIVE 8 · OBSCURE-E 0 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | LIVE | 2 | static import chain |
| `base.py` | LIVE | 2 | static import chain |
| `emergency.py` | LIVE | 3 | static import chain |
| `exploitation.py` | LIVE | 3 | static import chain |
| `exploration.py` | LIVE | 3 | static import chain |
| `filter_rungs.py` | LIVE | 3 | static import chain |
| `hypothesis.py` | LIVE | 3 | static import chain |
| `orientation.py` | LIVE | 3 | static import chain |

#### `tools/` — 31 files · LIVE 3 · OBSCURE-E 12 · OBSCURE-N 14 · DEAD 2

| file | class | depth | reached by |
|---|---|---|---|
| `_durability_writer.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `tools/durability_test.py:15` |
| `beat_rates.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `tests/gate/test_beat_rates.py:63` |
| `bracket_rt.py` | OBSCURE-E | — | static import from a test — `tests/gate/test_bracket_rt.py` |
| `build_action_book.py` | OBSCURE-E | — | static import from a test — `tests/gate/test_action_book.py` |
| `cold_ship.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `tests/gate/test_fabric_read_cache.py:587` |
| `comment_divergence.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/DECISION_ANALYSIS.md:144` |
| `consumption_sweep.py` | OBSCURE-N | — | NOMINAL ONLY: named in 6 other file(s) (prose, comment or filename list) — no invocation found — `record/canon/THE_LADDER.md:1214` |
| `context_minimiser.py` | OBSCURE-E | — | static import from a test — `tests/gate/test_context_min.py` |
| `control_arm.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/BUILD_PROGRAM_2.md:52` |
| `d5_profile_wrapper.py` | DEAD | — | no mention anywhere outside itself |
| `disk_ceiling.py` | OBSCURE-E | — | static import from a test — `tests/gate/test_disk_ceiling_preserves.py` |
| `dump_schema.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:79` |
| `durability_test.py` | OBSCURE-N | — | NOMINAL ONLY: named in 3 other file(s) (prose, comment or filename list) — no invocation found — `record/canon/THE_LADDER.md:730` |
| `efficiency_read.py` | OBSCURE-E | — | static import from a test — `tests/gate/test_efficiency_read.py` |
| `fleet_env.py` | LIVE | 1 | static import chain |
| `fork_divergence.py` | OBSCURE-N | — | NOMINAL ONLY: named in 3 other file(s) (prose, comment or filename list) — no invocation found — `record/canon/THE_LADDER.md:747` |
| `link3_live_check.py` | OBSCURE-N | — | NOMINAL ONLY: named in 3 other file(s) (prose, comment or filename list) — no invocation found — `tests/gate/test_link3_hook_and_vocabulary.py:39` |
| `live_coverage_diff.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `tests/gate/test_wiring_registry.py:38` |
| `n1_metric.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `tests/gate/test_qa_fixes_w4.py:210` |
| `norm_sweep.py` | OBSCURE-N | — | NOMINAL ONLY: named in 5 other file(s) (prose, comment or filename list) — no invocation found — `cognitive_game_player.py:1994` |
| `ood_lint.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/BUILD_PROGRAM_2.md:52` |
| `overnight_run.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `record/prereg/PREREG_SWARM_OFFLINE_MODE.md:26` |
| `premise_pass.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `record/canon/KNOBS.md:529` |
| `regen_series.py` | OBSCURE-E | — | static import from a test — `tests/gate/test_regen_series.py` |
| `replay_viewer.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/PROPAGATION_READ.md:40` |
| `repo_assess.py` | DEAD | — | no mention anywhere outside itself |
| `sigma_backfill.py` | OBSCURE-E | — | static import from a test — `tests/gate/test_sigma_backfill.py` |
| `socket_or_filler_lint.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/prereg/PREREG_READOUTS.md:23` |
| `split_half.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `tests/gate/test_beat_rates.py:18` |
| `sprint_keeper.py` | LIVE | 0 | static import chain |
| `swarm_supervisor.py` | LIVE | 0 | static import chain |

#### `tools/verify/` — 1 files · LIVE 0 · OBSCURE-E 0 · OBSCURE-N 1 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `hermetic.py` | OBSCURE-N | — | NOMINAL ONLY: named in 17 other file(s) (prose, comment or filename list) — no invocation found — `cognitive_loop.py:2055` |

#### `lab/` — 7 files · LIVE 0 · OBSCURE-E 2 · OBSCURE-N 4 · DEAD 1

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | DEAD | — | package marker: nothing in the tree imports this package |
| `branch_breeder.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `architecture/Autonomous Research Lab.md:420` |
| `code_tracer.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `architecture/Autonomous Research Lab.md:417` |
| `comparative_analyst.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `architecture/Autonomous Research Lab.md:418` |
| `evolution_runner_wrapper.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `architecture/Autonomous Research Lab.md:421` |
| `metrics.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `lab/evolution_runner_wrapper.py:69` |
| `trend_tracker.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `lab/branch_breeder.py:155` |

#### `manual_tools/` — 21 files · LIVE 0 · OBSCURE-E 1 · OBSCURE-N 7 · DEAD 13

| file | class | depth | reached by |
|---|---|---|---|
| `_extract_rungs.py` | OBSCURE-N | — | NOMINAL ONLY: named in 3 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:57` |
| `analyze_run.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/SWEEP_COMMENT_DIVERGENCE.md:22` |
| `analyze_run2.py` | DEAD | — | no mention anywhere outside itself |
| `audit_data_usage.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/F8A_READ.md:42` |
| `audit_orphaned_systems.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/HISTORY_TRACE.md:56` |
| `audit_performance.py` | DEAD | — | no mention anywhere outside itself |
| `check_deliberation_traces.py` | DEAD | — | no mention anywhere outside itself |
| `db_validation.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `README.md:381` |
| `gen_analysis_v2.py` | DEAD | — | no mention anywhere outside itself |
| `gen_compare.py` | DEAD | — | no mention anywhere outside itself |
| `gen_compare_v2.py` | DEAD | — | no mention anywhere outside itself |
| `infer_answerable_by.py` | DEAD | — | no mention anywhere outside itself |
| `observer_dashboard.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `README.md:390` |
| `profile_baseline.py` | DEAD | — | no mention anywhere outside itself |
| `scan_context_keys.py` | OBSCURE-N | — | NOMINAL ONLY: named in 4 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/AGENT_ACCESS_MAP.md:41` |
| `scan_disconnection_patterns.py` | DEAD | — | no mention anywhere outside itself |
| `temp_check.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `tests/gate/test_origin_marker.py:257` |
| `test_frame_hash_match.py` | DEAD | — | no mention anywhere outside itself |
| `test_ls20.py` | DEAD | — | no mention anywhere outside itself |
| `test_online.py` | DEAD | — | no mention anywhere outside itself |
| `validate_inferred_edges.py` | DEAD | — | no mention anywhere outside itself |

#### `manual_tools/analysis/` — 20 files · LIVE 0 · OBSCURE-E 5 · OBSCURE-N 13 · DEAD 2

| file | class | depth | reached by |
|---|---|---|---|
| `analyze_dependencies.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `architecture/Autonomous Research Lab.md:672` |
| `audit_cods.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:193` |
| `audit_prestige_system.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/README.md:28` |
| `autopoiesis_monitor.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `architecture/traceability/README.md:15` |
| `console_metrics_capture.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/analysis/oracle_health_monitor.py:40` |
| `diagnose_reasoning.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:188` |
| `gameplay_analyzer.py` | OBSCURE-N | — | NOMINAL ONLY: named in 4 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/utilities/cleanup_temp_files.py:56` |
| `network_health_report.py` | DEAD | — | no mention anywhere outside itself |
| `optimization_threshold_system.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:100` |
| `oracle_health_monitor.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `architecture/traceability/README.md:15` |
| `oracle_stuck_game_diagnostics.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:43` |
| `pariah_analysis.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/README.md:29` |
| `pariah_validator.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `architecture/traceability/README.md:18` |
| `performance_analyzer.py` | OBSCURE-E | — | lazy/in-function import — `evolutionary_engine.py:464` |
| `pipeline_health_check.py` | DEAD | — | no mention anywhere outside itself |
| `prestige_parasite_detector.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:104` |
| `sequence_pruning_system.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:77` |
| `theory_alignment_checker.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:194` |
| `theory_analysis.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/README.md:31` |
| `theory_verification.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/README.md:30` |

#### `manual_tools/database/` — 8 files · LIVE 0 · OBSCURE-E 0 · OBSCURE-N 7 · DEAD 1

| file | class | depth | reached by |
|---|---|---|---|
| `check_all_sequences.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:191` |
| `check_game_ids.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:191` |
| `check_sequences.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:191` |
| `compact_database.py` | DEAD | — | no mention anywhere outside itself |
| `fix_sequences.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:190` |
| `reactivate_best_sequences.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:192` |
| `reactivate_sequences.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:192` |
| `schema_inspector.py` | OBSCURE-N | — | NOMINAL ONLY: named in 3 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/utilities/cleanup_temp_files.py:57` |

#### `manual_tools/monitoring/` — 2 files · LIVE 0 · OBSCURE-E 0 · OBSCURE-N 2 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `review_scorecards.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/README.md:94` |
| `system_status_report.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/README.md:93` |

#### `manual_tools/utilities/` — 13 files · LIVE 0 · OBSCURE-E 4 · OBSCURE-N 8 · DEAD 1

| file | class | depth | reached by |
|---|---|---|---|
| `.vulture_whitelist.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:84` |
| `abstraction_schema.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:106` |
| `cleanup_temp_files.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:193` |
| `enhanced_database_interface.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:113` |
| `evolution_with_parasites.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:94` |
| `get_replay_url.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/README.md:104` |
| `migrate_mastery_system.py` | DEAD | — | no mention anywhere outside itself |
| `pycache_guard.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:194` |
| `quick_check.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/analysis/analyze_dependencies.py:189` |
| `remove_emojis.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/README.md:105` |
| `revive_agents.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:93` |
| `run_context.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `legacy/tests_dead_lineage/test_action_ladder.py:17` |
| `test_pariah_decay.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `manual_tools/README.md:106` |

#### `legacy/` — 19 files · LIVE 0 · OBSCURE-E 12 · OBSCURE-N 4 · DEAD 3

| file | class | depth | reached by |
|---|---|---|---|
| `_investigate_fast.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:77` |
| `_investigate_monopoly.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:77` |
| `_investigate_part2.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:77` |
| `_investigate_part3.py` | DEAD | — | no mention anywhere outside itself |
| `_investigate_part4.py` | DEAD | — | no mention anywhere outside itself |
| `_investigate_part5.py` | DEAD | — | no mention anywhere outside itself |
| `_temp_check.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `tests/gate/test_origin_marker.py:257` |
| `adaptive_action_limits.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/analysis/theory_alignment_checker.py:630` |
| `agent_factory.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `legacy/tests_dead_lineage/test_agent_factory.py:23` |
| `agent_self_model.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `legacy/tests_dead_lineage/test_metacog_eliminations.py:16` |
| `arc_api_client.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:63` |
| `automated_assessment_runner.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:92` |
| `console_tags.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:82` |
| `core_gameplay.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `__init__.py:12` |
| `disk_space_monitor.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:114` |
| `evolution_game_scheduler.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `manual_tools/utilities/cleanup_temp_files.py:112` |
| `game_loop.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `legacy/core_gameplay.py:60` |
| `game_scheduler.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `legacy/evolution_game_scheduler.py:25` |
| `learning_systems.py` | OBSCURE-E | — | named in an invocation (command line / dynamic import / string import) — `legacy/core_gameplay.py:61` |

#### `legacy/manual_tools/` — 13 files · LIVE 0 · OBSCURE-E 0 · OBSCURE-N 13 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `analyze_decision.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:80` |
| `check_api.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:80` |
| `check_gen2.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:78` |
| `check_gen2b.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:78` |
| `check_terminal_patterns.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:80` |
| `debug_routing.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:80` |
| `diagnosis_query.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:81` |
| `diagnosis_query_part2.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:81` |
| `find_tables.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:79` |
| `gen_analysis.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:80` |
| `list_danger_tables.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:79` |
| `trace_check.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:78` |
| `trace_deep_dive.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/FORGOTTEN_CAPABILITIES.md:78` |

#### `legacy/tests_dead_lineage/` — 6 files · LIVE 0 · OBSCURE-E 0 · OBSCURE-N 4 · DEAD 2

| file | class | depth | reached by |
|---|---|---|---|
| `test_action_ladder.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `vulture_whitelist.py:63` |
| `test_agent_factory.py` | DEAD | — | no mention anywhere outside itself |
| `test_critical_systems.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `architecture/cognitive_routing_architecture.md:1292` |
| `test_metacog_eliminations.py` | DEAD | — | no mention anywhere outside itself |
| `test_recent_changes.py` | OBSCURE-N | — | NOMINAL ONLY: named in 2 other file(s) (prose, comment or filename list) — no invocation found — `architecture/cognitive_routing_architecture.md:1294` |
| `test_replay_validation.py` | OBSCURE-N | — | NOMINAL ONLY: named in 1 other file(s) (prose, comment or filename list) — no invocation found — `record/findings/REPO_AUDIT_2026-08-20.md:61` |

#### `tests/` — 28 files · LIVE 0 · OBSCURE-E 27 · OBSCURE-N 0 · DEAD 1

| file | class | depth | reached by |
|---|---|---|---|
| `__init__.py` | DEAD | — | package marker: nothing in the tree imports this package |
| `conftest.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_blackboard.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_cognitive_router.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_database_interface.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_edge_inference.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_eisenhower_layer.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_epistemic.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_epistemic_stability.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_evolutionary_engine.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_graph_evolution.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_i_thread.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_meta_planner.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_persona_runtime.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_phase5_validation.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_phase6_production.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_phase75_stabilization.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_phase7_evolution.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_phenomenology_layer.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_pipeline_canaries.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_reasoning_data_usage.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_reasoning_system_fixes.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_safe_cleanup.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_sequence_system.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_theory_gating.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_trigger_controller.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_two_streams.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_valence_tagged_slot.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |

#### `tests/gate/` — 120 files · LIVE 0 · OBSCURE-E 120 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `test_action_book.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_affect_gains.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_affordance_harvest.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_agent_motion.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_applicability_index.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_backward_chaining.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_bet_spine.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_bracket_rt.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_budget_restoration.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_class_fission.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_click_economy.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_compat_old_books.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_composer_notes.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_composer_stage1.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_composer_stage2.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_composer_stage3.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_composer_stage4.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_composer_stage45.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_conditional_effects.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_consumer_driver.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_consumers.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_context_min.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_corpse_guard.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_cost_flip.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_credit_fallback.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_cross_wave_composition.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_d11_render_import.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_d8_instrument.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_d9_diagnostic_gate.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_dead_dedup.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_decline_branch.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_deploy_on_change.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_discrepancy_planner.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_disk_ceiling_preserves.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_e2e_pipeline.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_effect_atoms.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_efference_copy.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_efficiency_read.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_egocentric_substrate.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_evidence_preserving_cleanup.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_fabric_janitor.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_fabric_next_seq_cache.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_fabric_read_cache.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_fabric_seq_cache.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_frame_instruments.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_frame_normalisation.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_frame_unwrap.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_frontier_harvest.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_frontier_pariah.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_gate_stage1.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_goal_abduction.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_goal_spine.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_handoff_rate.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_hold_stops_recycles.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_import_gate.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_integration_wiring.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_knowledge_fabric.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_latents.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_level0_harvest.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_level_conventions.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_level_scoped_ideas.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_link3_hook_and_vocabulary.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_lp_drive.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_lp_rotation.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_mastery_lite.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_mdl_mint.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_mint_bootstrap.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_move_affordances.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_movement_stack.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_mute_verdict.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_narration_arms.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_narration_spine.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_negative_feeder.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_none_reasons.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_object_transforms.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_origin_marker.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_persistence.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_plan_frontier_veto.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_plan_wire.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_planner_budget.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_planner_retention.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_planner_scheduling.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_predictor_bank.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_properties.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_qa_fixes_w4.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_queue_characterization.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_random_shadow.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_ranked_drain.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_record_keeping.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_refit_destination.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_regen_series.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_replay_feed.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_replay_handoff.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_reset_discipline.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_residual_router.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_rho.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_rho_ladder_live.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_rho_rungs.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_role_binder.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_salient_prefix.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_seed_bias_widening.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_ship_clean.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_sigma_backfill.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_soak_bounded.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_sprint_keeper.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_starvation_codes.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_surprise_weighting.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_swallow_counters.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_system_determinism.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_tail_read.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_torn_writes.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_trace_writer.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_triangulation_consumer.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_typed_transforms.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_u2_checkpoint_retention.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_vectorised_scan.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_verdict_reason.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_verdict_stamps.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_verified_hydration.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |
| `test_wiring_registry.py` | OBSCURE-E | — | pytest collection (pytest.ini: testpaths=tests, python_files=test_*.py) — `pytest.ini:3` |

#### `environment_files/*/` — 28 files · LIVE 0 · OBSCURE-E 28 · OBSCURE-N 0 · DEAD 0

| file | class | depth | reached by |
|---|---|---|---|
| `ar25.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `bp35.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `cd82.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `cn04.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `dc22.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `ft09.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `ft09.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `g50t.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `ka59.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `lf52.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `lp85.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `ls20.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `ls20.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `m0r0.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `r11l.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `re86.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `s5i5.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `sb26.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `sc25.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `sk48.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `sp80.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `su15.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `tn36.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `tr87.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `tu93.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `vc33.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `vc33.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
| `wa30.py` | OBSCURE-E | — | ARC game environment source, loaded by directory scan at runtime (environments_dir default) — `arc_api_adapter.py:471` |
