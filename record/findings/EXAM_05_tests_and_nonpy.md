# EXAM 05 — `tests/**` (.py) and the non-.py surface

Examiner slice 05. Read-only. Nothing moved, nothing deleted. Every file below was opened.
Binding rubric: `record/findings/EXAMINATION_RUBRIC.md`, **including AMENDMENT 1 (the dot-dir hole)**,
which extended this slice to the invocation surface — see **THE INVOCATION SURFACE** at the foot.

**The headline is in that section, not in the tables.** CI's `pytest tests/gate -q` step — marked
BLOCKING, "these fail the build, that is the whole point of the ruling" — installs a hand-listed
subset of dependencies that omits `arc-agi` and `hypothesis`. Five gate files cannot be *collected*
under it and four more raise at run time. The blocking gate suite cannot have been green.

## COUNTS

**Part A — `tests/**`, every .py: 153 files**

| bucket | n |
|---|---|
| `tests/gate/test_*.py` | 124 |
| `tests/test_*.py` (root, legacy-era) | 26 |
| non-collecting support (`tests/__init__.py`, `tests/conftest.py`, `tests/gate/_ast_laws.py`) | 3 |
| **total** | **153** |
| ORPHANED — gates nothing (subject never imported, never read, never executed) | **3** |
| PARTIAL — majority of the file's tests assert on a local re-implementation, not on the shipped code | **2** |
| module-level imports that fail to resolve against the tree | **0** |
| `from X import Y` where `Y` is no longer defined in `X` | **0** |

Every test file is **live by constraint** (GM's rule: nothing under `tests/` is proposed for a move).
The classification column is ORPHANED?, not dest.

**Part B — non-.py outside `.`-dirs, `environment_files/`, `record/`: 86 files**

| bucket | n | live | preserve | considered_dead |
|---|---|---|---|---|
| `architecture/` | 25 | 6 | 19 | 0 |
| `checklists/` | 9 | 9 | 0 | 0 |
| `config/` (.json only; `cognitive_parameters.py` is .py → other slice) | 4 | 3 | 0 | 1 |
| `figures/` | 11 | 11 | 0 | 0 |
| `models/` | 1 | 1 | 0 | 0 |
| loose top-level | 35 | 34 | 0 | 1 |
| non-.py inside `tests/` (courtesy rows — my directory) | 6 | 5 | 1 | 0 |
| **total** | **91** | **69** | **20** | **2** |

**Invocation surface (added by Amendment 1): 4 dot-files that invoke, 1 of them inert**

| file | invokes | status |
|---|---|---|
| `.github/workflows/ci.yml` | 6 steps, 5 blocking | **2 blocking steps cannot pass** (missing deps) |
| `.githooks/pre-commit` | `ruff check .` | ACTIVE (`core.hooksPath = .githooks`) and agrees with CI |
| `.pre-commit-config.yaml` | vulture + whitelist, isort, 5 hygiene hooks | **INERT** — never installed, and `pre-commit`/`isort` are not in `.venv` |
| `.claude/settings.local.json` | nothing (permissions only, no hooks) | no invocation |

### Corrections to the leads I was handed

- **"36 root markdown files cited by name from live .py at ~102 sites."** The site count is right;
  the file count is not. There are **26** root .md files, and **25** of them are cited from .py.
  I counted **~100 citation sites** across those 25 (the 26th, `README.md`, matched only on the bare
  string `"README.md"` in a keep-list and a docstring — a false positive, though it is live for other
  reasons). The lead's "36" appears to predate the move of the rest under `record/`. **The conclusion
  holds and is stronger than stated**: these are load-bearing documents, and two of them
  (`WIRING_REGISTRY.md`, `KNOBS.md`) are not merely cited but **opened and parsed** at runtime.
- **`figures/*.svg` are the eleven law diagrams and are canon.** Confirmed — eleven files, all
  git-tracked, referenced as a set from `tests/gate/test_standing.py` via `record/corpus/FIGURES_TEXT_DIGEST.md`.
- **`models/`, `architecture/`, `checklists/` contain no .py.** Confirmed for all three. `config/`
  does contain one .py (`config/cognitive_parameters.py`) — flagged below, out of my slice.

---

# PART A — `tests/**`, one row per .py

`gates-what` names the module or behaviour the file asserts against. ORPHANED? is `no` unless the
subject cannot be located or is never touched.

## A.1 — support modules (not collected)

| path | gates-what | ORPHANED? | one line |
|---|---|---|---|
| `tests/__init__.py` | nothing — package marker | no | Sets `PYTHONDONTWRITEBYTECODE=1` before the docstring; makes `tests` a package. |
| `tests/conftest.py` | the suite's own path setup + the no-`__pycache__` law | no | Inserts repo root on `sys.path`, serves `db_path`/`db_connection` fixtures against root `core_data.db`, and fails the session in `pytest_sessionfinish` if any `__pycache__` survives. |
| `tests/gate/_ast_laws.py` | the seven structural laws of the loop, as AST-order predicates | no | Not collected (no `test_` names); six gate files delegate their law bodies here so a law has one body — `test_plan_wire`, `test_goal_abduction`, `test_goal_spine`, `test_level_conventions`, `test_link3_hook_and_vocabulary`, `test_lp_drive` all import it. |

## A.2 — `tests/` root (legacy-era, the cognitive-routing stack)

| path | gates-what | ORPHANED? | one line |
|---|---|---|---|
| `tests/test_blackboard.py` | `engines/cognition/blackboard.py`, `slot_registry.py` | no | 46 tests: TypedSlot get/set, checkpoint/restore, Rumsfeld assessment, edge trust, legacy-context shim. |
| `tests/test_cognitive_router.py` | `engines/cognition/cognitive_router.py`, `catastrophic_fallback.py`, `epistemic_state/tracker`, `search_context.py` | no | 65 tests: fallback detection/trigger, algorithm switching, transition responses, backtracking, frontier, DecisionRungSystem integration. |
| `tests/test_database_interface.py` | `database_interface.py` + `complete_database_schema.sql` | no | 23 tests: schema init from the .sql template, WAL mode, FK enforcement, sessions, persona logging. |
| `tests/test_edge_inference.py` | `engines/cognition/edge_inference.py` | no | 51 tests: static slot read/write analysis, category & heuristic analyzers, runtime observer, export/import round trip. |
| `tests/test_eisenhower_layer.py` | `engines/cognition/eisenhower_layer.py`, `config/cognitive_parameters.py` | no | 42 tests: Rumsfeld→Eisenhower bias, iterative gate, queue aging/promotion, all-eliminate fallback, rung unlock scores. |
| `tests/test_epistemic.py` | `engines/cognition/epistemic_state.py`, `epistemic_tracker.py`, `contradiction_detector.py` | no | 44 tests: quadrant computation (KK/KU/UK/UU), transition detection, contradiction classification. |
| `tests/test_epistemic_stability.py` | `engines/cognition/hysteresis.py`, `question_manager.py`, `uk_potential_index.py`, `epistemic_logging.py` | no | 75 tests: transition gates/cooldowns/thrash prevention, question lifecycle, Bloom-filter UK index, trace schema. |
| `tests/test_evolutionary_engine.py` | `evolutionary_engine.py`, `database_interface.py` | no | 24 tests: youth bonus decay, safe JSON parse, fitness, epigenetic inheritance, population load, mutation. |
| `tests/test_graph_evolution.py` | `engines/reasoning/graph_evolution.py`, `engines/cognition/phenomenology_layer.py` | no | 65 tests: valence-weighted edges, crystallization thresholds, decay, game-feel trajectory, anomaly detection. |
| `tests/test_i_thread.py` | `engines/consciousness/i_thread.py`, `database_interface.py` | no | 40 tests: w_A/w_B weight learning, stream conflict, synthesis surprise, role transitions, cache management. |
| `tests/test_meta_planner.py` | `engines/cognition/meta_planner.py`, `algorithms.py`, `precomputation.py`, `search_context.py` | no | 74 tests: eight search algorithms, bucketed cache keys, profile lookup, precomputation manager. |
| `tests/test_persona_runtime.py` | `engines/consciousness/persona_runtime.py` (`PersonaManager`, `PersonaDecision`), `database_interface.py` | **PARTIAL** | Subject exists and imports cleanly, but 5 of 12 tests are `assert runtime is not None` tautologies and 2 more are `if hasattr(...)` no-ops — see "TESTS THAT GATE NOTHING". |
| `tests/test_phase5_validation.py` | `engines/cognition/shadow_testing.py`, `routing_metrics.py`, `ab_testing.py` | no | 59 tests: shadow divergence analysis, metric targets, A/B phase config and phase metrics. |
| `tests/test_phase6_production.py` | `decision_rung_system.py`, `engines/cognition/edge_trust_manager.py`, `routing_traces.py` | no | 50 tests: ORDERING_PRESETS deprecation warnings, edge trust/toxicity, routing-trace store. |
| `tests/test_phase75_stabilization.py` | `engines/cognition/edge_trust_manager.py`, `path_crystallization.py`, `process_knowledge.py`, `routing_traces.py`, `rung_roles.py` | no | 27 tests: trust accumulation across games, no premature crystallization, negative-reputation decay, exit criteria. |
| `tests/test_phase7_evolution.py` | `engines/cognition/rung_roles.py`, `path_crystallization.py`, `process_knowledge.py` | no | 55 tests: rung role taxonomy, path analysis, crystallized paths, abstract pattern extraction. |
| `tests/test_phenomenology_layer.py` | `engines/cognition/phenomenology_layer.py` | no | 39 tests: FeltState, valence from blackboard state, hysteresis stabilizer, algorithm modulation, trace logging. |
| `tests/test_pipeline_canaries.py` | the cognitive stack end to end (`cognitive_router` → `epistemic_tracker` → eisenhower → phenomenology → hysteresis) | no | 21 integration canaries over many simulated cycles: quadrant/valence diversity, commit rate, hysteresis tick, signal wiring. |
| `tests/test_reasoning_data_usage.py` | **nothing** | **YES** | 48 tests, zero project imports — every assertion is against set arithmetic, dicts and regexes written inside the test file. |
| `tests/test_reasoning_system_fixes.py` | **nothing** | **YES** | 36 tests, zero project imports — asserts on `MagicMock` return values the fixtures themselves configure. |
| `tests/test_safe_cleanup.py` | `safe_cleanup.py` (`SafeDatabaseCleaner`) | no | 17 tests: zero-score games survive, old score history dies, dry-run is inert, winning sequences and agents never touched. |
| `tests/test_sequence_system.py` | **nothing** | **YES** | 35 tests against `MockDatabaseInterface` — a hand-written SQL-string matcher defined in the file; no storage or retrieval code is imported. |
| `tests/test_theory_gating.py` | `engines/reasoning/scientific_method_engine.py` (`ScientificMethodEngine`, `Theory`, `TheoryStatus`, `TheoryType`) | no | One test: theory-gated action scoring against an in-memory sqlite; symbols all still defined. |
| `tests/test_trigger_controller.py` | `engines/regulation/trigger_controller.py` | no | 20 tests: cooldown, damping on consecutive fires, corroboration, recording. |
| `tests/test_two_streams.py` | `engines/consciousness/sensation_engine.py` | no | 16 tests: Stream A/B synthesis with surprise scoring, tetrahedral sensation, conflict detection. |
| `tests/test_valence_tagged_slot.py` | `engines/cognition/valence_tagged_slot.py` (+ blackboard, eisenhower, phenomenology) | no | 45 tests: ValenceTaggedValue serialization, O(1) slot store, auto-tagging from CRITICAL_SLOT_VALENCE_RULES. |

## A.3 — `tests/gate/` (the v4 gate suite)

| path | gates-what | ORPHANED? | one line |
|---|---|---|---|
| `test_action_book.py` | `tools/build_action_book.py` + `engines/egocentric` | no | 17 tests: per-(game,action) semantics must be derived from recorded history, never authored; inverse pairs need real evidence-n. |
| `test_affect_gains.py` | `engines/egocentric/affect.py`, `fabric.py` | no | 5 tests: exactly two gain channels (seed-bias, mint-bar), bounded, replay-testable, narrated. |
| `test_affordance_harvest.py` | `cognitive_loop.py`, `engines/egocentric/frontier.py`, `fabric.py` | no | 13 tests: level-0 accrual un-gated, single write site, no double banking (CK-1b). |
| `test_agent_motion.py` | `engines/egocentric/router.py` + AGENT_MOTION predictor family | no | 9 tests: the family is earned only by self-propelled motion; constant-velocity and pursuit bets settle or carry residual. |
| `test_applicability_index.py` | `engines/egocentric/applicability` + `mint.py`, `fabric.py` | no | 13 tests: the anchor index must never prune a legal candidate; planner consults the filter before applying. |
| `test_backward_chaining.py` | `engines/egocentric/effects.py` (`invert_transform`), `planner.py` | no | 19 tests: Klein-group inverse per typed mechanism, round trips, backward chaining to identity. |
| `test_beat_rates.py` | `tools/beat_rates.py` | no | 20 tests: every rate prints its denominator; window boundaries; stalled-detection over two identical windows. |
| `test_bet_spine.py` | `engines/egocentric/betting.py`, `fabric.py` | no | 12 tests: the iced pricing spine — match-fraction scoring, hallucination penalty, settlements land with lineage. |
| `test_bracket_rt.py` | `tools/bracket_rt.py` | no | 14 tests: the R_T promote→seed→re-derive round trip; a seed must never carry atom content or playback. |
| `test_budget_restoration.py` | `cognitive_game_player.py` (role-scaled allowance) | no | 3 tests: replayed levels fund like live levels; ROLE_BASE_ATP multiplier is wired. |
| `test_class_fission.py` | `engines/egocentric/bank.py`, `binder.py` | no | 11 tests: bimodal settlement outcomes split a class once; discriminating feature named when findable. |
| `test_click_economy.py` | `engines/egocentric/spine.py` | no | 12 tests: credit the acted-on cell when no centroid exists; click drive needs no movement map. |
| `test_compat_old_books.py` | every `engines/egocentric` reader against a frozen old-schema fixture pack | no | 16 tests: sigma-less atoms, w-less settlements and the old import-queue triple must all still read. |
| `test_composer_notes.py` | `engines/egocentric/composer.py` note tokens | no | 15 tests: each compose-none token has exactly one note site; `notes={}` can no longer hide a branch. |
| `test_composer_stage1.py` | `engines/egocentric/applicability.py` psig + `mint.py` stamp sites | no | 13 tests: postcondition signature exact, psig stamped beside asig at all three mint write sites. |
| `test_composer_stage2.py` | `engines/egocentric/enables.py` + the mint's `act_offset` stamp | no | 13 tests: within-Γ ENABLES edges exact, act_offset stamped at the write site and never guessed on read. |
| `test_composer_stage3.py` | `engines/egocentric/composer.py` compose loop + `cognitive_loop._w3c_*` seams | no | 25 tests: compose runs only inside the W2b engage gate; composites enter as candidates, never citable. |
| `test_composer_stage4.py` | `composer.live_settle` / `settle_verdict` + `cognitive_loop._w3d_*` | no | 32 tests: one CANDIDATE→SETTLED transition, live-frame only, failure routed both ways, g7 asserted by identity. |
| `test_composer_stage45.py` | `composer.py`, `consumer.extent_bargain`, `applicability._derive_composite`, `observer`, `goal_abduction`, `perception` | no | 35 tests: the four silent successes at the seams between stages 1–4. |
| `test_conditional_effects.py` | `engines/egocentric/bank.py` ConditionalMiner + `router.py` | no | 9 tests: divergent outcomes under a remote state predicate emit EFFECT_IF; the buffer stays bounded. |
| `test_consumer_driver.py` | `engines/egocentric/consumer.py` `consume()` call site in `cognitive_loop` | no | 8 tests: the import queue actually drains at the episode boundary; the settle path swallows nothing. |
| `test_consumers.py` | static inventory over every production .py: written fabric topic ⇒ read outside its writer | no | 13 tests: the produced-but-never-consumed build gate, with an allowlist where each entry must cite a prereg and must be deleted when the consumer lands. |
| `test_context_min.py` | `tools/context_minimiser.py` + `mint.py` EXTENT_RATE | no | 17 tests: minimisation only ever drops what the evidence already disproved; rate-zero is byte-identical to pre-premium. |
| `test_corpse_guard.py` | `cognitive_game_player.py` corpse guard (needs `arcengine`, present in `.venv`) | no | 22 tests: never bank a terminal step, selection refuses a dead prefix, archive law, plus the CORPSE_GUARD=0 off-arm. |
| `test_cost_flip.py` | `cognitive_loop.py` + `engines/egocentric/latents.py` call sites | no | 14 tests: both live sites pass `cost_per_action=None`; below min-obs the estimator fails closed and flagged. |
| `test_credit_fallback.py` | `cognitive_loop.py` source (AST) | no | 2 tests: the credit branch keeps a pre-overwrite centroid and the bare-level mint exists — reads the real file. |
| `test_cross_wave_composition.py` | four cross-wave chains through bank/betting/effects/fabric/planner | no | 18 tests: IMPORT→VERIFY→PLAN, frontier veto over plan, object-typed inverse planning, fission-keyed settlement. |
| `test_d11_render_import.py` | `arc_api_adapter.install_headless_render_guard()` | no | 11 tests in fresh subprocesses: with the guard on, no matplotlib/fontTools module is ever imported. |
| `test_d8_instrument.py` | `cognitive_loop.py`, `decision_rung_system.py`, `rungs/base.py` fallback field | no | 26 tests: one field, no behaviour change — the router-fallback flag in both directions, byte-identity elsewhere. |
| `test_d9_diagnostic_gate.py` | `evolution_runner.py` SystemDiagnostic opt-in | no | 11 tests: flag absent ⇒ never constructed; flag read exactly once at init, never per generation. |
| `test_dead_dedup.py` | `engines/egocentric/frontier.py` dead-cell dedup + `WIRING_REGISTRY.md`/`KNOBS.md` rows | no | 21 tests: one episode clicking one cell five times banks one report; a cell needs two distinct records; off-arm. |
| `test_decline_branch.py` | `engines/egocentric/consumer` outcome enum + `effects.py` | no | 24 tests: DECLINED becomes expressible; not_found is strictly never matched-and-rejected. |
| `test_deploy_on_change.py` | `tools/swarm_supervisor.py` code fingerprint + HOLD | **PARTIAL** | 5 of 6 tests exercise `_fingerprint`, a copy of the mechanism defined inside the test file; only `test_the_real_supervisor_exposes_the_pieces` reads the shipped supervisor. |
| `test_discrepancy_planner.py` | `engines/egocentric/discrepancy.py`, `planner.py` | no | 9 tests: d is axis-wise and falsifiable; the planner spends against it or plans nothing. |
| `test_disk_ceiling_preserves.py` | `tools/disk_ceiling.py` | no | 4 tests: archive-then-truncate is a byte-identical round trip; claim-supporting paths are never touched. |
| `test_e2e_pipeline.py` | one synthetic episode through the real `CognitiveLoop` | no | 21 tests: every producer's output verified in the fabric afterwards — atoms, settlements, boundary books, narration. |
| `test_effect_atoms.py` | `engines/egocentric` EFFECT constructor + `fabric.py` | no | 11 tests: arity-two over time, canonical translation-invariant keying, the n=1 gate. |
| `test_efference_copy.py` | `engines/egocentric/binder.py` | no | 15 tests: predicted-change-mask subtraction replaces click-proximity attribution; the wire is live. |
| `test_efficiency_read.py` | `tools/efficiency_read.py`, `tools/wiring_receipts.py`, `WIRING_REGISTRY.md` | no | 31 tests: distance-to-that-player per game+level; unreached reference is not-measurable, never zero. |
| `test_egocentric_substrate.py` | `engines/egocentric/observer.py` + segmentation/tracking | no | 14 tests: contingent motion beats autonomous drift; cold start names nobody; the wiring is read-only. |
| `test_evidence_preserving_cleanup.py` | `safe_cleanup.py` | no | 4 tests: wins/level-completions/positive scores are kept forever; only old zero-evidence rows die. |
| `test_fabric_janitor.py` | `engines/egocentric/janitor.py` | no | 13 tests: compaction changes no consumer answer byte-for-byte; loud manifest every run. |
| `test_fabric_next_seq_cache.py` | `engines/egocentric/fabric.py` `_next_seq` | no | 24 tests: the high-water cache against an oracle across shrink, rewrite, out-of-band records and torn tails. |
| `test_fabric_read_cache.py` | `engines/egocentric/fabric.py` `_cached_stream` | no | 57 tests: parsed-stream cache — corpus edge cases, read counts, invalidation, boundedness, copy semantics. |
| `test_fabric_seq_cache.py` | `engines/egocentric/fabric.py` append path | no | 12 tests: append stops re-reading the whole stream and output stays byte-identical. |
| `test_frame_instruments.py` | `ruff` and `vulture` as subprocesses over `engines/egocentric`, `tools`, `tests/gate` | no | 2 tests; scope comes from `pyproject.toml [tool.ruff]` — both tools present in `.venv`. |
| `test_frame_normalisation.py` | `cognitive_game_player.py` frame normaliser | no | 4 tests: a multi-frame payload normalises to a grid; single-frame is unchanged; matches the banked evidence shape. |
| `test_frame_unwrap.py` | `engines/egocentric/perception.py`, `observer.py`, `engines/perception/perceiver.py` | no | 16 tests: a k-varying animation stack unwraps to the last grid on both paths. |
| `test_frontier_harvest.py` | `engines/egocentric/frontier.py`, `spine.py`, `fabric.py` | no | 14 tests: bank the experience not the death spot; untried remap; harvest written on both end kinds. |
| `test_frontier_pariah.py` | `engines/egocentric/frontier.py`, `spine.py` | no | 12 tests: a frontier death permanently removes an opening; nearest non-avoided remap; the preempt block vetoes. |
| `test_gate_stage1.py` | `engines/egocentric/grammar.py` + `gate.py` (shadow mode) | no | 64 tests: thirteen salvaged primes, nine heads, precedence, completeness, shadow never blocks. |
| `test_goal_abduction.py` | `engines/egocentric/goal_abduction.py`, `planner.py` | no | 26 tests: structural predicates mined at level-up; GoalBook credibility rises and falls; planner target mode. |
| `test_goal_spine.py` | `engines/egocentric/spine.py` | no | 11 tests: the wheel rule — confirmed reward earns the wheel, everything else is None. |
| `test_handoff_rate.py` | `cognitive_game_player.py` replay probability helper | no | 2 tests: bank-aware probability with exactly one RNG draw either way. |
| `test_hold_stops_recycles.py` | `tools/swarm_supervisor.py` HOLD semantics | no | 6 tests: HOLD defers the bounded-lifetime recycle and lifting it recycles exactly once. |
| `test_import_gate.py` | `engines/egocentric` import admission + `mint.EXTENT_RATE` | no | 8 tests: admission pays the same extent bargain the mint pays; no silent drops. |
| `test_integration_wiring.py` | `cognitive_loop.py` source (AST) — every producer's consumer named in code | no | 13 tests: binder feed, bank commit/settle, settlement routing, mint reach, import-queue persist, planner gating. |
| `test_knowledge_fabric.py` | `engines/egocentric/fabric.py` + the idea economy | no | 16 tests: JSONL scopes, monotonic seqs, read-only seed overlay, mint/echo/falsify economy. |
| `test_latents.py` | `engines/egocentric/latents.py`, `planner.py` | no | 12 tests: cost_per_action is a measured latent; the estimator is global, never game-conditioned. |
| `test_level0_harvest.py` | `engines/egocentric/frontier.py`, `spine.py` read sites | no | 6 tests: both read sites admit level 0, closing CK-1b's write/read asymmetry. |
| `test_level_conventions.py` | the playing-level vs completed-level register across every stream | no | 14 tests: which streams carry which convention, asserted in the source as well as the records. |
| `test_level_scoped_ideas.py` | `engines/egocentric/fabric.py` mint/priors level field | no | 9 tests: ideas carry the level their reward produced; seeding re-scopes on level change. |
| `test_lifecycle_cleanup.py` | `agent_lifecycle_manager.cleanup_ancient_inactive_agents` | no | 20 tests: the pre-fix FK-violating delete is the oracle; the fix deletes, leaves no orphan, and is loud on failure. |
| `test_link3_hook_and_vocabulary.py` | `cognitive_game_player.py`, `cognitive_loop.py`, the predicate vocabulary | no | 45 tests: `extract_predicates` returning 0 on every record, with the audit's binding ordering. |
| `test_lp_drive.py` | `engines/egocentric/lp_drive.py`, `affect.py`, `cognitive_loop.py` | no | 23 tests: three arms, fixed/random byte-identical to current, LP reweights toward the compressible site. |
| `test_lp_rotation.py` | the arm-rotation formula + `tools/swarm_supervisor.py` spawn | no | 8 tests: `sha1(game)+recycle_count mod 3`; every game visits every arm across three recycles. |
| `test_mastery_lite.py` | `engines/egocentric/mastery.py` | no | 9 tests: replay probability earned from replay reliability over a last-10 window; games independent. |
| `test_mdl_mint.py` | `engines/egocentric/mint.py` | no | 8 tests: SUPPORT × REACHABILITY × NOVELTY, accept iff the compression pays; every verdict recorded. |
| `test_mint_bootstrap.py` | `cognitive_loop.py` source (AST) | no | 3 tests: novel workspace evidence reaches the mint so the first atom can be born — reads the real file. |
| `test_move_affordances.py` | `engines/egocentric/frontier.py` `record_moves` | no | 14 tests: per-action changed/unchanged counts bias without vetoing; below the observation floor nothing is judged. |
| `test_movement_stack.py` | `engines/egocentric/agency.py`, `navigation.py`, `cognitive_loop.py` | no | 13 tests: CursorAgency + GridNav wired into the live path; the wall strip is never the cursor. |
| `test_mute_verdict.py` | `engines/egocentric/verdicts.py` | no | 5 tests: MUTE quarantines and answers with a deterministic discriminating probe. |
| `test_narration_arms.py` | `cognitive_loop.py`, `mint.py`, `router.py` under arms C and W | no | 29 tests: arm C's consumption must be real at two named decision points; the flip works both directions. |
| `test_narration_spine.py` | `cognitive_loop.py`, `router.py`, `fabric.py` | no | 23 tests: one bet-side record per step with bin, why-not-neighbour and memory range, emitted before the action. |
| `test_negative_feeder.py` | `engines/egocentric/starvation.py` neg_tried/neg_passed feed | no | 8 tests: the reserved counters are actually fed so NO_NEGATIVE_INSTANCES can fire. |
| `test_none_reasons.py` | `engines/egocentric/planner.py` `LAST_REASON` | no | 25 tests: a fixed bounded enum distinguishes nothing-arrived from arrived-and-rejected. |
| `test_object_transforms.py` | `engines/egocentric/effects.classify_object_transform` | no | 19 tests: one coherent object in clutter, relative shape signature, no false positives. |
| `test_origin_marker.py` | `engines/egocentric/mint.py` origin field + `tools/wiring_receipts.py` row | no | 25 tests: absence reads `unknown`, never `local`; composites stamped; mint_seq positional and increasing. |
| `test_persistence.py` | `engines/egocentric/persistence.py` + `cognitive_loop` seam | no | 36 tests: exactly-k firing, reset, non-repeating, consumer-only, no price reads it. |
| `test_plan_frontier_veto.py` | `engines/egocentric/frontier.py` at the PLAN DRIVE site | no | 10 tests: a banked fatal or merged-dead target is vetoed before the click; a vetoed drive falls back to shadow. |
| `test_plan_wire.py` | `cognitive_loop.py` source via `_ast_laws` | no | 2 tests: the seven [PLAN-GATE] counters sit in the EGO-PLAN region and stay out of `record_result`. |
| `test_planner_budget.py` | `engines/egocentric/planner.py` node budget | no | 5 tests: exploding branching returns None within the cap; small solvable cases solve identically. |
| `test_planner_retention.py` | `engines/egocentric/retention.py` + `cognitive_loop` | no | 38 tests: second call does less work, no leak across level change or fission, bounded, cold-vs-warm exact. |
| `test_planner_scheduling.py` | the W2b scheduler in `cognitive_loop.py` | no | 33 tests: the planner as last resort — starvation guard, no re-research of an unchanged world, abort routed. |
| `test_predictor_bank.py` | `engines/egocentric/bank.py` | no | 10 tests: one predictor per bound slot; a slot that can't bet isn't read. |
| `test_properties.py` | `effects.classify/invert_transform`, `starvation`, `fabric` (hypothesis) | no | 5 property tests over three pure surfaces; `hypothesis` is present in `.venv` and pinned in requirements-dev. |
| `test_qa_fixes_w4.py` | `engines/reasoning/symbolic_reasoning_engine.py`, `engines/cognition/cognitive_router.py`, `agency`, `bank`, `betting`, `effects`, `perception` | no | 19 regression tests for the four W4 routed fixes; the board-centre sentinel and scipy-free labelling. |
| `test_queue_characterization.py` | `engines/egocentric/consumer.py`, `lp_drive.py`, `mint.py` | no | 16 tests: an import-queue residual must be characterized (sigma + patches), not merely named. |
| `test_random_shadow.py` | `cognitive_loop.py` source (AST) | no | 1 test: no function-local `import random` may shadow the module — reads the real file. |
| `test_ranked_drain.py` | `engines/egocentric/consumer.py` drain order + registry/KNOBS rows | no | 19 tests: characterized records drain first; the off-arm is byte-identical to a FIFO reference. |
| `test_record_keeping.py` | `engines/egocentric/janitor.py`, `goal_abduction.py`, `fabric.py` | no | 14 tests: the janitor archives verbatim before it folds or strips; level-up frames persist; imported atoms keep source_game. |
| `test_refit_destination.py` | `engines/egocentric/router.py` refit stream | no | 5 tests; one of them (`test_the_bin_is_still_unreachable_in_production_and_this_test_says_so`) declares the gap it cannot close — that is honest, not orphaned. |
| `test_regen_series.py` | `tools/regen_series.py`, `tools/wiring_receipts.py` | no | 31 tests: within-fabric rho drift over time, no wall clock, bounded, with its registry row. |
| `test_replay_feed.py` | `cognitive_loop.py`, `observer.py`, `spine.py` | no | 6 tests: replayed actions teach observe-only and never credit or mint. |
| `test_replay_handoff.py` | `cognitive_game_player.py` source (AST) | no | 5 tests: the unconditional `return replay_result` is gone and the continuation budget is reduced by the replay. |
| `test_reset_discipline.py` | `cognitive_loop.py` `bump_episode` + reset counter | no | 11 tests: exactly one bump per boundary; the RESET-spam pattern is counted and narrated. |
| `test_residual_router.py` | `engines/egocentric/router.py` | no | 8 tests: every settled residual lands in exactly one of four bins, ordered by residual mass. |
| `test_rho.py` | `engines/egocentric` rho estimator | no | 16 tests: weighted Jaccard over atom signatures; n_eff formula and the collapse guard. |
| `test_rho_ladder_live.py` | the rho ladder's production callers + `WIRING_REGISTRY.md` | no | 15 tests: a persisted multi-rung record per pass; the partition case R1=0 but R2>0; the registry row flipped. |
| `test_rho_rungs.py` | `engines/egocentric` rho at three rungs | no | 18 tests: key-identity, frozen estimator, mag dropped at rung 2, rungs ordered. |
| `test_role_binder.py` | `engines/egocentric/binder.py` | no | 9 tests: BODY/WORKSPACE/REFERENCE/RESOURCE by invariance, never appearance; re-binds on level change. |
| `test_salient_prefix.py` | `cognitive_game_player.py` salient-prefix bank | no | 11 tests: playback channel only — no salient function touches a fabric stream (the membrane law). |
| `test_seed_bias_widening.py` | `engines/egocentric/affect.seed_gain` + `starvation`, `swallow` | no | 9 tests: starvation widens the seed bias multiplicatively within a cap; `gains()` keys stay exactly two. |
| `test_ship_clean.py` | production sources' import lists vs a pinned debt register | no | 4 tests: no pytest/hypothesis/ruff/vulture/pydantic/requests in production code; the register never grows. |
| `test_sigma_backfill.py` | `tools/sigma_backfill.py` | no | 11 tests: patch-derived sigma equals mint-time sigma; the rewrite is atomic and idempotent; refuses while workers are alive. |
| `test_soak_bounded.py` | 320 steps through the real loop's EGO result path | no | 16 tests: no exception storm, boundary books bounded, miner/seen-map/swallow-note bounded, fabric growth linear. |
| `test_sprint_keeper.py` | `tools/sprint_keeper.py`, `tools/fleet_env.py`, `tools/swarm_supervisor.py` | no | 21 tests: the relaunch-only watchdog — token-exact game substitution, whole-token liveness, spawn once on absence. |
| `test_standing.py` | `engines/egocentric/standing.py`, `planner._candidate_ids`, scheduler | no | 52 tests: the event fold, population-derived decay, Tukey fence, one eviction/re-entry writer; also the figure laws. |
| `test_starvation_codes.py` | `engines/egocentric/starvation.py`, `affect.py` | no | 16 tests: a fixed game-agnostic enum; at most one record per socket; residual not grade. |
| `test_surprise_weighting.py` | `engines/egocentric/mint.py` repetition decay | no | 5 tests: n identical repetitions fall below n distinct; the seen map stays bounded. |
| `test_swallow_counters.py` | `engines/egocentric/swallow.py` + `cognitive_loop` boundary | no | 14 tests: a fixed block enum, ≤1 enum-coded record per block, settled at end_game. |
| `test_symbol_receipts.py` | `tools/wiring_receipts.py` + `WIRING_REGISTRY.md` + the AST laws | no | 29 tests: a receipt only a line shift can break is not a check — insertion invisible, removal not, order real. |
| `test_system_determinism.py` | one full episode through the real `CognitiveLoop`, twice | no | 7 tests: byte-identical fabric writes, identical narration, no wall-clock-shaped fields. |
| `test_tail_read.py` | `engines/egocentric/affect._recent_settlements` tail read | no | 36 tests: an O(tail) read byte-identical to the O(stream) one across every malformed-file case. |
| `test_torn_writes.py` | every `engines/egocentric` reader against half-written JSONL | no | 17 tests: fabric, consumer, planner, book writers and janitor all skip a torn line and read the rest. |
| `test_trace_writer.py` | `game_player.GamePlayer._record_action_trace` | no | 7 tests: budget_total/budget_spend filled at the moment of the write; frames exact; old rows untouched. |
| `test_triangulation_consumer.py` | `engines/egocentric/consumer.py` + sigma at mint time | no | 31 tests: signature-first recognition, sigma persisted before any match, kin-echo law, seed imports. |
| `test_typed_transforms.py` | `engines/egocentric/effects.classify_transform` | no | 14 tests: each mechanism named exactly; a typed TRANSLATE fires where the raw exact-context fallback cannot. |
| `test_u2_checkpoint_retention.py` | `safe_cleanup.py` frontier-checkpoint path | no | 6 tests: archive all rows then truncate; structurally no score predicate in the deletion path. |
| `test_vectorised_scan.py` | `engines/egocentric` anchor scan | no | 13 tests: the vectorised scan is invisible except in time — byte-identical including the None case. |
| `test_verdict_reason.py` | `engines/egocentric/mint.py` verdict reason field | no | 14 tests: every verdict names its deciding clause; the failed list is complete and reason-first. |
| `test_verdict_stamps.py` | `engines/egocentric/mint.py` ep + sigma on verdicts, `tools/bracket_rt.py` | no | 16 tests: every verdict kind carries when and what-it-looked-like; old books still read. |
| `test_verified_hydration.py` | `cognitive_loop.py` + planner DRIVE gate | no | 3 tests: a fresh loop hydrates TRANSFERRED counts from the books instead of an empty in-memory dict. |
| `test_wiring_registry.py` | `tools/wiring_receipts.py` + `WIRING_REGISTRY.md` | no | 19 tests: the registry parses, statuses/dates valid, every claimed symbol still defined and referenced from production. |

---

# PART B — the non-.py surface

`reached-by` records HOW, with the site. "OPENED" means a code path resolves the path and reads the
bytes; "CITED" means the filename appears in a docstring or comment in live code — a real dependency
for a reader, but nothing breaks at runtime if the file moves.

## B.1 — `architecture/` (25 files, no .py)

| path | dest | reached-by (with site) | one line |
|---|---|---|---|
| `architecture/Autonomous Research Lab.md` | live | CITED — `lab/__init__.py:2` ("See architecture/Autonomous Research Lab.md for full specification") | The spec for the self-running research loop that `lab/` implements: sacred branches, the trial→theorise→modify→review cycle, the merge gate. |
| `architecture/baseline_profile.json` | live | STRING — `manual_tools/profile_baseline.py:343` (argparse `default="architecture/baseline_profile.json"`) | 30KB profiler output: `meta`, `summary`, `rung_profiles`, `context_slot_hotspots` — read back by the same tool as the comparison baseline. |
| `architecture/rung_dependency_matrix.json` | live | STRING — `manual_tools/infer_answerable_by.py:304` (argparse default) and `manual_tools/profile_baseline.py:278` (`PROJECT_ROOT / "architecture" / ...`) | 28KB: `rungs`, `slot_index`, `dependency_edges` — the machine-readable rung/slot dependency graph, genuinely loaded. |
| `architecture/ci-pycache-testing.md` | preserve | NONE | The written form of the no-`__pycache__` law that `pytest.ini` + `tests/conftest.py:pytest_sessionfinish` actually enforce — the rule is live even though the document is uncited. |
| `architecture/cognitive_routing_architecture.md` | live | CITED — `README.md` | v1.1, status IMPLEMENTED: the reference document for `engines/cognition/` Phases 0–11, the stack `tests/test_blackboard.py` … `tests/test_valence_tagged_slot.py` gate. |
| `architecture/cognitive_routing_addon_dual_matrix_phenomenology.md` | preserve | NAMED-ONLY — appears in `README.md` and `record/findings/CODEBASE_INVENTORY.md`; no code reads it | Marked PROPOSAL, but Phases 8–11 shipped (`eisenhower_layer.py`, `phenomenology_layer.py`, `valence_tagged_slot.py` all exist and are tested) — this is the design record for live code. |
| `architecture/runtime/README.md` | live | CITED — `manual_tools/utilities/run_context.py:9` ("Fields align with architecture/runtime/README.md and events.md") | The INIT/STEP/POST_STEP/FINALIZE loop-split and RunContext contract. |
| `architecture/runtime/events.md` | live | CITED — `event_bus.py:13` ("Events and payload expectations mirror architecture/runtime/events.md") | Authoritative event payload schemas and guard codes for the bus that `evolution_runner.py:55` and `game_player.py:31` import at module level. |
| `architecture/runtime/side-effects-map.md` | preserve | NAMED-ONLY — `architecture/traceability/README.md` | The `play_single_game` side-effect inventory mapped to plugins/events — the migration map for a refactor that is only partly landed. |
| `architecture/data-contracts/README.md` | preserve | NAMED-ONLY — the `README.md` string match at `run_context.py:9` / `cleanup_temp_files.py:129` is a bare-basename false positive; the real citation is `architecture/traceability/README.md` | The additive data spine (`attempts`, guard results, w_A/w_B/w_R); `attempts` does appear as an FK target in `complete_database_schema.sql:353`, so this landed in part. |
| `architecture/data-contracts/migrations.md` | preserve | NAMED-ONLY — `architecture/traceability/README.md` | Ordered SQL sketches for the additive schema changes; do-not-drop discipline. |
| `architecture/nfrs/README.md` | preserve | NAMED-ONLY — `architecture/traceability/README.md` | Non-functional requirements mapped to the airline-grade reliability stance. |
| `architecture/reliability/README.md` | preserve | NAMED-ONLY — `architecture/traceability/README.md` | Failure modes and playbooks; the "no silent failure ⇒ HOOK_FAILURE_DETECTED + stack_hash" principle the swallow-counter gate later re-derived independently. |
| `architecture/traceability/README.md` | preserve | NAMED-ONLY — `manual_tools/README.md`, `record/findings/CODEBASE_INVENTORY.md` | The hub: maps every architectural concept to an owning module. It is the only thing citing five of the docs above. |
| `architecture/traceability/adr-index.md` | preserve | NAMED-ONLY — `architecture/traceability/README.md` | ADR index (PROPOSED/ACCEPTED/REVISIT); ADR-001 is the event-bus decision that `event_bus.py` implements. |
| `architecture/ARC-API-TOOLKIT-DOCS/ACTION6_REFERENCE.md` | preserve | NONE | Vendor reference for the parameterised coordinate action — external documentation, not reproducible from this tree. |
| `architecture/ARC-API-TOOLKIT-DOCS/arcade.md` | preserve | NONE | Vendor toolkit doc (Arcade class). |
| `architecture/ARC-API-TOOLKIT-DOCS/close-scorecard.md` | preserve | NONE | Vendor API doc. |
| `architecture/ARC-API-TOOLKIT-DOCS/create-scorecard.md` | preserve | NONE | Vendor API doc. |
| `architecture/ARC-API-TOOLKIT-DOCS/environment-wrapper.md` | preserve | NONE | Vendor toolkit doc (EnvironmentWrapper). |
| `architecture/ARC-API-TOOLKIT-DOCS/get-scorecard.md` | preserve | NONE | Vendor API doc. |
| `architecture/ARC-API-TOOLKIT-DOCS/list-available-actions.md` | preserve | NONE | Vendor API doc. |
| `architecture/ARC-API-TOOLKIT-DOCS/list-games.md` | preserve | NONE | Vendor API doc. |
| `architecture/ARC-API-TOOLKIT-DOCS/quickstart.md` | preserve | NONE | Vendor quickstart — the offline copy of the toolkit docs the adapter was written against; `arc_agi` 0.9.9 is the pinned version in `.venv`. |
| `architecture/ARC-API-TOOLKIT-DOCS/render-games.md` | preserve | NONE | Vendor doc for the renderer — the same `arc_agi.rendering` that `test_d11_render_import.py` exists to keep out of headless workers. |

## B.2 — `checklists/` (9 files, no .py)

All nine are agent-role checklists split out of `.github/copilot-instructions.md`, each carrying the
"Absorbs: copilot-instructions Part N" provenance line. All nine are named by that file at
`.github/copilot-instructions.md:72–122` as the operating procedure for a named role. `.`-prefixed
directories are out of scope for moves but they are a real reader, so these are **live**.

| path | dest | reached-by (with site) | one line |
|---|---|---|---|
| `checklists/branch_breeder.md` | live | NAMED — `.github/copilot-instructions.md:103` | Procedure for combining winning branches. |
| `checklists/code_modifier.md` | live | NAMED — `.github/copilot-instructions.md:86` | Procedure for turning a hypothesis into a branch. |
| `checklists/code_reviewer.md` | live | NAMED — `.github/copilot-instructions.md:89` | Review procedure before a branch is admitted. |
| `checklists/code_tracer.md` | live | NAMED — `.github/copilot-instructions.md:74` | Procedure for producing execution traces from a trial. |
| `checklists/comparative_analyst.md` | live | NAMED — `.github/copilot-instructions.md:75` | Procedure for comparing arms and producing findings. |
| `checklists/evolution_runner.md` | live | NAMED — `.github/copilot-instructions.md:72` | Trial-running procedure; carries the immutable "never mock the API" rule. |
| `checklists/orchestrator.md` | live | NAMED — `.github/copilot-instructions.md:13` | The loop manager's checklist; venv verification, measurement over guessing. |
| `checklists/theorist.md` | live | NAMED — `.github/copilot-instructions.md:83,122` | Hypothesis-generation procedure; absorbs the theoretical-foundation and PTMA parts. |
| `checklists/trend_tracker.md` | live | NAMED — `.github/copilot-instructions.md:76` | Procedure for maintaining the cross-trial trend record. |

## B.3 — `config/` (4 .json; one .py noted below)

| path | dest | reached-by (with site) | one line |
|---|---|---|---|
| `config/rung_orderings.json` | live | OPENED — `decision_rung_system.py:549` (`self.config_path = config_path or str(Path(__file__).parent / 'config' / 'rung_orderings.json')`) | 3KB of named rung orderings (`experimental_curiosity_first`, `minimal_fear`, `maximum_caution`, `network_learner`) loaded by the decision system at construction. |
| `config/transition_responses.json` | live | OPENED — `engines/cognition/cognitive_router.py:194` (`_Path(__file__).resolve().parents[2] / "config" / "transition_responses.json"`), consumed at import via `TRANSITION_RESPONSES = _load_transition_responses()` | 5KB quadrant-transition → algorithm map; the router logs a warning and falls back to hardcoded defaults if it is missing, so a move degrades silently rather than crashing. |
| `config/question_taxonomy.json` | live | STRING — `manual_tools/infer_answerable_by.py:301` (argparse `default="config/question_taxonomy.json"`) | 30KB: `questions`, `slot_to_questions`, `rung_to_questions`, `category_counts` — the question taxonomy the answerable-by inference tool consumes. |
| `config/cognitive_edges.json` | **considered_dead** | **NONE** — the only occurrence of the name anywhere in the tree is the comment `engines/cognition/blackboard.py:346` "Static weight from cognitive_edges.json". No `open`, no `json.load`, no path construction reaches it. | 24KB of `edges`, `edge_statistics`, `subgraph_clusters`, `critical_paths` — a full static cognitive-edge graph that no code loads. See the note below; this is a preserve candidate if the GM wants the graph, but as of today it is a file the code only talks *about*. |

Note (out of my slice, recorded because it is in this directory): `config/cognitive_parameters.py` is
the one .py under `config/`. It is imported by `tests/test_eisenhower_layer.py` and named in
`tests/gate/test_ship_clean.py:59`; classification belongs to the .py examiner.

## B.4 — `figures/` (11 files, no .py) — canon

All eleven are git-tracked SVGs, referenced as a set (not individually) from
`tests/gate/test_standing.py:45` and `:836` — "THE LAWS (figures/\*.svg via
record/corpus/FIGURES_TEXT_DIGEST.md)". The digest is what the test actually reads; the SVGs are the
source of truth behind it. Confirmed canon, **live**.

| path | dest | reached-by (with site) | one line |
|---|---|---|---|
| `figures/Figure_1_The_Agent_REV3.svg` | live | NAMED as a set — `tests/gate/test_standing.py:45,836`; text in `record/corpus/FIGURES_TEXT_DIGEST.md` | Law diagram 1 — the agent. |
| `figures/Figure_2_The_Ground_REV (1).svg` | live | same | Law diagram 2 — the ground. Filename carries a literal `" (1)"`; any tooling that globs on it must quote. |
| `figures/Figure_3_Dependency_Chain_REV.svg` | live | same | Law diagram 3 — the dependency chain. |
| `figures/Figure_4_The_Membrane.svg` | live | same | Law diagram 4 — the membrane (the law `test_salient_prefix.py` enforces in code). |
| `figures/Figure_5_The_Mint_Pipeline_REV.svg` | live | same | Law diagram 5 — the mint pipeline. |
| `figures/Figure_6_Closure_Reachability_REV.svg` | live | same | Law diagram 6 — closure reachability. |
| `figures/Figure_7_The_Room_Chain_REV.svg` | live | same | Law diagram 7 — the room chain (C33). |
| `figures/Figure_8_The_Union_Surplus.svg` | live | same | Law diagram 8 — the union surplus. |
| `figures/Figure_9_Leave_Arrive_Search.svg` | live | same | Law diagram 9 — leave/arrive/search; the figure `test_queue_characterization.py` cites as FIG-9. |
| `figures/Figure_10_The_Ground_Maintainer.svg` | live | same | Law diagram 10 — the ground maintainer. |
| `figures/Figure_11_The_Habitat.svg` | live | same | Law diagram 11 — the habitat. |

## B.5 — `models/` (1 file, no .py)

| path | dest | reached-by (with site) | one line |
|---|---|---|---|
| `models/dynamics_model.pt` | live | STRING — `representation_learner.py:227` (`self.model_path = model_path or "models/dynamics_model.pt"`) | 7.4MB git-tracked torch checkpoint for `DynamicsModel`; loaded if present, a fresh model is built if not, and the whole path is inert when `TORCH_AVAILABLE` is false. `pyrightconfig.json` includes `models/**/*.py` — a dead include, there are no .py here. |

## B.6 — loose top-level (35 files)

### The 26 root markdown files

25 of 26 are cited by name from .py, at ~100 sites. Two are additionally **opened and parsed**.

| path | dest | reached-by (with site) | one line |
|---|---|---|---|
| `WIRING_REGISTRY.md` | live | **OPENED** — `tools/wiring_receipts.py:92` (`DEFAULT_REGISTRY`), `tools/live_coverage_diff.py:55`; plus six gate tests that parse it (`test_wiring_registry.py:102`, `test_symbol_receipts.py:73`, `test_ranked_drain.py:294`, `test_origin_marker.py:305`, `test_regen_series.py:366`, `test_rho_ladder_live.py:279`, `test_efficiency_read.py:344`); CITED from `cognitive_loop.py:4742`, `engines/egocentric/composer.py:113` | Not a document — a machine-parsed data file. 12 .py sites. Moving it breaks two tools and seven tests. |
| `KNOBS.md` | live | **OPENED** — `tests/gate/test_dead_dedup.py:336`, `test_ranked_drain.py:309`, `test_planner_retention.py:358`; CITED from `cognitive_loop.py:57`, `evolution_runner.py:212`, `engines/egocentric/persistence.py:86`, `router.py:36`, `tools/beat_rates.py:170` | The knob/amendment register; three gate tests read it as the authority for what a knob means. 11 .py sites. |
| `THE_LADDER.md` | live | CITED — 8 .py sites: `tools/efficiency_read.py:11`, `tools/regen_series.py:3`, `tests/gate/test_consumers.py:48`, `test_decline_branch.py:3`, `test_efficiency_read.py:4`, `test_ranked_drain.py:3`, `test_regen_series.py:3`, `test_wiring_registry.py:1` | The rung ladder and the currency rule (levels_completed); the standard `test_wiring_registry.py` enforces. |
| `CLAIM.md` | live | CITED — 7 .py sites: `cognitive_game_player.py:1491`, `engines/egocentric/consumer.py:58`, `effects.py:63`, `tests/gate/test_corpse_guard.py:26`, `test_dead_dedup.py:19`, `test_origin_marker.py:1`, `test_ranked_drain.py:17` | The binding ablation clause — every ranked/guarded build ships a passing off-arm because this file says so. |
| `PREREG_FINAL_GAPS.md` | live | CITED — 7 .py sites: `engines/egocentric/consumer.py:62`, `goal_abduction.py:1`, `lp_drive.py:1`, `rho.py:1`, `tests/gate/test_goal_abduction.py:1`, `test_lp_drive.py:1`, `test_rho.py:1` | Prereg for G-A/G-B/G-C/G-D: the rho estimator, the R_T bracket, goal abduction, the LP drive. |
| `PREREG_DRAIN_ORIGIN.md` | live | CITED — 6 .py sites: `engines/egocentric/consumer.py:47`, `effects.py:63`, `mint.py:77`, `tests/gate/test_origin_marker.py:1`, `test_ranked_drain.py:1`, `test_triangulation_consumer.py:198` | Prereg §A ranked drain + §B origin marker. |
| `PREREG_READOUTS.md` | live | CITED — 6 .py sites: `cognitive_loop.py:1004`, `engines/egocentric/affect.py:148`, `starvation.py:1`, `tests/gate/test_consumers.py:1`, `test_starvation_codes.py:1`, `tools/socket_or_filler_lint.py:1` | Prereg R1 (starvation codes) + R3 (produced-but-never-consumed). |
| `PREREG_PHASE2.md` | live | CITED — 4 .py sites: `cognitive_loop.py:1497`, `engines/egocentric/spine.py:4`, `tests/gate/test_goal_spine.py:8`, `tools/verify/hermetic.py:137` | Prereg for the goal spine and the wheel rule. |
| `PERF_AUDIT.md` | live | CITED — 3 .py sites: `engines/egocentric/affect.py:88`, `fabric.py:130`, `tests/gate/test_tail_read.py:3` | The performance audit; Q4 is the tail-read defect, cited with line numbers (`PERF_AUDIT.md:21-41`). |
| `PREREG_CK_WAVE1.md` | live | CITED — 3 .py sites: `cognitive_game_player.py:764`, `cognitive_loop.py:2728`, `tests/gate/test_affordance_harvest.py:1` | Prereg for CK-1a/CK-1b/CK-2: typed transforms, harvest un-gating, efference copy. |
| `PREREG_FRONTIER_HARVEST.md` | live | CITED — 3 .py sites: `cognitive_game_player.py:763`, `engines/egocentric/frontier.py:133`, `tests/gate/test_frontier_harvest.py:9` | Prereg 3d-ii: bank the experience, not the death spot. |
| `PREREG_REFIT_DESTINATION.md` | live | CITED — 3 .py sites: `cognitive_loop.py:2521`, `tests/gate/test_consumers.py:74`, `test_refit_destination.py:1` | Prereg: the BROKEN-rebinding bin needs a destination stream. |
| `VICTORY_PROTOCOL.md` | live | CITED — 3 .py sites: `engines/egocentric/janitor.py:33`, `tests/gate/test_consumers.py:20`, `test_record_keeping.py:1` | The record-keeping protocol: what costs nothing now is unrecoverable later — archive before you fold. |
| `EGOCENTRIC_PORT_PLAN.md` | live | CITED — 2 .py sites: `engines/egocentric/spine.py:4`, `tests/gate/test_goal_spine.py:4` | The porting plan for the egocentric substrate; §7 is the wheel rule. |
| `PREREG_CORPSE_GUARD.md` | live | CITED — 2 .py sites: `cognitive_game_player.py:428`, `tests/gate/test_corpse_guard.py:1` | Prereg for the corpse guard (F-1 of the frontier audit). |
| `PREREG_DEAD_DEDUP.md` | live | CITED — 2 .py sites: `engines/egocentric/frontier.py:21`, `tests/gate/test_dead_dedup.py:1` | Prereg for the dead-cell dedup and its off-arm (audit F-3). |
| `PREREG_FRONTIER_PARIAH.md` | live | CITED — 2 .py sites: `engines/egocentric/frontier.py:1`, `tests/gate/test_frontier_pariah.py:9` | Prereg 3d-i: fatal openings are banked and permanently avoided. |
| `PREREG_MARKETPLACE_MERGE.md` | live | CITED — 2 .py sites: `engines/egocentric/betting.py:1`, `tests/gate/test_bet_spine.py:8` | Prereg for merging the betting marketplace into the spine. |
| `PREREG_MASTERY_LITE.md` | live | CITED — 2 .py sites: `cognitive_game_player.py:101`, `engines/egocentric/mastery.py:3` | Prereg: replay probability earned from replay reliability. |
| `PREREG_PHASE1.md` | live | CITED — 2 .py sites: `engines/egocentric/observer.py:15`, `tests/gate/test_egocentric_substrate.py:8` | Prereg for the egocentric perception substrate. |
| `PREREG_PHASE3A.md` | live | CITED — 2 .py sites: `engines/egocentric/fabric.py:1`, `tests/gate/test_knowledge_fabric.py:9` | Prereg for the knowledge fabric and the idea economy. |
| `PREREG_SMART_CLEANUP.md` | live | CITED — 2 .py sites: `engines/egocentric/janitor.py:1`, `tests/gate/test_fabric_janitor.py:3` | Prereg B14: size-triggered, loud, compaction-not-deletion. |
| `THE_GOALS.md` | live | CITED — 2 .py sites: `tools/efficiency_read.py:5`, `tests/gate/test_efficiency_read.py:3` | The seat-2 sequencing list; ITEM-2 is the efficiency read. |
| `PREREG_BUDGET_RESTORATION.md` | live | CITED — 1 .py site: `cognitive_game_player.py:241` | Prereg: replayed levels fund like live levels; roles scale allowances. |
| `PREREG_D3_VERIFIER.md` | live | CITED — 1 .py site: `safe_cleanup.py:2268` | Prereg for the D3 verifier inside the cleaner. |
| `README.md` | live | STRING (weak) — the two .py hits (`manual_tools/utilities/cleanup_temp_files.py:129`, `run_context.py:9`) are bare-basename false positives; genuinely referenced from `requirements.txt` context and as the repo's front door | The project overview: four subsystems, the foundational-paper link, the ARC-AGI acknowledgment. Live as the entry document, not as a code dependency. |

### The 9 non-markdown loose files

| path | dest | reached-by (with site) | one line |
|---|---|---|---|
| `complete_database_schema.sql` | live | OPENED — 12 .py sites incl. `database_interface.py:96` (schema init), `database_logger.py:164`, `schema_auto_maintenance.py:33`, `agent_lifecycle_manager.py:333`, `engines/cognition/epistemic_logging.py:44`, `tests/test_database_interface.py:52`, `tools/consumption_sweep.py:94` | 281 `CREATE TABLE` statements — the authoritative schema every fresh database is built from. The single most load-bearing non-.py file in the tree. |
| `core_data.db` | live | OPENED — ~100 .py sites; the default `db_path` almost everywhere (`database_interface.py:31`, `evolution_runner.py:246`, `engines/registry.py:22`, `engines/__init__.py:25`, `safe_cleanup.py:165`, `tests/conftest.py` `MAIN_DB_PATH`, …) | 9.5MB SQLite production database. **Not git-tracked** — it exists only on this box, and `tests/conftest.py:MAIN_DB_PATH` points every db-fixture at it. |
| `core_data.db-wal` | live | OPENED — implicitly by every sqlite connection (WAL mode is set in `database_interface.py`); named explicitly at `tests/gate/test_disk_ceiling_preserves.py:137` (`test_wal_is_measured_but_not_budgeted`) | 3.8MB write-ahead log. Live sqlite artifact, not a document; deleting it while a connection is open loses committed data. |
| `core_data.db-shm` | live | OPENED — sqlite shared-memory index for the WAL; no source names it | 32KB sqlite runtime artifact; exists only while the database is attached. |
| `pyproject.toml` | live | OPENED — `tests/gate/test_frame_instruments.py` runs `ruff check` from the repo root, which reads `[tool.ruff]` include/per-file-ignores from here; cited at `test_frame_instruments.py:3` | The house code-law: ruff scope is `engines/egocentric/`, `tools/`, `tests/gate/`, with per-file-ignores encoding the blanket-containment rule. A gate test fails if this moves. |
| `pytest.ini` | live | OPENED — pytest itself (`testpaths = tests`, `--import-mode=importlib`, `filterwarnings = error`) | The suite's own configuration; `filterwarnings = error` is why `test_phase6_production.py` can assert on deprecation warnings. |
| `requirements.txt` | live | STRING — `manual_tools/utilities/cleanup_temp_files.py:117` lists it as a protected TIER-2 file; referenced from `README.md` | Runtime dependency pins: python-dotenv, aiohttp, numpy, pandas, and the official ARC-AGI-3 SDK. |
| `requirements-dev.txt` | live | NAMED-ONLY — `record/findings/BUILD_PROGRAM_2.md`; no code reads it | The five dev pins (hypothesis 6.165.7, numpy 2.5.1, pytest 9.1.1, ruff 0.16.3, vulture 2.16) — all five are what `.venv` actually has, and `test_ship_clean.py` exists precisely to keep them out of production imports. |
| `pyrightconfig.json` | **considered_dead** | **NONE** — no .py, .md, .json, .toml or .yaml in the tree names it; no CI task invokes pyright; `pyright` is not in `.venv` or in `requirements-dev.txt` | Pyright config with `"typeCheckingMode": "off"` and every meaningful report suppressed — a type-checker configuration that disables type checking, for a checker that is not installed. Its `include` also lists `models/**/*.py`, a directory with no .py in it. |

## B.7 — courtesy rows: non-.py inside my own directory (6 files)

| path | dest | reached-by (with site) | one line |
|---|---|---|---|
| `tests/README.md` | preserve (needs correction, not a move) | NAMED-ONLY — `manual_tools/README.md`, `record/findings/CODEBASE_INVENTORY.md`; the `.py` hits are bare-basename false positives | A five-row table of "Test Files" of which **three do not exist at this path**: `test_critical_systems.py` and `test_recent_changes.py` now live in `legacy/tests_dead_lineage/`, and `test_new_modules.py` exists nowhere in the tree. It also omits all 124 `tests/gate/` files. It documents a suite that has not existed for some time. |
| `tests/gate/fixtures/old_books/collective/atoms.jsonl` | live | OPENED — `tests/gate/test_compat_old_books.py` (`test_the_pack_exists`, `test_old_atoms_carry_no_new_era_fields`, `test_gamma_loads_and_applies_a_sigma_less_atom`) | The frozen pack's atom stream: real earlier-era record shapes, deliberately sigma-less, proving new readers still read old books. |
| `tests/gate/fixtures/old_books/collective/settlements.jsonl` | live | OPENED — `test_compat_old_books.py` (`test_old_settlements_and_verdicts_carry_no_w`) | Frozen pre-`w` settlement records. |
| `tests/gate/fixtures/old_books/collective/mint_verdicts.jsonl` | live | OPENED — `test_compat_old_books.py` (same test) | Frozen pre-`ep`/pre-`sigma` mint verdicts; the shapes `test_verdict_stamps.py::TestOldBooksCompat` also has to tolerate. |
| `tests/gate/fixtures/old_books/collective/import_queue.jsonl` | live | OPENED — `test_compat_old_books.py` (`test_import_queue_entries_are_the_old_triple`) | The pre-characterization import-queue triple, before sigma and patches were added. |
| `tests/gate/fixtures/old_books/collective/frontier_harvest.jsonl` | live | OPENED — `test_compat_old_books.py` (`test_fabric_query_returns_records_for_every_old_stream`) | Frozen frontier-harvest records for the old-books query sweep. |

Caution recorded, not a claim: `.gitattributes` is `* text=auto`, so git normalises line endings on
these five committed `.jsonl` files at checkout. `test_compat_old_books.py` parses them as JSON per
line and is insensitive to that; but this is a committed *frozen* pack whose whole point is that its
bytes do not move, and `text=auto` means git decides its bytes, not the pack. Nothing in the suite
asserts byte-identity against these files today.

---

# TESTS THAT GATE NOTHING

Three files, 119 test functions between them, that cannot fail because of anything in the production
tree. This is the same family as the 28-of-109 registry receipts that never pointed at their own
symbol: the mechanism of the check is intact, the check is attached to nothing.

They are distinguishable from the honest source-scanning gates (`test_consumers.py`,
`test_integration_wiring.py`, `test_mint_bootstrap.py`, `test_random_shadow.py`,
`test_credit_fallback.py`, `test_replay_handoff.py`, `test_ship_clean.py`), which also declare no
module-level project imports — but those **open real files** (`cognitive_loop.py`,
`cognitive_game_player.py`, `tools/swarm_supervisor.py`, or every production .py by `os.walk`) and
assert against their AST. Delete the subject and those go red. Delete the subject of the three below
and nothing happens.

### 1. `tests/test_sequence_system.py` — 35 tests, 824 lines

**The subject that no longer exists:** the sequence storage/retrieval system. The docstring says it
"validates the critical sequence storage and retrieval functionality that enables knowledge sharing
between agents across generations". The file imports `asyncio, json, os, sqlite3, sys, tempfile,
unittest, dataclasses, datetime, typing, unittest.mock` — **and nothing from this project**.

What it actually tests is `MockDatabaseInterface`, defined at line 58 of the test file itself: a
hand-written class whose `execute_query` does substring matching on SQL text
(`if "select" in query_lower and "winning_sequences" in query_lower: ...`) and returns dicts it was
handed. `TestSequenceStorage`, `TestSequenceRetrieval`, `TestSequenceReplay`,
`TestLevelNumberTracking`, `TestSequenceValidation`, `TestDatabaseSchemaIntegrity`,
`TestSequenceSystemIntegration` all run against that mock. `MockGameState` is likewise local.
The real sequence machinery — `winning_sequences`, `action_traces`, `level_sequence_usage`,
`sequence_reputation` — is never imported, so the tests hold whatever those tables and their writers
do.

**Note it is also the file `tests/README.md` marks "Priority: HIGH".**

### 2. `tests/test_reasoning_data_usage.py` — 48 tests, 724 lines

**The subject that no longer exists:** the "reasoning log data usage improvements" — available-action
change detection, win-validated hypothesis prioritisation, frame-changes→self-model learning, network
bootstrap, genome fetch, emotional-state computation. The docstring names all thirteen. The file
imports `os, sys, json, unittest.mock, pytest` — **and nothing from this project**. `re` is imported
inside six test bodies.

Every assertion is against logic re-typed into the test. `test_detects_new_actions_after_click`
builds `previous = {5,6,7}` and `current = {1,2,3,4,5,6,7}` and asserts
`current - previous == {1,2,3,4}` — Python set subtraction, not the agent's detector.
`test_action_direction_mapping` builds a four-entry dict inside the test and asserts one of its
values. `test_parses_movement_from_frame_change` writes its own `re.search(r'color_(\d+)', ...)`
against its own string. The two production names that appear anywhere in the file — `rule_engine`
(line 185) and `sensation_engine` (line 189) — are inside string literals, not calls.

### 3. `tests/test_reasoning_system_fixes.py` — 36 tests, 587 lines

**The subject that no longer exists:** the "Reasoning System Overhaul" fixes — emergent-reasoning
bootstrap and fallback, CODS-guided escape, win-strategy recording, stuck-point recording, the CODS
adaptive threshold. The file imports `json, os, sqlite3, sys, typing, unittest.mock, pytest` —
**and nothing from this project**.

Its three fixtures (`mock_db`, `mock_game_state`, `mock_cods_engine`) are `MagicMock`s configured in
the fixture body with the exact values the tests then assert on — e.g. `mock_cods_engine` is given
`suggest_action` returning `{'action': 1, 'confidence': 0.45, ...}` and the tests check that
confidence. The fixture's own docstring concedes the drift: *"Named 'mock_cods_engine' for backward
compatibility but actually mocks PrimitiveSuggester behavior."* The engine it is named for is gone;
the mock outlived it, and so did 36 tests. `TestEmergentReasoningBootstrap` says in a comment
"Import the method we're testing" and then does not import it.

## Two more that partly gate nothing (kept separate — the subject does exist)

### `tests/gate/test_deploy_on_change.py` — 5 of 6 tests assert on a copy

`_fingerprint(root, skip)` is defined at line 30 **of the test file**. Five of the six tests
(`test_stability_no_edit_means_no_deploy`, both `test_known_positive_*`,
`test_known_negative_proctor_tooling_does_not_deploy`, `test_f3_the_hold_holds`) call that local copy
over a `tmp_path` tree; `test_f3_the_hold_holds` even computes the deploy decision itself
(`would_deploy = (not hold.exists()) and current != deployed`) rather than asking the supervisor.
The sixth, `test_the_real_supervisor_exposes_the_pieces`, is the only one that opens
`tools/swarm_supervisor.py` — and it checks for five tokens by substring plus one slice assertion on
the skip block. If `code_fingerprint` in the shipped supervisor drifted from the test's copy, five of
six tests would keep passing. The file itself says the risk out loud in that test's docstring: *"The
mechanism must exist in the shipped file, not only in this test's copy of it."* It is one assertion
against five.

### `tests/test_persona_runtime.py` — 7 of 12 tests are inert

The subject exists: `PersonaManager` and `PersonaDecision` are both defined in
`engines/consciousness/persona_runtime.py` and the import resolves. But:

- `test_action_proposer_concept`, `test_observer_persona_concept`, `test_strategy_evaluator_concept`
  are each exactly `assert runtime is not None` — three tests whose only content is that the fixture
  ran.
- `test_runtime_has_required_methods` iterates a list of three method names and asserts callability
  **only inside `if hasattr(runtime, method)`** — it passes if the class has none of them.
- `test_proposal_generation_does_not_crash` is wrapped in `if hasattr(...)` and catches
  `TypeError, ValueError, KeyError` — it passes whether the method exists, works, or raises.
- `test_runtime_has_database` accepts either `db` or `database`.

Five of these seven would survive `PersonaManager` losing every method it has. The remaining five
tests (`test_runtime_creates_successfully`, `test_persona_tables_exist`, and the schema checks) do
touch real behaviour.

---

# THE INVOCATION SURFACE

Added by Amendment 1. Read-only; dot-files are never moved. The question is not "what do these
files *say*" but "what do they *call*, does it exist, and do the two runs agree".

**Complete enumeration of invokers.** There are no Makefiles, no `.sh`, `.bat`, `.cmd` or `.ps1`
anywhere outside `.venv`/`.git` (searched to depth 3 and by name across the tree). There is no
`.gitlab-ci.yml`, no `.vscode/`, no `.travis.yml`. `.claude/settings.local.json` contains a
`permissions` key and nothing else — no `hooks`, no `statusLine`, no `env`, so it invokes nothing.
`.gitattributes` is one line (`* text=auto`). That leaves exactly three invokers:
`.github/workflows/ci.yml`, `.githooks/pre-commit`, and `.pre-commit-config.yaml`.

## (a) Every repo file the invokers call

### `.github/workflows/ci.yml` — triggers on push and PR to `branches: ['**']`

| step | invokes | blocking? | target exists? |
|---|---|---|---|
| Install dependencies | `pip install vulture pytest ruff` + `python-dotenv aiohttp numpy pandas` | — | n/a — **see (b), this list is the defect** |
| RUNG 0d — consumption sweep | `python tools/consumption_sweep.py --strict` | **BLOCKING** | yes; `--strict` is a real flag (`tools/consumption_sweep.py:270`), and it fails on what is NEW against the baseline (`:364`) |
| RUNG 0c — wiring registry | `pytest tests/gate/test_wiring_registry.py -q` | **BLOCKING** | yes; needs only `tools/wiring_receipts.py` + `WIRING_REGISTRY.md`, both present, no third-party deps beyond pytest |
| OOD lint | `python tools/ood_lint.py` | **BLOCKING** | yes; `main()` at `:212` with an optional `--root` defaulting to the repo, so a bare call is correct |
| ruff | `ruff check .` | **BLOCKING** | yes; the `.` is governed by `pyproject.toml [tool.ruff] include`, so it resolves to `engines/egocentric/**`, `tools/**`, `tests/gate/**`, `pyproject.toml` |
| gate suite | `pytest tests/gate -q` | **BLOCKING** | directory exists — **but see (b): it cannot pass** |
| vulture | `vulture engines/ cognitive_loop.py cognitive_game_player.py manual_tools/ --min-confidence 80 --ignore-names "_*" --exclude "deprecated/,tests/"` | advisory (`continue-on-error: true`) | all four targets exist; `--exclude deprecated/` names a directory that **does not exist** (harmless, but a dead reference) |

Also reached indirectly and therefore live: `tools/consumption_baseline.json` (the `--strict`
comparison baseline `consumption_sweep.py` reads), and `pyproject.toml` (governs the ruff step).

### `.githooks/pre-commit` — ACTIVE

`git config core.hooksPath` returns `.githooks`, and `.git/hooks/` contains no non-sample files.
So this shell script is the one and only hook that runs on this box. It invokes
`.venv/Scripts/python.exe -m ruff check .` (falling back to `python -m ruff`) and blocks the commit
on a non-zero exit. It calls no repo .py file. Its header records why it exists: three tools shipped
with ruff errors in one session after the rule was already known — "knowing a rule and holding it are
different states".

### `.pre-commit-config.yaml` — **INERT**

| hook | invokes | target exists? |
|---|---|---|
| vulture (remote v2.14) | `--min-confidence=80 --exclude=deprecated/,tests/,manual_tools/ --ignore-names=_* vulture_whitelist.py`, `files: ^(engines/\|core_gameplay\.py\|decision_rung_system\.py\|autonomous_evolution_runner\.py)` | `vulture_whitelist.py` **yes** (93 lines, root); `engines/` yes; `decision_rung_system.py` yes; **`core_gameplay.py` NO** (it is at `legacy/core_gameplay.py`, and the pattern is anchored `^`); **`autonomous_evolution_runner.py` NO** (the file is `evolution_runner.py`); `--exclude=deprecated/` names a directory that does not exist |
| check-yaml, end-of-file-fixer, trailing-whitespace, check-added-large-files (`--maxkb=500`), check-ast | remote hooks | excludes reference `deprecated/`, which does not exist |
| isort | `--profile black --skip deprecated` | `deprecated` does not exist |
| protect-game-files (local) | a `bash -c` that echoes and exits 1 on any `environment_files/` path | `environment_files/` yes |

**Why inert:** `pre-commit install` writes `.git/hooks/pre-commit`. `.git/hooks/` has no installed
hooks, and `core.hooksPath` is redirected to `.githooks` anyway — which would bypass an installed
one even if it existed. Neither `pre_commit` nor `isort` is present in `.venv/Lib/site-packages`.
This file has not run on this box. Its header still reads "Pre-commit hooks for **BitterTruth-AI**"
— the same inherited-boilerplate marker that `ci.yml`'s own history comment says was purged from CI
on 2026-08-18. CI was fixed; this file was not, and nobody noticed because nothing runs it.

## (b) Calls whose target does not exist — the checks asserting nothing

**1. CI's BLOCKING gate suite cannot be collected, let alone pass.**
The workflow installs `vulture pytest ruff python-dotenv aiohttp numpy pandas`. It never runs
`pip install -r requirements.txt` or `-r requirements-dev.txt`. Two required distributions are
therefore absent in CI:

- **`arc-agi>=0.1.0`** (`requirements.txt:14`) — supplies `arcengine` and `arc_agi`.
- **`hypothesis==6.165.7`** (`requirements-dev.txt`) — and `requests`, pulled in by `arc_api_adapter.py`.

Computing the transitive module-level import closure of all 124 gate files against CI's installed
set, **5 fail at collection**:

| file | missing at collection | the import site |
|---|---|---|
| `tests/gate/test_properties.py` | `hypothesis` | `:26` `from hypothesis import assume, given, settings` — bare, no `importorskip` |
| `tests/gate/test_corpse_guard.py` | `arcengine` | `:50` `from arcengine import GameState` — bare |
| `tests/gate/test_frame_normalisation.py` | `arcengine` | `:35` `from cognitive_game_player import CognitiveGamePlayer` → `cognitive_game_player.py:31` |
| `tests/gate/test_trace_writer.py` | `arcengine` | `from game_player import ...` → `game_player.py` |
| `tests/gate/test_d9_diagnostic_gate.py` | `arcengine`, `arc_agi`, `requests` | `import evolution_runner` → `arc_api_adapter.py`, `context_builder.py`, `outcome_processor.py` |

and **4 more raise at run time** because they import `cognitive_game_player` lazily inside a test
body rather than at module level: `test_budget_restoration.py:23`, `test_handoff_rate.py:24`,
`test_link3_hook_and_vocabulary.py:396`, `test_salient_prefix.py` (same pattern).

A pytest collection error is exit code 2. `pytest tests/gate -q` is declared BLOCKING. **Either this
workflow has been red on every push since it was written on 2026-08-18, or it has never run.** Both
readings are the same defect the rubric was written for: the file's own header says the previous CI
was called "a CI gate for weeks. It was not one." The header is describing the current file.

Note the shape precisely, because it is the reason nobody saw it: the *first three* blocking steps
(consumption sweep, wiring registry, ood lint) all pass cleanly under CI's dependency set — they need
only pytest and stdlib. A reader glancing at a failure would see it land in step 5 or 6, on
`arcengine`, and read it as an environment problem rather than as the gate never having been green.

**2. `.pre-commit-config.yaml` names two files that do not exist**, both anchored with `^` so they
can never match: `core_gameplay.py` (moved to `legacy/core_gameplay.py`) and
`autonomous_evolution_runner.py` (the file is `evolution_runner.py`; the old name survives only in a
docstring at `representation_learner.py:220`). Four hooks additionally exclude `deprecated/`, a
directory that is gone. Because the config is inert, none of this has ever failed loudly.

**3. `models/dynamics_model.pt` is 7.4MB and git-tracked** while `.gitignore:54` ignores `*.pt` and
`.pre-commit-config.yaml` sets `check-added-large-files --maxkb=500`. It is tracked in spite of both.
That is only possible with a force-add, or — more likely — because the hook that would have caught it
does not run.

## (c) Do CI and the local checks agree?

**ruff: yes, exactly.** CI runs `ruff check .` and `.githooks/pre-commit` runs `ruff check .` from
the same root. Both resolve through `pyproject.toml [tool.ruff] include`, so both cover
`engines/egocentric/**`, `tools/**`, `tests/gate/**`. The one divergence is version: CI does
`pip install ruff` unpinned, while `requirements-dev.txt` pins `ruff==0.16.3` and `.venv` has exactly
that. A new ruff release can turn CI red without a line of this repo changing.

**vulture: no — three different runs, three different scopes, and only the inert one is correct.**

| where | scope | whitelist passed? | blocking? |
|---|---|---|---|
| `.github/workflows/ci.yml` | `engines/ cognitive_loop.py cognitive_game_player.py manual_tools/` | **NO** | advisory |
| `.pre-commit-config.yaml` | `^(engines/\|core_gameplay.py\|decision_rung_system.py\|autonomous_evolution_runner.py)`, excluding `manual_tools/` | **YES** (`vulture_whitelist.py`) | would block — **but never runs** |
| `tests/gate/test_frame_instruments.py::test_vulture_finds_no_dead_code_in_the_engine` | `engines/egocentric` only | **NO** | **BLOCKING** (inside the gate suite) |

The three disagree on every axis. CI *includes* `manual_tools/` deliberately (its comment: excluding
the directory that holds the orphan auditor is how the auditor went 195 days unnoticed); the
pre-commit config *excludes* it. The gate test narrows to `engines/egocentric` and is the only one
that can actually fail a build. And **`vulture_whitelist.py` — 93 lines naming `IThreadType`,
`IThread`, `RepresentationLearner`, `CognitiveStageSystem`, `DatabaseInterface`, `EngineRegistry`
and others as intentional false positives — is passed by exactly one of the three, the one that is
inert.** Its suppressions therefore apply to nothing. Two of its own comment blocks describe
`deprecated/engines_decision/`, a directory that no longer exists.

That is the same finding as this week's registry receipts and as Part A's three orphaned test files,
in a third place: **`vulture_whitelist.py` is a live-looking, maintained, root-level artifact that no
executing check consumes.** Whoever owns the root .py slice should have it — it is not dead code, it
is code whose only caller was switched off.

**pytest: partially.** CI runs `pytest tests/gate -q` (124 files). `pytest.ini` sets
`testpaths = tests`, so a bare local `pytest` runs 150 files — the 26 legacy `tests/test_*.py` as
well. CI never runs those 26, which includes all three of the orphaned files in the section above.
Nothing would have told CI they gate nothing, because CI does not run them.

## What this means for the reachability verdicts elsewhere in this file

Applying Amendment 1 to my own tables: I re-searched every file I classified across `.github/**`,
`.pre-commit-config.yaml`, `.githooks/**` and `.claude/**`. **Three of my classifications gained a
caller and one changed:**

- `pyproject.toml` — already live; now additionally reached by `ci.yml` (ruff step) and
  `.githooks/pre-commit`. Confirmed live from three directions.
- `tools/consumption_baseline.json` (in the `tools/` slice, flagged here for its owner) — read by
  `tools/consumption_sweep.py --strict`, which `ci.yml:41` invokes as a BLOCKING step. Live.
- `requirements.txt` / `requirements-dev.txt` — my "NAMED-ONLY" verdict for `requirements-dev.txt`
  stands and is now *worse* news: CI does not install either file, which is the root of finding (b1).
- `config/cognitive_edges.json` — **unchanged at considered_dead.** I re-checked it against every
  dot-file. No CI step, no hook, no `.claude` command names it. The dot-dir hole was not what was
  hiding this one; nothing is reading it.

No file I marked `considered_dead` or `preserve` turned out to have a dot-dir caller, and
`figures/*.svg` gained none either.

---

## Residue — things I could not settle inside this slice

1. **`config/cognitive_edges.json` (24KB) is loaded by nothing.** `engines/cognition/blackboard.py`
   carries a field comment saying edge weight is "Static weight from cognitive_edges.json", and
   `blackboard.py` does `import json` — but only for `json.dumps` on path keys and slot values, and
   `json.loads` on checkpoint restore. There is no reader. Either the loader was removed and the
   comment survived it, or it was never written. The file has `edges`, `edge_statistics`,
   `subgraph_clusters` and `critical_paths` — that is a real artifact, and
   `engines/cognition/edge_inference.py` (which `tests/test_edge_inference.py` exercises with 51
   tests including `TestExportImport`) is the plausible producer. Worth one grep by the examiner who
   owns `engines/cognition/`: if `edge_inference` can re-emit it, this is preserve; if not, it is a
   24KB graph nobody can regenerate.
2. **`tests/README.md` documents a suite that no longer exists** — three of its five rows point at
   files that are either in `legacy/tests_dead_lineage/` or nowhere, and it lists none of the 124
   gate tests. It needs correcting, not moving.
3. **`legacy/tests_dead_lineage/` holds six more `test_*.py`.** They are outside `tests/` so outside
   my slice, but `pytest.ini` sets `testpaths = tests`, so they are never collected — flagged for
   whoever owns `legacy/`.
4. **`core_data.db` is not git-tracked** (`.gitignore:57` `*.db`) and `tests/conftest.py` points its
   `db_path` / `db_connection` fixtures at it by absolute path. Any test using those fixtures is
   silently box-dependent — and in CI, where the file cannot exist, they are running against a
   database that is absent or empty.
5. **I could not determine whether `.github/workflows/ci.yml` has ever completed green.** That
   requires the Actions run history, which is not in the tree. The static analysis in (b1) says it
   cannot have, but "it has never been triggered" is an equally consistent explanation and needs one
   look at the repository's Actions tab to separate. Whichever it is, the fix is the same one line:
   `pip install -r requirements.txt -r requirements-dev.txt` in place of the hand-listed subset.
6. **`vulture_whitelist.py` belongs to the root-.py slice, but its only caller is switched off** —
   recorded here because the fact is only visible from the invocation surface, and the .py examiner
   would otherwise see a root-level file referenced from a committed config and call it live.
