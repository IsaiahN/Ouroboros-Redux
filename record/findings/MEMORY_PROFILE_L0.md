# MEMORY PROFILE, L0 — what five instruments established and what they did not (2026-08-21)

Proctor-run reads on sp80 (the fleet's heaviest box, ~1GB RSS on the long-running worker,
fleet growth +2..+11 MB/min per box). Deliverable: the object is NOT named. What is named is
where it is not, and the instrument that would name it.

## Established (each with its sensitivity check)

| read | instrument | sensitivity check | result |
|---|---|---|---|
| 1 | tracemalloc, 300s, fresh process | dump landed mid-run (PLAN records precede it) | Python heap 75MB; ~40MB import machinery |
| 2 | gc.get_objects() ndarray walk | **FAILED** — "2 arrays, 0MB" in a running worker is impossible | void: numpy arrays are not GC-tracked |
| 3 | root-walk from 12 cognitive root types | constructed 4MB holder asserted | 0.1MB of arrays reachable from the agent's state |
| 4 | root-walk v2: every gc container, two dumps 270s apart | constructed 4MB holder asserted | arrays 1.1→1.4MB; objects +9k; sqlite connections 23→23 |
| 5 | correlation: growth rate vs largest stream file per box | n/a (a table) | no correlation (cd82 17.8MB +11/min; sc25 52MB +2.6/min) |

Also read: drive arm at recycles=0 (inconclusive: fast and slow boxes both `fixed`); level
(0 on both a fast and a slow grower).

## Falsified
- "numpy arrays held by the agent" — reads 3, 4.
- "Python-heap growth" — reads 1, 4 (+9k objects in 270s is nothing).
- "sqlite connection leak" — read 4 (23 constant).
- "heap fragmentation from fabric I/O `_next_seq` re-reads, proportional to stream size" — read 5.
  (PREREG_FABRIC_IO stands on its own CPU-profile evidence; it is not also the memory fix.)

## Open
The growth is native, unheld by any Python object, and clusters by box (ka59/cd82/wa30
~+11 MB/min vs +2..4 for the rest) on a property not yet identified. Remaining suspects:
(a) a C-extension buffer not owned by a Python container (scipy/sklearn workspaces, sqlite
page cache under a non-default `cache_size`, the arc_agi environment's own state);
(b) Windows heap retention from large transient allocations on a path that is NOT the
fabric stream (candidate: `import_queue.jsonl` — 52MB on ka59/sc25 — if the import door
reads it whole);
(c) per-generation environment objects freed late (held by a frame/traceback cycle until
a full gc — read 4 ran gc.collect() before each census, so they would have been freed,
but their native buffers' RSS may be retained by the allocator).

## The instrument that names it (builder-grade, prereg before build)
An in-process sampler: every cycle, `GetProcessMemoryInfo` via ctypes (no psutil in the
venv) → (rss, private bytes) appended to the narration as a `[MEM]` token with the cycle's
phase tokens (plan mode, mint verdict, import-door reads, generation boundary). The
deliverable is the PHASE whose presence predicts the RSS step — a regression of ΔRSS on
phase indicators over ~1h of one fast box and one slow box. Known-positive: allocate and
free a 50MB bytes object at a known cycle and confirm the step appears at that cycle.
Sensitivity before trust, as above.

## Instrument lessons carried
- `gc.get_objects()` cannot see numpy arrays; walk from tracked holders.
- `hasattr()` does not swallow werkzeug's RuntimeError — guard heap walks with bare except.
- A census of live output filters on PROCESS START, not commit time.
- A known-positive is part of the instrument, not an afterthought: two of five reads were
  voided by their own check before a number was reported.

## Instrument note (2026-08-21, the ramp sampler)
Windows commits lazily: a `bytearray(100MB)` moves neither working set nor the sampler
until its pages are touched, so the known-positive read 0MB and refused the run. The
sampler now reads PRIVATE (committed) bytes — what the supervisor's mem-kill sees grow —
beside working set, and the known-positive touches every page. Sixth instrument, third
self-refusal before a number was reported.
