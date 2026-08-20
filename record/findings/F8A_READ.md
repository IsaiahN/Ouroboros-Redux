# F-8a — HAS THE SCORE-KEYED CHECKPOINT DELETION ALREADY DESTROYED ANYTHING?

AUTHORITY: Isaiah — *"Read it, don't fix it — I want to know whether it has already
destroyed anything before it changes."* **Nothing was changed. This is a read.**

---

## THE ANSWER: NO. AND THE REASON IS WORSE THAN THE DEFECT.

`safe_cleanup.py::_clean_frontier_checkpoints` keeps the top 20 rows per
`(game_type, level_number)` ordered by `survival_score DESC, times_extended DESC`, and
deletes the rest. **It has destroyed nothing, because it has never had an input.**

| scope | sqlite files scanned | `frontier_checkpoints` rows |
|---|---|---|
| 25 live swarm boxes | 25 | **0** |
| `.runs` entire (arms, controls, archive) + the sibling lineage `../Ouroboros` | **106** | **0** |

Zero rows. In either lineage. Ever. Against **557,251 action traces** in the live boxes.
No partition anywhere is at the tell-tale 20; there are no partitions.

**A defect I looked for and did NOT find** (stated so the read is not one-sided): the
`DELETE ... WHERE (game_type, level_number, terminal_frame_hash) IN (...)` addresses rows by
a triple that is the table's **actual PRIMARY KEY**, so it cannot take collateral rows that
merely share a hash with a condemned one. Checked, clean.

## SO D-1 IS NOT EXONERATED. IT IS UNEMPLOYED.
It is harmless **not because it is safe but because the organ it prunes has never produced a
row.** The instant the writer starts working, a score-keyed deletion runs against real
checkpoints, and `survival_score` is a proxy — the same class of key that ate the census in
`re86` (112→8) and `tu93` (97→12). **Disposition unchanged; only urgency changes.
D-1 is LATENT, not INERT.** Fixing the writer without fixing D-1 first arms it.

---

## WHAT THE READ ACTUALLY TURNED UP

**The whole frontier-checkpoint system is built and has never once run.** Present and
correct: an architecture document, a writer with four guards, an UPSERT whose `ON CONFLICT`
target **exactly matches** the live PRIMARY KEY, two purpose-built indexes
(`idx_frontier_checkpoints_best`, `..._usage`), a registered decision rung, slot-registry
entries naming it as both reader and writer, a section in `audit_data_usage.py`, and this
cleanup routine. **Everything exists except the arrival of data.**

### WHY — THE WRITER IS ON A PATH THE LIVE RUNNER NEVER ENTERS
`_save_frontier_checkpoint` (`learning_systems.py:749`) has **exactly one call site**:
`LearningSystems.update()` at `learning_systems.py:366`, inside `if outcome.is_death:`.
`LearningSystems` is constructed in **exactly one place**: `core_gameplay.py:206`, inside
`GameplayEngine`. **Nothing outside `core_gameplay.py` and `tests/` ever constructs
`GameplayEngine` or `GameLoop`** — and there is no dynamic route (no `importlib`,
`__import__` or `getattr` reaching either module).

**The decisive check:** walking every `import`/`from` statement reachable from
`evolution_runner.py` — the live entry point, function-local imports included — gives a
closure of **29 modules. `core_gameplay` is not in it. `learning_systems` is not in it.**
The live runner imports `GamePlayer` and `CognitiveGamePlayer` directly.

Dates corroborate: `learning_systems.py` last changed **2026-02-07**, `core_gameplay.py`
**2026-02-10**; `cognitive_game_player.py` changed **today**. Two branches of the same
project, one of which stopped being executed six months ago and nobody noticed.

**GENUS: built-plumbed-never-called, degree *the organ is never called*.**

### A SECOND, DIFFERENT GENUS AT THE SAME CALL SITE
The other write in that same `if outcome.is_death:` block —
`_record_terminal_pattern` → `INSERT INTO terminal_patterns` — targets a table that **does
not exist in any of the 25 boxes.** So even if the path were live, half the block would
throw `no such table` into a bare `except`. **GENUS: schema-never-written.**
**One `if` block, two writes, two different failure genera, both silent.**

### AND THE READER IS LIVE, AND PERMANENTLY STARVED — RUNG 0d
`frontier_checkpoint` **is registered**, in two profiles: `decision_rung_system.py:135`
(efficiency, priority **4**) and `:481` (priority **5**). That is very early — ahead of
`three_try_sequence`. Its query runs on every frontier level of every game and returns
`None` every time.

**It does not abort. It yields quietly** (`logger.debug` on failure, `return None` on empty)
— which is precisely why six months passed. **A consumer that fails loudly gets fixed; a
consumer that fails politely gets forgotten.** The cost is not a crash, it is a decision
slot at priority 4 that can never fire, in a ladder whose ordering was tuned as if it could.

### COMMENT–CODE DIVERGENCE FOUND IN PASSING (feeds the sweep, task 4)
`rungs/exploitation.py` declares `default_priority = 6  # Very early - before
three_try_sequence (8)`. The registry registers this rung at **4** and **5**, and registers
`three_try_sequence` at **5** in the efficiency profile — where its class says **8**.
**The comment states an ordering rationale that is not the ordering in force.**

Also noted, not exercised here: `_is_frontier_level` returns `True` on exception — it
**fails open**, so an unreadable `winning_sequences` makes every level look like a frontier.

---

## WHAT I DID NOT DO
No fix. No sweep. No deletion. No schema change. D-1 stands exactly as it was, and so does
the writer. **Every claim above is a count or a call-graph fact, not an inference from
design intent.**

## WHAT THIS OWES UPWARD
1. **D-1's disposition is still Seat 3's**, but it should be ruled on *before* anyone
   repairs the writer, not after — the repair is what arms it.
2. **Whether the frontier-checkpoint system is meant to be alive at all** is a SUBJECT
   question and not mine. If it is, this is a real capability the project has been paying
   for and not receiving. If it is not, a registered rung at priority 4 and a cleanup
   routine are both lying about it.
