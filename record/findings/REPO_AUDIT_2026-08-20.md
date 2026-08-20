# THE REPOSITORY AUDIT (2026-08-20) — live set, remnants, the shared-DB defect

Seat 3's three priorities: (1) root actually clean, (2) the root database examined and its
references resolved, (3) used-vs-remnant across the whole tree with a salvage list.

---

## 1 · THE LIVE SET, COMPUTED NOT ASSERTED
**Method:** import closure from the two entry points (`evolution_runner.py`,
`tools/swarm_supervisor.py`), then **expanded through `engines/registry.py`, which loads
modules BY STRING** (`module='…'` → `importlib.import_module`). Static closure **145 files →
170 with the registry pass**. The registry rescued two root modules a static read condemns:
`breakthrough_budget_allocator.py`, `representation_learner.py`.

**Root `.py`: 56 → 42.** The 42 = 34 live (closure) + `__init__.py` + 7 held back:
- **test-anchored dead lineage** (`core_gameplay`, `game_loop`, `learning_systems`,
  `agent_factory`, `agent_self_model`): imported ONLY by each other and by `tests/` — the
  F-8a lineage. **Moving them breaks the suite; retiring their tests is a Seat 3 ruling.**
- **tooling-anchored**: `vulture_whitelist.py` (named in two gate tests' exclude lists),
  `schema_auto_maintenance.py` (imported by a manual_tools utility).

**Moved to `legacy/` (14, zero imports anywhere, checked as import + dotted path + bare
string):** the six `_investigate_*` one-offs, `_temp_check`, `adaptive_action_limits`,
`arc_api_client` *(SALVAGE: holds the correct git-derived scorecard tagging)*,
`automated_assessment_runner`, `console_tags`, `disk_space_monitor` *(SALVAGE: DA item —
fold its per-table reporting into disk_ceiling)*, `evolution_game_scheduler`,
`game_scheduler` *(imported only by evolution_game_scheduler — moved as a pair)*.

**Root markdown 26** — the live-cited set (22, at 102 citation sites in live code) plus 4
canon reload points. **Root logs 0, root DB 0** (below).

## 2 · THE ROOT DATABASE — examined, and it produced today's defect
**Contents:** 284 tables, all 25 games, 171k action_traces, 1,802 game_results, 0 wins, max
`level_completions` 1. **Last data write 2026-08-17 23:23 UTC; last any-table write
2026-08-18 09:58 (461 `system_logs` rows). Nothing since, across two days of swarm play.**

**MERGE VERDICT: NOTHING TO MERGE.** Per-game, the swarm boxes cover every level the root DB
has — ar25's box holds an L2 route the root lacks. The root's extra sequences (lp85 42 vs 29)
are same-level alternates, not reach. It is a **pre-swarm generation**, kept as evidence.
*(First comparison said the opposite — a swallowed `no such column` made every box read
empty. Caught because box counts were already known to be non-zero.)*

**THE DEFECT THE EXAMINATION FOUND — D-6, THE SHARED-DB ANCHOR.** The move failed:
**the file was LOCKED by current workers.** All 52 processes postdate the relaunch; workers
run with `cwd=box`; so something resolves the path to the REPO. Found:
`engines/reasoning/symbolic_reasoning_engine.py:49` —
`DB_PATH = Path(__file__).parent.parent.parent / "core_data.db"` — consumed at `:1775` as
the constructor fallback. **The module is registry-loaded in every worker, so all 25 workers
held open handles on ONE shared root file** — the "one evidence pool" collapse in code, idle
today (handles open, zero writes) and latent tomorrow.
**FIXED:** `DB_PATH = Path("core_data.db")`, cwd-relative, matching every sibling engine's
default. Ruff clean, 6 symbolic tests green. **FALSIFIER, checked after the deploy: no new
`core_data.db` may appear at the repo root** — if one does, a second module also anchors to
the repo and the fix was incomplete. The old DB moves to `.runs/legacy_db/` once handles
release at the deploy restart.

## 3 · REMNANT MAP (recursive, `.`-dirs skipped) & SALVAGE
| where | verdict |
|---|---|
| `engines/` `rungs/` | live (registry + closure). `engines/social/cods_types.py` flagged protected-unreferenced. |
| `tests/` (2 000+) | live via pytest discovery. **Sub-question for a ruling: the dead-lineage tests** (`test_action_ladder`, `test_replay_validation`, …) test code nothing runs. |
| `tools/` `manual_tools/` `lab/` | proctor/CLI tooling, reached by humans and gates. 21 candidates in `FORGOTTEN_CAPABILITIES.md` §B stand. |
| `legacy/` (new) | quarantined remnants, history preserved via `git mv`. |
| `architecture/ checklists/ config/ figures/ environment_files/ DOCS/` | inventoried; no live-code references found by the string check except `config/` (worker YAML) and `environment_files/` (game metadata — **live**). Detail pass queued. |

**SALVAGE LIST (union with `FORGOTTEN_CAPABILITIES.md`):** `scan_context_keys` (found a dead
branch in the live decision system on first run) · `oracle_stuck_game_diagnostics` (per-tier
break detector = the Ladder's thesis in code) · `_extract_rungs` (rung inventory; the priority
divergence) · `arc_api_client.generate_tags` (correct scorecard lineage tagging) ·
`disk_space_monitor` (per-table sizes → fold into disk_ceiling) · `sequence_miner`
(level-scoping, already known) · the `diagnosis_query` pair (cross-generation learning read —
one read before any removal).


---

## ADDENDUM (same day) — THE FALSIFIER FIRED: A SECOND, UNLOCATED CREATOR
The historical DB is **archived intact in `.runs/legacy_db/`** (moved after a recorded
supervisor kill+relaunch released the handles). Then the falsifier ran: **a fresh
`core_data.db` appeared at root at 06:10, the launch minute — 282 tables, ZERO rows**, a
schema-only create via `DatabaseInterface._initialize_database_from_template`.

**So a second creator exists**, and it is not: the egocentric package (zero
`DatabaseInterface` references), the supervisor's own code (no DB calls), or the fixed
symbolic engine (now cwd-relative; box DBs advancing normally, zero writes to the root file).

**Workers are verified clean.** The root file is an empty shell something recreates at launch.
**The hunt switches from grep to instrument** — greps have missed it twice, so the next beat
opens with a stack-trace probe in `DatabaseInterface.__init__` that logs its caller whenever
the resolved path is the repo root: catch it in the act once rather than read for it a third
time.
