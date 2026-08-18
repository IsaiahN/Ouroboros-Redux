# PERF AUDIT (2026-08-17) — causes, not mitigations

MEASUREMENT CONTEXT, and it conditions everything: **4 logical processors**; a single
SATA disk with `Avg. Disk sec/Write = 22-32 ms` at queue depth 2.9-4.4 (HDD-class write
service time); and load during measurement varied 20x (109 python.exe / 18,670 MB at
peak, 6 procs / 411 MB at the end). No "average" reading from this box is meaningful
without naming which of those it was taken under.

## Q4 FIRST, BECAUSE IT IS THE ANSWER: THE SHAPE IS **GROWTH**

Three curves. Two are flat, and that is what makes the third conclusive.

  FLAT 1 — the WRITE path does not degrade.
    fabric append, 0-20 records: 0.3837 ms | 4980-5000 records: 0.4328 ms = **1.13x**
    (and the seq cache earning its keep: drop it and append at N=5000 costs
     764.59 ms vs 0.39 ms — **1,951x**. fabric.py:107 is load-bearing.)

  FLAT 2 — per-open latency does not degrade, so it is not the AV and not the disk.
    settlements.jsonl, first-20 opens 165 us | last-20 opens 166 us over 907 opens = **1.0x**

  **THE ONE THAT GROWS — the READ path is O(stream length), on a per-step call:**
    records    20      100     500    1,000   2,500   5,000  10,000  20,000   40,000
    gains()  0.314   0.668   2.633   5.087  12.587  27.164  56.511 132.964  **262.250 ms**
    A STRAIGHT LINE: **5.3 ms per 1,000 records. 835x from N=20 to N=40,000.**

`engines/egocentric/fabric.py:153-165 query()` is a FULL-FILE PARSE — no seek, no index,
`json.loads` per line. Its shipped consumer:

    # engines/egocentric/affect.py:54-58   (VERIFIED AT HEAD BY SEAT 2)
    def _recent_settlements(self):
        rows = self.fabric.query("collective", "settlements")   # FULL RE-READ
        return rows[-self.WINDOW:]                              # WINDOW = 20

called via `_aff.gains()` at **cognitive_loop.py:1783 — TWICE PER STEP.**

LIVE RECEIPT: `.runs/assembly1` settlements = 5,479 KiB / 38,630 records ->
`gains()` = **161.99 ms per call = 324 ms/step**, against **0.6 ms/step on episode 1.
An 11x slowdown with ZERO change in what the loop does.**

**THE SLOWNESS IS A READ THAT RESCANS EVERYTHING EVER WRITTEN, TWICE PER STEP, TO ANSWER
A QUESTION ABOUT THE LAST 20 RECORDS.**

### AND IT IS NOT ONE BOX — SEAT 2 VERIFIED THE WHOLE SWARM
Every live worker is past the janitor's own trigger. `janitor.py:63 STREAM_MAX_BYTES =
2 MiB`, `SETTLE_KEEP = 100`:
    assembly1 5,479 KiB | ls20 4,314 | sk48 4,292 | g50t 4,278 | wa30 4,274 |
    sb26 4,238 | ka59 4,228 | re86 4,224 ... **ALL >2x THE TRIGGER.**
The janitor is documented OFFLINE-ONLY (`janitor.py:44`), the box has not been stopped,
so it has never swept. Accumulation measured at **1.36 settlement records per step,
perfectly linear**. Even after a sweep the 2 MiB ceiling is ~14,000 records ~= 75 ms per
call ~= 150 ms/step — **the ceiling is still a tax.**

## Q1 — TEST SUITE RUNTIME: 1020 passed in 524.67 s
**40 of 1020 tests (3.9%) account for 430.5 s = 82.1% of runtime.**

MECHANISM 1 — a 533-statement schema rebuilt on every `CognitiveLoop()` in a fresh cwd.
  `cProfile` on test_reset_discipline.py: **66.594 s of 80.9 s (82%) in 8 calls to
  `sqlite3.Connection.executescript`.** Chain: a function-scoped `run_dir` fixture
  `os.chdir`s to tmp_path -> `CognitiveLoop.__init__` -> `Perceiver.__init__` ->
  **`engines/perception/object_detector.py:37  def __init__(self, db_path: str =
  "core_data.db")` — A RELATIVE DEFAULT, RESOLVED AGAINST THE CWD** -> rebuilds
  `complete_database_schema.sql` (265,059 bytes, **281 CREATE TABLE + 252 CREATE INDEX**).
  Cost: 2.45 s idle, 8.32 s loaded. **26 core_data.db files >=1 MB per gate run, 88.1 MB
  written to %TEMP% => 64 s floor / 216 s loaded = 12-41% of the suite, from one
  relative-path default.**

MECHANISM 2 — test fixtures commit SQLite in default journal mode.
  `tests/gate/test_efficiency_read.py:54 _db()` calls `sqlite3.connect(path)` and sets
  NO PRAGMAS, unlike `database_interface.py:66-82` which sets WAL.
    DEFAULT (journal=DELETE, synchronous=FULL) commit median: **313.09 ms**
    WAL + synchronous=NORMAL (what the real code uses):      **0.03 ms**
  **10,000x.** 92% of that file's 69.5 s is execute+commit on tables with <6 rows.

NOT the cause: no sleeps anywhere in the hot paths; no subprocesses in the top 40; the
`PYTHONDONTWRITEBYTECODE=1` recompile + sessionfinish `os.walk` + tmp GC total ~5 s.

## Q2 — OFFLINE EPISODE WALL-CLOCK (hermetic 300-step drive)
    import cognitive_loop   4.854 s   (of which 2.691 s is THE SAME schema executescript,
                                       fired at IMPORT time via engines/__init__ ->
                                       registry -> database_logger.py:154)
    CognitiveLoop()         0.007 s   (free here — the DB already exists; in the gate
                                       tests the order reverses and the ctor pays it)
    300 x cycle            15.619 s   (52.1 ms/step)
    TOTAL                  20.526 s   **per-episode FIXED = 4.907 s = 24%**
  Per-step split: **I/O 3.59 s (23%)** — 2,274 opens / 300 steps = **7.6 opens per step**,
  of which settlements.jsonl alone is 907 opens / 3.256 s. **CPU: `effects.py:523
  apply_effect` = 10.4 ms/call, 7.025 s cumulative = 45% of step time, driven by
  1,950,000 `ndarray.all()` calls — a per-cell Python loop over numpy scalars.**
  **WAITING: ZERO.** No sleeps, no locks, no network.

### A BELIEF IN THE CODEBASE IS WRONG BY ~1000x
`tests/gate/test_e2e_pipeline.py:26` states "this box's antivirus makes fabric
read-after-append pathologically slow", and the suite is SHAPED AROUND THAT BELIEF.
Measured (n=400 each, Defender RealTimeProtection ON):
    fh.seek+read (no syscall) 0.30 us | os.fstat 14.60 us | os.path.isfile 28.70 us |
    open+close 59.90 us | open+write+close 214.30 us
Identical inside %TEMP% and beside the repo, so no path exclusion is in play.
**THE AV TAX IS ~15 us PER KERNEL OP PLUS ~30-45 us PER PATH RESOLUTION — TENS OF
MICROSECONDS. THE MILLISECONDS ARE THE DISK: 22-32 ms PER DURABLE WRITE.** That is why
one sqlite commit costs 313 ms and one schema build costs 2.45 s. The AV is real and
~1000x smaller than the code assumes.

## Q3 — PROCESS HYGIENE: NOTHING LEAKS; SOMETHING WAS LAUNCHED TWICE
**TWO INDEPENDENT SWARM SUPERVISORS RAN SIMULTANEOUSLY, STARTED 2m22s APART**, each
running the full 25-game roster: 109 python.exe / 18,670 MB on a **4-core box = 27x
oversubscription**. `.runs/swarm/status.txt` reported `r/m/c = 0/0/0` — **neither
supervisor knew the other existed.**
This violates the single-writer invariant the seq cache is licensed by
(`fabric.py:10-13`: "each stream has a single WRITER process by design ... so the
in-memory advance can never hand out a seq twice"). With two writers it can.

  **SEAT 2 MEASURED THE ACTUAL DAMAGE RATHER THAN ASSUMING IT:**
  1,564 streams scanned for repeated seq values.
  **4 STREAMS AFFECTED, 5 DUPLICATE SEQS TOTAL, MAX REPEAT 2**
  (ls20 import_queue, tn36 mint_verdicts, wa30 import_queue, wa30 settlements x2).
  => THE COLLISION IS REAL AND NEGLIGIBLE. Every census figure this project has
  reported off these streams STANDS. Recording it so the invariant breach is on the
  record even though the harm was ~0.

  No supervisors are running now (verified: 0). No handle leak (205 -> 205 over 500
  steps). One orphan pytest, since exited.

**WITHIN one process, memory does not fully release:** RSS 69.8 -> 80.8 MB over 500 steps
(**+22 KB/step, monotonic**); `gc.get_objects()` 48,010 -> 58,793 (**+22 retained objects
per step, linear**). Retained Python objects, not fragmentation and not handles. This is
why `MEM_CAP_MB = 1200` has to exist.

## THE SEPARATION ISAIAH ASKED FOR
    schema rebuild per fresh-cwd construct/import   2.45-8.3 s, x26 per gate run  CONSTANT
    per-episode fixed setup                         4.907 s = 24% of an episode   CONSTANT
    fabric append                                   1.13x over 5,000 records      FLAT
    per-file open latency                           1.0x over 907 opens           FLAT
    **fabric.query on the per-step affect read      0.31 ms -> 262 ms; 162 ms live  GROWTH**
    process RSS / retained objects                  +22 KB, +22 objects per step  GROWTH
BOTH ARE PRESENT AND THEY ARE SEPARABLE. The constant term is one relative-path default
and one missing PRAGMA. The growth term is one full-file read serving a 20-record window.

## BEARING ON THE CONTROL ARM (checked, not assumed)
`PREREG_CONTROL_ARM.md:25-29` reports CAPABILITY (levels per episode) and THROUGHPUT
(levels per hour) **separately, never averaged**, and pre-commits the branch "STRIPPED
WINS ON LEVELS-PER-HOUR ONLY -> the stack is a THROUGHPUT problem, not a capability one."
The growth tax above is exactly the mechanism that would produce that branch, and the
full arm pays it while the stripped arm does not. **The prereg separated the two before
the number arrived, so this does not invalidate the arm — it supplies the mechanism for
one of its pre-committed outcomes.** Both arm fabrics verified at 0 settlement bytes so
far; both worktrees single-writer.
