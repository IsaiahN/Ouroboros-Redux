# PREREG — THE SEQ WATERMARK: give the beat a clock without giving a record one (2026-08-21)

Status: DRAFT for Seat 3. Queued behind symbol receipts (the last queue item). Small,
tooling-grain, no engine file, no record schema change.

## The defect (tools/beat_rates.py's headline finding, PORT_LOG 2026-08-21)
No ego_fabric record on any topic on any box carries a timestamp — every record is `seq`
plus its domain fields. So every frame-internal rate the mandate's item 3 asks for
(minted / used / composed / retired / rederived per hour) **cannot be windowed at all**.
The beat currently prints a sound zero (stream mtime precedes the window) or NOT READABLE
(mtime inside it), plus all-time populations labelled "not a rate". That is honest and it
is not a learning curve.

## The trap, stated first
The obvious repair — a UTC field on `fabric.append` — **would break the byte-identity
gate** (`tests/gate/test_system_determinism.py`: every stream identical across two
identically-seeded runs). That gate is the strongest falsifier in five of this week's
builds, and it already forced a wall-clock `ms` field out of a gate record tonight. A
timestamp inside a record is that same defect wearing a useful hat. **No record gains a
clock.**

## The object
A WATERMARK SIDECAR — not a stream, not a record, never read by the agent: a per-box file
`.runs/swarm/<box>/watermarks.jsonl`, appended by the LAUNCHER (the supervisor at its
existing 60s poll; the sprint keeper at its equivalent), each line
`{"utc": ISO8601, "streams": {"<scope>/<topic>": <head seq>, ...}}`.
Windowing is then exact in SEQ space: the beat resolves a window's [start, end] UTC to the
bracketing watermarks and counts records whose `seq` falls between them. Resolution equals
the poll interval (60s) — finer than the hourly rates asked for.

Why the launcher and not the worker: the launcher is already outside the agent's
determinism surface (it writes status.txt and deploys.jsonl today), it survives worker
death, and it needs no engine edit. The worker never reads the file, so no agent behaviour
depends on wall-clock — the property `test_system_determinism` protects.

## Mechanism
1. One helper beside the existing deploy-record assembly (ONE assembly, both launchers call
   it — the `fleet_env_for` precedent): read each stream's head seq cheaply (the tail read
   `fabric._tail_records`/`_seed_seq` already does exactly this; do not parse whole files),
   append one line per poll.
2. `tools/beat_rates.py` gains `_window_seq(box, topic, t0, t1)` returning `(seq_lo,
   seq_hi)` or None; when None it falls back to today's mtime bracket unchanged (the
   fallback is the undo).
3. Bounded: the sidecar is truncated by the existing janitor policy (one new entry), and a
   missing/short sidecar degrades to the mtime bracket — never to a guess.

## Falsifiers (tests/gate/test_seq_watermark.py)
- F1 · NO RECORD CHANGES: the fabric's streams are byte-identical with the watermark writer
  running and not running (the determinism suite stays green; asserted directly).
- F2 · THE WINDOW IS EXACT: a constructed stream appended across three watermark ticks —
  the beat's count for a window equals the records actually appended in it, exactly, for
  every window boundary including both edges (half-open `(lo, hi]`, matching today's rule).
- F3 · DEGRADATION IS STATED: no sidecar → the mtime bracket and today's output, byte-for-
  byte; a sidecar with a gap → the window that spans the gap reads NOT READABLE, never an
  interpolation.
- F4 · THE AGENT NEVER READS IT: AST assertion that no module under `engines/` or the loop
  references the watermark file or the helper.
- F5 · CHEAP: the writer's per-poll cost is bounded by one tail read per stream, counted
  (no whole-file parse), asserted by counting reads on a constructed box.

## The laws this build satisfies (figures/*.svg)
- FIGURE 10 — "install what can be violated": today the fabric's own claim "these are the
  records of what happened" cannot be checked against WHEN, and the watermark is the
  convention that makes the window statable. It authors no verdict and no atom.
- FIGURE 2 — the anchor does not update: the launcher's clock is outside the frame it
  measures, and the agent cannot move it. Putting the clock inside the record would make
  the measured frame the author of its own time.
- FIGURE 1 — the rates it enables stay labelled frame-internal; a clock does not make
  minting progress.

## What this does NOT fix (named so nobody assumes it)
RETIRED is unreadable because no atoms record carries `evicted` yet (standing_half_life
writes the first ones — after it deploys). USED is unreadable on 7 boxes because their
`settlements` predate `atom_key`. `agents.retirement_reason` is NULL fleet-wide and has no
`retired_at` — that is a separate writer defect at the economy's grain. A clock does not
write a field nobody writes.
