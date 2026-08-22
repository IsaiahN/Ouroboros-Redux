# EXAM 02 — `engines/` EXCEPT `egocentric/` and `cognition/`

Binding rubric: `record/findings/EXAMINATION_RUBRIC.md`. Built on the earlier automated pass
`record/findings/CODEBASE_INVENTORY.md` (which is corrected in four places below, each with its
receipt). Branch `v4-cold`. **Read-only. Nothing moved, nothing deleted, nothing renamed.**

Every one of the 85 files was opened. Where a file's `__doc__` is `None` the reason is stated
(see DEFECT D below — it is not an absence of documentation, it is a bug).

**RUBRIC AMENDMENT 1 applied.** Dot-directories were searched as invocation sites (never as move
candidates) before any row was called unreached: `.github/**`, `.githooks/**`, `.claude/**`,
`.pre-commit-config.yaml`, `pyproject.toml`, `pytest.ini`, and every root `*.yml/.toml/.cfg/.ini/.sh/.ps1`
(`.env` not opened; `.git`, `.venv` and the four cache dirs skipped as caches). **No dest row in
this document changed.** What the amendment did surface is recorded in *DOT-DIR INVOCATION CHECK*
below, and it is not nothing: CI names this slice's exact blind spot and deliberately does not
gate on it.

---

## COUNTS

| | files |
|---|---|
| **TOTAL `.py` in slice** (all of `engines/**` minus `egocentric/`, `cognition/`, `.`-dirs) | **85** |
| **live** | **74** |
| **preserve** | **10** |
| **considered_dead** | **1** |
| unreadable | 0 |

By package: `engines/` 4 · `consciousness/` 7 · `memory/` 5 · `perception/` 15 ·
`perception/terminal/` 4 · `planning/` 5 · `postgame/` 6 · `reasoning/` 5 · `regulation/` 6 ·
`self_model/` 16 · `social/` 12.

Reach mechanisms actually found in this slice: STATIC 41 · STRING (`ENGINE_CONFIGS` →
`importlib.import_module` at `engines/registry.py:381`) 24 · LAZY-from-a-live-module 12 ·
TEST-ONLY 1 · NONE 7. **CI/hook/config invocation: 0** (Amendment 1; see DOT-DIR INVOCATION CHECK).

---

## THE FOUR HEADLINE FINDINGS

These are the reason the pass was worth doing. Details and receipts follow the table.

### DEFECT A — 14 methods declared in `engines/interfaces.py` exist on NO implementation, and 21 live rung call sites are `hasattr`-guarded no-ops because of it

`engines/interfaces.py` is 25 `Protocol` classes describing what the rungs call on each engine.
Nothing enforces it: `engines/registry.py:42-45` has the `TYPE_CHECKING` imports **commented
out** with `# TODO: Add back when engines/interfaces.py is fully typed`. Diffing each Protocol
against the class the registry actually loads (`ENGINE_CONFIGS`):

| Protocol (`engines/interfaces.py:line`) | implementation loaded by the registry | method declared, **absent on the impl** |
|---|---|---|
| `ScientificMethodInterface:196,215` | `ScientificMethodEngine` | `get_theory_stage`, `questioning_engine` |
| `TerminalPatternInterface:249` | `TerminalPatternDetector` | `detect_terminal_approach` |
| `ViralPackageInterface:334` | `ViralPackageEngine` | `get_pariahs` |
| `IThreadInterface:406,410,414` | `IThread` | `get_wA`, `get_wB`, `spawn_death_persona` |
| `NearMissAnalyzerInterface:435` | `NearMissAnalyzer` | `get_insights` |
| `SubgoalPlannerInterface:457` | `SubgoalPlanner` | `get_current_subgoal` |
| `BudgetAllocatorInterface:475` | `BreakthroughBudgetAllocator` | `get_budget` |
| `RegulatorySignalInterface:496` | `RegulatorySignalEngine` | `get_active_signals` |
| `ReplayLearningInterface:622` | `ReplayLearningEngine` | `get_current_prediction` |
| `ImaginationBudgetInterface:640` | `ImaginationBudgetManager` | `calculate_budget` |
| `NetworkExplorationInterface:663` | `NetworkExplorationTracker` | `get_exploration_stats` |

Each of these names is also the exact string a live rung guards on. The rungs are defensive, so
nothing raises — the rung constructs the engine, asks `hasattr`, gets `False`, and returns an
empty `RungResult`. **Twenty-one such sites** (the guarded method does not exist on the class):

```
rungs/exploitation.py:837   near_miss_analyzer.get_insights            -> NearMissAnalyzer
rungs/exploitation.py:1494  subgoal_planner.get_current_subgoal        -> SubgoalPlanner
rungs/exploitation.py:3435  trigger_sequences.get_proven_sequence      -> TriggerSequenceTracker
rungs/exploitation.py:3456  trigger_sequences.predict_trigger_effect   -> TriggerSequenceTracker
rungs/exploitation.py:3834  valence_goals.get_inferred_goal            -> ValenceGoalEngine
rungs/exploitation.py:3862  valence_goals.get_negative_valence_objects -> ValenceGoalEngine
rungs/exploitation.py:3894  replay_learning_engine.get_current_prediction -> ReplayLearningEngine
rungs/filter_rungs.py:335   terminal_pattern_detector.detect_terminal_approach
rungs/hypothesis.py:47      scientific_method_engine.get_theory_stage
rungs/hypothesis.py:258/259 i_thread.get_wA / get_wB
rungs/hypothesis.py:263     i_thread.spawn_death_persona
rungs/hypothesis.py:1046    belief_system.get_active_beliefs           -> BeliefSystem
rungs/hypothesis.py:1238    symbolic_tracker.suggest_transformation    -> SymbolicStateTracker
rungs/orientation.py:131    grid_analyzer.analyze_grid_structure       -> GridAnalyzer
rungs/orientation.py:153    scientific_method_engine.questioning_engine
rungs/orientation.py:720    breakthrough_allocator.get_budget
rungs/orientation.py:749    regulatory_engine.get_active_signals
rungs/orientation.py:798    visual_analyzer.grid_walking_index         -> VisualAnalyzer
rungs/orientation.py:1158   imagination_budget.calculate_budget        -> ImaginationBudgetManager
rungs/orientation.py:1194   network_exploration_tracker.get_exploration_stats
```

Three whole rungs have **no reachable body at all** — every statement after the guard is dead:
`NearMissAnalyzerRung` (`rungs/exploitation.py:828-852`, priority 48, ordered at
`decision_rung_system.py:215`), `ImaginationBudgetRung` (`rungs/orientation.py:1152-1175`,
priority 4, ordered at `decision_rung_system.py:159`), `NetworkExplorationStatsRung`
(`rungs/orientation.py:1185-1213`, priority 9). Others degrade silently to a literal — e.g.
`rungs/hypothesis.py:47` yields the default `'exploring'` on every single call, so the
"theory contradicted → force exploration" branch at `:49` can never be taken.

The registry's `fallback_legacy_attr` does not rescue these: it only fires when the *import or
instantiation* fails (`engines/registry.py:413-419`), and these modules import cleanly.

**This is the highest-value item in the slice.** Nine engines in this slice are constructed
every episode and their output is discarded at the boundary.

### DEFECT B — all 19 package-level `get_*()` accessors are dead, which invalidates 17 reachability rows in the previous inventory

`engines/{perception,memory,planning,regulation,social,consciousness}/__init__.py` each define
lazy accessor functions whose whole purpose is the in-function import. **Not one of the 19 is
called anywhere in the tree** (searched `.py` across the repo, excluding the definitions
themselves):

`get_object_detector`, `get_object_tracker`, `get_event_detector`, `get_spatial_effect_learner`,
`get_multi_object_goal_tracker`, `get_visual_cortex` (perception) · `get_near_miss_analyzer`
(memory) · `get_replay_learning_engine` (planning) · `get_regulatory_signal_engine`,
`get_network_exploration_tracker` (regulation) · `get_viral_package_engine`,
`get_resonance_detector`, `get_prestige_engine`, `get_primitive_suggester`,
`get_package_compressor`, `get_cods_engine` (social) · `get_i_thread`, `get_sensation_engine`,
`get_persona_manager` (consciousness).

`CODEBASE_INVENTORY.md` classifies 17 modules `OBSCURE-E — lazy/in-function import —
engines/X/__init__.py:NN`. **That edge does not execute.** For 16 of the 17 a *different*, real
site reaches them (named per row below); for exactly one — `persona_runtime.py` — the dead
accessor was the only production edge, so it is TEST-ONLY. Corrected rows below.

### DEFECT C — `engines/postgame/` confirmed a closed island, 6 files, zero callers (lead verified)

Verified by full-tree string sweep on the package path and on all five exported symbols
(`PostGameProcessor`, `FitnessCalculator`, `LessonsExtractor`, `LessonsLearnedEngine`,
`DeathCauseHypothesis`, `ARCRLVRFramework`). Every hit is either inside the package or one of:
`README.md:347` (a documentation inventory row), `context_builder.py:154` (a comment naming the
`lessons_learned` **database table**, not the module), `decision_rung_system.py:196/317` and
`rungs/exploitation.py:3883/4501` (the string `replay_learning`, which is the name of a **live
rung**, colliding with the module name). `engines/__init__.py` does not import the package.
Its stated caller is named twice in its own text — `engines/postgame/__init__.py:28` and
`engines/postgame/orchestrator.py:10`, *"Call this from `game_loop.py` when a game ends"* — and
`game_loop.py` is in `legacy/`. **Re-checked against dot-dirs per Amendment 1: `engines/postgame`
and all six of its symbols appear nowhere in `.github/**`, `.githooks/pre-commit`, `.claude/**`,
`.pre-commit-config.yaml`, `pyproject.toml` or `pytest.ini`. No CI step, no hook, no config
string reaches it. The island holds.**

### DEFECT D — the "Rule 1" prelude silences the module docstring in 63 files

The convention

```python
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'  # Rule 1: Disable pycache
"""Module docstring..."""
```

puts the string **after** a statement, so it is a discarded expression, not a docstring:
`Module.__doc__` is `None`. 63 files repo-wide, 40 of them in this slice, including every file
in `engines/postgame/`, all of `engines/self_model/` except two, and `engines/registry.py`'s
sub-package peers. Consequence: `help()`, `pydoc`, `inspect.getdoc`, and any docstring-driven
tooling see nothing. The text is still readable in the file, which is why no summary below is
marked "unreadable". `engines/self_model/__init__.py` and `engines/perception/__init__.py` get
it right (docstring first, `import os` second) — the fix is a two-line reorder, not a rewrite.

---

## DOT-DIR INVOCATION CHECK (Rubric Amendment 1)

Searched as invocation sites, never as move candidates: `.github/**` (workflows + the two
copilot-instruction docs), `.githooks/pre-commit`, `.claude/**`, `.pre-commit-config.yaml`,
`pyproject.toml`, `pytest.ini`, and every root-level `*.yml/*.toml/*.cfg/*.ini/*.sh/*.ps1`.
`.env` was not opened. `.git`, `.venv`, `.pytest_cache`, `.ruff_cache`, `.hypothesis` skipped as
caches; `.gamma_library`, `.residual_bank`, `.runs` are run/data stores holding no config.

**Rows changed by the amendment: none.** No dot-dir file invokes any module in this slice.
Four things it did establish, which belong on the record:

**1 · CI reads this entire slice, on every push and PR, and knowingly does not gate on it.**
`.github/workflows/ci.yml:61-65` runs `vulture engines/ … --min-confidence 80` with
`continue-on-error: true`. The comment above it, `:56-60`, says why in the project's own words:

> *"Vulture cannot see past `__init__` re-exports — that blind spot hid `sequence_miner.py` for
> months (WIRING_REGISTRY.md). It stays non-blocking BECAUSE it is known-incomplete."*

That is the **exact** defect class this examination found three more instances of in this slice:
`engines/planning/sequence_miner.py` (the named one), `engines/self_model/completion_predictor.py`
and `engines/social/network_contributor.py` — each import-reachable only through a package
`__init__` re-export, each symbol-unreferenced outside `legacy/`. The CI comment is correct about
its own tool and correct about the consequence; the consequence has three more names than it lists.

**2 · The pre-commit hook scans `engines/` on every commit, and a whitelist is actively
suppressing findings inside this slice.** `.pre-commit-config.yaml:10-19` runs vulture with
`files: ^(engines/|core_gameplay\.py|decision_rung_system\.py|autonomous_evolution_runner\.py)`
and `--exclude=deprecated/,tests/,manual_tools/`, passing `vulture_whitelist.py`. Three of that
whitelist's entries exist solely to silence vulture on files in this slice:
`vulture_whitelist.py:7` (`IThreadType`, for `engines/consciousness/weaving_reporter.py`),
`:36` (`MortalityState`, for `engines/consciousness/deliberation_engine.py:1019`) and `:37`
(`WorldModel`, for `deliberation_engine.py:1025`). All three are legitimate type-hint
suppressions — recorded because a whitelist is where a genuinely dead symbol would hide next,
and these three are the only slice entries in it.

**3 · Two BLOCKING CI steps analyse this slice's source but do not execute it.**
`ci.yml:42` `python tools/consumption_sweep.py --strict` and `ci.yml:48` `python tools/ood_lint.py`
both read repo source, as does `ci.yml:51` `ruff check .`. Static analysis is contact, not
invocation: none of them constructs an engine or calls a method, so none rescues a `preserve` row.
Stated so the distinction is on the record rather than assumed.

**4 · The one test in this slice is outside the CI path.** `ci.yml:53-54` runs `pytest tests/gate -q`,
not the whole suite (`pytest.ini` sets `testpaths = tests`, but CI passes an explicit path).
`tests/test_persona_runtime.py` — the sole reference to `engines/consciousness/persona_runtime.py`
— sits in `tests/`, so it never runs in CI. The `preserve` call on that file is strengthened, not
weakened, by the dot-dir check.

`.githooks/pre-commit` is a ruff-only blocking hook (`git config core.hooksPath .githooks`);
it names nothing in this slice. `.claude/` holds only `settings.local.json` and a scheduler lock.
`.github/copilot-instructions-v4-legacy.md:541,577` show `from engines.perception.visual_cortex
import VisualCortex` in prose example blocks — documentation, and `visual_cortex` is live anyway.

**5 · Two run artefacts under `.runs/` independently corroborate this document.** Neither is an
invocation — both are outputs — but both are checkable evidence, so they are recorded:

- **`.runs/live_closure.json`** — a 170-entry runtime closure, 125 of them under `engines/`.
  It **omits** ten of my eleven non-live rows: `engines/planning/sequence_miner.py`, all six
  `engines/postgame/*`, `engines/social/cods_types.py`, `engines/social/execution_trace_miner.py`,
  `engines/social/remote_effect_learner.py`. It **includes**
  `engines/consciousness/persona_runtime.py` — the one disagreement, and it is explained by
  DEFECT B: a closure walker that follows `engines/consciousness/__init__.py:30` without asking
  whether `get_persona_manager()` is ever called will include it. My TEST-ONLY call stands.
  (`.runs/assess_py.txt` — the output of `tools/repo_assess.py`, itself the DEAD proto-instrument
  named in `CODEBASE_INVENTORY.md` item 24 — independently records `engines/social/cods_types.py
  refs=0` at line 173.)
- **`.runs/root_db_probe.log:1565-1590`** — a captured traceback showing the real cost of the
  `sequence_miner` re-export. Importing `engines.planning.sequence_abstraction` runs
  `engines/planning/__init__.py:5` → `engines/planning/sequence_miner.py:40`
  (`logger = get_engine_logger("sequence_miner")`) → `engines/engine_logger.py:78` → `:224`
  `DatabaseLogHandler()` → `:115` `SharedDatabaseLogHandler()`, and the probe's next line is
  `=== ROOT DB OPENED ===`. **The unreferenced module is not inert: it is imported on every
  `engines.planning.*` import and its module-level logger construction opens a database handler.**
  That is an argument for resolving its status, and a caution against moving it casually — the
  `__init__.py:5` line has a runtime side effect, not just a name binding.

**`.gamma_library/` (1 JSON), `.residual_bank/` (18 JSON) and `.runs/` are run/data stores, and
`.runs/arms/<hash>/` is a full swarm-arm worktree — a second checkout of this repository.** Its
hits on slice module names are copies of the same source files, not references to them. Nothing in
any of the three is configuration that selects a module by string.

---

## LEADS FROM THE BRIEF — VERDICTS

| lead | verdict |
|---|---|
| `engines/postgame/` is a closed island, 6 files, zero callers, docstring names a caller in `legacy/` | **CONFIRMED** in full (DEFECT C). Its `replay_learning.py` is additionally a pure re-export shim of a live module. |
| `engines/perception/palette_detector` has NO live counterpart | **Half wrong.** The *capability* claim stands (nothing else in the live stack represents a frame region that is instructions rather than state). The *reachability* implication does not: it is imported at `rungs/orientation.py:314` inside `PaletteDetectionRung` (`name = "palette_detection"`, registered `rungs/orientation.py:1302`, priority-ordered at `decision_rung_system.py:134,154,228,254,393,438,477`). It is LIVE and it runs early in every ladder. |
| `engines/perception/spatial_learning` has NO live counterpart | **Same correction.** Imported three times at `rungs/exploitation.py:1230,1242,1254` inside `SpatialRelationshipRung` (`name = "spatial_relationship"`, registered `:4483`, ordered `decision_rung_system.py:306`). LIVE. |
| similar orphaned discover/falsify pairs in this slice | **One found, and it is worse than a pair — it is a writer with no reader.** `engines/reasoning/deliberation_audit.py` is instantiated live at `decision_rung_system.py:636`, so the *write* side (`start_deliberation`/`add_alternative`/`record_choice`/`record_outcome`) runs; its four *read* methods — `analyze_wrong_predictions:481`, `get_alternative_success_rate:523`, `get_rung_performance:579`, `mark_better_alternative:620` — are called from **nowhere outside the file**. The top-5-alternatives table is filled every episode and never queried. Second instance, same shape: `engines/memory/near_miss_analyzer.py` writes `near_miss_patterns` but `analyze_near_miss` and `get_near_miss_report` have no external caller, and the one rung that would call it is a DEFECT-A no-op. |

---

## THE TABLE — one row per file

`dest` · `reached-by WITH THE SITE` · what it does · (preserve: capability + why it may matter)

### `engines/` — 4 files

| path | dest | reached-by (site) | what it does |
|---|---|---|---|
| `engines/__init__.py` | live | STATIC — package init runs on every `engines.X` import; `rungs/base.py:447` and `decision_rung_system.py:598` construct `EngineRegistry` | Package façade: re-exports 24 Protocols from `interfaces.py`, `EngineRegistry`/`get_registry`, and convenience classes from `cognition`, `consciousness`, `memory`, `self_model`, `social`. Does **not** import `perception`, `planning`, `reasoning`, `regulation`, `postgame`. |
| `engines/engine_logger.py` | live | STATIC — module-level import in ~46 files, e.g. `engines/social/viral_package_engine.py:30`, `engines/postgame/orchestrator.py:42` | Per-engine logger: console formatter + a DB log handler, plus `log_import_error` / `log_engine_init` / `log_silent_failure` — the hooks that make `registry.py`'s "no silent failures" claim true. |
| `engines/interfaces.py` | live | STATIC — `engines/__init__.py:39` | 25 `Protocol` definitions for every rung↔engine call. **Unenforced** (`engines/registry.py:42-45` comments out the `TYPE_CHECKING` imports) and 11 of the Protocols declare 14 methods no implementation defines — see DEFECT A. |
| `engines/registry.py` | live | STATIC — `rungs/base.py:447`, `decision_rung_system.py:598/732`, `engines/__init__.py:65` | Data-driven lazy registry: `ENGINE_CONFIGS` holds 33 `module=`/`class_name=` strings resolved by `importlib.import_module` at `:381`. This is the STRING reach mechanism for 24 files in this slice, and the reason `engines/` cannot be flattened. |

### `engines/consciousness/` — 7 files

| path | dest | reached-by (site) | what it does |
|---|---|---|---|
| `engines/consciousness/__init__.py` | live | STATIC — `engines/__init__.py:125` | Re-exports `WeavingReporter`; defines `get_i_thread`/`get_sensation_engine`/`get_persona_manager`, **all three uncalled** (DEFECT B). |
| `engines/consciousness/deliberation_engine.py` | live | STATIC — `engines/consciousness/i_thread.py:45` | Gut-instinct vs deliberation: `compute_deliberation_budget`, `capture_gut_instinct`, `conduct_deliberation`, `decide_action`; queries episodic memory, past attempts, network hypotheses, available primitives. |
| `engines/consciousness/i_thread.py` | live | STRING — `ENGINE_CONFIGS['i_thread']` `engines/registry.py:217`; also STATIC `cognitive_game_player.py:41`, `agent_operating_mode_system.py:40` | The Stream-A/Stream-B weight weaver: `detect_conflict`, `synthesize`, `learn_from_outcome`, personality label, surprise. Delegates all four deliberation methods to `DeliberationEngine` — but constructs a **fresh `DeliberationEngine(self.db)` on every call** at `:950`, `:974`, `:999`. |
| `engines/consciousness/i_thread_types.py` | live | STATIC — `i_thread.py:51`, `deliberation_engine.py:36` | 14 dataclasses/enums for the consciousness system: `DeathType`, `DeathPersona`, `StreamProposal`, `ConflictResult`, `SynthesisResult`, `EpisodicMemory`, `AgentNarrative`, `MortalityState`, `ReasoningLog`, `IThreadState`. |
| `engines/consciousness/persona_runtime.py` | **preserve** | TEST-ONLY — `tests/test_persona_runtime.py:23`, and **that test is not run by CI**: `.github/workflows/ci.yml:54` invokes `pytest tests/gate -q`, and this test lives in `tests/`, not `tests/gate/`. Its only production edge is `engines/consciousness/__init__.py:30`, inside `get_persona_manager()`, which nothing calls (DEFECT B) | `PersonaManager`: spawn/bind temporary personas to theories, generate proposals, allocate attention, track per-persona reliability, hindsight credit, lifecycle enforcement. **Capability:** a proposal-attribution economy — *which sub-agent proposed this, and how often is that one right* — scored on hindsight. The live stack scores atoms, arms and agents; it has no per-persona reliability ledger, and no mechanism that prunes a persona for being consistently wrong. 58 KB, and `manual_tools/analysis/theory_alignment_checker.py:427` lists it as a theory-required component. |
| `engines/consciousness/sensation_engine.py` | live | STRING — `engines/registry.py:211`; STATIC `horizontal_transfer_engine.py:35`, `evolutionary_engine.py:27` | Emotional/sensation layer over actions 1-7: perceive→recall sensation→bias action→learn; tetrahedral sensation, mortality sensations, semantic impressions. |
| `engines/consciousness/weaving_reporter.py` | live | STATIC — `engines/consciousness/__init__.py:10` → `engines/__init__.py:125` | Per-decision self-reflection report; delegates to `IThread`, adds 1-in-10 local sampling with always-store exceptions for conflicts and level ends. |

### `engines/memory/` — 5 files

| path | dest | reached-by (site) | what it does |
|---|---|---|---|
| `engines/memory/__init__.py` | live | STATIC — `engines/__init__.py:128` | Re-exports `EpisodicMemorySystem`, `GenerationClock` helpers, `TemporalIntegrator`; `get_near_miss_analyzer()` uncalled (DEFECT B). |
| `engines/memory/episodic_memory.py` | live | STRING — `engines/registry.py:172`; STATIC `engines/memory/__init__.py:13`; also `cognitive_game_player.py:55` | Agent autobiographical memory: personal-history queries, wA-vs-wB stream comparison, pre-game autobiography synthesis, runtime narrative, wA/wB persistence at game end. |
| `engines/memory/generation_clock.py` | live | STATIC — `engines/self_model/embedding_matcher.py:35`, `engines/memory/__init__.py:14` | Hardware-agnostic time: `composite_time = generation + action/max_actions`; exponential generation decay, access boost, relevance score, per-knowledge-type half-lives. |
| `engines/memory/near_miss_analyzer.py` | live (constructed, output discarded) | STRING — `engines/registry.py:178`, triggered by `rungs/exploitation.py:829` | Analyses high-score losses: successful vs failed actions, missing elements, critical mistakes, improvement suggestions, actions-to-win estimate, near-miss pattern extraction. **Its consumer rung is a DEFECT-A no-op** (`get_insights` does not exist), and `analyze_near_miss`/`get_near_miss_report` have no external caller. |
| `engines/memory/temporal_integrator.py` | live | LAZY — `decision_rung_system.py:609` | Multi-scale exponential integration of outcomes (immediate 0.1 gen / tactical 1 / strategic 10 / historical ∞); exploration appetite, rung modulation, comprehension confidence from prediction error. |

### `engines/perception/` — 15 files

| path | dest | reached-by (site) | what it does |
|---|---|---|---|
| `engines/perception/__init__.py` | live | STATIC — package init runs on `cognitive_loop.py:50` (`engines.perception.perceiver`) | Re-exports `PlayerLocalizer`, `PropertyExtractor`, `TerminalPatternDetector`, `VisualAnalyzer`, `VisualReasoningEngine`; six `get_*()` accessors, **all uncalled** (DEFECT B). |
| `engines/perception/event_detector.py` | live | LAZY — `outcome_processor.py:287` (invoked at `:369`); also `rungs/hypothesis.py:312`, `rungs/orientation.py:656` | Discrete event vocabulary over tracked objects — MOVEMENT / COLLISION / FUSION / lifecycle / transformation — plus causal attribution of an event to an action and whole-frame process classification. |
| `engines/perception/object_detector.py` | live | LAZY — `engines/perception/perceiver.py:44` | Flood-fill object detection in a frame, persistence to DB, and its own frame-to-frame track builder. |
| `engines/perception/object_tracker.py` | live | STATIC — `engines/perception/event_detector.py:16`; LAZY `rungs/hypothesis.py:322` | Object identity across frames via `scipy.ndimage.label` + Hungarian matching; shape signatures, movement summary, alignment check. |
| `engines/perception/palette_detector.py` | live | LAZY — `rungs/orientation.py:314` inside `PaletteDetectionRung` (registered `rungs/orientation.py:1302`, ordered `decision_rung_system.py:134`) | Two-stage: extract objects (hollow/rectangular/isolated classification), then detect palette/legend blocks and their **mapping direction** (inside-out vs top-to-bottom, wide→vertical, tall→horizontal). |
| `engines/perception/perceiver.py` | live | STATIC — `cognitive_loop.py:50` | Multimodal perception integration: spatial, object, goal, temporal and causal channels integrated into one `PerceptualField` plus a narrative. |
| `engines/perception/perceptual_field.py` | live | STATIC — `cognitive_loop.py:51`, `engines/perception/perceiver.py:31` | The perception output dataclasses: `CellDiff`, `ActionEffect`, `TilePosition`, `KnownEffect`, `PerceptualField`. |
| `engines/perception/player_localizer.py` | live | STATIC — `evolution_runner.py:87` | Unsupervised "which object am I": act in a direction, diff frames, correlate change direction with action direction; confidence + persistence fallback. |
| `engines/perception/property_extractor.py` | live | STATIC — `evolution_runner.py:88`, `game_player.py:30` | Symbolic properties of the player sprite: dominant colour, shape signature, coarse orientation; handles both symbolic grids and RGB. |
| `engines/perception/sparse_grid.py` | live | LAZY — `rungs/orientation.py:517` inside `SparseGridRung` (`name = "sparse_grid"`, `rungs/orientation.py:468`) | Sparse dict frame encoding with `diff`, `structural_hash`, `color_invariant_hash`, `find_pattern`, `find_repeated_structures`, `extract_connected_components`, `normalize_to_origin`, `apply_color_mapping`. |
| `engines/perception/spatial_learning.py` | live | LAZY — `rungs/exploitation.py:1230`, `:1242`, `:1254` inside `SpatialRelationshipRung` (registered `:4483`) | `SpatialEffectLearner` (which clicked position affects which other positions, with confidence), `MultiObjectGoalTracker` (known winning grid configurations), and a second `PropertyExtractor` (see PAIRS #1). |
| `engines/perception/terminal_pattern_detector.py` | live | STRING — `engines/registry.py:152` | Death-foresight: frame-hash terminal patterns, relative-threat patterns, false-positive recording, graduated action weights, position-death summary. Façade over `terminal/` (delegates at `:845`, `:856`, `:863`, …). One DEFECT-A hole: `detect_terminal_approach` is guarded at `rungs/filter_rungs.py:335` and does not exist. |
| `engines/perception/visual_analyzer.py` | live | STRING — `engines/registry.py:147` | ACTION6 target finder: colour anomalies, colour clusters, frame changes, grid-exploration targets, adaptive radius, oscillation detection, clicked-coordinate memory. One DEFECT-A hole: `grid_walking_index` (`rungs/orientation.py:798`). |
| `engines/perception/visual_cortex.py` | live | LAZY — `context_builder.py:44`; also `engines/perception/perceiver.py:37` | Full scene understanding: grid structure, panel detection + role assignment, tiling by periodicity, flood-fill objects, symmetry, transformation hypotheses (colour mapping / tile rearrangement / pattern completion), narrative, PNG render. 75 KB, the largest file in the slice. |
| `engines/perception/visual_reasoning.py` | live | STATIC — `engines/cognition/rule_induction.py:35` | Semantic features of an ARC grid: symmetry, repeating patterns, colour distribution, shapes, spatial relations, likely transformations, complexity. |

### `engines/perception/terminal/` — 4 files (all live, all statically imported by the façade)

| path | dest | reached-by (site) | what it does |
|---|---|---|---|
| `engines/perception/terminal/__init__.py` | live | STATIC — package init on `engines/perception/terminal_pattern_detector.py:46` | Re-exports the three trackers; documents the split from `terminal_pattern_detector.py`. |
| `engines/perception/terminal/dangerous_objects.py` | live | STATIC — `terminal_pattern_detector.py:46` (held as `self._dangerous_objects`, `:82`) | Colour/pattern danger: record a dangerous object, propagate danger to similar objects, check, find a safe direction away from a colour, action-triggered danger. |
| `engines/perception/terminal/death_zones.py` | live | STATIC — `terminal_pattern_detector.py:49` (`self._death_zones`, `:81`) | Spatial danger regions per level: record/check zones, safe-direction search, survival credit, zone challenging, age decay. |
| `engines/perception/terminal/game_over_theory.py` | live | STATIC — `terminal_pattern_detector.py:50` (`self._theory_generator`, `:83`) | Human-readable hypotheses about why game-overs happened, from death zones and dangerous objects. |

### `engines/planning/` — 5 files

| path | dest | reached-by (site) | what it does |
|---|---|---|---|
| `engines/planning/__init__.py` | live | STATIC — package init on the registry's `importlib` load of `engines.planning.sequence_abstraction` (`engines/registry.py:260`) | Re-exports `SubgoalPlanner`, `SequenceAbstraction`, **`SequenceMiner`, `MiningResult`**; `get_replay_learning_engine()` uncalled (DEFECT B). Line 5 is the *only* thing in the tree that reaches `sequence_miner`. |
| `engines/planning/replay_learning_engine.py` | live (constructed, output discarded) | STRING — `engines/registry.py:265` | Learn *why* a sequence works: predict before each replay action, compare to outcome, classify frame change, induce rules, flag wasted actions for the optimiser. **DEFECT A**: `rungs/exploitation.py:3894` guards `get_current_prediction`, which the class does not define. |
| `engines/planning/sequence_abstraction.py` | live | STRING — `engines/registry.py:260`; LAZY `engines/consciousness/i_thread.py:67,92`, `deliberation_engine.py:105`, `engines/self_model/few_shot_relations.py:46` | Concept matching over sequences: pattern extraction, LCS similarity, abstract templates with variant slots, relational-pattern cache, contrastive hints, frontier templates, primitive requirements. |
| `engines/planning/sequence_miner.py` | **preserve** | STATIC — `engines/planning/__init__.py:5` **and nothing else**; `SequenceMiner(` appears zero times in production and in tests (re-confirmed this pass; `WIRING_REGISTRY.md:218-222` records it as SEVERED). Its only dot-dir occurrence is `.github/workflows/ci.yml:57`, a **comment** explaining why the vulture step is advisory — a mention, not an invocation | Retroactive mining of banked winning sequences: `compute_level_breakpoints` / `backfill_level_breakpoints`, interaction-trigger extraction from frame diffs, action-effectiveness and level-outcome backfill. **Capability:** the only code in the tree that can segment a stored sequence *by the level each action belonged to* — "these actions solved THIS board" as distinct from "these actions get me back to where I was". The `level_breakpoints` schema column exists and has never been written. This is the canonical near-deletion; it is re-listed unchanged. |
| `engines/planning/subgoal_planner.py` | live (constructed, guard fails) | STRING — `engines/registry.py:253` | Decomposes a board into objectives → subgoals → per-subgoal action priorities; records execution and learns subgoal patterns. **DEFECT A**: `rungs/exploitation.py:1494` guards `get_current_subgoal`, absent. |

### `engines/postgame/` — 6 files · the closed island

| path | dest | reached-by (site) | what it does · capability |
|---|---|---|---|
| `engines/postgame/__init__.py` | **preserve** | NONE — nothing in the tree imports `engines.postgame`; the only external mention is `README.md:347`, a doc inventory row | Package façade + the contract, stated at `:28`: *"Single entry point for `game_loop.py`"*, and `game_loop.py` is in `legacy/`. **Capability:** kept with the package so the package remains importable if preserved; it is the only place the four-stage post-game contract is written down. |
| `engines/postgame/fitness_calculator.py` | **preserve** | NONE (only `engines/postgame/orchestrator.py:46` and `__init__.py:50`, both inside the island) | Configurable-weight evolutionary fitness from ARC-native rewards: derived metrics, agent consistency, action effectiveness, exploration bonus, variance, population summary, and a `validate_reward_calculation` self-check including coordinate validation. **Capability:** a *declared, weighted, auditable* fitness function with a validator. The live path scores in `evolutionary_engine`/`outcome_processor` with weights spread across call sites; nothing else in the tree can answer "what exactly was this generation scored on" from one object, and nothing else validates its own reward arithmetic. Bears on mandate item 4. |
| `engines/postgame/lessons_extractor.py` | **preserve** | NONE (island-internal only) | Extracts transferable lessons from one game: success and failure patterns, induced rules, optimisation insights, score increases/decreases/plateaus, repeated and redundant patterns, most-efficient actions, consistency. **Capability:** *plateau detection inside a single episode* (`_find_plateaus`) and *redundancy detection* (`_find_redundant_patterns`) — neither exists in the live stack, which detects flatness only across generations, by hand, in `record/log/PORT_LOG.md`. |
| `engines/postgame/lessons_learned.py` | **preserve** | NONE (island-internal only; every automated hit elsewhere is the `lessons_learned` **DB table** name, e.g. `context_builder.py:154`) | Two engines. `LessonsLearnedEngine`: network-level lesson store with schema migration, score-trajectory and stuck-period analysis, lesson hashing/dedup, "did this lesson help" feedback. `DeathCauseHypothesis`: records each death, maintains and *validates* hypotheses about what kills agents, records survivals as counter-evidence, produces threat-object lists. **Capability:** a falsifiable death-cause hypothesis with both positive and negative evidence. The live `frontier`/`death_zones` path books *where* deaths happen; nothing books *what kind of thing* kills, nor retracts the belief on survival. |
| `engines/postgame/orchestrator.py` | **preserve** | NONE — `PostGameProcessor` and `ARCRLVRFramework` appear zero times outside the island | The single post-game entry point: fitness → lessons → replay summary → winning-sequence storage → agent-stat and wA/wB persistence, in a fixed order, returning one `PostGameResult`. Plus a deprecated `ARCRLVRFramework` back-compat shim. **Capability:** *ordering*. The live build performs several of these steps in scattered places with no defined sequence and no single result object; this is the only written-down statement of what must happen at game end and in what order. |
| `engines/postgame/replay_learning.py` | **considered_dead** | NONE | 44 lines, no logic: re-exports `ReplayLearningEngine`/`ReplayLearningContext`/`ReplayPrediction` from the live `engines/planning/replay_learning_engine.py` and aliases `ReplayLearner = ReplayLearningEngine`. Adds a second import path for classes that already have one, and would break if the island moved without `engines/planning`. Nothing is lost by retiring it; **if the GM preserves the package as a unit, this file should still be dropped rather than carried.** |

### `engines/reasoning/` — 5 files

| path | dest | reached-by (site) | what it does |
|---|---|---|---|
| `engines/reasoning/__init__.py` | live | STATIC — package init on `game_player.py:37` / `evolution_runner.py:177` / `decision_rung_system.py:627` | Re-exports `ScientificMethodEngine`, `SymbolicReasoningEngine`, `WorldModel`, `WorldState`. |
| `engines/reasoning/deliberation_audit.py` | live (**writer only — no reader**) | LAZY — `decision_rung_system.py:627`, instantiated `:636` | Records the top-5 alternative interpretations per decision, which was chosen and why, and links the outcome back. Write path runs every episode; the four analysis methods (`analyze_wrong_predictions:481`, `get_alternative_success_rate:523`, `get_rung_performance:579`, `mark_better_alternative:620`) are called from nowhere outside this file. |
| `engines/reasoning/graph_evolution.py` | live | STATIC-in-`try` — `engines/cognition/cognitive_router.py:65` and `:73` | Valence-weighted edge crystallisation: THREAT paths need 1.5× traversals, CONFUSION 2.0×, high-success BOREDOM 0.7×; plus `FeelTrajectoryStore` and per-game emotional-trajectory anomaly detection. |
| `engines/reasoning/scientific_method_engine.py` | live | STRING — `engines/registry.py:275`; STATIC `engines/reasoning/__init__.py:14`, `evolution_runner.py:170` | Three engines in 90 KB: `ScientificMethodEngine` (observation → theory → designed experiment → belief update → generalisation), `QuestioningEngineWithTeeth` (questions that *block* actions), `GamesAsTeachersEngine` (lesson extraction + transfer testing + coverage ratio). Two DEFECT-A holes: `get_theory_stage` (`rungs/hypothesis.py:47`) and `questioning_engine` (`rungs/orientation.py:153`). |
| `engines/reasoning/symbolic_reasoning_engine.py` | live | STATIC — `engines/reasoning/__init__.py:15`, `game_player.py:37`, `evolution_runner.py:177` | 97 KB, the largest module: object/world-state model, compositional goals with AND/OR, connected-component scene parser, agent identification by action-movement correlation, belief nodes with decay and competing-belief spawning, surprise, physics/trigger rules, BFS/A*/MCTS planner, plan cache, and a gameplay integration layer. |

### `engines/regulation/` — 6 files

| path | dest | reached-by (site) | what it does |
|---|---|---|---|
| `engines/regulation/__init__.py` | live | STATIC — package init on the registry `importlib` load of `engines.regulation.frustration_detector` (`engines/registry.py:228`) | Re-exports `FrustrationDetector`, `ImaginationBudgetManager`, `compute_mental_modeling_budget`; two `get_*()` accessors, both uncalled (DEFECT B). |
| `engines/regulation/frustration_detector.py` | live | STRING — `engines/registry.py:227`, consumed at `rungs/orientation.py:266` (`is_frustrated` — this one **does** exist) | Per-agent stuck/0-progress detection with action-diversity scoring, a **dynamic quorum threshold** across agents, a network desperation signal, and resolution application. |
| `engines/regulation/imagination_budget.py` | live (constructed, guard fails) | STRING — `engines/registry.py:239` | `compute_mental_modeling_budget` (a free function nothing calls) plus `ImaginationBudgetManager`: performance-adjusted budget, persona allowance, `can_speculate`, `can_spawn_investigator`, synthesis depth. **DEFECT A**: `rungs/orientation.py:1158` guards `calculate_budget`; the class has no such method, so `ImaginationBudgetRung` is a total no-op. |
| `engines/regulation/network_exploration_tracker.py` | live (constructed, guard fails) | STRING — `engines/registry.py:243` | Collective spatial knowledge: what the *network* has explored per level, region mapping, action coverage, unexplored-region priority, per-session persistence. **DEFECT A**: `rungs/orientation.py:1194` guards `get_exploration_stats`; absent. `NetworkExplorationStatsRung` is a total no-op. |
| `engines/regulation/regulatory_signal_engine.py` | live (constructed, guard fails) | STRING — `engines/registry.py:233` | Distributed homeostasis by signals: per-agent and system signal emission, role-need signals, response processing, parameter adjustment with recorded regulation events, expiry cleanup, and `calculate_control_error` (intended vs actual population ratios). **DEFECT A**: `rungs/orientation.py:749` guards `get_active_signals`; absent. |
| `engines/regulation/trigger_controller.py` | live | STATIC — `engines/regulation/regulatory_signal_engine.py:33` | Anti-resonance protection for metric triggers: consecutive-fire tracking, damped magnitude, required corroboration, fire-rate history. |

### `engines/self_model/` — 16 files (all live)

Note: `engines/registry.py` loads four of these by `module='engines.self_model'` + `class_name`
(`:81, :87, :93, :99`), so **`engines/self_model/__init__.py`'s re-exports are load-bearing** —
this is one of the reasons `engines/` cannot be flattened.

| path | dest | reached-by (site) | what it does |
|---|---|---|---|
| `engines/self_model/__init__.py` | live | STATIC — `engines/__init__.py:131`; also the resolution target of `ENGINE_CONFIGS` `module='engines.self_model'` at `engines/registry.py:81,87,93,99` | Re-exports 24 names from the 15 sibling modules. Docstring-first (does **not** have DEFECT D). |
| `engines/self_model/action6_behavior.py` | live | STRING — `engines/registry.py:98` via the package re-export at `__init__.py:30`; consumed `rungs/exploration.py:271,306,339` | All ACTION6 learning: pseudo-buttons, object selection and control verification, shape generalisation ("horizontal bars are selectable", not "colour 9"), availability-change tracking as a selectability signal. |
| `engines/self_model/belief_system.py` | live (one guard fails) | STRING — `engines/registry.py:138` | Beliefs with explicit dependencies, cascade invalidation with audit trail, confidence propagation, belief chains. **DEFECT A**: `rungs/hypothesis.py:1046` guards `get_active_beliefs`; the class exposes `get_beliefs`, not that name. |
| `engines/self_model/click_behavior.py` | live | STRING — `engines/registry.py:133`; LAZY `outcome_processor.py:298`; consumed `rungs/exploitation.py:1632-1944` (four sites, all methods present) | Classifies clicks as toggle / collect / select / trigger from evidence, maintains per-object click profiles, predicts behaviour, exposes collectible / dangerous / trigger object sets. |
| `engines/self_model/cognitive_core.py` | live | STRING — `engines/registry.py:74` (`class_name='CognitiveCore'`) | The canonical `SelfModelInterface` implementation, replacing the ~10,000-line `AgentSelfModel`: lazily composes `EmbeddingMatcher`, `FewShotRelations`, `NetworkSharingEngine`, `ControlTracker` (`:68, :78, :88, :98`). |
| `engines/self_model/completion_predictor.py` | live by import, **called only from `legacy/`** | STATIC — `engines/self_model/__init__.py:34` → `engines/__init__.py:133`; the only instantiation in the tree is `legacy/agent_self_model.py:27` | Given key state + known tool effects, computes minimum tool uses to match key to lock, plans tool visit order from agent position, estimates total actions to completion. A re-export blind spot of the `sequence_miner` shape — import-reachable, symbol-unreferenced outside `legacy/`. Flagged, not moved (it is inside a live package). |
| `engines/self_model/control_tracker.py` | live | STRING — `engines/registry.py:104`; LAZY `engines/self_model/cognitive_core.py:98`; consumed `rungs/orientation.py:1083` | "I am this object": records action→movement observations, scores them to a confidence tier, verifies continued control, persists a control map. |
| `engines/self_model/discovery_engine.py` | live | STRING — `engines/registry.py:109`; consumed `rungs/exploitation.py:87` | Systematic object-discovery state machine: identify targets, emit the next probing action, process movement vs click results, record discoveries, deterministic order for reproducibility. |
| `engines/self_model/embedding_matcher.py` | live | STRING — `engines/registry.py:80`; LAZY `cognitive_core.py:68`; consumed `rungs/exploitation.py:3530` | Frame-embedding nearest-neighbour action suggestion with generation-based recency (30-generation half-life) and an access-frequency boost. |
| `engines/self_model/few_shot_relations.py` | live | STRING — `engines/registry.py:86`; LAZY `cognitive_core.py:78`; consumed `rungs/exploitation.py:3586` | Exposes few-shot invariants/variants out of `SequenceAbstraction` for fast control bootstrapping. 135 lines, the smallest non-`__init__` file in the slice. |
| `engines/self_model/grid_analysis.py` | live (guard fails) | STRING — `engines/registry.py:114` | Frame differencing, collision detection, rotation detection, region classification, autonomous-object finding, object shape, plus `quick_diff`/`frames_identical`. **DEFECT A**: `rungs/orientation.py:131` guards `analyze_grid_structure`; absent (the class has `get_diff`, `classify_regions`, …). |
| `engines/self_model/network_sharing.py` | live | STRING — `engines/registry.py:92`; LAZY `cognitive_core.py:88`; consumed `rungs/exploitation.py:3657` | The six-tier hypothesis colony for self-model knowledge: share → validate → use → select → synthesise composites, with reliability updates. |
| `engines/self_model/symbolic_tracker.py` | live (one guard fails) | STRING — `engines/registry.py:287`; consumed `rungs/hypothesis.py:1223,1233` | Key/lock symbolic state across frames: shape signature, match score, transformation needed, tool-effect detection, match progress, network persistence. **DEFECT A**: `rungs/hypothesis.py:1238` guards `suggest_transformation`; the class defines `get_transformation_needed`. |
| `engines/self_model/trigger_sequences.py` | live (two guards fail) | STRING — `engines/registry.py:118` | Trigger chains (X causes Y causes Z), proven action sequences per level, conditional triggers, reliability. **DEFECT A ×2**: `rungs/exploitation.py:3435` guards `get_proven_sequence` (class has `get_proven_sequences`, plural) and `:3456` guards `predict_trigger_effect` (absent). A one-character miss and a missing method. |
| `engines/self_model/universal_patterns.py` | live | LAZY — `evolution_runner.py:163` | Cross-game transferable patterns with scope escalation (game → family → universal), evidence-gated confidence, transferable-knowledge packaging, outcome prediction. |
| `engines/self_model/valence_goals.py` | live (two guards fail) | STRING — `engines/registry.py:123` | Good/bad valence associations for objects, goal inference from how a level ended, safe/danger region classification, reward prediction. **DEFECT A ×2**: `rungs/exploitation.py:3834` guards `get_inferred_goal` (class has `get_goal`) and `:3862` guards `get_negative_valence_objects` (class has `get_all_valences`). |

### `engines/social/` — 12 files

| path | dest | reached-by (site) | what it does · capability |
|---|---|---|---|
| `engines/social/__init__.py` | live | STATIC — `engines/__init__.py:141` | Re-exports `AgentHypothesisSystem`, `AgentNetworkContributor`; six `get_*()` accessors, **all uncalled** (DEFECT B), including a deprecated `get_cods_engine()` that emits a warning nobody can trigger. |
| `engines/social/cods_types.py` | **preserve** | **NONE** — zero references tree-wide; the only mentions are `record/findings/FORGOTTEN_CAPABILITIES.md:63` (which flags it as *"NOT A CANDIDATE, LISTED FOR PROTECTION"*) and `record/findings/REPO_AUDIT_2026-08-20.md:60` | `BayesianHypothesis` (prior/posterior with `is_confirmed`/`is_refuted`/`sample_size`), `OperatorResult`, `CODSGameContext`. **Capability:** a hypothesis type carrying an explicit Bayesian posterior and an explicit *refuted* state with a sample size. The live `pricing.Hypothesis` is iced and the live ledger records falsification without a posterior or an n. Already under a protection note — re-confirmed unreferenced this pass, not re-argued. |
| `engines/social/execution_trace_miner.py` | **preserve** | **NONE** — zero references; named only in `record/findings/REFACTOR_PLAN_AND_READ.md:27` and `record/retired/progress.md:1208` | Records every primitive call, aggregates recent sequences, mines frequent and success-correlated sub-sequences with a confidence score, and tracks which mined patterns have already been composed (`mark_composed` / `get_uncomposed_patterns`). **Capability:** mining at the *execution-trace* grain — what the agent actually did, in order — rather than at the frame or atom grain, plus a composed/uncomposed frontier so the same pattern is not re-proposed. Nothing in the live composer path reads its own call log. |
| `engines/social/hypothesis_system.py` | live | STRING — `engines/registry.py:281`; STATIC `engines/cognition/__init__.py:17`; consumed `rungs/hypothesis.py:1106,1143` | Agent-*created* hypotheses (gated on FORMAL_OPERATIONAL stage): create, test, record results, primitive-aware generation. Also mortality: legacy score, dying thoughts, memento mori, mortality reflection. |
| `engines/social/network_contributor.py` | live by import, **called only from `legacy/`** | STATIC — `engines/social/__init__.py:16` → `engines/__init__.py:141`; the only instantiation is `legacy/agent_self_model.py:46` | Viral exchange without a coordinator: broadcast a failed attempt, share a success insight, query peer insights and peer failures, self-assess against the network baseline, reject an insight. Second re-export blind spot of the `sequence_miner` shape in this slice. Flagged, not moved. |
| `engines/social/package_compressor.py` | live | LAZY — `result_recorder.py:480`; also `safe_cleanup.py:1069` and `:1098` | LCS similarity over a cluster of successful sequences → one template with variable holes; compresses viral packages and winning sequences. *(Correction: `CODEBASE_INVENTORY.md:586` gives the reach as `engines/social/__init__.py:50`, a dead accessor; the real, live site is `result_recorder.py:480`.)* |
| `engines/social/pariah_manager.py` | live | STATIC — `engines/social/viral_package_engine.py:28` (held as `self._pariah_manager`, `:53`) | Failure patterns as negative selection: create from failure, spread awareness, action penalties (role-adjusted), network-paralysis detection, obsolescence checking, and toxicity decay as an explicit formula. |
| `engines/social/prestige_engine.py` | live | STATIC — `evolutionary_engine.py:23` | Social capital separate from economic capital: prestige affects breeding priority / survival protection / bonus slots and **never** action budgets — enforced by `assert_no_budget_effect` raising `PrestigeBudgetViolationError`. |
| `engines/social/primitive_suggester.py` | live | STRING — `engines/registry.py:188`; consumed `rungs/exploitation.py:3778` | The CODS replacement: apply seed primitives (symmetry, motion, colour clusters, edges, novelty, goal) to a frame, map outputs to action candidates, learn which primitive→action mappings work. |
| `engines/social/remote_effect_learner.py` | **preserve** | **NONE** — zero references; named only in `record/findings/REFACTOR_PLAN_AND_READ.md:27` and `record/retired/progress.md:1207` | Observes an action, finds *all* frame changes regardless of distance from the acted-on cell, characterises the effect, forms distance-agnostic causal hypotheses, **validates them against later observations**, and shares/queries them on the network. **Capability:** unbounded action-at-a-distance with a validation step. The live `enables.act_offset` is a bounded single offset; there is no live representation for "clicking here changes something across the board", and no live remote-effect hypothesis that can be refuted. |
| `engines/social/resonance_detector.py` | live | STRING — `engines/registry.py:201`; STATIC `evolution_runner.py:142`; LAZY `i_thread.py:84`, `deliberation_engine.py:96`, `regulatory_signal_engine.py:282`; consumed `rungs/hypothesis.py:504` | Patterns that recur across *different agent roles*: belief hashing, theory/control/strategy classification, compressed-template scanning, visual resonance, combined score, role-based query gate. |
| `engines/social/viral_package_engine.py` | live | STRING — `engines/registry.py:195`; STATIC `evolution_runner.py:93`; consumed `rungs/filter_rungs.py:281,288,730` | Positive selection: build viral packages from sequences or operators, infect agents, spread, track retrieval and improvement, package action weights, obsolescence, emotional-compatibility matching. Delegates all eight pariah methods to `PariahManager`. One DEFECT-A hole: `get_pariahs` (`engines/interfaces.py:334`) exists on neither class. |

---

## PAIRS AND DUPLICATES

**1 · A genuine name collision inside one package — `PropertyExtractor` ×2.**
`engines/perception/property_extractor.py:22` (player-sprite properties: dominant colour, shape
signature, orientation) and `engines/perception/spatial_learning.py:378` (grid-level properties:
`detect_position_changes`, `extract_grid_state`, `pixel_to_grid`). Two unrelated classes, same
name, same package. `engines/perception/__init__.py:5` re-exports the first; `rungs/exploitation.py:1254`
imports the second by its module path. `from engines.perception import PropertyExtractor` and
`from engines.perception.spatial_learning import PropertyExtractor` return different classes.
This is the only outright hazard in the list.

**2 · Six connected-component / flood-fill implementations.**
`engines/perception/object_detector.py:92` · `engines/perception/visual_cortex.py:1302` ·
`engines/perception/palette_detector.py:241` (+ a `:294` scipy-free fallback with its own inner
`flood_fill` at `:305`) · `engines/perception/sparse_grid.py:557` ·
`engines/perception/perceiver.py:785` · `engines/reasoning/symbolic_reasoning_engine.py:341`.
A seventh inner one at `engines/perception/visual_reasoning.py:239` and an eighth at
`engines/self_model/action6_behavior.py:647`. All in this slice; none share code.

**3 · Seven frame-diff implementations.**
`engines/self_model/grid_analysis.py:185` (`get_diff`, the typed one) ·
`engines/perception/sparse_grid.py:717` (`sparse_diff`) ·
`engines/perception/perceiver.py:759` · `engines/perception/player_localizer.py:182` ·
`engines/perception/visual_analyzer.py:735` · `engines/planning/replay_learning_engine.py:627` ·
`engines/social/remote_effect_learner.py:165` · `engines/perception/spatial_learning.py:517` ·
`engines/reasoning/scientific_method_engine.py:1054`. Nine, counting all of them.

**4 · Four shape-signature implementations.**
`engines/self_model/action6_behavior.py:535` · `engines/self_model/symbolic_tracker.py:157` ·
`engines/perception/object_tracker.py:166` · `engines/perception/property_extractor.py:150`.
`action6_behavior`'s is the only one documented as generalising ("horizontal bars are
selectable, not colour 9"); the other three are private and mutually incompatible.

**5 · Two object-tracking-across-frames implementations, one package apart.**
`engines/perception/object_detector.py` (`track_objects_across_frames` / `_build_track` /
`_find_matching_object`, greedy) vs `engines/perception/object_tracker.py` (`track_objects` /
`_match_objects`, scipy label + Hungarian). The second is the one `event_detector.py:16`
depends on; the first is reached separately through `perceiver.py:44`. Both run in the same
episode by different paths.

**6 · Two LCS implementations.**
`engines/social/package_compressor.py:35` (`_lcs_length`, module-level) and
`engines/planning/sequence_abstraction.py:434` (`SequenceAbstraction._lcs`, a method).
`sequence_abstraction.py:23` already names ``engines.social.package_compressor.build_template_from_cluster``
in its own docstring, so the dependency is acknowledged and then not taken.

**7 · Three lesson extractors, two of them in the dead island.**
`engines/postgame/lessons_extractor.py::LessonsExtractor` and
`engines/postgame/lessons_learned.py::LessonsLearnedEngine` both extract lessons from a finished
game and both write a `lessons_learned`-shaped table; the live third is
`engines/reasoning/scientific_method_engine.py::GamesAsTeachersEngine.extract_lesson`. If the
island is preserved, the two postgame ones should be reconciled with each other first — they are
duplicates *within* the package, not just against the live path.

**8 · One re-export shim.** `engines/postgame/replay_learning.py` → `engines/planning/replay_learning_engine.py`.
Declared and honest (`"Rule 3: No orphaned code (re-export, not duplicate)"`), but it is a second
import path to live classes from a dead package. Marked `considered_dead` above.

**NOT duplicates — verified delegation façades, recorded so nobody re-litigates them:**
`viral_package_engine` → `pariah_manager` (eight `*args, **kwargs` pass-throughs, `:69-99`) ·
`terminal_pattern_detector` → `terminal/{death_zones,dangerous_objects,game_over_theory}`
(`:81-83`, delegating from `:839` onward) · `i_thread` → `deliberation_engine`
(`:937-1010`) · `cognitive_core` → `{embedding_matcher, few_shot_relations, network_sharing,
control_tracker}` (`:68-98`). One efficiency note on the third: `IThread` builds a **new**
`DeliberationEngine(self.db)` at `:950`, `:974` and `:999` — three constructions per decision
where one cached instance would do.

---

## CAPABILITY NOT IN THE LIVE BUILD

The GM's category. Split into two tiers, because they need different decisions.

### Tier 1 — capability that is *unreached*: `preserve` rows, 10 files

| # | path | the capability | why it may matter |
|---|---|---|---|
| 1 | `engines/planning/sequence_miner.py` | segmenting a banked winning sequence **by the level each action belonged to** (`compute_level_breakpoints`, `backfill_level_breakpoints`) | The distinction "these actions solved THIS board" vs "these actions return me to where I was" is expressible nowhere else in the tree. The `level_breakpoints` schema column exists and has never been written. Re-confirmed unchanged. |
| 2 | `engines/postgame/orchestrator.py` | a **defined order** for game-end processing, returning one result object | The live build does several of these steps in scattered places with no stated sequence. This is the only written contract for what must happen at game end. Mandate item 4. |
| 3 | `engines/postgame/fitness_calculator.py` | a weighted, configurable fitness function **with a self-validator** (`validate_reward_calculation`, coordinate validation) | Nothing live can answer "what exactly was this generation scored on" from one object, and nothing live checks its own reward arithmetic. |
| 4 | `engines/postgame/lessons_extractor.py` | **within-episode plateau detection** (`_find_plateaus`) and **redundancy detection** (`_find_redundant_patterns`) | The build detects flatness only across generations, by hand, in prose. Mandate items 3 and 5, at a finer grain than `lab/trend_tracker`. |
| 5 | `engines/postgame/lessons_learned.py` | `DeathCauseHypothesis`: a falsifiable hypothesis about **what kind of thing kills**, updated by deaths *and retracted by survivals* | The live `frontier`/`death_zones` path books *where* deaths happen. Nothing books the *kind* of killer, and nothing withdraws the belief on evidence of survival. |
| 6 | `engines/postgame/__init__.py` | the package marker and the only place the four-stage contract is stated | Carried with the package; not independently valuable. |
| 7 | `engines/consciousness/persona_runtime.py` | per-persona **reliability accounting with hindsight credit** and lifecycle pruning | The economy scores atoms, arms and agents. It has no ledger of *which internal proposer* was right, and no mechanism that retires one for being consistently wrong. 58 KB; named as theory-required at `manual_tools/analysis/theory_alignment_checker.py:427`. |
| 8 | `engines/social/remote_effect_learner.py` | **unbounded** action-at-a-distance, with hypothesis validation and network sharing | `enables.act_offset` is a bounded single offset. There is no live representation for "clicking here changes something across the board", and no live remote-effect claim that can be refuted. |
| 9 | `engines/social/execution_trace_miner.py` | mining at the **execution-trace** grain, with a composed/uncomposed frontier | The live path mines frames and atoms. Nothing reads the agent's own call log, and nothing prevents the composer from re-proposing a pattern it already composed. |
| 10 | `engines/social/cods_types.py` | `BayesianHypothesis` — explicit posterior, explicit `is_refuted`, explicit `sample_size` | The live ledger records falsification without a posterior or an *n*. Already under a protection note; re-confirmed unreferenced, not re-argued. |

### Tier 2 — capability that IS reached, constructed every episode, and **thrown away at the boundary**

This tier is not a `preserve` list — every file here is `live`. It is the more actionable half:
the code runs, the wiring is one identifier away from working, and the build currently pays the
construction cost for nothing. Root cause is DEFECT A.

| capability | the module (live) | the one line that discards it |
|---|---|---|
| learning from near-misses — the positive-side residual of the frontier | `engines/memory/near_miss_analyzer.py` | `rungs/exploitation.py:837` guards `get_insights`; class has `analyze_near_miss` / `get_near_miss_report`. Whole rung dead. |
| budgeting **how much** to simulate before acting | `engines/regulation/imagination_budget.py` | `rungs/orientation.py:1158` guards `calculate_budget`; class has `get_persona_allowance` / `can_speculate` / `get_synthesis_depth`. Whole rung dead. |
| spatial coverage as a **network-wide** quantity; unexplored-region priority | `engines/regulation/network_exploration_tracker.py` | `rungs/orientation.py:1194` guards `get_exploration_stats`; class has `get_network_exploration_map` / `get_exploration_priority_action`. Whole rung dead. |
| network homeostasis signals reaching the decision path | `engines/regulation/regulatory_signal_engine.py` | `rungs/orientation.py:749` guards `get_active_signals`. |
| "my theory is contradicted → stop exploiting" | `engines/reasoning/scientific_method_engine.py` | `rungs/hypothesis.py:47` guards `get_theory_stage`; falls back to the literal `'exploring'` every call, so the contradiction branch at `:49` is unreachable. |
| questions that **block** actions | `engines/reasoning/scientific_method_engine.py` (`QuestioningEngineWithTeeth`) | `rungs/orientation.py:153` guards `questioning_engine`. |
| replay prediction feeding the live decision | `engines/planning/replay_learning_engine.py` | `rungs/exploitation.py:3894` guards `get_current_prediction`. |
| current subgoal reaching the ladder | `engines/planning/subgoal_planner.py` | `rungs/exploitation.py:1494` guards `get_current_subgoal`. |
| proven trigger chains and trigger-effect prediction | `engines/self_model/trigger_sequences.py` | `rungs/exploitation.py:3435` guards `get_proven_sequence` — the class defines `get_proven_sequences`. **A single missing `s`.** And `:3456` guards `predict_trigger_effect`, absent. |
| inferred goals and negative-valence avoidance | `engines/self_model/valence_goals.py` | `rungs/exploitation.py:3834` guards `get_inferred_goal` (class: `get_goal`); `:3862` guards `get_negative_valence_objects` (class: `get_all_valences`). |
| active beliefs reaching the hypothesis rungs | `engines/self_model/belief_system.py` | `rungs/hypothesis.py:1046` guards `get_active_beliefs` (class: `get_beliefs`). |
| suggested symbolic transformation | `engines/self_model/symbolic_tracker.py` | `rungs/hypothesis.py:1238` guards `suggest_transformation` (class: `get_transformation_needed`). |
| grid-structure analysis at the survey rung | `engines/self_model/grid_analysis.py` | `rungs/orientation.py:131` guards `analyze_grid_structure`. |
| terminal-approach detection in the filter | `engines/perception/terminal_pattern_detector.py` | `rungs/filter_rungs.py:335` guards `detect_terminal_approach`. |
| wA/wB and death-persona spawning at the hypothesis rungs | `engines/consciousness/i_thread.py` | `rungs/hypothesis.py:258,259,263` guard `get_wA`, `get_wB`, `spawn_death_persona`. |
| **the ranked counterfactual record being read back** | `engines/reasoning/deliberation_audit.py` | not a guard — the writer runs (`decision_rung_system.py:636`) and the four readers (`:481, :523, :579, :620`) have no caller anywhere. |

At least four of these are **name mismatches, not missing capability** —
`get_proven_sequence`/`get_proven_sequences`, `get_active_beliefs`/`get_beliefs`,
`get_inferred_goal`/`get_goal`, `suggest_transformation`/`get_transformation_needed`. Those four
are one-identifier fixes. The rest need a small adapter or a decision about which side is right.
**Nothing was changed. This is the list.**

---

## LIMITS OF THIS READ

1. **Reachable ≠ fired.** Every registry row is a *lazy* property; the engine is built only when
   a rung touches it. Where the rung is a DEFECT-A no-op the engine may never be constructed at
   all — I read the guard, I did not run the ladder.
2. **DEFECT A was found by AST diff of Protocols and `hasattr` string literals against class
   bodies.** A method injected at runtime (`setattr`, a mixin resolved dynamically, a `__getattr__`)
   would present as missing here. None was found in these classes, but absence of a hit is not
   proof. Each row cites its file:line so the call is checkable.
3. **`legacy/` was read but not classified** — it is outside the slice. Two files
   (`completion_predictor.py`, `network_contributor.py`) are reached only from there, and are
   marked live-by-import with that fact stated rather than being called dead.
4. **`engines/egocentric/` and `engines/cognition/` are another agent's slice.** Where a site in
   those packages reaches one of my files (`cognitive_router.py:65` → `graph_evolution`;
   `rule_induction.py:35` → `visual_reasoning`; `cognition/__init__.py:17` → `hypothesis_system`;
   `slot_registry.py` naming rungs) I cite it but did not audit it.
5. **`engines/` cannot be flattened.** Re-confirmed independently: `engines/registry.py` resolves
   four `self_model` engines by `module='engines.self_model'` (`:81, :87, :93, :99`), i.e. through
   the package `__init__` re-export, and 24 more by dotted sub-package strings at `:381`. Removing
   any `__init__.py` in this slice breaks the registry. Stated; nothing proposed.
6. **Dot-dirs were searched as invocation sites, per Amendment 1** — 11,736 files under dot-dirs,
   dotfiles and root config were scanned by module name (see DOT-DIR INVOCATION CHECK). `.env` was
   not opened, per the brief; `.git`, `.venv` and four cache dirs were skipped as caches. The
   residual risk is a module selected by a dynamically-built string inside `.runs/`'s JSON/JSONL
   data, which would not match a bare-name search.
7. The tree may move. Re-run before acting on any row.
