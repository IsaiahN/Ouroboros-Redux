# EXAM 04 — `manual_tools/**`, `legacy/**`, `lab/**`

Rubric: `record/findings/EXAMINATION_RUBRIC.md` (binding), **including RUBRIC AMENDMENT 1**
— dot-prefixed directories are skipped for MOVES but **searched for REACHABILITY**. Built on
`record/findings/CODEBASE_INVENTORY.md`, which is corrected in **nine** places below.

**Amendment 1 was applied after the first draft and it changed this document.** Its effect
on this slice is stated in full at C7-C9 and summarised here: **one file moved
`considered_dead` → `preserve`** (`manual_tools/analysis/analyze_dependencies.py`, which is
a mandated step of the repo's own code-review checklist), **all seven `lab/**` files gained a
materially stronger reached-by** (from prose in an architecture doc to a documented
invocation in an auto-loaded agent instruction file with six matching runbooks), and **the
whole of `manual_tools/` was found to be under an active CI step on every push and PR.**
No file moved in the other direction.

**Snapshot:** branch `v4-cold`, HEAD `e1cce38`, working tree clean at start of read,
2026-08-22. Method: `ast.parse` only — **no module in this slice was imported or executed
at any point.** Every file was opened; docstring, top-level `def`/`class` names, and the
import set were extracted from the parse tree. Where a claim needed a site, the site was
read in full and is quoted.

Exclusions honoured: `docs/GAME_TRUTH`, `ouroboros_cpu/objective_grammar.py`, the
train-set-answers directory and `.env` were not opened. No game frame decoded. No game id,
colour or object identity appears below. **Nothing was moved, deleted or edited.**

**Amendment-1 reachability surfaces searched** (search only; nothing in a dot-directory is
proposed for a move or a restructure). The complete set of invocation-capable script/config
files in this repo was enumerated with `find`, not assumed: `.github/workflows/ci.yml`,
`.github/copilot-instructions.md`, `.github/copilot-instructions-v4-legacy.md`,
`.pre-commit-config.yaml`, `.githooks/pre-commit`, `.claude/settings.local.json`,
`pyproject.toml`, `pytest.ini`, and the nine runbooks in `checklists/`. **There is no
Makefile, and no `.sh`/`.ps1`/`.bat`/`.cmd` anywhere in the tree outside `.venv/` and
`.runs/cold_venv/`** (both third-party). Also swept and clean for this slice: `.claude/`,
`.hypothesis/`, `.gamma_library/`, `.residual_bank/`, `.runs/` (excluding the vendored
`cold_venv/` and the `arms/<hash>/` worktree copies, which are repo clones rather than
invocation sites) and `.runs/archive/`. `.pytest_cache/` and `.ruff_cache/` are tool caches.

---

## COUNTS

| | files |
|---|---|
| **`.py` in slice** (recursive, `.`-prefixed **dirs** skipped) | **108** |
| &nbsp;&nbsp;· `manual_tools/**` | 63 |
| &nbsp;&nbsp;· `legacy/**` | 38 |
| &nbsp;&nbsp;· `lab/**` | 7 |
| plus one `.`-prefixed **file** inside a normal dir (`manual_tools/utilities/.vulture_whitelist.py`) — examined, **live by constraint** | 1 |
| **files walked** | **109** |
| unreadable | **0** |
| syntax errors on parse | **0** |

**Destinations proposed (nothing executed):**

| dest | files |
|---|---|
| **live** | **2** (`performance_analyzer.py` — lazy live path; `.vulture_whitelist.py` — dot-prefixed, by constraint) |
| **preserve/** | **39** |
| **considered_dead/** | **68** |
| **total rows** | **109** — one per file walked, no file without a row |

*(Pre-amendment: 38 / 69. `manual_tools/analysis/analyze_dependencies.py` moved across; see
C7.) The 39 preserve rows map onto the 34 numbered entries in **CAPABILITY THIS BUILD DOES
NOT HAVE** as follows: 34 numbered, plus 4 carried in that section's "Adjacent" paragraph
(`manual_tools/database/compact_database.py`,
`legacy/manual_tools/diagnosis_query{,_part2}.py`, `lab/__init__.py`), plus
`legacy/game_scheduler.py` folded into entry 30 as the base class its preserved subclass
requires. 34 + 4 + 1 = 39.*

---

## NINE CORRECTIONS TO `CODEBASE_INVENTORY.md` (each checkable at the cited line)

C1-C6 come from reading the sites the inventory cites. **C7-C9 come from the Amendment 1
dot-directory sweep and could not have been found without it** — they are the same hole the
amendment was issued for, landing in this slice.

The inventory's FINDING 4 is right about the genus and then trips over it in its own
`OBSCURE-E` tier. Corrections 1, 2 and 4 are all the same mistake: **a filename in a list
is not an invocation.**

**C1 · `manual_tools/utilities/cleanup_temp_files.py`'s `KEEP_FILES` is a DELETE-WHITELIST,
not a call site.** The inventory tiers ~14 rows `OBSCURE-E` citing `cleanup_temp_files.py`
lines 56/57/63/77/92/93/94/100/104/106/112/113/114. Read at line 53:
`# Files to KEEP (whitelist - never delete these)`. Every one of those lines is a bare
string in a `set` literal. **These 14 rows are NAMED-ONLY, not executable-reachable:**
`manual_tools/analysis/{gameplay_analyzer, optimization_threshold_system,
prestige_parasite_detector, sequence_pruning_system}.py`,
`manual_tools/database/schema_inspector.py`,
`manual_tools/utilities/{abstraction_schema, enhanced_database_interface,
evolution_with_parasites, revive_agents}.py`,
`legacy/{arc_api_client, automated_assessment_runner, disk_space_monitor,
evolution_game_scheduler}.py`, and (outside this slice) root `schema_auto_maintenance.py`.
The whitelist is also **stale**: it names `autonomous_evolution_runner.py`,
`breakthrough_detector.py`, `run_evolution.py`, `ouroboros_coordinator.py` — verified absent
from the tree.

**C2 · `tests/gate/test_origin_marker.py:257` is an EXCLUSION list, and it does not name
`manual_tools/temp_check.py` at all.** The line reads
`or base in ("_temp_check.py", "vulture_whitelist.py")` inside `_prod_files()`, which
*skips* those basenames. The inventory's substring match also caught `temp_check.py` off
`_temp_check.py`. So: `legacy/_temp_check.py` is NAMED-ONLY (in a skip list);
`manual_tools/temp_check.py` is **NONE** — its name occurs nowhere outside itself. The same
line excludes `base.startswith("_investigate")`, which is the only tree mention of three
`legacy/_investigate_part*.py` files.

**C3 · `legacy/core_gameplay.py` is NOT reached by `__init__.py:12`.** Line 12 is prose in
the root docstring. The real statement is `__init__.py:32`,
`from .core_gameplay import GameplayEngine, conservative_strategy, exploration_strategy,
random_strategy` — and it is broken twice: `core_gameplay.py` is **not at the root** (it is
in `legacy/`, so `.core_gameplay` cannot resolve), and three of the four names it imports
**do not exist** in `legacy/core_gameplay.py` (its only module-level functions are
`quick_play` and `list_all_games`). The whole block sits under `except ImportError: pass`
at line 39. It has been failing silently for as long as the file has been in `legacy/`.
`legacy/core_gameplay.py`'s reachability is **NONE**, and with it the chain it heads
(`game_loop.py:60`, `learning_systems.py:61`).

**C4 · `manual_tools/analysis/theory_alignment_checker.py:630` names
`adaptive_action_limits.py` inside a `code_locations=[...]` string list** on a
`TheoryRequirement` dataclass — documentation of where a requirement should hold, not an
import. `legacy/adaptive_action_limits.py` is NAMED-ONLY.

**C5 · NEW SITE, not in the inventory — `manual_tools/**` and `legacy/**` are inside the
swarm's DEPLOYMENT FINGERPRINT; `lab/**` is explicitly outside it.**
`tools/swarm_supervisor.py:93-101` walks `REDUX` hashing every `.py` by
`(relpath, size, mtime_ns)` to decide whether to restart the fleet, with this exclusion set
and this comment, verbatim:

```
dns[:] = [d for d in dns
          if d not in (".git", ".runs", ".venv", "__pycache__",
                       "node_modules", ".ruff_cache", "tests", "lab",
                       # proctor tooling: workers never import it, so editing
                       # it must NOT restart the swarm. manual_tools is NOT here:
                       # evolutionary_engine.py:464 lazily imports
                       # manual_tools.analysis.performance_analyzer, so it IS
                       # live-path and a change to it must deploy.
                       "tools", "docs", "architecture")]
```

Consequence, stated because it is a live operational fact and not a classification:
**touching any of the 63 files under `manual_tools/`, or any of the 38 under `legacy/`,
changes the deployment hash and restarts the swarm** — including the 74 rows below marked
`considered_dead`. One module's lazy import has coupled the whole directory to deployment.
Moving them is therefore not neutral; it is a fleet restart. `lab/` and `tools/` are exempt.

**C6 · NEW SITE, not in the inventory — a LIVE GATE TEST asserts that
`lab/trend_tracker.py` and `lab/comparative_analyst.py` are cited by name.**
`tests/gate/test_beat_rates.py:512-531`
(`test_the_exemplar_decision_is_recorded_in_the_docstring`) asserts that
`tools/beat_rates.py.__doc__` contains the literal strings `lab/trend_tracker.py`,
`lab/comparative_analyst.py`, `NAME THE EXEMPLAR`, `ensure_schema` and `GENERATION`, **and**
that neither name appears in the module body. This is a stronger reached-by than
NAMED-ONLY-in-prose: a test fails if the citation is dropped. The reason recorded at
`tools/beat_rates.py:85-107` is verified correct on all four counts (see the CAPABILITY
section, entry 21). **It is a verdict about fit for one instrument, not a verdict about the
capability** — which is precisely why the GM asked for it recorded here.

**C7 · AMENDMENT 1 · `manual_tools/analysis/analyze_dependencies.py` is a MANDATED STEP of
the repo's own code-review checklist, and it has been silently unrunnable.**
Four documented invocation sites, none of them visible to a dot-dir-skipping scan and none
of them in the inventory:

```
checklists/code_reviewer.md:9
    - [ ] Run dependency analysis: python manual_tools/analysis/analyze_dependencies.py --stats --orphans
.github/copilot-instructions-v4-legacy.md:139
    - Run `python manual_tools/analysis/analyze_dependencies.py --stats --orphans` before major changes
.github/copilot-instructions-v4-legacy.md:164
    - **Regenerate Command**: `python manual_tools/analysis/analyze_dependencies.py --full --core --reasoning`
.github/copilot-instructions-v4-legacy.md:325
    - Use `manual_tools/analysis/analyze_dependencies.py` for import graph analysis
```

A checkbox in a review runbook is a caller. **I had this file marked `considered_dead`; it
is now `preserve`, and this is the only destination the amendment changed.** The sharper
finding is the second half: the tool shells out to `pydeps`, and **`pydeps` is verified
absent from `.venv`** (it is in `requirements.txt` under "Development & Testing", never
installed). So `checklists/code_reviewer.md`'s first checkbox cannot pass — its
`--orphans` mode is an orphan-detector that has itself been unable to run. That is exactly
the defect genus this examination exists to find, sitting inside the checklist that was
supposed to catch it.

**C8 · AMENDMENT 1 · the whole of `lab/` is invoked from an auto-loaded agent instruction
file, with six matching runbooks — not "named in prose in an architecture doc".**
`.github/copilot-instructions.md` ("AUTONOMOUS RESEARCH LAB — ORCHESTRATOR INSTRUCTIONS",
v5.0, 2026-02-17) is loaded automatically by GitHub Copilot in this repository. It contains
**THE LOOP** at lines 69-76, calling five lab modules by function —

```python
run_evolution(branch="lab/mainline")       # checklists/evolution_runner.md
metrics = compute_metrics()                 # lab/metrics.py
traces = run_code_tracer()                  # checklists/code_tracer.md
analysis = run_comparative_analyst()        # checklists/comparative_analyst.md
trend = update_trend_tracker()              # checklists/trend_tracker.md
```

— and a **YOUR PYTHON SCRIPTS** table at lines 132-139 mapping six of the seven lab files
to a runbook. **`checklists/` exists** and contains nine files, five of which are the named
per-module runbooks (`branch_breeder.md`, `code_tracer.md`, `comparative_analyst.md`,
`evolution_runner.md`, `trend_tracker.md`). This is a documented operating procedure with
its apparatus present, i.e. a caller. All seven `lab/**` rows move from **NAMED-ONLY** to
**STRING — documented invocation**; their destination (`preserve`) is unchanged but the
case is much stronger. **Stated honestly:** the regime that file describes (a Copilot
orchestrator working on `lab/mainline` and `experiment/*` branches) is *not* the current
swarm regime, so this is a live invocation surface for a *different operator*, not evidence
that the fleet runs `lab/`. It raises `lab/` above prose; it does not make it live.

**C9 · AMENDMENT 1 · `manual_tools/` is scanned by a CI step on every push and every PR —
and `.pre-commit-config.yaml` still excludes exactly what CI was deliberately un-excluded
from.** `.github/workflows/ci.yml:57-64`:

```
# ── ADVISORY. Vulture cannot see past __init__ re-exports -- that blind spot hid
# sequence_miner.py for months (record/canon/WIRING_REGISTRY.md). It stays non-blocking BECAUSE
# it is known-incomplete, and manual_tools/ is NO LONGER EXCLUDED: excluding the
# directory that holds the orphan auditor is how the auditor itself went 195 days
# unnoticed as an orphan.
- name: 'vulture (ADVISORY - known blind spot on re-exports)'
  continue-on-error: true
  run: vulture engines/ cognitive_loop.py cognitive_game_player.py manual_tools/ ...
```

Three things follow. **(a)** `manual_tools/` is under an active, ruled-upon CI scan; any
move of that directory changes what that step sees, and the GM has already ruled once on
exactly that exclusion. **(b) The two gates contradict each other on this directory:**
`.pre-commit-config.yaml:14` still passes `--exclude=deprecated/,tests/,manual_tools/` to
the same tool — pre-commit excludes precisely what CI was changed to include, so the ruling
holds on push and is reversed on commit. **(c)** The same hook's file filter at
`.pre-commit-config.yaml:18` is
`^(engines/|core_gameplay\.py|decision_rung_system\.py|autonomous_evolution_runner\.py)` —
anchored at the start of the path, so it names `core_gameplay.py` **at the repo root, where
it no longer is** (it is `legacy/core_gameplay.py`, and can therefore never match), and
`autonomous_evolution_runner.py`, **verified absent from the tree entirely**. In practice
that hook filters to `engines/` alone. This is a third independent confirmation of C3: the
root→`legacy/` move left stale references in three places (`__init__.py:32`,
`cleanup_temp_files.py`'s whitelist, and this hook), and none of them errors.

**What the amendment did NOT change:** no `legacy/**` file gained a caller — the sweep found
zero references to any `legacy/` module across every surface listed above
(`copilot-instructions-v4-legacy.md` is a filename, not a reference to the directory; its
only slice mentions are the four `manual_tools` lines in C7 plus prose at :177). No other
`manual_tools/**` file gained one either: `analyze_dependencies.py` is the single named
command. And no file moved from `preserve` toward `considered_dead`.

---

## THE TABLE

`reached-by` uses the rubric's six classes. Every non-live row names the ONE site.

### `lab/` — 7 files · live 0 · preserve 7 · considered_dead 0

`lab/` is a single coherent loop specified in `architecture/Autonomous Research Lab.md`
(lines 417-421 name five of the seven) **and driven from `.github/copilot-instructions.md`,
which the amendment sweep found — see C8.** It is `python -m`-driven end to end and has **no
importer anywhere outside itself**, but it is not uncalled: an auto-loaded orchestrator
instruction file executes five of the seven in a documented loop and maps six to runbooks in
`checklists/`. It should move as one unit or not at all — the two in-package edges
(`branch_breeder.py:155`, `evolution_runner_wrapper.py:69`) are lazy imports that break if
the package is split, and **six of the seven rows below have a runbook in `checklists/` that
would be orphaned by a move.**

| path | dest | reached-by (with the site) | what it does | preserve: capability, and why it may matter |
|---|---|---|---|---|
| `lab/__init__.py` | preserve | NONE — nothing imports the package; it exists so the `python -m lab.x` invocations in `.github/copilot-instructions.md:69-76` resolve | two-comment package marker pointing at `architecture/Autonomous Research Lab.md` | Load-bearing for every `-m` entry point in the package; the package cannot run without it |
| `lab/branch_breeder.py` | preserve | **STRING — documented invocation**: `.github/copilot-instructions.md:138` (script table → `checklists/branch_breeder.md`, present). Also NAMED-ONLY at `architecture/Autonomous Research Lab.md:420` | git-only combinatorial crossbreeding of experiment branches; `generate_combinations`, `create_crossbred_branch`, `get_breeding_candidates`; lazily reads `lab.trend_tracker.get_successful_experiments` at :155 | **Crossbreeding CHANGES, not agents.** The live build breeds agent genomes; nothing combines two successful *code experiments*. Nearest live counterpart: NONE |
| `lab/code_tracer.py` | preserve | **STRING — documented invocation**: `.github/copilot-instructions.md:72` (`run_code_tracer()` in THE LOOP) and `:135` → `checklists/code_tracer.md`, present | discovers which subsystems actually engaged, from `traces/` files or the `cognitive_routing_traces` table, with subsystem names discovered at runtime; `_detect_failure_patterns` | Engagement measured **from runs**, not from source. Nearest live: `tools/live_coverage_diff.py` and `tools/consumption_sweep.py` — both read source. This is the third leg neither has |
| `lab/comparative_analyst.py` | preserve | **STRING — documented invocation**: `.github/copilot-instructions.md:73` (`run_comparative_analyst()`) and `:136` → `checklists/comparative_analyst.md`, present. Also **gate-asserted** at `tests/gate/test_beat_rates.py:521` | splits runs into success/failure cohorts per game type, extracts every numeric feature, ranks by **Cohen's d** (`_cohens_d`, :30), sorts by `abs_effect` | **Effect-size attribution over every discovered feature.** Nearest live: `tools/split_half.py` — one hand-picked statistic, one direction. This ranks all of them and reports the size of the gap, not just its sign |
| `lab/evolution_runner_wrapper.py` | preserve | **STRING — documented invocation**: `.github/copilot-instructions.md:71` (`run_evolution(branch="lab/mainline")`) and `:139` → `checklists/evolution_runner.md`, present | switches to a target branch, runs `evolution_runner.py` as a subprocess, collects before/after metrics via `lab.metrics` (:69), returns structured results | The **trial harness**: branch → run → before/after. Nearest live: `tools/control_arm.py` assigns an arm; nothing runs a branch and returns a paired measurement |
| `lab/metrics.py` | preserve | **STRING — documented invocation**: `.github/copilot-instructions.md:72` (`metrics = compute_metrics()  # lab/metrics.py`) and `:134`. Also LAZY — `lab/evolution_runner_wrapper.py:69` | the 5 benchmark metrics computed from `game_results` alone; `_discover_columns` so the contract survives schema drift; `compute_trend` | A **stable measurement contract**: depends on one table's schema and discovers its own columns. Nearest live: `tools/beat_rates.py` (richer, but bound to fabric streams + per-box DBs). This one is portable |
| `lab/trend_tracker.py` | preserve | **STRING — documented invocation**: `.github/copilot-instructions.md:75` (`trend = update_trend_tracker()`), `:76` (`trend.ready_for_new_hypothesis()` gates the loop) and `:137` → `checklists/trend_tracker.md`, present. Also LAZY — `lab/branch_breeder.py:155`; also **gate-asserted**, `tests/gate/test_beat_rates.py:520` | `lab_experiments` + `lab_metric_snapshots` tables: every experiment, hypothesis, before/after metrics, outcome; `check_readiness`, `detect_convergence` (:274), `get_successful_experiments` | **Experiment memory with an automatic plateau verdict.** Nearest live: `record/log/PORT_LOG.md` — prose, held by hand. Its unit (GENERATION) and its writes (`ensure_schema` at every entry point) are why `beat_rates` did not call it; neither fact touches the capability. **Note the amendment sharpened this one twice over: it is not only cited by a gate test, it is the GATE OF A DOCUMENTED LOOP** — `copilot-instructions.md:76` will not proceed to a new hypothesis until this module says there is enough signal |

### `manual_tools/` (root) — 21 files · live 0 · preserve 10 · considered_dead 11

| path | dest | reached-by (with the site) | what it does | preserve: capability, and why it may matter |
|---|---|---|---|---|
| `manual_tools/_extract_rungs.py` | preserve | NAMED-ONLY — `record/findings/FORGOTTEN_CAPABILITIES.md:57` | regex-extracts `class X(DecisionRung)` from a rung-system source file and groups by category | **The tree's only live cross-repo edge.** Line 5 hard-codes `c:\Users\Admin\Documents\GitHub\BitterTruth-AI\decision_rung_system.py`. **I searched the whole slice for others and there are none** — this is the single hit for `[A-Za-z]:[\\/]Users` and for `GitHub[\\/]` across all 109 files. Preserve as the *evidence* that this tree cannot enumerate its own habitat alone (inventory FINDING 5) |
| `manual_tools/analyze_run.py` | considered_dead | NAMED-ONLY — `record/findings/SWEEP_COMMENT_DIVERGENCE.md:22` | date-pinned SQL report over one specific 2026 run | — |
| `manual_tools/analyze_run2.py` | considered_dead | NONE | same, re-run with a corrected id filter | — |
| `manual_tools/audit_data_usage.py` | preserve | NAMED-ONLY — `record/findings/F8A_READ.md:42` | 1187 lines, `DataUsageAuditor` with **13 named audits**, each simulating a retrieval function against the real DB to find rows that EXIST and are SILENTLY DROPPED by a guard or threshold (wisdom, death patterns, biases, mastery, hypotheses, sequences, viral packages, sensation, frontier, abstraction hints, replay activation, death blocking) | **Suppression measured on real rows.** Nearest live: `tools/consumption_sweep.py` — static AST writer/reader pairing, which proves a reader *exists*. This proves the reader *returned nothing*, which is the failure mode pairing cannot see |
| `manual_tools/audit_orphaned_systems.py` | preserve | NAMED-ONLY — `record/findings/HISTORY_TRACE.md:56` | five audits: engines registered but never accessed; rungs reading context keys nobody sets; tables that exist but are never written; engine methods never called; features documented but not implemented | **The examination as a program.** Nearest live: this document, `tools/repo_assess.py` (itself dead). Audit 2 (reads-a-key-nobody-sets) is the exact defect class `scan_context_keys.py` found live on first run |
| `manual_tools/audit_performance.py` | considered_dead | NONE | one-off SQL audit of action-decision latency | superseded by `tools/efficiency_read.py`, `tools/d5_profile_wrapper.py` |
| `manual_tools/check_deliberation_traces.py` | preserve | NONE | reads the deliberation-audit trace table and prints per-decision alternatives | **The reader half of an orphan pair.** `engines/reasoning/deliberation_audit.py` (inventory HELD #6, lazy-only from `decision_rung_system.py:627`) is the writer. Writer unreached, reader unreached — a second closed loop with neither half reachable, alongside `edge_inference`/`validate_inferred_edges` |
| `manual_tools/db_validation.py` | considered_dead | NAMED-ONLY — `README.md:381` | checks agent modes, boolean columns and sqlite pragmas | superseded by `tools/dump_schema.py` |
| `manual_tools/gen_analysis_v2.py` | considered_dead | NONE | generation analysis via timestamp-correlated trace windows | generation-pinned |
| `manual_tools/gen_compare.py` | considered_dead | NONE | two-generation comparison + cross-gen knowledge transfer | generation-pinned |
| `manual_tools/gen_compare_v2.py` | considered_dead | NONE | three-generation comparison | generation-pinned |
| `manual_tools/infer_answerable_by.py` | preserve | NONE | inverts `rung_dependency_matrix.json` — "rung X reads slot Y, therefore rung X can ANSWER questions about Y" — into a question taxonomy, tagged with a Rumsfeld (known/unknown ×2) relevance | **Findability as a derived artefact.** Nearest live: NONE. The taxonomy is generated from structure rather than authored, so it cannot drift from the structure the way a hand-written list does |
| `manual_tools/observer_dashboard.py` | preserve | NAMED-ONLY — `README.md:390` | ten sections over `core_data.db`: generations, PTMA loop health, knowledge accumulation, routing, evolutionary health, gaps/interventions, metacognition, action diversity, primitives, DB summary | **One page that shows the whole organism at once.** Nearest live: `tools/beat_rates.py` — deliberately narrow (rates with denominators, per game, read-only). This is the wide complement; sections 6 (gaps/interventions) and 7 (predictions/assumptions/theories) have no live equivalent at all |
| `manual_tools/profile_baseline.py` | preserve | NONE | `DecisionProfiler`: per-rung avg/max/p95 latency and per-rung memory via `tracemalloc`, context reads/writes per decision, decisions per second | **Per-rung cost attribution.** Mandate item 2. Nearest live: `tools/d5_profile_wrapper.py` profiles a run; nothing attributes latency or memory *to a rung*, which is the number needed to decide what to cut |
| `manual_tools/scan_context_keys.py` | preserve | NAMED-ONLY — `record/findings/AGENT_ACCESS_MAP.md:41` | 61 lines: diffs context keys READ by rungs against keys PROVIDED by `ContextBuilder` | **On record as having found a live defect on its first run.** Nearest live: NONE. The cheapest instrument in the slice and the one with the best hit rate |
| `manual_tools/scan_disconnection_patterns.py` | preserve | NONE | scans source for six idioms that silently drop data: `if X is None: return`, threshold gates that return `None`, `getattr(...,None)` + `is None`, DB query followed by a skipping conditional, `if not hasattr`, silent `None` returns | **The static half of `audit_data_usage.py`.** Nearest live: `tools/socket_or_filler_lint.py`, `tools/ood_lint.py` — different patterns. Together with `audit_data_usage.py` this is a matched static/runtime pair for one defect genus |
| `manual_tools/temp_check.py` | considered_dead | **NONE** (inventory said `tests/gate/test_origin_marker.py:257` — see C2; that line does not contain this filename) | prints recent action traces and decision reasons | — |
| `manual_tools/test_frame_hash_match.py` | considered_dead | NONE | tests a position-bucket death-pattern lookup; docstring records the table rename | — |
| `manual_tools/test_ls20.py` | considered_dead | NONE | one-game smoke test against the SDK | — |
| `manual_tools/test_online.py` | considered_dead | NONE | online-mode/API-key smoke test | — |
| `manual_tools/validate_inferred_edges.py` | preserve | NONE | **module-level** `from engines.cognition.edge_inference import EdgeInferenceEngine` at :36; three-list validation (CONFIDENT / UNCERTAIN / MISSING) plus `check_for_cycles`, `check_orphan_rungs`, `check_contradicting_edges`, `analyze_confidence_distribution` | **The falsifier for the wiring-discovery engine — verified.** `engines/cognition/edge_inference.py` (HELD #7) is lazy-only from `decision_rung_system.py:1329`; this is its only consumer and nothing reaches this. A machine that discovers its own wiring, plus the machine that catches it discovering wrong, and no path to either |

### `manual_tools/analysis/` — 20 files · live 1 · preserve 13 · considered_dead 6

| path | dest | reached-by (with the site) | what it does | preserve: capability, and why it may matter |
|---|---|---|---|---|
| `manual_tools/analysis/analyze_dependencies.py` | **preserve** *(was `considered_dead`; changed by the Amendment 1 sweep — C7)* | **STRING — documented invocation, four sites**: `checklists/code_reviewer.md:9` (a required checkbox: "Run dependency analysis: python manual_tools/analysis/analyze_dependencies.py --stats --orphans"), `.github/copilot-instructions-v4-legacy.md:139`, `:164`, `:325`. Also NAMED-ONLY at `architecture/Autonomous Research Lab.md:672` | `--full` / `--cycles` / `--core` / `--reasoning` / `--orphans` / `--stats` dependency graphs via `pydeps` + Graphviz; `find_orphaned_modules`, `analyze_cycles`, `check_graphviz` | **A mandated review step that cannot currently run.** `pydeps` is verified absent from `.venv` (it sits in `requirements.txt` under "Development & Testing" and was never installed), so the first checkbox of `checklists/code_reviewer.md` — an *orphan detector* — has itself been silently unrunnable. Nearest live: `CODEBASE_INVENTORY.md` answers the orphan question with a stdlib `ast` parser and no third party. **The capability worth keeping is `analyze_cycles`** (circular-import detection), which nothing in `tools/` provides; the honest fix is to reimplement it on the parser that already works rather than carry a dependency on an uninstalled binary. Note also: its `entry_points` set (:188-194) is the second filename-inventory that FINDING 4 warns about |
| `manual_tools/analysis/audit_cods.py` | considered_dead | NAMED-ONLY — `analyze_dependencies.py:193` (entry-point *list*) | undocumented SQL poke at CODS tables | — |
| `manual_tools/analysis/audit_prestige_system.py` | preserve | NAMED-ONLY — `manual_tools/README.md:28` | `PrestigeAuditor`: distribution stats, outliers, "parasites", unbounded-growth and negative-value checks, dampening effectiveness | **Pathology detection on a reputation currency.** Nearest live: `engines/egocentric/standing.py` maintains standing but never audits its own distribution. A currency with no outlier check is a currency that can silently run away |
| `manual_tools/analysis/autopoiesis_monitor.py` | preserve | NAMED-ONLY — `architecture/traceability/README.md:15` | four self-production metrics — `calculate_emergence_gain`, `calculate_identity_drift`, `calculate_control_error`, `calculate_loop_detection_score` — plus `get_system_health`, `get_metric_trend`, and **`detect_regime_change(generation, window=20)`** | **Identity drift and regime change.** Nearest live: NONE for either. "Am I still the same system I was 20 windows ago, and did something discontinuous just happen" is a question the live stack cannot currently ask |
| `manual_tools/analysis/console_metrics_capture.py` | preserve | LAZY — `manual_tools/analysis/oracle_health_monitor.py:40` (inside `try: … except ImportError`) | 857 lines. `ReasoningLogCapture` records reasoning payloads **in-process** and runs live diagnostics on them; `ConsoleMetricsCapture` aggregates per-game and per-generation (CODS activations, escape attempts, sequence replays, stuck detections, actions) | **In-process instrumentation instead of post-hoc log parsing.** Nearest live: fabric JSONL streams read after the fact by `tools/beat_rates.py`. This measures while the decision is being made, which is the only place a reasoning payload still exists |
| `manual_tools/analysis/diagnose_reasoning.py` | considered_dead | NAMED-ONLY — `analyze_dependencies.py:188` | one-shot diagnostic for why primitives/reasoning under-fire | era-specific; superseded by the oracle checks below |
| `manual_tools/analysis/gameplay_analyzer.py` | considered_dead | **NAMED-ONLY** (inventory said OBSCURE-E via `cleanup_temp_files.py:56` — that is the KEEP whitelist, C1) | per-generation gameplay stats with `--hours`/`--generations`/`--compare` | superseded by `tools/beat_rates.py` |
| `manual_tools/analysis/network_health_report.py` | preserve | NONE | thirteen network metrics: population, emergence gain, **role saturation**, sequence health, **information velocity**, game performance and type breakdown, frontier status, CODS status, cognitive development, frustration, prestige distribution | **Collective-level metrics with no live counterpart.** `tools/beat_rates.py` covers per-game rates; role saturation (is the population over-specialised) and information velocity (how fast does a finding cross the network) exist nowhere in the live stack |
| `manual_tools/analysis/optimization_threshold_system.py` | preserve | **NAMED-ONLY** (inventory said OBSCURE-E via `cleanup_temp_files.py:100` — KEEP whitelist, C1) | `optimization_status` table keyed **(game_id, level_number)**: `is_level_optimized`, `get_best_sequence_for_level`, `get_optimization_targets`, stale-status cleanup | **Per-LEVEL "stop optimising this, it is done".** This is the `sequence_miner` genus — the live `retention.RetentionStore` tags `(game, level)` as a scope but has no notion of a level being *finished*. Without it, effort has no terminating condition per level |
| `manual_tools/analysis/oracle_health_monitor.py` | **preserve — the headline** | NAMED-ONLY — `architecture/traceability/README.md:15` | 1812 lines. Seven typed pathologies (`PathologyType`: stagnation, blind play, CODS inactive, sequences unused, premature termination, no unlocks, action waste); six health checks; **and a complete closed intervention loop** — `select_experiment` → `start_experiment` → `_apply_experiment` (:1431, writes the actual config: unlocks a primitive, lowers a threshold, raises a budget multiplier) → `should_evaluate_experiment` → `evaluate_experiment` (:1268, verdict `success`/`failure`/`inconclusive` from measured improvement, ±0.05) → **`_rollback_experiment` (:1486) on failure, restoring `old_value`** → `_update_patterns` (:1589, per-(pathology, intervention) success/failure counts) → `_create_experiment_from_pattern`. Tables: `oracle_experiments`, `oracle_interventions`, `oracle_patterns`. Also `get_bug_investigation_prompt` — emits an LLM-ready prompt for a detected reasoning bug | **PROMOTION AND ROLLBACK ON EVIDENCE — and it is here, not in `ab_testing`.** (I searched: **no `ab_testing` module exists anywhere in this slice**; `engines/cognition/ab_testing.py` is outside it.) Nearest live: `lp_drive.assign_arm` assigns an arm and `tools/control_arm.py` fixes one — the build can assign and can do neither of the other two. This module additionally does what `ab_testing` does not: it **learns which intervention fixes which pathology** and proposes the next experiment from that table. Bears directly on mandate item 4 |
| `manual_tools/analysis/oracle_stuck_game_diagnostics.py` | preserve | NAMED-ONLY — `record/findings/FORGOTTEN_CAPABILITIES.md:43` | `check_stuck_games` then `diagnose_stuck_game`, walking tiers 1-3, 4, 5, 6 in order to find **which tier the learning chain broke at**; `get_learning_health_summary` | **Locating the break, not detecting the stall.** Nearest live: `starvation.py` detects starvation; `frontier.py` books deaths. Neither answers "at which rung did the chain stop", which is FIGURE 3's question — a reading below the break is a reading of nothing |
| `manual_tools/analysis/pariah_analysis.py` | considered_dead | NAMED-ONLY — `manual_tools/README.md:29` | one-off analysis-paralysis check on the pariah system | superseded by `pariah_validator.py` below |
| `manual_tools/analysis/pariah_validator.py` | preserve | NAMED-ONLY — `architecture/traceability/README.md:18` | validates every active pariah (blacklisted thing) against a cache of actual winning sequences; **`_increment_false_positive`**, `_deactivate_pariah` when falsified, `_cleanup_stale_awareness`, `record_pariah_success` | **A blacklist that is measured being wrong.** Nearest live: `falsified_ledger.py` records falsifications but does not keep a false-positive rate *per blacklist entry* and does not retire an entry on it. A permanent blacklist with no false-positive accounting is how a system talks itself out of the only move that works |
| `manual_tools/analysis/performance_analyzer.py` | **live** | **LAZY, from a live entrypoint** — `evolutionary_engine.py:464`, `from manual_tools.analysis.performance_analyzer import PerformanceAnalyzer`, inside `_calculate_diversity_fitness_component` | population statistics, top performers, improvement rate, comprehensive success rate, **`calculate_diversity_fitness`** (the method the live caller wants), win-rate/score-efficiency/health trends, `_detect_stagnation_indicators`, strategy effectiveness + recommendations | The one live-path file in the slice. **Caveat for the GM:** the call site wraps the import in `except Exception` and returns `0.0`, so an ImportError here is indistinguishable from a genuine zero diversity score. It imports `numpy` at module level (:16); `numpy` is present in `.venv` and in `requirements.txt`, so it resolves today — but nothing would report it if it stopped |
| `manual_tools/analysis/pipeline_health_check.py` | preserve | NONE | seven named detectors for the exact silent-pipeline bugs of one prior session: fitness disconnection (results written, performance table empty ⇒ **evolution has zero selection signal**), population bloat, coordinate blacklisting, fallback monopoly, counter inflation, session integrity, sequence utilisation; plus `apply_auto_fixes` / `fix_population_bloat` | **Regression tests for defects that produce no error.** Nearest live: `tests/gate/**` asserts on code shape; these assert on *data shape in a running database*. Check 1 alone catches the failure where evolution runs for N generations on no signal at all |
| `manual_tools/analysis/prestige_parasite_detector.py` | preserve | **NAMED-ONLY** (inventory said OBSCURE-E via `cleanup_temp_files.py:104` — KEEP whitelist, C1) | detects agents accruing prestige without contributing; **`calculate_knowledge_transfer_rate`** per agent; `recommend_sunset`; **`archive_agent_reasoning` before sunsetting** | **Contribution measured as transfer, and archived before retirement.** Nearest live: `standing.py` / retirement paths retire on performance. Nothing asks "did anything this agent learned reach anyone else", and nothing preserves an agent's reasoning at the moment it is retired |
| `manual_tools/analysis/sequence_pruning_system.py` | preserve | **NAMED-ONLY** (inventory said OBSCURE-E via `cleanup_temp_files.py:77` — KEEP whitelist, C1) | scores every banked sequence, deactivates the bad ones, **records a pruning event per removal** with the reason, and reports `get_pruning_stats` | **Garbage collection for the library, with receipts.** Nearest live: `mastery.py` gates *replay* of a sequence; nothing removes one. A library that only grows eventually costs more to search than it returns, and there is currently no instrument that would show that happening |
| `manual_tools/analysis/theory_alignment_checker.py` | preserve | NAMED-ONLY — `analyze_dependencies.py:194` | declares `TheoryRequirement`s (expected behaviour + `test_query` + `code_locations` + `database_tables`), runs each query, grades ALIGNED/DIVERGED, `_check_code_location` by AST, and emits a `generate_fix_plan`. Separately: an **incremental console-log review cursor** — `get_last_checked_timestamp`, `get_new_warnings_and_errors`, `mark_logs_as_reviewed`, `categorize_errors` | **Executable specification.** Nearest live: `record/prereg/*.md` states requirements in prose and `tests/gate/**` asserts on source; nothing runs a *query* against the live database and grades the system against a stated theory. The log cursor is separately valuable: "everything new since I last looked" is a primitive the beat currently lacks |
| `manual_tools/analysis/theory_analysis.py` | considered_dead | NAMED-ONLY — `manual_tools/README.md:31` | ad-hoc SQL version of the above | superseded by `theory_alignment_checker.py` |
| `manual_tools/analysis/theory_verification.py` | considered_dead | NAMED-ONLY — `manual_tools/README.md:30` | checks DB alignment with a named theory doc | superseded by `theory_alignment_checker.py` |

### `manual_tools/database/` — 8 files · live 0 · preserve 1 · considered_dead 7

Seven of the eight are single-purpose SQL pokes at the winning-sequence tables, written
during one debugging episode; four of them **mutate** the sequence table.

| path | dest | reached-by (with the site) | what it does | preserve: capability, and why it may matter |
|---|---|---|---|---|
| `manual_tools/database/check_all_sequences.py` | considered_dead | NAMED-ONLY — `analyze_dependencies.py:191` | lists sequences that "should be reactivated" | — |
| `manual_tools/database/check_game_ids.py` | considered_dead | NAMED-ONLY — `analyze_dependencies.py:191` | inspects id patterns in the sequence table | — |
| `manual_tools/database/check_sequences.py` | considered_dead | NAMED-ONLY — `analyze_dependencies.py:191` | sequence status for two specific games | — |
| `manual_tools/database/compact_database.py` | preserve | NONE | `VACUUM INTO` a new file then swap — reclaims space needing **1× free space, not 2×** as plain `VACUUM` does | **The one reclaim mechanism that fits inside the disk ceiling.** `tools/disk_ceiling.py` gates at 30 GB and does archive-then-truncate on *files*; it cannot shrink a bloated sqlite file, and plain `VACUUM` needs headroom a box at the ceiling does not have by definition |
| `manual_tools/database/fix_sequences.py` | considered_dead | NAMED-ONLY — `analyze_dependencies.py:190` | **mutates**: reactivates the best sequence per game/level | one-off repair, superseded by `optimization_threshold_system.get_best_sequence_for_level` |
| `manual_tools/database/reactivate_best_sequences.py` | considered_dead | NAMED-ONLY — `analyze_dependencies.py:192` | **mutates**: same, for games with missing/deactivated sequences | — |
| `manual_tools/database/reactivate_sequences.py` | considered_dead | NAMED-ONLY — `analyze_dependencies.py:192` | **mutates**: same again, plus a deactivation-source investigation | — |
| `manual_tools/database/schema_inspector.py` | considered_dead | **NAMED-ONLY** (inventory said OBSCURE-E via `cleanup_temp_files.py:57` — KEEP whitelist, C1) | tables, per-table info, row counts, samples, full dump, and `--find <column>` across all tables | superseded by `tools/dump_schema.py`; the one thing it adds is `find_tables_with_column`, worth a five-line port rather than a preserve |

### `manual_tools/monitoring/` — 2 files · live 0 · preserve 0 · considered_dead 2

| path | dest | reached-by (with the site) | what it does | preserve: capability, and why it may matter |
|---|---|---|---|---|
| `manual_tools/monitoring/review_scorecards.py` | considered_dead | NAMED-ONLY — `manual_tools/README.md:94` | `ScorecardReviewer` intended to drive a browser over the scorecard page and grade playbacks | **A shell, not a capability.** Every browser step is an unimplemented stub — `# This would be implemented using browser_subagent` (:51), `# This would use browser_subagent to:` (:66, :101), and `main()` prints "[IDEA] To integrate with browser automation" (:213). Nothing here executes |
| `manual_tools/monitoring/system_status_report.py` | considered_dead | NAMED-ONLY — `manual_tools/README.md:93` | one-shot "are all phases integrated" check | phase-era artefact |

### `manual_tools/utilities/` — 13 files (12 + 1 dot-file) · live 1 · preserve 2 · considered_dead 10

| path | dest | reached-by (with the site) | what it does | preserve: capability, and why it may matter |
|---|---|---|---|---|
| `manual_tools/utilities/.vulture_whitelist.py` | **live (by constraint)** | NAMED-ONLY — `record/findings/FORGOTTEN_CAPABILITIES.md:84` | vulture ignore-list for intentionally-unused code (context-manager signatures, documented placeholders, seed primitives) | Dot-prefixed; the rubric excludes it from any move. Examined and left where it is |
| `manual_tools/utilities/abstraction_schema.py` | considered_dead | **NAMED-ONLY** (KEEP whitelist, `cleanup_temp_files.py:106` — C1) | `CREATE TABLE`s the abstraction tables and verifies them | one-time DDL |
| `manual_tools/utilities/cleanup_temp_files.py` | considered_dead | NAMED-ONLY — `analyze_dependencies.py:193` | pattern-based temp-file deletion guarded by `SKIP_DIRS` and a 60-entry `KEEP_FILES` whitelist | **Actively hazardous to keep reachable.** Superseded by `safe_cleanup.py` (lazy from `tools/swarm_supervisor.py:178`), and its whitelist is provably stale — it names `autonomous_evolution_runner.py`, `breakthrough_detector.py`, `run_evolution.py`, `ouroboros_coordinator.py`, all verified absent. It is also the source of C1's 14 mis-tiered rows |
| `manual_tools/utilities/enhanced_database_interface.py` | considered_dead | **NAMED-ONLY** (KEEP whitelist, `cleanup_temp_files.py:113` — C1) | 89-line subclass wiring `schema_auto_maintenance` into query execution | thin wrapper |
| `manual_tools/utilities/evolution_with_parasites.py` | considered_dead | **NAMED-ONLY** (KEEP whitelist, `cleanup_temp_files.py:94` — C1) | runs evolution with parasite detection interleaved | **cannot import**: module-level `import autonomous_evolution_runner`, verified absent from the tree |
| `manual_tools/utilities/get_replay_url.py` | considered_dead | NAMED-ONLY — `manual_tools/README.md:104` | builds a scorecard URL from a session id | superseded by `tools/replay_viewer.py` |
| `manual_tools/utilities/migrate_mastery_system.py` | considered_dead | NONE | one-time hard reset of all sequences to NOVICE, with `dry_run` / `show_status` / `execute_migration` | self-declared ONE-TIME migration, already applied |
| `manual_tools/utilities/pycache_guard.py` | considered_dead | NAMED-ONLY — `analyze_dependencies.py:194` | walks the tree for `__pycache__` and exits non-zero | superseded — `pytest.ini` records that `conftest.py`'s `sessionfinish` hook enforces this |
| `manual_tools/utilities/quick_check.py` | considered_dead | NAMED-ONLY — `analyze_dependencies.py:189` | post-run telemetry spot-check | superseded by `observer_dashboard.py` |
| `manual_tools/utilities/remove_emojis.py` | considered_dead | NAMED-ONLY — `manual_tools/README.md:105` | strips emoji from `.py` files to avoid Windows cp1252 encode crashes | genuinely platform-relevant, but a 30-line regex codemod — cheaper to rewrite than to carry |
| `manual_tools/utilities/revive_agents.py` | preserve | **NAMED-ONLY** (KEEP whitelist, `cleanup_temp_files.py:93` — C1) | `AgentRevivalSystem`: three typed triggers — `_detect_performance_regression` (a game previously solved is being lost again), `_detect_diversity_collapse`, `_detect_specialist_need` — each selecting candidates from an agent **archive**, then `revive_agent` / `process_revival_triggers` / `mass_revive_inactive_agents` | **Retirement is reversible on evidence.** Nearest live: the build retires agents and has no path back. This is the population-level twin of the oracle's `_rollback_experiment`: the two mechanisms that let a decision be undone when the evidence turns, and neither is reachable |
| `manual_tools/utilities/run_context.py` | preserve | NAMED-ONLY — `legacy/tests_dead_lineage/test_action_ladder.py:17` | typed attempt-scoped state: `BudgetState`, `HeartbeatState`, `GuardState`, and `RunContext` carrying `mode` (LIVE / REPLAY_VALIDATION / EVAL), the three weights, **`sequence_source_id` / `operator_source_id` / `source_mode`**, `attention_windows`, and `guard_snapshot()`. Purely in-memory by design ("Guard enforcement and DB writes remain outside") | **Provenance of the action, as a typed field.** Nearest live: `ContextBuilder`'s `DecisionContext` dict plus locals in `cognitive_loop.py`. The three `*_source_id` / `source_mode` fields answer "where did this action come from — a banked sequence, an operator, or a fresh decision" as data rather than by inference; `guard_snapshot()` makes the three guards inspectable at any step. Cited by `architecture/runtime/README.md` |
| `manual_tools/utilities/test_pariah_decay.py` | considered_dead | NAMED-ONLY — `manual_tools/README.md:106` | validates pariah decay and role-adjusted tolerance | one-shot validation of a shipped change |

### `legacy/` (root) — 19 files · live 0 · preserve 4 · considered_dead 15

| path | dest | reached-by (with the site) | what it does | preserve: capability, and why it may matter |
|---|---|---|---|---|
| `legacy/_investigate_fast.py` | considered_dead | NAMED-ONLY — `record/findings/FORGOTTEN_CAPABILITIES.md:77` | indexed-subset queries from one closed investigation | — |
| `legacy/_investigate_monopoly.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:77` | rung-monopoly / coordinate-fixation probe; docstring says "Temporary" | — |
| `legacy/_investigate_part2.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:77` | 30-line follow-up query | — |
| `legacy/_investigate_part3.py` | considered_dead | NAMED-ONLY — `tests/gate/test_origin_marker.py:258` names the `_investigate` **prefix in a skip list** (C2) | rung monopoly from routing traces | — |
| `legacy/_investigate_part4.py` | considered_dead | NAMED-ONLY — same skip-list prefix | per-game action-cap investigation | — |
| `legacy/_investigate_part5.py` | considered_dead | NAMED-ONLY — same skip-list prefix | routing rung-monopoly deep dive | — |
| `legacy/_temp_check.py` | considered_dead | **NAMED-ONLY, in a SKIP list** — `tests/gate/test_origin_marker.py:257` (C2) | "delete after use" system-state check; its own docstring says so | — |
| `legacy/adaptive_action_limits.py` | preserve | **NAMED-ONLY** (inventory said invocation via `theory_alignment_checker.py:630` — that is a `code_locations` string, C4) | 1228 lines. `AdaptiveActionLimits`: generation performance, limit adjustment with logged reasons, and **`calculate_agent_salary`** — a per-agent action budget on an explicitly separate currency from prestige (":363 Prestige = Social Capital … Actions = Economic Capital … NEVER mix them"), with role multipliers, network-role-need adjustment (±0.3), a **growth-based** progress bonus, a low-start boost, a stagnation penalty for high-starters who coast, and an unbeaten-game bonus | **A two-currency economy where effort is metabolic and reputation is social.** Nearest live: `betting.py` prices a bet, `pricing.py` prices a hypothesis, `standing.py` holds reputation — all one currency. Nothing issues an *action budget* as a distinct resource, so a high-standing agent cannot currently be starved of actions, nor a struggling one subsidised. The growth-based bonus is separately notable: it pays the derivative, not the level |
| `legacy/agent_factory.py` | considered_dead | NAMED-ONLY — `legacy/tests_dead_lineage/test_agent_factory.py:23` (a test that pytest does not collect — `pytest.ini` `testpaths = tests`) | five agent archetypes with genomes, epigenetics, `create_agent_from_parents`, `_crossover_genomes`, `_determine_offspring_type`, and per-archetype action selection | superseded: `evolutionary_engine.py` (live) owns breeding, and the rung ladder replaced per-archetype action selection |
| `legacy/agent_self_model.py` | considered_dead | NAMED-ONLY — `legacy/tests_dead_lineage/test_metacog_eliminations.py:16` (uncollected) | 64-line pure compatibility shim re-exporting nine classes from their canonical engine homes | **Before any move: its docstring is the only record in the tree of how a 15,513-line, 9-class monolith was split across nine engine modules.** The code is redundant; the map is not. Copy the docstring into `record/` first |
| `legacy/arc_api_client.py` | considered_dead | **NAMED-ONLY** (KEEP whitelist, `cleanup_temp_files.py:63` — C1) | async `aiohttp` ARC client: scorecard open/close, reset game/level, send action, tags | superseded by the live `arc_api_adapter.py`, which carries `create_scorecard`/`get_scorecard` (:623, :656). Also **cannot import**: `aiohttp` verified absent from `.venv` |
| `legacy/automated_assessment_runner.py` | preserve | **NAMED-ONLY** (KEEP whitelist, `cleanup_temp_files.py:92` — C1) | `run_post_generation_assessment` runs **eight named assessments** (level completion, abstraction usage, breakthrough momentum, sequence validation, prestige distribution, matching pipeline, subgoal planning, resonance detection), generates recommendations, **stores** the assessment, and offers `get_trend_analysis` over stored assessments | **A scheduled self-assessment that is stored and trended.** Nearest live: `outcome_processor.py` handles one episode; `engines/postgame/**` is the intended pipeline and is itself a dead island (inventory FINDING 3). This is the one file in the tree that runs a fixed battery *after every generation* and can compare today's answer to last week's |
| `legacy/console_tags.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:82` | `log`/`log_ok`/`log_warn`/`log_error` + row formatters for consistent console tags | unused; the codebase logs directly |
| `legacy/core_gameplay.py` | considered_dead | **NONE** — its only importer, `__init__.py:32`, is broken and swallowed (C3) | `GameplayEngine`, a thin wrapper over `GamePlayer` (sync) and `GameLoop` (async) | **Self-declared deprecated in its own docstring**: ".. deprecated:: … All production game-playing flows through `game_player.py` directly. No production code imports this module." |
| `legacy/disk_space_monitor.py` | considered_dead | **NAMED-ONLY** (KEEP whitelist, `cleanup_temp_files.py:114` — C1) | `check_disk_space_or_abort`, `get_table_sizes`, `suggest_cleanup_actions` | superseded by `tools/disk_ceiling.py`, which gates rather than warns. The one uncovered piece is `get_table_sizes` — per-*table* byte attribution inside the DB, where `disk_ceiling` accounts per file. Worth a note, not a preserve |
| `legacy/evolution_game_scheduler.py` | preserve | **NAMED-ONLY** (KEEP whitelist, `cleanup_temp_files.py:112` — C1) | assigns games to agents, reorders the queue by **resonance priority** (`_get_resonance_game_priorities`, `_reorder_games_by_resonance`), then `record_scheduling_outcome` and **`get_scheduling_effectiveness`** | **A scheduler that scores its own assignments.** Nearest live: `engines/egocentric/scheduler.py` decides *when to engage the planner*, not *which game to give which agent*, and nothing measures whether an assignment was a good one afterwards. Preserve together with `game_scheduler.py` — it subclasses it |
| `legacy/game_loop.py` | considered_dead | **NONE** — reached only from `legacy/core_gameplay.py:60`, which is itself unreached (C3) | clean async state machine `STARTING → PLAYING → [LEVEL_COMPLETE] → GAME_WON/GAME_OVER → FINISHED`, plus a `SyncGameLoop` | superseded by `game_player.py` / `cognitive_loop.py`. **Cross-reference:** this is the module `engines/postgame/**` names in its own docstrings as its intended caller (inventory FINDING 3) — the missing half of that island is here, and it is dead too |
| `legacy/game_scheduler.py` | preserve | NAMED-ONLY — `legacy/evolution_game_scheduler.py:25` is a real module-level import, but from an unreached module | base `GameScheduler`: per-agent game selection with priority rules, stale-game cleanup, active-game tracking, `get_stats` | Carried only because `evolution_game_scheduler.py` (above) subclasses it; splitting them breaks the preserved capability |
| `legacy/learning_systems.py` | considered_dead | **NONE** — reached only from `legacy/core_gameplay.py:61` (C3) | one lazy-loading façade over CODS, replay learning, self-model, terminal detection and the primitive suggester, with `on_game_start` / `on_game_end` / `update` hooks | superseded — `cognitive_loop.py` does this inline for the live stack |

### `legacy/manual_tools/` — 13 files · live 0 · preserve 2 · considered_dead 11

All thirteen are era-specific one-shot SQL scripts, already assessed at
`record/findings/FORGOTTEN_CAPABILITIES.md:75-82`; I re-read each and agree with that
assessment for eleven of them. The two exceptions are the pair that document itself flags.

| path | dest | reached-by (with the site) | what it does | preserve: capability, and why it may matter |
|---|---|---|---|---|
| `legacy/manual_tools/analyze_decision.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:80` | 66-line decision-system SQL probe | — |
| `legacy/manual_tools/check_api.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:80` | SDK/game-flow smoke check | — |
| `legacy/manual_tools/check_gen2.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:78` | routing-trace summary for one generation | generation-pinned |
| `legacy/manual_tools/check_gen2b.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:78` | same, with corrected column names | generation-pinned |
| `legacy/manual_tools/check_terminal_patterns.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:80` | inspects a death-pattern table; its own docstring records that the table it was written for was removed in Jan 2026 | — |
| `legacy/manual_tools/debug_routing.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:80` | monkey-patches the router to trace one specific error | — |
| `legacy/manual_tools/diagnosis_query.py` | preserve | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:81` | 321 lines: "analyze what the system has learned **across generations**" — a sectioned cross-generation learning report | **A cross-generation learning query.** `FORGOTTEN_CAPABILITIES.md:81` itself calls this pair "the largest here — **worth one read before removal**, because a cross-generation learning query is close to the split-half question". I did the read and it is: this asks whether generation N knows more than generation N−k, which `tools/split_half.py` asks only within a run. Preserve until the query it encodes is ported |
| `legacy/manual_tools/diagnosis_query_part2.py` | preserve | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:81` | 266 lines: routing traces, action patterns and root-cause analysis, continuing the above | Second half of the same query; useless apart from it |
| `legacy/manual_tools/find_tables.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:79` | 14-line table lister | `tools/dump_schema.py` |
| `legacy/manual_tools/gen_analysis.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:80` | knowledge-transfer check for one generation | generation-pinned |
| `legacy/manual_tools/list_danger_tables.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:79` | 21-line lister of death/danger tables | `tools/dump_schema.py` |
| `legacy/manual_tools/trace_check.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:78` | finds traces for one named generation | generation-pinned |
| `legacy/manual_tools/trace_deep_dive.py` | considered_dead | NAMED-ONLY — `FORGOTTEN_CAPABILITIES.md:78` | epistemic-regression dive for one named generation | generation-pinned |

### `legacy/tests_dead_lineage/` — 6 files · live 0 · preserve 0 · considered_dead 6

**Not protected by the rubric's `tests/` constraint** — they are under `legacy/`, and
`pytest.ini` sets `testpaths = tests`, so **none of these is collected by any test run.**
Two of them are also self-disabled in their own header comments.

| path | dest | reached-by (with the site) | what it does | preserve: capability, and why it may matter |
|---|---|---|---|---|
| `legacy/tests_dead_lineage/test_action_ladder.py` | considered_dead | NAMED-ONLY — `vulture_whitelist.py:63` | four action-ladder / fallback tests against `core_gameplay` | header comment: "Skip until mocking infrastructure is updated to match current codebase"; imports the unreachable `legacy/core_gameplay.py` |
| `legacy/tests_dead_lineage/test_agent_factory.py` | considered_dead | NONE | 5 classes / 14 tests over `AgentFactory` on a temp DB | not collected; subject is `considered_dead` |
| `legacy/tests_dead_lineage/test_critical_systems.py` | considered_dead | NAMED-ONLY — `architecture/cognitive_routing_architecture.md:1292` | 7 `unittest` classes asserting on **live database invariants** (sequence integrity, validation rates, pioneer coverage, budget, bloat ratio, role balance) | Genuinely a different genus from the `tests/gate/**` suite — but every threshold is pinned to a 2025-12 population, it runs against the real DB, and it is uncollected. The *idea* (data-shape invariants) is preserved instead via `manual_tools/analysis/pipeline_health_check.py` |
| `legacy/tests_dead_lineage/test_metacog_eliminations.py` | considered_dead | NONE | one test over the `agent_self_model` shim | not collected |
| `legacy/tests_dead_lineage/test_recent_changes.py` | considered_dead | NAMED-ONLY — `architecture/cognitive_routing_architecture.md:1294` | 7 classes validating one 2025-12-03 session's fixes and five then-new tables | dated by construction |
| `legacy/tests_dead_lineage/test_replay_validation.py` | considered_dead | NAMED-ONLY — `record/findings/REPO_AUDIT_2026-08-20.md:61` | three replay-validation tests against `core_gameplay` | imports the unreachable `legacy/core_gameplay.py` |

---

# CAPABILITY THIS BUILD DOES NOT HAVE

**HELD. Nothing here is a recommendation and nothing was moved.** 34 entries, grouped so
the shape is visible: the slice's unreached capability is not scattered — it clusters into
five families, and the largest family is *the system acting on its own measurements*.
(Entry 34 was added by the Amendment 1 sweep and is numbered last so the earlier numbering
stays stable for anyone already reading against it.)

Each entry: **what it does · nearest live counterpart or NONE · why it might matter.**

## FAMILY A — Acting on evidence, and being able to take it back (4)

**1 · `manual_tools/analysis/oracle_health_monitor.py` — THE ENTRY THIS EXAMINATION WAS FOR.**
*What it does:* names seven pathologies, detects them from the database, selects an
intervention, **applies it to the live configuration** (`_apply_experiment`:1431 — unlocks a
primitive, lowers a threshold, raises a budget multiplier), waits, **evaluates it against
measured improvement** (`evaluate_experiment`:1268, verdict at ±0.05), **rolls it back on
failure** (`_rollback_experiment`:1486, restoring the recorded `old_value`), and then
**updates a per-(pathology, intervention) success/failure table** it uses to propose the
next experiment (`_update_patterns`:1589, `_create_experiment_from_pattern`:1666).
*Nearest live counterpart:* `lp_drive.assign_arm` — assignment only. `tools/control_arm.py`
— pins an arm. **The build can assign an arm and can neither promote nor roll one back.**
*Why it might matter:* this is the loop that closes measurement onto action. It is also
strictly more than A/B: an A/B harness learns which *arm* won this time; this learns which
*kind of intervention* fixes which *kind of pathology*, and carries that across episodes.
Mandate item 4. **Note for the GM: the brief attributed this to an `ab_testing` module — I
searched all 109 files and no `ab_testing` module exists in this slice. The capability is
here, in a 1812-line file classified NAMED-ONLY off a single line in a README.**

**2 · `manual_tools/utilities/revive_agents.py`.** *What it does:* three typed triggers —
performance regression on a previously-solved game, diversity collapse, unmet specialist
need — each selecting candidates from an agent archive, then reviving them.
*Nearest live counterpart:* **NONE.** The build retires; there is no path back.
*Why it might matter:* it is the population-level twin of entry 1's rollback. Retirement
that cannot be undone means every retirement decision must be right the first time, on
evidence that by construction has not finished arriving.

**3 · `manual_tools/analysis/pariah_validator.py`.** *What it does:* re-checks every active
pariah (blacklisted thing) against a cache of actual winning sequences, keeps a
**false-positive count per entry**, and deactivates the entry when falsified.
*Nearest live counterpart:* `falsified_ledger.py` — records falsifications, does not keep a
per-entry false-positive rate and does not retire an entry on one.
*Why it might matter:* a blacklist with no false-positive accounting is the mechanism by
which a system permanently talks itself out of the one move that works.

**4 · `manual_tools/analysis/sequence_pruning_system.py`.** *What it does:* scores banked
sequences, deactivates the bad ones, and records a pruning event with its reason.
*Nearest live counterpart:* `mastery.py` gates *replay*; nothing removes a sequence.
*Why it might matter:* the library only grows. There is currently no instrument that would
show the point at which searching it costs more than it returns.

## FAMILY B — Instruments that measure the system rather than the game (9)

**5 · `manual_tools/analysis/autopoiesis_monitor.py`.** Emergence gain, **identity drift**,
control error, loop-detection score, health history, metric trend, and
**`detect_regime_change(window=20)`**. *Counterpart:* NONE for drift or regime change.
*Why:* "am I still the same system, and did something discontinuous just happen" is
unaskable today; a regime change currently presents as noise in a rate.

**6 · `manual_tools/analysis/network_health_report.py`.** Thirteen collective metrics;
**role saturation** and **information velocity** have no live analogue. *Counterpart:*
`tools/beat_rates.py` (per-game rates). *Why:* over-specialisation of the population, and
the speed at which a finding crosses the network, are properties of the collective that
per-game rates cannot express.

**7 · `manual_tools/analysis/oracle_stuck_game_diagnostics.py`.** Walks tiers 1-3, 4, 5, 6
in order to locate **which tier the learning chain broke at**. *Counterpart:*
`starvation.py` detects the stall; `frontier.py` books the deaths — neither locates the
break. *Why:* FIGURE 3 — a reading below the break is a reading of nothing, so knowing
*where* the break is determines which readings are meaningful.

**8 · `manual_tools/observer_dashboard.py`.** Ten sections over one database, including
gaps/interventions and metacognitive health (predictions, assumptions, theories).
*Counterpart:* `tools/beat_rates.py`, deliberately narrow. *Why:* the wide read and the
narrow read answer different questions; sections 6 and 7 have no live equivalent at all.

**9 · `manual_tools/profile_baseline.py`.** Per-rung avg / max / **p95** latency, per-rung
memory via `tracemalloc`, context reads/writes per decision, decisions per second.
*Counterpart:* `tools/d5_profile_wrapper.py` profiles a run, not a rung. *Why:* mandate
item 2. You cannot decide what to cut from a ladder without a per-rung cost.

**10 · `manual_tools/analysis/console_metrics_capture.py`.** Captures reasoning payloads
**in-process** and runs live diagnostics on them; aggregates per game and per generation.
*Counterpart:* fabric JSONL read after the fact. *Why:* the reasoning payload exists only
while the decision is being made; after that only its shadow is on disk.

**11 · `lab/code_tracer.py`.** Discovers which subsystems actually engaged, from traces,
with subsystem names discovered at runtime. *Counterpart:* `tools/live_coverage_diff.py`,
`tools/consumption_sweep.py` — both read source. *Why:* "was it wired" and "did it fire"
are different questions and the tree can currently only answer the first.

**12 · `manual_tools/analysis/audit_prestige_system.py`.** Outliers, unbounded growth,
negative values, dampening effectiveness over a reputation currency. *Counterpart:*
`standing.py` maintains standing but never audits its own distribution. *Why:* an
unaudited currency can run away without any single step looking wrong.

**13 · `lab/metrics.py`.** Five metrics from one table, with `_discover_columns` so the
contract survives schema drift. *Counterpart:* `tools/beat_rates.py`, bound to fabric
streams and per-box databases. *Why:* a measurement that is portable across boxes and
branches is what makes a *comparison* possible; the current beat is per box by design.

## FAMILY C — Finding what is broken when nothing raises an error (6)

**14 · `manual_tools/audit_data_usage.py`.** Thirteen audits, each simulating a retrieval
function against the real database to find rows that exist and are silently dropped by a
guard or a threshold. *Counterpart:* `tools/consumption_sweep.py` — static AST pairing,
which proves a reader exists. *Why:* pairing cannot see a reader that ran and returned
nothing, which is the entire failure mode.

**15 · `manual_tools/scan_disconnection_patterns.py`.** The static half of the same pair:
six source idioms that silently drop data. *Counterpart:* `tools/socket_or_filler_lint.py`,
`tools/ood_lint.py` — different patterns. *Why:* together with 14, a matched static/runtime
pair for one defect genus. Neither half is reachable.

**16 · `manual_tools/analysis/pipeline_health_check.py`.** Seven detectors for silent
pipeline bugs; check 1 catches **evolution running with zero selection signal**.
*Counterpart:* `tests/gate/**` asserts on code shape. *Why:* these assert on *data shape in
a running database* — the class of defect that produces correct-looking logs for N
generations.

**17 · `manual_tools/audit_orphaned_systems.py`.** Engines registered but never accessed;
rungs reading keys nobody sets; tables never written; methods never called; features
documented but not implemented. *Counterpart:* this document; `tools/repo_assess.py` (also
dead). *Why:* it is this examination as a program rather than as a periodic sweep.

**18 · `manual_tools/scan_context_keys.py`.** 61 lines diffing keys read by rungs against
keys provided by `ContextBuilder`. *Counterpart:* NONE. *Why:* already on record as having
found a live defect on its first run — the best value-per-line in the slice.

**19 · `manual_tools/analysis/theory_alignment_checker.py`.** Requirements as data
(expected behaviour + test query + code locations + tables), graded ALIGNED/DIVERGED with a
generated fix plan; **plus an incremental log-review cursor** (`get_last_checked_timestamp`
/ `get_new_warnings_and_errors` / `mark_logs_as_reviewed`). *Counterpart:* `record/prereg/`
states requirements in prose; `tests/gate/**` asserts on source. *Why:* nothing runs a
query against the live database and grades the system against a stated theory. And
"everything new since I last looked" is a primitive the beat does not have.

**34 · `manual_tools/analysis/analyze_dependencies.py`** *(added by the Amendment 1 sweep —
C7).* *What it does:* full / cycles / core / reasoning / orphans / stats dependency graphs,
via `pydeps` + Graphviz. *Nearest live counterpart:* `CODEBASE_INVENTORY.md` covers orphans
with a stdlib `ast` parser; **nothing anywhere covers `analyze_cycles`** — circular-import
detection has no instrument in `tools/`. *Why it might matter:* this is the sharpest single
finding of the amendment sweep and it is not really about the file. `checklists/code_reviewer.md:9`
makes running it a **required checkbox of every code review**, and `pydeps` has never been
installed in `.venv`, so **the repo's mandated orphan check has itself been an orphan** —
a checkbox that reports nothing, ticked by process rather than by result. The capability
worth keeping is the cycle detector; the finding worth keeping is that a gate can be
mandated, documented, and inert at the same time, and only a dot-directory search reveals it.

## FAMILY D — Discovering, and falsifying, the system's own structure (4)

**20 · `manual_tools/validate_inferred_edges.py`.** Cycle detection, orphan rungs,
contradicting edges, confidence distribution — over the graph produced by
`engines/cognition/edge_inference.py`, which it imports at module level (:36).
*Counterpart:* NONE. *Why:* **verified closed loop, neither half reachable.** The engine
discovers the system's own wiring; this catches it discovering wrong. Without the second
half the first half is unfalsifiable and therefore unusable.

**21 · `manual_tools/check_deliberation_traces.py`.** Reads the deliberation-audit traces.
*Counterpart:* NONE — its writer, `engines/reasoning/deliberation_audit.py`, is lazy-only
from `decision_rung_system.py:627`. *Why:* **a second writer/reader pair with neither half
reachable.** Two independent instances of the same genus in one slice is a pattern, not an
accident: the reader is written last and never wired, so the writer's output is never read
and the writer looks unnecessary.

**22 · `manual_tools/infer_answerable_by.py`.** Inverts the rung read-matrix into "which
questions are answerable by whom", with a Rumsfeld taxonomy. *Counterpart:* NONE. *Why:*
derived from structure, so it cannot drift from the structure the way a hand-maintained
list does.

**23 · `manual_tools/_extract_rungs.py`.** A rung census by regex — **and the tree's only
live cross-repo edge.** Line 5 hard-codes
`c:\Users\Admin\Documents\GitHub\BitterTruth-AI\decision_rung_system.py`. *Counterpart:*
NONE. *Why:* **I searched all 109 files for other absolute or cross-repo paths and there are
none — this is the single hit.** Its value is not the census; it is the standing proof that
this tree cannot enumerate its own habitat alone (inventory FINDING 5). It should not be
lost quietly.

## FAMILY E — Experiment memory, and the economy (10)

**24 · `lab/trend_tracker.py`.** Experiment memory: hypothesis, before/after metrics,
outcome per experiment; `check_readiness`; `detect_convergence`. *Counterpart:*
`record/log/PORT_LOG.md` — prose, held by hand. *Why:* mandate items 3 and 5 in code — a
rate, and an automatic "this has been flat for N". **Verified against the standing verdict:**
`tools/beat_rates.py:85-107` declined to call it on four counts and `tests/gate/test_beat_rates.py:512`
enforces that citation. All four are true — its convergence is indexed by GENERATION over
`lab_metric_snapshots`; every public entry point calls `ensure_schema()` which `CREATE TABLE`s
and commits (confirmed at `trend_tracker.py:90/166/208/222/279/342`); `DB_PATH` is one
repo-root database; and CONVERGED ≠ STALLED. **None of the four is about the capability.**
What the fleet lacks is not a convergence test at generation grain — it is *any* durable,
queryable record that experiment X was tried, with hypothesis H, and moved metric M by δ.

**25 · `lab/comparative_analyst.py`.** Cohorts by success/failure, every numeric feature
ranked by **Cohen's d**. *Counterpart:* `tools/split_half.py` — one statistic, one
direction. *Why:* effect size over *all* discovered features tells you how big the gap is
and which feature owns it; a single hand-picked statistic tells you only its sign.

**26 · `lab/branch_breeder.py`.** Combinatorial crossbreeding of successful *experiment
branches* via git. *Counterpart:* NONE. *Why:* the build breeds agent genomes; nothing
combines two successful *changes*.

**27 · `lab/evolution_runner_wrapper.py`.** Branch → run → before/after metrics, as a
structured result. *Counterpart:* `tools/control_arm.py` pins an arm; nothing runs a branch
and returns a paired measurement. *Why:* it is the harness the other three lab modules
assume; without it 24-26 have no input.

**28 · `legacy/adaptive_action_limits.py`.** A two-currency economy: prestige is social
capital, **actions are metabolic capital**, explicitly never mixed; per-agent salary with
role multipliers, network-need adjustment, a growth-based progress bonus, a low-start boost
and a stagnation penalty. *Counterpart:* `betting.py` / `pricing.py` / `standing.py` — one
currency. *Why:* with a single currency, a high-standing agent cannot be starved of actions
and a struggling one cannot be subsidised. Paying the *derivative* (growth) rather than the
level is the part that is hardest to re-derive and easiest to get wrong.

**29 · `legacy/automated_assessment_runner.py`.** Eight named assessments run after every
generation, stored, and trended. *Counterpart:* `outcome_processor.py` handles one episode;
`engines/postgame/**` is the intended pipeline and is itself a dead island. *Why:* the only
file in the tree that runs a fixed battery on a schedule and can compare today's answer to
last week's.

**30 · `legacy/evolution_game_scheduler.py`** (+ **`legacy/game_scheduler.py`**, its base —
carried only to keep it whole). Assigns games to agents, reorders by resonance priority,
then records the outcome and reports **`get_scheduling_effectiveness`**. *Counterpart:*
`engines/egocentric/scheduler.py` decides when to engage the planner, not which game to
give whom, and nothing scores an assignment afterwards. *Why:* a scheduler that never
learns whether its assignments were good is an open loop sitting upstream of everything.

**31 · `manual_tools/analysis/optimization_threshold_system.py`.** Per **(game, level)**:
is this level optimised, what is its best sequence, which levels remain targets.
*Counterpart:* `retention.RetentionStore` tags `(game, level)` as a *scope* — not as a
*terminating condition*. *Why:* this is the `sequence_miner` genus again. Without a per-level
"done" flag, effort has no stopping rule and the same level is re-optimised forever.

**32 · `manual_tools/analysis/prestige_parasite_detector.py`.** Knowledge-transfer rate per
agent, parasite detection, sunset recommendation, **and archiving the agent's reasoning
before it is sunset**. *Counterpart:* retirement on performance. *Why:* nothing asks whether
what an agent learned reached anyone else, and nothing preserves its reasoning at the moment
it is destroyed.

**33 · `manual_tools/utilities/run_context.py`.** Typed attempt-scoped state with
`mode` (LIVE / REPLAY_VALIDATION / EVAL), the three weights, `attention_windows`,
`guard_snapshot()`, and — the part with no live analogue — **`sequence_source_id` /
`operator_source_id` / `source_mode`**. *Counterpart:* `ContextBuilder`'s `DecisionContext`
dict plus locals in `cognitive_loop.py`. *Why:* "where did this action come from — a banked
sequence, an operator, or a fresh decision" is currently inferred; here it is a field. Every
attribution question downstream depends on that answer being recorded rather than
reconstructed.

**Adjacent, preserved above but not re-argued as separate capability:**
`manual_tools/database/compact_database.py` (`VACUUM INTO` — the only DB reclaim that fits
inside a 30 GB ceiling with 1× headroom), `legacy/manual_tools/diagnosis_query{,_part2}.py`
(cross-generation learning query, flagged "worth one read before removal" by
`FORGOTTEN_CAPABILITIES.md:81` — the read is done and the flag is upheld), `lab/__init__.py`
(load-bearing for every `-m` entry point in that package).

---

## LIMITS OF THIS READ

1. **Deployment coupling is not reachability, and it cuts the other way.** Per C5, every
   file under `manual_tools/` and `legacy/` — including all 74 marked `considered_dead` —
   is inside `tools/swarm_supervisor.py`'s deploy fingerprint. **Moving them restarts the
   fleet.** That is an operational fact the GM should weigh before approving; it is not an
   argument for or against any row.
2. **Reachable ≠ running.** The one live row (`performance_analyzer.py`) is reached through
   `try: … except Exception: return 0.0` at `evolutionary_engine.py:463-473`. An import
   failure there is indistinguishable from a genuine zero. I did not run it; I confirmed its
   one non-stdlib dependency (`numpy`) resolves in `.venv`.
3. **`legacy/` has no `__init__.py`, and neither does `manual_tools/` or
   `manual_tools/analysis/`.** The live lazy import works only via PEP 420 namespace
   packages. Several `legacy/` modules import their siblings by bare name
   (`from game_loop import …`), which resolves only when `legacy/` itself is on `sys.path`.
   Any move must account for this; it is why those chains are dead in practice as well as
   in principle.
4. **`OBSCURE-N` / NAMED-ONLY is a judgement about one line.** I re-read every line I
   reclassified and quote it. The 14 rows in C1 and the 2 in C2 were re-read individually;
   the remaining NAMED-ONLY citations inherited from the inventory were spot-checked, not
   re-read exhaustively.
5. **The second repository.** `manual_tools/_extract_rungs.py:5` points outside this tree
   and I did not follow it (out of slice, and the rubric's read is of this tree). The habitat
   remains un-enumerable from here alone.
6. **A copy of `lab/` exists under a `.`-prefixed directory** (`.runs/arms/<hash>/lab/`). It
   is a swarm arm worktree — a repo clone, not an invocation site — and was excluded from
   the Amendment 1 sweep on that ground, which is a judgement I am stating rather than
   hiding. Nothing in a dot-directory is proposed for a move or a restructure.
7. **Amendment 1 changed this document once and could change it again.** Every "nothing
   reaches this" verdict above now rests on a sweep of nine named configuration and
   instruction surfaces plus every dot-directory in the tree — but the sweep is only as good
   as its enumeration, and the enumeration is of *files that exist today*. A CI workflow on
   another branch, a runbook a human keeps outside the repo, or a scheduled job defined in
   the GitHub UI rather than in `.github/workflows/` would all still be invisible. The one
   class I can rule out by construction: there is no Makefile and no shell script of any
   kind in this tree outside vendored directories, so there is no hand-run build target to
   miss.
