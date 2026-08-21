# PREREG — FABRIC I/O: PARSED-STREAM CACHE + PER-STEP DB BATCH (2026-08-21)

**AUTHORITY:** F1_VERDICT_AND_SHADOW_TEST.md WINDOW FIVE (g50t, composer stages 1-3 live):
with the planner bounded, `record_result` 29.9% ← `fabric._read_stream` 28.0% (556 calls /
130 cycles: `fabric.query` re-parses whole JSONL streams ~4× per cycle — planner
`_candidate_ids` on atoms, affect `_mint_verdicts`, lp_drive's two reads, latents/binder/
composer/bank on the Γ topic) + sqlite `execute` 17.5% (4,601 calls ≈ 35/cycle, mostly
under `record_result`). Produced-once, parsed-many. This is a RULE-R3 change: behaviour-
preserving, so the gate is "returns EXACTLY what the old path returned", not "looks right".

**EXEMPLARS:** `tests/gate/test_tail_read.py` (the oracle is a LITERAL TRANSCRIPTION of the
pre-fix reader, never the live code); `tests/gate/test_fabric_seq_cache.py` (read count asserted
by COUNTING, never wall-clock); `fabric._tail_records` (decoding a slice from a line boundary).

## STAGE 1 · THE PARSED-STREAM CACHE (fabric.py only)
**Shape.** One process-level dict keyed by `os.path.abspath(stream)`. Entry: `records` (the
parsed dicts of every TERMINATED line, in file order), `parsed_upto` (byte offset just past
the last universal-newline terminator — never mid-line), `anchor` (the last 64 bytes before
`parsed_upto`; fewer if the file is shorter), `size` (size at last sync). `query` serves each
root's stream from the cache, then applies `where`/`limit` exactly as today over the same
concatenation (seeds first, then local). `_read_stream` itself is UNCHANGED and remains the
oracle; the cache is a layer above it. `query_tail` stays on `_tail_records` (already O(tail)).

**The read, every call.** stat → `size`. Then exactly one of:
1. MISSING (stat fails / not a file) → drop the entry, return `[]` (what `_read_stream` does).
2. VALID — `size >= parsed_upto` AND the 64 bytes at `[parsed_upto-64, parsed_upto)` equal
   `anchor` (one open, one seek, one short read — the cache never trusts a stat alone) →
   decode ONLY `[parsed_upto, size)` with the same decoder as `_tail_lines` (utf-8,
   errors=replace, universal newlines — starting at a terminator keeps the decoder in the
   whole-file state, fabric.py:100-105); every terminated line is parsed with `_read_stream`'s
   exact rules (strip, skip blank/corrupt/non-dict), APPENDED to `records`, and `parsed_upto`
   advances to the last terminator. The UNTERMINATED remainder (a torn or in-flight tail) is
   parsed and RETURNED but NEVER cached — so a complete-but-unterminated last line is included
   (as the oracle includes it) and is re-read on the next call, when it may have grown.
3. INVALID — `size < parsed_upto`, or the anchor differs (a rewrite of any length, including
   one that happened to grow the file, or an edit within stat granularity) → full `_read_stream`,
   re-seed the entry from scratch. mtime is NOT part of the rule: its granularity varies by
   filesystem and an identical-size rewrite inside one tick would pass it; the anchor does not.

**Why the torn-tail safety holds.** `parsed_upto` never passes an unterminated line, so a
partial multibyte sequence at EOF, a write cut mid-record, or a `\r` whose `\n` has not landed
all sit in the volatile remainder, decoded from the same boundary the oracle reaches them from
(a split `\r\n` yields a blank line; the same `strip()` skips it). Concurrent appends by the
stream's single writer (fabric.py:11-13) are growth, not rewrite: path 2, tail-parsed.

**Derived, never the sole holder.** The cache holds nothing the file does not, is dropped by
`drop_read_cache()` (the `reload_seqs` pattern, fabric.py:210), and is never written back.
Returned records are SHALLOW copies (`dict(r)`): a consumer mutating a top-level key cannot poison the next read.

## STAGE 2 · PER-STEP DB BATCH (gated by an attribution read)
The finding names the count (35/cycle) and the parent, not the sites. **Stage 2 opens with a
one-window attribution read — sqlite `execute` by CALLER** — before any batching lands. The
two candidates already visible in the tree: `database_logger.DatabaseLogHandler.emit` (one
INSERT + one COMMIT + a lock per log record, handler level DEBUG, engine loggers at DEBUG —
engine_logger.py:213-225) and `DatabaseInterface.execute_query`'s per-statement auto-commit
(FIX #16, database_interface.py:1380-1384). Batching is designed for whichever the read names.

**Shape.** A step boundary on the writer: statements inside a step EXECUTE IMMEDIATELY on the
same thread-local connection (FIX #16's property — written in action N, readable in N+1 — is
preserved by sqlite's read-your-uncommitted-writes on that connection) and COMMIT ONCE at step
end. Nothing is queued or reordered: statement order on the connection is unchanged and a
commit boundary cannot permute it. Reads outside the step (`_load_prior_knowledge`) are untouched.

**The writer-defect trio, applied** (PORT_LOG.md:1388-1390): *parameter-not-passed* — the
batched path binds every column the single-statement path bound, asserted by F4 row equality;
*lossy reprs* — no value is re-serialised (`str()`/repr) on its way into a batch, asserted by
per-column `typeof()` equality; *taint stamped loudly* — a step that fails mid-way COMMITS
ITS EXECUTED PREFIX (the same prefix today's code would have made durable) and stamps the
step (counter + narrated line); it never rolls back and never swallows.

## WHAT MUST NOT CHANGE
- Every `query` returns byte-identical records to `_read_stream`-backed `query` today, in the
  same order, under the same `where`/`limit`. The uncached path stays in the file as the
  equivalence oracle (the scalar-oracle pattern of W2a-2).
- Append-only semantics: the cache never writes; `append`/`_next_seq`/the seq cache are
  untouched; the janitor's archive-then-truncate still invalidates by shrink (path 3).
- The consumers gate: no NEW `.append(scope, "topic", …)` or `.query(scope, "topic", …)`
  call sites anywhere; `tests/gate/test_consumers.py` and its ALLOWLIST are byte-unchanged
  and run green before and after.
- DB: same rows, same order, same columns, same types; same visibility within the process.

## FALSIFIERS
- **F1 · EQUIVALENCE (absolute):** a constructed corpus — empty file, missing file, one
  record, blank lines, corrupt lines, non-dict lines, CRLF/bare-CR, invalid UTF-8, multibyte
  at the 64-byte anchor boundary, a terminated tail, a torn tail, a complete-but-unterminated
  tail, a tail that later grows into a full record, an append between two reads, a rewrite
  (shrink) between reads, a rewrite that GROWS the file, a same-size rewrite, a seed root +
  local root spanning window — cached `query` == oracle `query` (literal transcription) at
  EVERY read in every sequence, plus every stream on a real box replayed. Any divergence fails.
- **F2 · THE READ COUNT COLLAPSES (the point):** a constructed 100-cycle run issuing today's
  per-cycle query set against growing streams: full `_read_stream` calls per cycle drop from
  ~4 to 0 after warm-up (asserted by counting, the seq-cache probe), and bytes decoded per
  cycle are bounded by bytes appended since the previous cycle plus the volatile remainder.
- **F3 · INVALIDATION BOTH WAYS:** an append does NOT invalidate (0 full reads, tail-parsed);
  a rewrite DOES (exactly one full read, then steady state again); a file truncated mid-read
  (shrunk between the stat and the anchor read) falls to path 3 and returns the oracle's answer.
- **F4 · THE BATCH PRESERVES ROWS:** a constructed step of N mixed statements, batched vs
  single-commit, yields identical tables (row order, count, every column's value and
  `typeof()`); a step aborted after k statements leaves exactly the first k rows.
- **R4:** constructed streams with known record sets reproduce those sets exactly; a
  constructed step with known rows lands those rows.
- **Known-negatives:** empty stream → `[]`; missing file → `[]` and no entry; truncated
  mid-read → oracle answer; an entry whose file vanished → dropped, not served.

## MEASUREMENT, PRE-COMMITTED
The SIXTH profile window on the same worker (g50t), same harness as window five. Stage 1
wins if `_read_stream` leaves the top cluster (its share falls to a minority of
`record_result`'s). Stage 2 wins if sqlite `execute` does the same. **THE LOSING CONDITION:**
if `record_result`'s share HOLDS with both gone, the cost is the per-step computation under
it — observer.observe, the spine, bet_book.settle, goal abduction, the frontier book — not
the reads, and the successor read is named now: **the record_result callee decomposition
read** (cumulative share per direct callee, one window), the next prereg's authority. Stage 2's
own losing condition: if commits were not the cost (WAL + synchronous=NORMAL makes one cheap),
the term is statement COUNT and the successor is the DB log handler's level, not batching.

## UNDO · SCOPE GUARD
Undo: `KnowledgeFabric.READ_CACHE = False` routes `query` to `_read_stream` (one dispatch);
step batching is one flag restoring commit-per-statement. Scope: `fabric.py`; the DB files only
as the attribution read names; the step boundary is two calls at the cycle's existing edge. No
signature, mint, planner, index, retention, or seq-cache changes. ≤ 2 gate files added, none modified.

## PROCTOR REVIEW (2026-08-21) — accepted with two riders
Accepted as drafted: the 64-byte anchor over mtime (granularity argument holds); query_tail
uncached; stage 2 gated by the attribution read — and the DatabaseLogHandler's
INSERT+COMMIT-per-DEBUG-record is the suspect to check FIRST, since a log handler paying a
commit per line is the writer-defect family in a new coat; stage 2's own losing condition
named separately. RIDER 1 — the cache is NOT unbounded: the L0 mem-kill suspects grow by
RETAINED STATE, not compute (the CPU read was flat while RSS hit 1.3GB), so an unbounded
parsed-stream cache is a candidate accelerant of exactly that defect. Bound it (LRU by
bytes, cap derived from observed stream sizes) and state the interaction with the L0
memory profile explicitly. RIDER 2 — shallow copies: add a falsifier that nested mutation
of a returned record does not alias into the cache (or audit every consumer and document
the aliasing as a contract) — the dirty-but-invisible failure is the one to gate.
