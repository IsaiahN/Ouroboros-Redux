# THE COMMENT–CODE DIVERGENCE SWEEP (2026-08-18) — `tools/comment_divergence.py`

Isaiah's spare-capacity item (4). A comment is a **claim about the code, and nothing checks
it** — and it is the number a reader believes when deciding whether a constant is
deliberate, which makes it the premise pass's input.

**474 files scanned. 8 candidates.** R4 fires both ways on every run (known-positive
`wal_autocheckpoint`; known-negative `busy_timeout`, three lines above it in the same
function, stays clean).

## ALL EIGHT, READ BY HAND — because eight is small enough that reporting a count would be laziness

| # | site | verdict |
|---|---|---|
| 1 | `database_interface.py:81` | **REAL.** *"Checkpoint every 1000 pages (~4MB) instead of default 1000 pages"* over `wal_autocheckpoint=100`. **Says 1000 twice, and the second use is self-contradictory** ("instead of default 1000" where 1000 is also the claimed new value). Code sets 100; the trailing `# 400KB` agrees with 100. **The comment is wrong by 10×**, and this is the constant whose provenance PERF_AUDIT already flagged. |
| 2 | `tests/test_epistemic_stability.py:134` | **REAL, MILD.** *"default decay is 10 ticks"*, loop runs `range(15)`. Plausibly deliberate (run past the decay to prove it settled) but **the comment states a default it does not read from the code**, so if the default moves the test still says 10. |
| 3 | `engines/perception/object_tracker.py:127` | **FALSE POSITIVE, benign.** *"Process each ARC color (0-12)"* over `range(13)`. Exclusive bound; comment and code agree. |
| 4 | `performance_analyzer.py:366` | **FALSE POSITIVE.** *"Max 50% penalty"* over `..., 0.5)`. Percent vs fraction. |
| 5 | `engines/egocentric/fabric.py:88` | **FALSE POSITIVE.** Prose about a 64 KB tail block over `_TAIL_BLOCK = 65536`. Unit conversion. |
| 6 | `mastery_system.py:363` | **FALSE POSITIVE.** The integers are a date stamp `FIX (2026-01-28)`; the year is filtered, the month and day are not. |
| 7 | `tools/durability_test.py:2` | **FALSE POSITIVE.** `FIX #16` in a module docstring. |
| 8 | `manual_tools/analyze_run.py:130` | **FALSE POSITIVE.** A section comment landing on a `"=" * 85` separator. |

**2 real of 8. Precision ~25%** — acceptable *only* because the population is 8 and reading
it costs minutes. **This is a candidate finder and its output is never a verdict.**

## THE NUMBER THAT MATTERS MORE, AND IT IS THE UNFLATTERING ONE: **RECALL 1 OF 3**
I found three divergences by hand today. **The sweep catches one of them.**

| hand-found | caught? | why not |
|---|---|---|
| `wal_autocheckpoint` comment 1000 vs code 100 | **YES** | same line-block |
| `evolution_runner.py:1616` *"Safe cleanup every 10 generations"* vs `health_monitor` **30** | **NO** | **CROSS-FILE.** The annotated line `self._health_monitor.run_safe_cleanup(...)` contains **no integer at all** — the claim's referent is in another module. |
| `rungs/exploitation.py` `default_priority = 6  # ... before three_try_sequence (8)` vs registry **4/5** | **NO** | **SINGLE DIGITS.** `INT` requires ≥2 digits, chosen to keep 0/1 structural noise out — and that floor silently discards every priority, retry count and small cap in the repo. |

**Stated plainly: this instrument would not have found two of the three defects that motivated
it.** Both misses are structural, not tuning: one needs cross-module resolution, the other
needs a way to admit single digits without drowning. **Neither is fixed here** — extending it
is a build, and it is written up in Decision Analysis form rather than taken tonight.

## A DEFECT IN MY OWN INSTRUMENT, CAUGHT MID-BUILD AND WORTH RECORDING
The historical-reference suppressor (*a comment naming a PAST value is provenance, not
divergence*) shipped first as a regex containing **literal backspace bytes** — `\b` written
through a shell heredoc that collapsed the escape. **The regex could never match, so the
suppressor was inert while appearing to work**, and the candidate count was unchanged.
It was caught only because the count did not move when it should have.

**Two things follow.** (i) **Anything containing a backslash goes through the file tools, not
a shell heredoc** — the same failure would silently weaken any regex-based instrument.
(ii) The first version also lacked word boundaries, which is **exactly the `'pre'`-inside-
`'predicted'` false positive that forced the R4 amendment**. Same defect, same session, second
instrument. **The suppressor's word list was then narrowed** — `instead of` was removed,
because *"instead of default 1000 pages"* is a claim about the value in force, not provenance,
and suppressing it would have killed the known-positive.

## WHAT THIS OWES UPWARD
1. **The `wal_autocheckpoint` comment is wrong by 10× and is APPARATUS.** The pragma itself
   is under a standing "stays put" instruction; **the comment is not the pragma**, but I have
   not touched it either — correcting a provenance comment on a constant that is itself
   awaiting a ruling is Seat 3's call, not a night-shift edit.
2. **Recall 1-of-3 is the finding, not the 8 candidates.** An instrument whose measured
   recall is a third should be reported with that number attached every time it is cited.
