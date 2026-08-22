# EXAM 03 — the repo root, `tools/**`, `rungs/**`, `config/**`

Scope: the 37 top-level `*.py`, plus every `.py` under `tools/`, `rungs/`, `config/`
(`.`-prefixed directories skipped). **79 files. Every one opened — docstring and top-level
`def`/`class` names at minimum. Nothing moved, nothing deleted, nothing edited.**

Built on `record/findings/CODEBASE_INVENTORY.md` (which covers 78 of these 79 —
`tools/wiring_receipts.py` postdates it). Where this read disagrees with that document the
row says so and names the site; the corrections are collected under **WHERE THIS READ
CORRECTS THE INVENTORY**.

Snapshot: branch `v4-cold`, HEAD `e1cce38`, 2026-08-22. Dirty at examination time:
`agent_lifecycle_manager.py`, `evolution_runner.py` (**both under a builder's edit — read
only, not touched**), `record/log/PORT_LOG.md`; untracked `tests/gate/test_lifecycle_cleanup.py`.

Exclusions honoured: `docs/GAME_TRUTH`, `ouroboros_cpu/objective_grammar.py`, the
train-set-answers directory and `.env` were not opened. No frame decoded. No game id, colour
or object identity appears below.

---

## COUNTS

| | files |
|---|---|
| **TOTAL in slice** | **79** |
| `(root)/*.py` | 37 |
| `tools/**` | 33 (32 in `tools/`, 1 in `tools/verify/`) |
| `rungs/**` | 8 |
| `config/**` | 1 |
| | |
| **live** | **61** |
| **preserve** | **15** |
| **considered_dead** | **3** |
| unreadable | 0 |

By reached-by mechanism:

One primary mechanism per file; the rows below name secondary sites where they exist.

| mechanism | root | tools | rungs | config | **total** |
|---|---|---|---|---|---|
| STATIC — module-level import from an entrypoint chain | 29 | 2 | 8 | 1 | **40** |
| ENTRYPOINT — operator command line (`__main__`) | 2 | 2 | — | — | **4** |
| STRING — registry / CI yaml / subprocess / `spec_from_file_location` / pre-commit | 3 | 5 | — | — | **8** |
| LAZY — in-function import only | 1 | 1 | — | — | **2** |
| TEST-ONLY — a gate test is the only executor | — | 8 | — | — | **8** |
| NAMED-ONLY — named in prose/ladder/prereg; nothing invokes | 1 | 8 | — | — | **9** |
| NONE — no import, no string, no test, anywhere | 1 | 7 | — | — | **8** |
| | 37 | 33 | 8 | 1 | **79** |

**The root is 35/37 live.** The two that are not are `__init__.py` (a stale package marker
naming a module that lives in `legacy/`) and `schema_auto_maintenance.py`. `tools/` is the
opposite shape: 17 of 33 reached, 16 not.

---

## THE TABLE

`site` is the ONE line that reaches the file. Paths relative to repo root.

### `(root)/` — 37 files · live 35 · preserve 1 · considered_dead 1

| path | dest | reached-by (with the site) | what it does | if preserve: the capability |
|---|---|---|---|---|
| `__init__.py` | **considered_dead** | NONE. No `.py` in the tree imports the repo root as a package; `pytest.ini` comments say it is deliberately ignored ("Ignore the root `__init__.py` which has relative imports") | Package marker. Sets `PYTHONDONTWRITEBYTECODE` then `try:`-imports `.arc_api_adapter`, **`.core_gameplay`** and `.database_interface` under a bare `except ImportError: pass`. `core_gameplay` is in `legacy/`, so the try arm can never fully succeed and the failure is silent. Header still reads "BitterTruth-AI"; `__author__ = "Tabula Rasa Team"` | — |
| `abstraction_config.py` | live | STATIC — `engines/perception/object_detector.py:24` (`from abstraction_config import is_abstraction_enabled`) | Feature flags + thresholds for the abstraction layer; `is_abstraction_enabled`, `get_abstraction_config`, AB-test sample rate | — |
| `agent_lifecycle_manager.py` | live | STATIC — `evolution_runner.py:121` | Retires underperformers, purges ancient inactive agents with an FK cascade (`_fk_dependents`, `_cascade_dependents`, `_MAX_CASCADE_DEPTH`), archives their knowledge first. **UNDER EDIT AT EXAMINATION TIME** (dirty; new untracked `tests/gate/test_lifecycle_cleanup.py` alongside) | — |
| `agent_operating_mode_system.py` | live | STATIC — `evolutionary_engine.py:21`, also `evolution_runner.py:184` | Assigns operating modes/roles across the population, derives role from weights, phase checks, role-saturation metrics | — |
| `arc_api_adapter.py` | live | ENTRYPOINT (`__main__`) **and** STATIC — `evolution_runner.py:46`, `context_builder.py:39`, `outcome_processor.py:38` | The SDK wrapper: `ArcadeWrapper`, `GameEnvironment`, `Observation`, offline/online mode, and the headless render guard (`install_headless_render_guard`) | — |
| `breakthrough_budget_allocator.py` | live | STRING — `engines/registry.py:297` `module='breakthrough_budget_allocator'`, fed to `importlib.import_module` at `engines/registry.py:381` | Per-game action budget from network-level wins; batch budgets and their distribution log | — |
| `cognitive_game_player.py` | live | STATIC — `evolution_runner.py:64`. (Named an entrypoint by the rubric, but it has **no `if __name__`** — it is reached only through the runner) | Plays a game through the cognitive loop; records action productivity, persists causal knowledge and mechanics, writes observation records and frame snapshots | — |
| `cognitive_loop.py` | live | STATIC — `cognitive_game_player.py:33`. Also LAZY from `tools/live_coverage_diff.py:175` | The loop. 5,421 lines: `CognitiveLoop`, `PerceptualBlackboardAdapter`, plus the W2b/W3c/W3d/narration/gate step helpers. Holds the ~11 in-function imports that are the only reach into `engines/egocentric/*` | — |
| `collective_reasoning_engine.py` | live | STATIC — `evolution_runner.py:128` | Multi-agent voting sessions: propose, weight votes, resolve, record the collective insight | — |
| `concept_discovery_engine.py` | live | STATIC — `evolution_runner.py:156`. Also LAZY at `engines/planning/sequence_abstraction.py:51`, `engines/reasoning/scientific_method_engine.py:49`, `engines/social/resonance_detector.py:58` | Tracks operator patterns to emergence, names emergent concepts, computes lineage; plus `StructuralPatternLibrary` (structural hash → suggested action) | — |
| `context_builder.py` | live | STATIC — `evolution_runner.py:50` | Builds the `DecisionContext` the rung system consumes; checkpoint metadata, frame-divergence tracking, frame hashing | — |
| `database_interface.py` | live | STATIC — 83 module-level importers; nearest `agent_lifecycle_manager.py:25` | The DB. Creates each box DB from `complete_database_schema.sql` (`:96`), ensures persona/role-transition/affinity tables, domain-alignment history | — |
| `database_logger.py` | live | STATIC — `decision_rung_system.py:40`, `engines/engine_logger.py:45` | Logging handler that writes to the DB; also reads `complete_database_schema.sql` (`:164`) to bootstrap | — |
| `decision_rung_system.py` | live | ENTRYPOINT-adjacent (`__main__`) **and** STATIC — `evolution_runner.py:54` | The rung ladder: `DecisionRungSystem` + `CoreGameplayAdapter`, ordering presets, shadow mode, category enable/disable. Consumes `RUNG_REGISTRY` from `rungs/` at `:53` | — |
| `event_bus.py` | live | STATIC — `evolution_runner.py:55`, `game_player.py:31` | Pub/sub `EventType`/`Event`/`EventBus` with a hook-failure event | — |
| `evolution_runner.py` | live | **ENTRYPOINT** (`__main__`, `main()`); the origin of most of the static chain above | The thin orchestrator: population init, agent/game selection, cadence, collective deliberation, shutdown handling. **UNDER EDIT AT EXAMINATION TIME** (dirty) | — |
| `evolution_types.py` | live | STATIC — `evolution_runner.py:56`, `game_player.py:32`, `cognitive_game_player.py:35` | `AgentState` and `GameResult` — the shared dataclasses of the Phase-4.1 split | — |
| `evolutionary_engine.py` | live | STATIC — `evolution_runner.py:89` | Fitness (ARC/standard/specialist/diversity/meta-learning), breeding-pair selection, crossover, mutation. Holds the function-local import of `manual_tools` at `:464` | — |
| `game_player.py` | live | STATIC — `evolution_runner.py:59`. (Named an entrypoint by the rubric; **no `if __name__`**) | Plays one game for one agent with fully injected dependencies; scorecards, action traces, player state, property transformations, ablation bookkeeping | — |
| `health_monitor.py` | live | STATIC — `evolution_runner.py:60` | Post-generation health assertions; `run_safe_cleanup` (every 30 generations) and observation-log truncation. **This is the production caller of `safe_cleanup.py`** | — |
| `horizontal_transfer_engine.py` | live | STATIC — `evolution_runner.py:107` | Donor→recipient trait transfer gated on emotional compatibility, with adaptive per-layer rates | — |
| `mastery_system.py` | live | STATIC — `evolution_runner.py:191`; consumed at `game_player.py:769` and `:1347` | Replay as a privilege: diversity/robustness/consistency/efficiency → tier → `should_allow_replay`, ablation skip rates | — |
| `meta_learning_curriculum.py` | live | STATIC — `evolution_runner.py:114` | Per-agent curriculum stages; selects single / similar-pair / diverse / novel game sets and advances stages | — |
| `multi_stage_matching_pipeline.py` | live | **TWO sites.** STRING — `engines/registry.py:303` `module='multi_stage_matching_pipeline'` (→ `importlib` at `registry.py:381`); LAZY — `engines/reasoning/symbolic_reasoning_engine.py:2150` | Five-stage sequence fallback (exact → prefix → suffix → subsequence → conceptual) with maturity-adjusted thresholds | — |
| `network_health_responder.py` | live | STATIC — `evolution_runner.py:135` | Turns network-health readings into mutation-rate, role-allocation and exploration-budget adjustments | — |
| `network_intelligence_engine.py` | live | STATIC — `evolution_runner.py:100` | Ecosystem snapshots: knowledge, information-flow, persona, resilience, population, metabolic metrics; emergence gain | — |
| `outcome_processor.py` | live | STATIC — `context_builder.py:40` | Classifies each action's result (frame change, score/level change, death, level complete, win); `OutcomeTracker` detects oscillation and stuck streaks | — |
| `pipeline_assertions.py` | live | STATIC — `evolution_runner.py:68`, `game_player.py:33`, `result_recorder.py:22` | Write-through assertions at the moment of writing — the answer to the silent-disconnection family. Contract spot-checks for context, viral package, resonance, sequence | — |
| `primitive_unlock_manager.py` | live | STATIC — `concept_discovery_engine.py:40`, `evolution_runner.py:149` | Gates primitives locked→emerging→unlocked on cross-game success rate and confidence | — |
| `representation_learner.py` | live | STATIC — `engines/self_model/cognitive_core.py:26`, `engines/self_model/embedding_matcher.py:29` | Optional torch frame encoder: trains on recent traces, embeds frames, finds similar situations. Degrades on `TORCH_AVAILABLE` | — |
| `result_recorder.py` | live | STATIC — `evolution_runner.py:69` | Stores game results; persists world model, winning sequences, post-win processing, sequence generalisation | — |
| `safe_cleanup.py` | live | **LAZY — `health_monitor.py:133`** (inside `run_safe_cleanup`, fired every 30 generations from the runner). Second site: `tools/swarm_supervisor.py:178` | 2,436 lines of retention: zero-score games, score history, system logs, navigation history, action-trace distillation, knowledge compression, rule merging. D-1/D-2 open against it | — |
| `schema_auto_maintenance.py` | **preserve** | NAMED-ONLY in production. Its one importer is `manual_tools/utilities/enhanced_database_interface.py:21` — itself unreached. `manual_tools/utilities/cleanup_temp_files.py:110` is a `KEEP_FILES` **inventory**, not an invocation | Detects schema drift against the live DB, regenerates `complete_database_schema.sql`, writes a versioned `schema_versions` row and a version history | **Schema drift detection with versioning.** `complete_database_schema.sql` is read on the live path (`database_interface.py:96`, `database_logger.py:164`) and by CI (`tools/consumption_sweep.py:94`), yet **nothing checks it still matches the DB**. This is the only code in the slice that closes that loop, and it does it with a version log rather than a bare overwrite |
| `seed_primitives.py` | live | STATIC — `engines/social/primitive_suggester.py:30`. Also LAZY — `rungs/base.py:47` (`DecisionRung._ensure_primitives`) | 16,799 lines: the `SeedPrimitiveRegistry` of ~315 executable primitives by category, with `P()`/`call()` accessors | — |
| `system_diagnostic.py` | live | STATIC — `evolution_runner.py:205` | The every-10-generations health report: gauge trends, disconnected tables, bottlenecks, knowledge utilisation, compression, resonance, overall score | — |
| `system_health_gauges.py` | live | STATIC — `evolution_runner.py:198`, `system_diagnostic.py:27` | The seven runtime gauges (centralization, retention, authority, equity, compression, transfer, belief turnover) + Gini and the unhealthy-streak trip | — |
| `vulture_whitelist.py` | live *(by constraint — tooling anchor)* | STRING — `.pre-commit-config.yaml:17` passes it as a positional argument to the `vulture` hook. (The `tests/gate/*` hits at `test_origin_marker.py:258`, `test_wiring_registry.py:110`, `_ast_laws.py:49` are **exclude lists**, not invocations) | 94 lines of `# noqa: F821` anchors naming symbols vulture would otherwise flag, each with the file:line it defends | — |

### `config/` — 1 file · live 1

| path | dest | reached-by (with the site) | what it does |
|---|---|---|---|
| `config/cognitive_parameters.py` | live | STATIC — `engines/cognition/cognitive_router.py:129` (also `eisenhower_layer.py:37`, `hysteresis.py:23`, +2) | The tiered parameter block (TIER 1 critical / 2 performance / 3 fine-tuning) with `validate`, `diff`, `from_dict_by_tier`, plus `CognitiveParameterHistory` (record/snapshot/find_changes) and the `DEFAULT_COGNITIVE_PARAMS` singleton |

### `rungs/` — 8 files · live 8 (all by static chain)

Every rung module is reached the same way: `decision_rung_system.py:53` does
`from rungs import RUNG_REGISTRY`; `rungs/__init__.py` imports each domain's `RUNGS` dict
and merges them with a hard collision check that raises `ImportError`.

| path | dest | reached-by (with the site) | what it does |
|---|---|---|---|
| `rungs/__init__.py` | live | STATIC — `decision_rung_system.py:53` | Merges the six domain `RUNGS` dicts into one flat `RUNG_REGISTRY`, raising on any duplicate key; re-exports the base types |
| `rungs/base.py` | live | STATIC — `decision_rung_system.py:54` and all six domain modules (`rungs/emergency.py:11` …) | The ABC and shared plumbing: `DecisionRung`, `RungResult`, `KnowledgeProvenance`, `DecisionStrategy`, action-availability helpers, `Action6CoordinateProvider`, and the lazy primitive loader at `:47` |
| `rungs/emergency.py` | live | STATIC — `rungs/__init__.py:27` | 2 hard safety rungs: infinite-loop breaker, coordinate-oscillation breaker |
| `rungs/exploitation.py` | live | STATIC — `rungs/__init__.py:28` | The largest module in the slice (4,505 lines): 32 rungs that spend knowledge — discovery replay, frontier topology/checkpoints, three-try sequences, state matching, spatial relationships, click-behaviour learning, constraint satisfaction, rule transfer, constraint decoding |
| `rungs/exploration.py` | live | STATIC — `rungs/__init__.py:29` | 2 rungs: smart action selection (with tried-position avoidance) and Action6 object exploration with repetition decay and abstention |
| `rungs/filter_rungs.py` | live | STATIC — `rungs/__init__.py:30` | 11 weight-modifying safety gates: death avoidance, prior lessons, three-layer filter, pariah avoidance, terminal pattern, destructive-action detection, budget-aware planning, theory contradiction, viral weights, metacognitive elimination, contextual failure |
| `rungs/hypothesis.py` | live | STATIC — `rungs/__init__.py:31` | 16 theory-forming rungs: scientific method, two streams, metacognitive prediction, theory gate, sensation, I-thread, event understanding, resonance, interactable-tile discovery, goal-relationship modelling, belief/hypothesis systems, symbolic tracker, deliberation, hypothesis testing, assumption formation |
| `rungs/orientation.py` | live | STATIC — `rungs/__init__.py:34` | 15 world-understanding rungs: survey, questioning, exploration phase, frustration, palette detection (`:314` is the only reach into `engines/perception/palette_detector.py`), sparse grid (`:517`, likewise `sparse_grid.py`), frame interpretation, breakthrough budget, regulatory signal, grid exploration, affordance detection, control tracker, imagination budget, network exploration stats, self-trust boost |

### `tools/**` — 33 files · live 17 · preserve 14 · considered_dead 2

**Structural fact stated first, because it changes how every row below should be read:**
there is **no `tools/__init__.py` and no `tools/verify/__init__.py`**. Every
`from tools import X` in the gate suite resolves only as a PEP-420 namespace package with
the repo root on `sys.path`. `tools/` is also outside `record/canon/WIRING_REGISTRY.md`'s production
globs, so **no file here carries a receipt and the registry cannot vouch for any of it** —
the four `tools/*` rows that do appear in the registry (`efficiency_read`,
`context_minimiser`, `regen_series`, `bracket_rt`) are all marked **SEVERED**, i.e. the
registry records them as instruments precisely because nothing production-side calls them.

| path | dest | reached-by (with the site) | what it does | if preserve: the capability |
|---|---|---|---|---|
| `tools/swarm_supervisor.py` | live | **ENTRYPOINT** (operator CLI; `.runs/swarm_supervisor.log`, `.runs/supervisor.out/.err` on disk) | The full-fleet driver: one worker per game, memory cap, bounded lifetime with the HOLD deferral, DB garbage collection/VACUUM, code fingerprinting and deploy-on-change, loud respawn-under-HOLD | — |
| `tools/sprint_keeper.py` | live | **ENTRYPOINT** (operator CLI; `.runs/sprint_argv.txt` on disk) | Relaunch-only watchdog for sprint-mode workers: every interval, if no live `evolution_runner --game <g>` exists, spawn one and log it. Deliberately does *not* deploy, fingerprint or honour HOLD | — |
| `tools/fleet_env.py` | live | STATIC — `tools/swarm_supervisor.py:47` **and** `tools/sprint_keeper.py:59` | The single statement of per-worker environment: the game roster `GAMES`, the `;`-joined cross-mount seed dirs, and the LP-drive arm assignment. Written explicitly to kill a transcription that drifted | — |
| `tools/consumption_sweep.py` | live | **STRING — `.github/workflows/ci.yml:41`, a BLOCKING CI step** (`python tools/consumption_sweep.py --strict`) on every push and PR | Two AST passes: writer-reader pairing for every published stream and written table (readers classified abort-like vs decide-like), and literal-in-decision vs measurement-exists | — |
| `tools/ood_lint.py` | live | **STRING — `.github/workflows/ci.yml:47`, a BLOCKING CI step** (`python tools/ood_lint.py`) | Full-scan of production sources for three answer-encoding smells: game-id literals, absolute-coordinate magic pairs, level-name specials; inline waivers supported | — |
| `tools/wiring_receipts.py` | live | STATIC — `tools/live_coverage_diff.py:53`; imported by 5 gate tests (`test_wiring_registry.py:93`, `test_symbol_receipts.py:62`, `test_origin_marker.py:43`, `test_efficiency_read.py:42`, `test_regen_series.py:39`); CLI documented at `record/canon/WIRING_REGISTRY.md:42` | The symbol-anchored receipt grammar `file:ENCLOSING/KIND:NAME#ORDINAL@LINE`, its AST resolver, and the three registry operations `migrate | refresh | demote`. **Postdates `CODEBASE_INVENTORY.md` — it has no row there** | — |
| `tools/live_coverage_diff.py` | live | TEST-anchored + named as the empirical gate at `record/canon/WIRING_REGISTRY.md:16` and `tests/gate/test_wiring_registry.py:58` | Runs a bounded synthetic hermetic episode through the real `CognitiveLoop` under branch coverage, then diffs executed lines against `record/canon/WIRING_REGISTRY.md`. Artifacts on disk: `.runs/real.coverage`, `.runs/real_cov_run.log`, `.runs/live_closure.json` | — |
| `tools/disk_ceiling.py` | live | STRING — `tools/overnight_run.py:90` (subprocess) **and** STATIC from `tests/gate/test_disk_ceiling_preserves.py:31` | The 30 GB hard ceiling that *gates* rather than warns: archive-then-truncate, never delete; claim-supporting paths kept regardless; WAL excluded from the budget but printed | — |
| `tools/beat_rates.py` | live | TEST — `tests/gate/test_beat_rates.py:61` and `:557` (`importlib.import_module("tools.beat_rates")`); cited as the beat instrument at `record/canon/KNOBS.md:112`, `record/canon/THE_LADDER.md:1224` | The hourly beat as rates with denominators, per game, never averaged: ground first and alone, everything else tagged `[frame-internal]`; exposure floors, residual by slot, learning, economy, carried cost | — |
| `tools/split_half.py` | live | **LAZY — `tools/beat_rates.py:443`** (`from tools import split_half as sh`, for the per-game floor); also `tests/gate/test_beat_rates.py:18`. Artifact: `.runs/split_half_run1.log` | Best-ever `level_completions` in the first half of a window against the second, split by episode count so both halves have equal n by construction; refuses to report when the window cannot be split | — |
| `tools/bracket_rt.py` | live | TEST — `tests/gate/test_bracket_rt.py:37`, `tests/gate/test_verdict_stamps.py:218`. Registry row `record/canon/WIRING_REGISTRY.md:201` = **SEVERED** | The R_T bracket residual: export a promoted atom through the membrane as a prior (sigma only), re-derive in a fresh box, measure the divergence. Asserts the membrane law rather than assuming it (`MembraneViolation`) | — |
| `tools/build_action_book.py` | live | TEST — `tests/gate/test_action_book.py:57`; named as its builder by the live module `engines/egocentric/action_book.py:15`. Artifacts: `.runs/book_rebuild.log`, `.runs/book_rebuild_clean.log` | Stage 0 of the reasoning gate: folds the atoms stream and the read-only `action_traces` DB into a per-action effect book, with eleven explicit refusal codes for missing evidence | — |
| `tools/efficiency_read.py` | live | TEST — `tests/gate/test_efficiency_read.py:41`. Registry row `record/canon/WIRING_REGISTRY.md:190` = **SEVERED** | Distance-to-that-player, read-never-target, with the prohibition on being a knob or arm objective written into a module constant (`PROHIBITION`) and the reference-source discovery it depends on | — |
| `tools/regen_series.py` | live | TEST — `tests/gate/test_regen_series.py:38`. Registry row `record/canon/WIRING_REGISTRY.md:194` = **SEVERED**. Artifact: `.runs/regen_series.jsonl` | The within-fabric rho-drift time series — the missing second term of the roving-pool gate's pricing (weighted-Jaccard digest drift per snapshot) | — |
| `tools/context_minimiser.py` | live | TEST — `tests/gate/test_context_min.py:74`. Registry row `record/canon/WIRING_REGISTRY.md:191` = **SEVERED** | The retro context-minimisation pass: intersect multiple observations of one key into DONT_CARE cells while always retaining changed cells plus one ring; singletons emitted unchanged and marked. Writes to a NEW file, refuses to name the input. **Also a one-shot — see below** | — |
| `tools/sigma_backfill.py` | live | TEST — `tests/gate/test_sigma_backfill.py:28` (16 call sites) | Derives sigma for pre-B13 atoms from the stored before/after patches and rewrites each `atoms.jsonl` atomically, behind a paranoid "no other python process alive" guard. **Also a one-shot, already run — see below** | — |
| `tools/n1_metric.py` | live | STRING — `tests/gate/test_qa_fixes_w4.py:210` (`spec_from_file_location("n1_metric_under_test", …)`) | Mint-to-independent-verification gap per atom, over fabric seq. Carries an honesty clause: it discovers the linkage field from the records and reports "atom-blind" when the books carry none | — |
| `tools/cold_ship.py` | **preserve** | NAMED-ONLY — `tests/gate/test_fabric_read_cache.py:587` counts it in prose ("cold_ship x2"); no invocation. Artifact `.runs/cold_venv` shows it has run | Kaggle-parity smoke: a bare interpreter (stdlib + numpy only) in a throwaway venv, network killed first, read-only seed mount, with an `--inline` meta-path-blocker fallback | **The only ship-clean check in the slice.** Nothing else verifies the knowledge substrate runs without dev dependencies, without network, on a read-only mount. That is a deployment-shaped failure nothing else in this tree can see |
| `tools/comment_divergence.py` | **preserve** | NONE in production (3 hits, all under `record/`) | Flags every comment that states a number the adjacent code does not use, with an explicit statement of what it does *not* prove | **A comment is an unchecked claim.** It found three real divergences by hand (`database_interface.py:80-81` says 1000 twice where the pragma sets 100; a "every 10 generations" comment over a 30-generation function; a rung priority comment disagreeing with the registry). This is the input the premise pass consumes |
| `tools/control_arm.py` | **preserve** | NONE in production (2 hits, all under `record/`). Artifact directory `.runs/arms` shows it has run | Paired-box control-arm driver: one git worktree per sha, same game and same shared seed mount, separate boxes, N episodes per arm, then a delta report | **Verdicts become causal.** Registered verdicts read off the live swarm are confounded with time, budget and luck; this is the only machine here that produces an arm delta instead of a wall-clock coincidence. Nothing in the live path can do this |
| `tools/d5_profile_wrapper.py` | **preserve** | **NONE — zero mentions anywhere outside itself.** Artifacts `.runs/d5_profile_*.pstats` and `PORT_LOG.md:1885` reading one show it has run | Runs a worker in-process and dumps cProfile stats on a timer at a fixed window, then exits cleanly — because cProfile writes nothing on a kill and a slow worker cannot finish a generation inside a profiling window | **The only way to profile a worker too slow to finish.** Carries its own guard in the docstring: proportions, not absolutes; no threshold may be set against these numbers. That caveat is the valuable half and it exists nowhere else |
| `tools/dump_schema.py` | **preserve** | NONE in production. **But its output is load-bearing**: `complete_database_schema.sql` (271 KB, last written 2026-08-10) is read at `database_interface.py:96`, `database_logger.py:164` and `tools/consumption_sweep.py:94` | 32 lines: dumps `core_data.db`'s tables/indexes/triggers/views to `complete_database_schema.sql` | **The producer of a live-path input with no other producer in the slice except `schema_auto_maintenance.py`.** If the canonical schema file is ever lost or stale, this is one of only two things that can regenerate it. **See the one-shot section: re-running it against the wrong DB overwrites the canonical schema** |
| `tools/fork_divergence.py` | **preserve** | NAMED-ONLY — `record/canon/THE_LADDER.md:747` and `:823` record its measurement; nothing invokes it. `DEFAULT_OTHER` at `:25` points at the sibling repo `../Ouroboros` | Counts known-positive and known-negative markers in both lineages: does a fix made in one fork exist in the sibling | **The one instrument aimed at FINDING 5's problem.** Its own docstring states the asymmetry that makes it necessary: defects propagate by inheritance, fixes propagate only by someone remembering — so divergence grows monotonically unless something looks. It ships with known-positive and known-negative controls, so a silent failure is detectable |
| `tools/link3_live_check.py` | **preserve** | NAMED-ONLY — `tests/gate/test_link3_hook_and_vocabulary.py:39` describes it in prose as the operator half; no invocation | Runs the abduction vocabulary against every level-up frame on disk, read-only, printing three pre-committed clauses including two predicates that must stay at exactly zero | **The operator half of a falsifier whose other half is pinned to fixtures.** The gate test cannot read `.runs/**` (the janitor compacts it), so the claim can only be re-measured against reality by this file. Without it the falsifier is half-open |
| `tools/norm_sweep.py` | **preserve** | NAMED-ONLY — `cognitive_game_player.py:1994` (a comment about its result), `tests/gate/test_frame_normalisation.py:12` (prose); `record/canon/THE_LADDER.md:575` records the finding | Asymmetric-normalisation sweep: where a helper normalises an input, does every sibling input go through it. Word-boundary tokens over nine known pairs. **No `if __name__` — the module body runs the sweep at import**, with relative paths, so it must be run from the repo root | **The defect class recurs and is invisible to unit tests.** It found the link-3 defect (`_get_frame_array(pre)` with post passed raw). Its own limitation is stated in the output, which is why the sibling gate test cites it rather than replacing it |
| `tools/overnight_run.py` | **preserve** | NAMED-ONLY — `record/prereg/PREREG_SWARM_OFFLINE_MODE.md:26`. Artifacts `.runs/overnight_run.jsonl` and `.runs/overnight_stdout.log` show it has run | The twelve-hour offline run: cycles of 25 unique games back-to-back, stopping on a disk-gate breach, a zero-new-session cycle (its own falsifier), or the clock. Nothing irreversible for the duration | **A long unattended run with a falsifier built in.** The stop conditions are the capability: it refuses to "log and continue". **Defect to state: `:29` hard-codes `C:\Users\Admin\Documents\GitHub\Ouroboros\.venv\Scripts\python.exe` — an interpreter in a different repository.** Every other tool derives its interpreter from `sys.executable` or `__file__`. As written this cannot run on this tree unless that sibling venv exists |
| `tools/premise_pass.py` | **preserve** | NAMED-ONLY — `record/canon/KNOBS.md:564` describes it; `record/canon/THE_LADDER.md:710`/`:730` mention it only as a file that shipped with ruff errors. Nothing invokes it | Every constant, threshold, cap, window and default in production with its git-blame date and surrounding context, bucketed PREMISE MOVED / PREMISE UNKNOWN / STILL HOLDS | **Age used as a search index, not as a verdict** — the docstring says so explicitly ("the date is how you find them, not how you judge them"). The build has `record/canon/KNOBS.md` as prose; this is the only thing that derives the list from the source, so the prose cannot silently fall behind |
| `tools/replay_viewer.py` | **preserve** | **NONE — zero mentions anywhere outside itself.** Statically imports the LIVE module `engines/cognition/cognitive_frame.py` | Renders `CognitiveFrame` replays four ways: one-line-per-action console log, multi-line dashboard, standalone HTML report, JSON | **The only renderer of the cognitive frame.** `CognitiveFrame` is produced on the live path and read back only as records; this turns a run into something a human can watch. Its HTML output is self-contained, so a replay survives the box being cleaned |
| `tools/repo_assess.py` | **preserve** | **NONE — zero mentions anywhere outside itself** (the known lead, re-verified). But `.runs/assess_py.txt` (613 lines) is its output verbatim — header `REPOSITORY ASSESSMENT (skips every .-prefixed dir at every level)`, 480 files scanned — **so it has run at least once** | The four-verdict repo read (LIVE / CAPABILITY / MISFILED / SUPERSEDED), with the guard product SUPPORT × REACHABILITY × NOVELTY where any zero forbids a removal, and the lazy-import lesson encoded in the docstring: a module name is searched three ways — as an import, as a dotted path, and as a bare quoted string | **Confirmed DEAD BY ITS OWN CRITERIA, and it is the proto-instrument this whole examination improves on** (FIGURE 6). Two things it holds that the inventory and this document do not: (a) the guard is a *product*, so novelty at zero blocks a removal mechanically rather than by a reader remembering; (b) `main()` prints "a zero here is NOT a verdict — NOVELTY is unchecked, and that guard is read by a human, not by this script" — the refusal to convert a scan into a decision, in code |
| `tools/socket_or_filler_lint.py` | **preserve** | NAMED-ONLY — `record/prereg/PREREG_READOUTS.md:23`. Explicitly PROCTOR-ONLY: "never wired into agent code or agent-visible tests" | Lints a builder's diff for content markers in agent code — nested numeric list literals, game-id-shaped strings, numeric dict literals of size ≥ 3 — and exits 1 on any flag | **The socket-vs-filler grade, and it is deliberately unreachable from the agent side.** Its unreachability from production is a design property, not decay — but nothing on the proctor side invokes it either, which is the part that has decayed. Complements `ood_lint.py` (which CI *does* run) by grading the diff rather than the tree |
| `tools/verify/hermetic.py` | **preserve** | **NONE.** The 17 "mentions" the inventory counted are the English adjective *hermetic*; searching the module path `tools/verify/hermetic` or `tools.verify.hermetic` returns **zero hits outside the file itself** (one in `record/`). Artifact directory `.runs/hermetic` shows it has run | 1,174 lines: run v4 in isolation so two runs can be compared at all — a `sitecustomize.py` injected to seed every RNG at interpreter startup, a fresh sandbox DB per replicate, and the `run`/`check`/`band`/`cutwire`/`goalprobe` verbs | **The determinism harness, and the reason it exists is a fact about this system: v4 is not deterministic (two identical invocations gave 74 and 69 actions, diverging at step 1) and runs are not independent (the 43 MB DB survives, so replicate N continues replicate N-1).** Every unqualified v4 number is unreadable without this. `cutwire` (byte-identity ablation) has no counterpart anywhere in the live tree. **Also: `record/prereg/PREREG_SMART_CLEANUP.md:8` names a sibling `tools/verify/fabric_janitor.py` that does not exist in this tree** |
| `tools/durability_test.py` | **considered_dead** | NAMED-ONLY — `record/canon/THE_LADDER.md:730` mentions it only as a file that shipped with 5 ruff errors; **`PORT_LOG.md:1031` records its result**. Nothing invokes it | Runs `_durability_writer.py` as a child at three `wal_autocheckpoint` settings, hard-kills it, reopens and counts recovered rows | — (the experiment it embodies is finished; see the one-shot section) |
| `tools/_durability_writer.py` | **considered_dead** | STRING — `tools/durability_test.py:15` (subprocess) **and nothing else** | 19 lines: commits N rows under production pragmas then `os._exit(9)` — a hard kill with no close, no atexit, no checkpoint | — (dies with its parent) |

---

## PAIRS AND DUPLICATES

1. **`tools/dump_schema.py` ↔ `schema_auto_maintenance.py` — two writers of one canonical
   file, neither reached.** Both write `complete_database_schema.sql`
   (`dump_schema.py:7` `OUT_PATH`; `schema_auto_maintenance.py:33` `SCHEMA_FILE_PATH`).
   `dump_schema` is a 32-line unconditional overwrite; `schema_auto_maintenance` is the
   richer one — it *detects drift first*, logs a `schema_versions` row, and keeps a version
   history. The file they both write is read on the live path at `database_interface.py:96`
   and `database_logger.py:164`. **A load-bearing artefact with two unreached producers and
   no checker.** They are not redundant: keep both, but they should not be reasoned about
   separately.

2. **`tools/durability_test.py` ↔ `tools/_durability_writer.py` — a parent/child pair,
   dead together.** The child exists only to be killed by the parent (`durability_test.py:15`)
   and has no other caller. Neither is meaningful alone. Both proposed `considered_dead` as
   one unit; splitting them would leave an orphan that cannot be understood.

3. **`tools/ood_lint.py` ↔ `tools/socket_or_filler_lint.py` — the same smell, two sides.**
   Both hunt game-id-shaped literals and hardcoded grids in agent code. `ood_lint` scans the
   **tree** and is a blocking CI step; `socket_or_filler_lint` scans a **diff** and is
   proctor-only, deliberately invisible to the agent. Not duplicates — but a reader who finds
   one will assume the other is redundant, so the split is recorded here.

4. **`tools/consumption_sweep.py` ↔ `tools/live_coverage_diff.py` ↔ `tools/wiring_receipts.py`
   — the three layers of the same wiring question, only two of which run.** `consumption_sweep`
   asks "is anything written that nothing reads" (CI, blocking). `wiring_receipts` asks "does
   the claimed structure still exist" (gate tests + CLI). `live_coverage_diff` asks "does the
   branch ever execute" — and `record/canon/THE_LADDER.md:319` records that it **has never run in its
   strong mode**. The empirical layer is the one that is not running.

5. **`tools/swarm_supervisor.py` ↔ `tools/sprint_keeper.py` — a deliberate near-duplicate,
   already de-duplicated once.** Both spawn `evolution_runner` workers; the keeper's docstring
   enumerates exactly what it does *not* replicate. The overlap that mattered — the roster and
   the environment assembly — was extracted to `tools/fleet_env.py` on 2026-08-21 precisely
   because a transcription had drifted. This is the pattern the other pairs above have not had
   applied to them.

6. **`tools/beat_rates.py` ↔ `tools/split_half.py` — resolved by import, not by copy.**
   `beat_rates.py:443` imports `split_half`'s `required_per_half` rather than restating the
   derivation, with a comment at `:431` saying why. Recorded as the correct handling of a
   shared derivation, for contrast with pair 1.

7. **`rungs/exploitation.py::MultiStageMatchingRung` ↔ `multi_stage_matching_pipeline.py` —
   one capability, two entry paths.** The root module is reached both as an `ENGINE_CONFIGS`
   registry string (`engines/registry.py:303`) and as a lazy import
   (`engines/reasoning/symbolic_reasoning_engine.py:2150`), while a rung of the same name sits
   in the ladder. Not a duplicate implementation, but two independent routes into the same
   pipeline, neither of which mentions the other.

8. **Root `__init__.py` ↔ `legacy/core_gameplay.py`.** The root package marker imports
   `.core_gameplay`, which is in `legacy/`. The import is inside `try: … except ImportError:
   pass`, so the breakage is silent and permanent. The marker also still calls the project
   "BitterTruth-AI" — the same stale identity `CODEBASE_INVENTORY.md` FINDING 5 flags.

---

## ONE-SHOT TOOLS ALREADY RUN

**A distinct category from dead. These finished their job; the evidence that they ran is on
disk or in the log. Re-running several of them would be actively harmful, which is why this
section exists separately — a reader who finds them unreferenced and re-runs them to "check
what they do" can destroy data.**

| tool | evidence it has run | re-running it does what |
|---|---|---|
| `tools/sigma_backfill.py` | `PORT_LOG.md:673` — "sigma_backfill's process guard fired twice — once correctly (my own …)" | **REWRITES `atoms.jsonl` FILES IN PLACE.** Fabrics are append-only in live operation; this tool is the exception and its own docstring calls the contract out in a boxed banner. It refuses to run while any other python process is alive, but that guard is bypassable with `--force`. **Do not re-run without the swarm stopped and a copy of the fabrics.** The legacy atoms it targets have already been given sigma; a second pass over already-stamped atoms is wasted work at best |
| `tools/dump_schema.py` | `complete_database_schema.sql` present, 271,631 bytes, written 2026-08-10 | **OVERWRITES THE CANONICAL SCHEMA FILE** from whatever `core_data.db` happens to be in the current working directory — the path is relative (`Path("core_data.db")`). Run from a box directory, or against a DB carrying experimental tables, it silently replaces the template every new box is built from (`database_interface.py:96`). The safer instrument for the same job is `schema_auto_maintenance.py`, which detects drift and versions the change first |
| `tools/context_minimiser.py` | Registry row `record/canon/WIRING_REGISTRY.md:191`, dated 2026-08-20, SEVERED `[instrument]` | Safe by construction — it is read-only on the source and refuses an output path naming the input. The retro pass over the pre-W2 streams is the part that is done; the mint now minimises at re-observation, so a second retro pass has nothing new to find |
| `tools/durability_test.py` + `tools/_durability_writer.py` | `PORT_LOG.md:1031` records the result: a child commits 500 rows under production pragmas then dies hard | The question is answered — committed data survives a hard kill at every `wal_autocheckpoint` setting, so checkpoint frequency decides WAL replay size, not survival. Both `wal_autocheckpoint=100` and the per-statement commit were chosen against this and the answer has not changed. Re-running writes `dur_100.db`, `dur_1000.db`, `dur_10000.db` (+ WAL/SHM) into `tools/` and hard-kills three child processes |
| `tools/norm_sweep.py` | `record/canon/THE_LADDER.md:575` records the measurement; `cognitive_game_player.py:1994` comments on its result; `PORT_LOG.md:998` records its ruff errors | Read-only. **But it has no `if __name__` guard — the sweep runs on import**, so any `import tools.norm_sweep` executes it, and its `FILES` list uses relative paths, so from the wrong cwd it silently scans nothing and prints `CANDIDATES: 0`. That zero is indistinguishable from a clean tree |
| `tools/d5_profile_wrapper.py` | four `.runs/d5_profile_<box>*.pstats` files (before/after pairs for two boxes; box names elided per the read's constraints), read at `PORT_LOG.md:1885` | Harmless but expensive — it runs a real worker in-process for a fixed window. The D-5 baseline it was built for is taken (before/after pairs on disk) |
| `tools/repo_assess.py` | `.runs/assess_py.txt`, 613 lines, its exact header and format | Read-only. Its output is stale relative to this examination, but the tool is not a migration — it is a re-runnable read. Listed here only because its artefact is what proves the file works, which no reference in the tree does |
| `tools/cold_ship.py` | `.runs/cold_venv` present | Re-creates or reuses the bare venv and re-runs the smoke. Safe, slow, network-dependent on first creation |
| `tools/control_arm.py` | `.runs/arms` present | **Creates and removes git worktrees** (`_ensure_worktree` / `_remove_worktree`) and drives full episode runs per arm. Safe if the tree is clean; on a dirty tree — and two files are dirty right now — worktree creation is where it will fail |
| `tools/build_action_book.py` | `.runs/book_rebuild.log`, `.runs/book_rebuild_clean.log` | **Not one-shot by design** — its own docstring says it rebuilds the book from scratch each run. Listed here only because the artefacts look like a completed migration and could be mistaken for one |
| `tools/wiring_receipts.py` `migrate` | `record/canon/WIRING_REGISTRY.md` rows are already in the six-column symbol-anchored form | `migrate` is the one-shot verb (position receipts → symbol receipts); `refresh` and `demote` are the ongoing ones. Re-running `migrate` over already-migrated rows is the harmful case in this file |
| `tools/overnight_run.py` | `.runs/overnight_run.jsonl`, `.runs/overnight_stdout.log` | Re-runnable by design (twelve-hour cycles). **But as written it cannot run on this tree**: `:29` points `PY` at an interpreter inside a different repository |

---

## WHERE THIS READ CORRECTS THE INVENTORY

Six corrections, each with the site so the call is checkable.

1. **`tools/consumption_sweep.py` and `tools/ood_lint.py` are not "nominal only" — they are
   BLOCKING CI steps.** `.github/workflows/ci.yml:41` runs
   `python tools/consumption_sweep.py --strict` and `:47` runs `python tools/ood_lint.py`, on
   every push and every pull request to every branch. `CODEBASE_INVENTORY.md:617` and `:631`
   classify both OBSCURE-N, "no invocation found". **The cause is structural: the inventory
   skips `.`-prefixed directories at every level, and `.github/` is one.** CI is the single
   most reliable invocation site a repository has, and the exclusion rule makes it invisible.
   Any future sweep must read `.github/workflows/**` for invocation even while excluding it
   from the move proposal.

2. **`safe_cleanup.py`'s production caller is `health_monitor.py:133`, not
   `tools/swarm_supervisor.py:178`.** `CODEBASE_INVENTORY.md:355` names only the supervisor.
   The live site is `HealthMonitor.run_safe_cleanup`, reached from the runner every 30
   generations — i.e. the deletion path runs in ordinary operation, not only when an operator
   drives the supervisor. Given D-1 and D-2 are still open against this file, which caller is
   authoritative is not a bookkeeping detail.

3. **`schema_auto_maintenance.py` is not reached by an invocation.**
   `CODEBASE_INVENTORY.md:356` cites `manual_tools/utilities/cleanup_temp_files.py:110` as
   "named in an invocation". That line is inside the `KEEP_FILES` set — the inventory's own
   FINDING 4 identifies exactly this set as a filename inventory rather than a call site. Its
   only real importer is `manual_tools/utilities/enhanced_database_interface.py:21`, itself
   unreached. Same misread applies to the `breakthrough_budget_allocator.py` and
   `multi_stage_matching_pipeline.py` entries in that set, though both of those are reached
   for real through `engines/registry.py`.

4. **`vulture_whitelist.py`'s reaching site is `.pre-commit-config.yaml:17`, not
   `tests/gate/test_origin_marker.py:257`.** The pre-commit hook passes the file as a
   positional argument to `vulture`. The three `tests/gate` occurrences
   (`test_origin_marker.py:258`, `test_wiring_registry.py:110`, `_ast_laws.py:49`) are
   `PROD_EXCLUDE_NAMES` **exclusion** lists — the opposite of an invocation. Note also that
   the CI vulture step (`ci.yml`, advisory) does **not** pass the whitelist, so the two
   vulture runs in this repo do not use the same configuration.

5. **`tools/verify/hermetic.py` has zero real references, not seventeen.**
   `CODEBASE_INVENTORY.md:647` reports "named in 17 other file(s)" with the site
   `cognitive_loop.py:2055`. That line reads `# Relative root (cwd-scoped: hermetic)` — the
   English adjective. Searching the module path (`tools/verify/hermetic`, `tools.verify.hermetic`)
   returns nothing outside the file. A bare-stem name search cannot distinguish a module name
   from a common word, and *hermetic* is used as a word 20+ times in this tree.

6. **`tools/wiring_receipts.py` has no row in `CODEBASE_INVENTORY.md`** (that section lists 31
   files; there are 32 in `tools/`). It postdates the read, as the inventory's own "the tree
   was in flight during this read" caveat anticipated. It is live.

---

## THREE THINGS WORTH THE GM'S ATTENTION BEYOND THE ROWS

1. **`tools/` has no `__init__.py` — not in `tools/`, not in `tools/verify/`.** Nine gate
   tests do `from tools import X`, which resolves only as a PEP-420 namespace package with the
   repo root on `sys.path`. It works today. It is also the reason `tools/` sits outside
   `record/canon/WIRING_REGISTRY.md`'s production globs, so **nothing in this directory carries a receipt
   and the registry cannot vouch for any of it** — including the two files CI blocks on. The
   four `tools/*` rows that do appear in the registry are all marked SEVERED.

2. **A second cross-repo hard-coded absolute path, extending FINDING 5.**
   `CODEBASE_INVENTORY.md` FINDING 5 names one (`manual_tools/_extract_rungs.py:5` →
   `BitterTruth-AI`). There are two more in this slice: `tools/overnight_run.py:29` pins the
   interpreter to `…\GitHub\Ouroboros\.venv\Scripts\python.exe` — a **third** repository name —
   and `tools/fork_divergence.py:25` defaults to `../Ouroboros` (that one by design). Every
   other tool in the slice derives its paths from `__file__`. The tree therefore refers to
   itself under three names — Ouroboros-Redux, Ouroboros, BitterTruth-AI — and the root
   `__init__.py` still carries the third.

3. **The preserve set here is heavily weighted toward instruments that measure the build
   rather than play the game** — determinism (`verify/hermetic.py`), causality
   (`control_arm.py`), ship-cleanliness (`cold_ship.py`), premise age (`premise_pass.py`),
   comment truth (`comment_divergence.py`), fork drift (`fork_divergence.py`), profiling
   (`d5_profile_wrapper.py`), and the repo read itself (`repo_assess.py`). Not one of them is
   invoked by anything. `tools/live_coverage_diff.py` is the near-miss: it *is* reached, and
   `record/canon/THE_LADDER.md:319` records that its strong mode has never run. **The pattern is not that
   the build lacks instruments. It is that the instruments have no caller** — which is the
   same shape as the wiring defects they were each written to catch.
