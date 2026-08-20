# THINGS WE ALREADY BUILT AND FORGOT (2026-08-20)

Seat 3: *"the valuable output here isn't the cleanup. It's the list of things we already built
and forgot."* **Nothing here is built or removed. This is the list.**

**Method:** every `.py` outside `.`-prefixed dirs was checked for references as an import, a
dotted path, **and a bare quoted string**. 480 files; 124 with no reference; **83 of those are
tests reached by pytest's filename discovery and 16 are CLI entry points reached by a human** —
neither is dead, and "no reference" there was a property of my checker, not of the files.
**25 true candidates remain.**

---

# A · CAPABILITY WE DO NOT HAVE — preserve, do not build

## A1 · `manual_tools/scan_context_keys.py` — **AND IT ALREADY FOUND A LIVE DEFECT**
**What it is:** an automated **produced-vs-consumed check for the context dict** — it extracts
every `context.get('k')` / `context['k']` the rungs read and compares against what
`ContextBuilder.to_dict()` emits.

**Why it matters:** this is the *"produced, recorded, and not read"* genus **mechanised, on a
surface nothing else audits.** `tools/consumption_sweep.py` covers fabric streams; the context
dict — **the actual input to every decision rung** — has never been checked by anything.

**IT WAS RUN. FIRST OUTPUT: 34 keys consumed, 83 provided, 6 flagged missing, 55 provided-and-
never-consumed.** Verified each of the 6 by hand rather than reporting the tool's number:
- **4 are false positives** — `exploration_appetite` is written at `decision_rung_system.py:863`,
  and `was_productive` / `was_destructive` / `was_wasted` at `cognitive_game_player.py:477-479`.
  The tool only inspects `ContextBuilder`, so "missing from ContextBuilder" ≠ "never supplied".
- **`game_state_mode` — A DEAD BRANCH THAT LOOKS LIVE.** Exactly one occurrence in the whole
  live tree: `decision_rung_system.py:1188`,
  `if context.get('game_state_mode', 'unknown') == 'exploration':` — **nothing anywhere writes
  it**, so the default is always returned, the comparison is always False, and the branch never
  executes. *This is the canon's textbook form: `context.get(X, DEFAULT)` where nothing sets X.*
- **`last_rung_name` — a permanently-taken fallback.** Read at `:1106` as
  `context.get('last_rung_name') or (…)`; nothing writes it, so the `or` branch is always used.
  Milder, because the code anticipated absence — but the `context.get` half is dead.

**To bring it in:** it is a standalone read; it needs R4 (a known-positive key that must flag
and a supplied key that must not) and the ContextBuilder-only blind spot fixed so it checks
*all* writers, not one. **Half a day. It would have found the two above on any week it ran.**

## A2 · `manual_tools/analysis/oracle_stuck_game_diagnostics.py` (20 KB)
**What it is:** a stuck-game detector that diagnoses **which tier of a 6-tier chain is broken**,
explicitly *"DIAGNOSTIC ONLY — no interventions imposed on agents… If games stay stuck, a TIER
is broken. Fix the SYSTEM, not the agents."*

**Why it matters:** that is **THE_LADDER's own thesis, written into the system a era earlier** —
find the broken link rather than optimise around it. And the board has **16 games that have
never completed a level** plus **D-5 (progress buys slowdown)**. A per-tier break detector is
the shape of instrument this board wants and does not have.

**To bring it in:** its 6 tiers must be mapped onto the current architecture before it can say
anything true — the tiers it names are from the network-learning era. **Read it against the
loop's eight steps first; if the tiers do not map, its value is the idea and not the code.**

## A3 · `manual_tools/_extract_rungs.py`
Extracts rung classes from `decision_rung_system.py` and groups them by category. **Directly
relevant to a known open divergence:** `FrontierCheckpointRung.default_priority = 6` while the
registry registers it at **4 and 5**. A rung inventory would make that class of mismatch
mechanical rather than incidental.

## A4 · `engines/social/cods_types.py` — **NOT A CANDIDATE, LISTED FOR PROTECTION**
Under `engines/`, i.e. current agent architecture, which Seat 3 put out of scope. It defines
`CODSGameContext`, `OperatorResult`, **`BayesianHypothesis`**, `update_frame`. It shows as
unreferenced because nothing imports it *today*. **Do not remove. Flagged so that a future
sweep does not mistake it for dead.**

---

# B · REMOVAL CANDIDATES — nothing the live tree lacks
**Not removed. Proposed, pending a ruling**, because removal is reversible and changes no number
on the board but is not mine to take until the autonomy criterion is ruled.

| files | what they are | why superseded |
|---|---|---|
| `_investigate_fast.py`, `_investigate_monopoly.py`, `_investigate_part2..5.py` (6) | one-off scripts from the VC33 rung-monopoly investigation; one says *"Temporary investigation script"* in its own docstring | the question they answered is closed and the current instruments cover the surface |
| `manual_tools/check_gen2.py`, `check_gen2b.py`, `trace_check.py`, `trace_deep_dive.py` | pinned to specific generations (*"find gen 5013 traces"*, *"gen 5013 KK→UK regressions"*) | generation-pinned, and those generations are long gone |
| `manual_tools/find_tables.py`, `database/list_danger_tables.py` | schema pokes | `tools/dump_schema.py` does this |
| `manual_tools/analyze_decision.py`, `debug_routing.py`, `gen_analysis.py`, `check_api.py`, `check_terminal_patterns.py` | era-specific one-shots; `check_terminal_patterns` targets a table that **does not exist in any of the 25 boxes** | superseded by the current reads |
| `manual_tools/diagnosis_query.py`, `diagnosis_query_part2.py` (23 KB) | *"analyze what the system has learned across generations"* | **the largest pair here — worth one read before removal**, because a cross-generation learning query is close to the split-half question |
| `console_tags.py` | `log`/`log_ok`/`log_warn`/`log_error` helpers | unused; the codebase logs directly |

**`manual_tools/utilities/.vulture_whitelist.py`** is dot-prefixed and skipped by the rule.

---

# C · WHAT THIS EXERCISE DEMONSTRATED
**A forgotten tool found a live defect on its first run.** `scan_context_keys.py` had zero
references, sat in `manual_tools/`, and would have been a removal candidate under any rule that
counted references — and it identified a dead branch in the live decision system in one
execution.

**That is the argument for the list, and it is also the warning about the sweep.** Reference
count measures whether anything *calls* a file. It does not measure whether the file *knows
something*. **The guards are a product: SUPPORT (no references) was satisfied for all 25, and
NOVELTY — does it hold capability the tree lacks — is the guard that had to be read by hand,
and it is the one that saved two of them.**
