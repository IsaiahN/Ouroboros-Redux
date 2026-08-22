"""THE SEQ WATERMARK -- a clock for the BEAT, and for no record.

record/prereg/PREREG_SEQ_WATERMARK.md.

THE DEFECT. No ego_fabric record on any topic on any box carries a timestamp:
every record is `seq` (fabric.append's monotonic per-stream counter) plus its
domain fields. So every frame-internal rate the mandate's item 3 asks for --
minted / used / composed / retired / rederived PER HOUR -- cannot be windowed at
all. tools/beat_rates.py prints a sound zero (stream mtime precedes the window)
or NOT READABLE (mtime inside it) and refuses to invent the rest.

THE TRAP, STATED FIRST. The obvious repair -- a UTC field on `fabric.append` --
WOULD BREAK THE BYTE-IDENTITY GATE (tests/gate/test_system_determinism.py: every
stream identical across two identically-seeded runs). That gate already forced a
wall-clock `ms` field out of a gate record this week. A timestamp inside a record
is that same defect wearing a useful hat. **NO RECORD GAINS A CLOCK.**

THE OBJECT. A SIDECAR -- not a stream, not a record, never read by the agent:

    .runs/swarm/<box>/watermarks.jsonl        (BESIDE ego_fabric, never inside it)
    {"utc": "2026-08-22T01:23:45", "poll": 60,
     "streams": {"collective/<topic>": <head seq>, ...}}

one line per LAUNCHER POLL. Windowing is then exact in SEQ space: the beat
resolves a window's [start, end] UTC to the bracketing watermarks and counts the
records whose `seq` falls between them. Resolution equals the poll interval --
finer than the hourly rates asked for.

WHY THE LAUNCHER AND NOT THE WORKER (FIGURE 2 -- the anchor does not update): the
launcher is already outside the agent's determinism surface (it writes status.txt
and deploys.jsonl today), it survives worker death, and it needs no engine edit.
The worker never reads this file, so no agent behaviour depends on wall-clock --
which is the property test_system_determinism protects. Putting the clock inside
the record would make the measured frame the author of its own time.

ONE ASSEMBLY, BOTH LAUNCHERS -- the `tools/fleet_env.py` precedent exactly: the
supervisor calls `write_all` at its 60s poll and the sprint keeper at its
--interval pass, neither transcribing the other. A transcription drifts.

WHAT IS WATERMARKED, and what is not. The COLLECTIVE scope only, every
`<topic>.jsonl` in it, by directory listing so a new topic is covered the day it
appears. NOT the personal scope: 308 narration streams on one box x 25 boxes is
the cost F5 bounds, and no line of the beat windows narration (rung 1's residual
is a bounded tail sample with its denominator printed, never a window). Archive
and sidecar files (`<topic>.archive.jsonl`) are skipped by construction -- a
topic name carries no dot.

WHAT LEAVES A STREAM HERE IS ONE INTEGER. `head_seq` reads the LAST record of a
stream through `KnowledgeFabric._tail_records(path, 1)` -- the fabric's own
O(tail) reader, named rather than re-derived (it is what `_seed_seq` uses for the
same question) -- and returns `int(rec["seq"])`. No domain field is read, none is
written, and no stream is ever opened for writing.

BOUNDED, BY THE JANITOR'S OWN NUMBER. The sidecar is trimmed when it exceeds
`FabricJanitor.STREAM_MAX_BYTES` (2 MB, imported -- NOT transcribed, NOT a new
knob), keeping the newest half. Retention at 60s and ~25 collective streams is
therefore never less than ~30 hours of ticks, which is the horizon the beat can
window over. SIZE-triggered, never cadence-triggered: the janitor's own
philosophy, applied to the janitor's own threshold.

WHY THE TRIM LIVES HERE AND NOT IN THE JANITOR. The prereg said "truncated by the
existing janitor policy (one new entry)". engines/egocentric/janitor.py is
PRODUCTION, and this file's F4 falsifier is that NO module under engines/ -- and
not the loop -- references the watermark at all. A janitor policy row would have
been the one thing the falsifier forbids. So the bound is enforced by the writer,
against the janitor's imported constant, and the residue is stated here.

IMPORT-TIME PURITY. Module import touches no file and imports no engine: the
fabric and the janitor are imported INSIDE the functions that need them. Both
launchers hold a clean-import gate (tests/gate/test_sprint_keeper.py, F5 of
tests/gate/test_hold_stops_recycles.py) and the beat holds its own.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

WATERMARK_NAME = "watermarks.jsonl"
FABRIC_DIR = "ego_fabric"
SCOPE = "collective"
SUFFIX = ".jsonl"

# The two field names the beat resolves a window with, named once so the reader
# and the writer cannot drift: `utc` is the launcher's clock at the tick, `poll`
# is the launcher's OWN declared cadence in seconds (the supervisor's POLL_SEC,
# the keeper's --interval). `poll` is what makes the beat's gap rule DERIVED
# rather than chosen: a boundary further from its bracketing tick than the writer
# said it polls is a MISSED TICK, and the window over it is NOT READABLE.
F_UTC, F_POLL, F_STREAMS = "utc", "poll", "streams"


def utc_now() -> str:
    """ISO8601 UTC in the shape deploy_record already writes (no offset, no Z):
    the ledger and the sidecar are read by the same eyes on the same box."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def scope_dir(box_dir: str) -> str:
    return os.path.join(box_dir, FABRIC_DIR, SCOPE)


def watermark_path(box_dir: str) -> str:
    return os.path.join(box_dir, WATERMARK_NAME)


def stream_files(box_dir: str) -> List[Tuple[str, str]]:
    """[(key, path)] for every collective stream on this box, sorted by key.

    `key` is "<scope>/<topic>" -- the prereg's stated shape. A basename whose
    topic part carries a dot is NOT a topic (`atoms.archive.jsonl`,
    `atoms.jsonl.bak` never reaches here since it does not end in .jsonl): the
    janitor's archives hold records already removed from the stream, and
    watermarking them would put a second seq series under one name."""
    out: List[Tuple[str, str]] = []
    try:
        names = sorted(os.listdir(scope_dir(box_dir)))
    except OSError:
        return out
    for name in names:
        if not name.endswith(SUFFIX):
            continue
        topic = name[:-len(SUFFIX)]
        if not topic or "." in topic:
            continue
        out.append((SCOPE + "/" + topic, os.path.join(scope_dir(box_dir), name)))
    return out


def head_seq(path: str) -> Optional[int]:
    """The stream's head seq: ONE tail read, never a whole-file parse.

    `KnowledgeFabric._tail_records(path, 1)` is the fabric's own answer to this
    exact question (`_seed_seq` asks it the same way), so a torn tail, a blank
    line and a non-dict line are skipped here exactly as the fabric skips them.

    0  -- the stream is absent or holds no well-formed record: nothing has been
          appended, and seq 1 is the first append there will ever be.
    None -- the last well-formed record carries no readable `seq`. NOT a guess
          and NOT a zero: the beat treats a null head as "this topic is not
          windowable at this tick" and degrades to the mtime bracket. A zero
          here would rewind the window's floor and over-count."""
    from engines.egocentric.fabric import KnowledgeFabric  # lazy: import purity
    tail = KnowledgeFabric._tail_records(path, 1)
    if not tail:
        return 0
    raw = tail[-1].get("seq")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def stream_heads(box_dir: str) -> Dict[str, Optional[int]]:
    """{"collective/<topic>": head seq} for every collective stream present.

    A key ABSENT from a tick means the stream file did not exist at that tick,
    which is head 0 and nothing else -- the reader may treat it as 0 soundly,
    because this writer emits every file it finds, including the empty ones."""
    return {key: head_seq(path) for key, path in stream_files(box_dir)}


def watermark_record(box_dir: str, poll: float,
                     utc: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """One tick, or None when this box has no fabric at all to watermark.

    None (rather than an empty record) is the whole reason a launcher may call
    this unconditionally: a box directory that exists because a worker was
    spawned into it, with no fabric yet, gains no file.

    A fabric that exists with an EMPTY collective scope DOES tick, with
    `streams: {}`. That tick is not noise -- it is the floor the beat needs: it
    says every topic stood at head 0 at that instant, so the first records ever
    appended are inside the first window that brackets it."""
    if not os.path.isdir(os.path.join(box_dir, FABRIC_DIR)):
        return None
    return {F_UTC: utc if utc is not None else utc_now(),
            F_POLL: int(poll),
            F_STREAMS: stream_heads(box_dir)}


def append_watermark(box_dir: str, poll: float,
                     utc: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Append one tick to the box's sidecar and bound the file. Returns the
    record written, or None (no fabric here, or the write failed).

    A failure is SILENT BY DESIGN, in the shape `append_ledger` already uses: the
    sidecar is an instrument's input, and a launcher that dies because a
    measurement could not be taken is a worse launcher."""
    rec = watermark_record(box_dir, poll, utc)
    if rec is None:
        return None
    path = watermark_path(box_dir)
    try:
        with open(path, "a", encoding="utf-8") as fh:
            # A CRASH-TORN TAIL COSTS ONE TICK, NEVER TWO. If the last line has no
            # terminator (the launcher died mid-append), this tick would MERGE with
            # it and be lost with it -- the fabric's own `clean` rule, which the
            # fabric must live with because its bytes are gate-compared and a
            # sidecar's are not. Here the torn line is simply closed: it stays
            # unparseable and the reader skips it, and this tick lands whole.
            if not _ends_clean(path):
                fh.write("\n")
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        return None
    _bound(path)
    return rec


def _ends_clean(path: str) -> bool:
    """True when the sidecar is absent, empty, or ends in a terminator -- read off
    the last byte, never by reading the file."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return True
    if size <= 0:
        return True
    try:
        with open(path, "rb") as fh:
            fh.seek(size - 1)
            return fh.read(1) in (b"\n", b"\r")
    except OSError:
        return True


def write_all(root: str, boxes, poll: float,
              utc: Optional[str] = None) -> List[str]:
    """One tick per box, ONE UTC for the whole sweep (so the fleet's ticks line
    up and a window resolves to the same pair of ticks on every box). Returns the
    boxes actually watermarked."""
    stamp = utc if utc is not None else utc_now()
    return [b for b in boxes
            if append_watermark(os.path.join(root, b), poll, stamp) is not None]


# ── the bound ─────────────────────────────────────────────────────────────────

def max_bytes() -> int:
    """The janitor's OWN per-stream threshold, imported. No new knob: change
    record/canon/KNOBS.md O2 and this moves with it."""
    from engines.egocentric.janitor import FabricJanitor  # lazy: import purity
    return int(FabricJanitor.STREAM_MAX_BYTES)


def _bound(path: str) -> None:
    """SIZE-triggered trim, keeping the NEWEST half: the janitor's philosophy
    (size, never cadence) against the janitor's own number. Atomic (tmp then
    replace), and the first partial line of the kept tail is dropped so the file
    always holds whole records."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return
    cap = max_bytes()
    if size <= cap:
        return
    keep = cap // 2
    try:
        with open(path, "rb") as fh:
            fh.seek(size - keep)
            blob = fh.read()
        cut = blob.find(b"\n")
        blob = blob[cut + 1:] if cut >= 0 else b""
        tmp = path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(blob)
        os.replace(tmp, path)
    except OSError:
        return


# ── the read side (the beat's, and nobody else's) ─────────────────────────────

def read_watermarks(path: str) -> List[Dict[str, Any]]:
    """Every well-formed tick in one sidecar, in file order.

    The fabric's own reader rules -- strip, skip blank, skip corrupt, skip
    non-dict -- because a crash mid-append is normal on these boxes and must
    never be fatal to a read. A tick with no `utc` or no `streams` dict is not a
    tick and is dropped here rather than half-interpreted downstream."""
    out: List[Dict[str, Any]] = []
    if not os.path.isfile(path):
        return out
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return out
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if (isinstance(rec, dict) and isinstance(rec.get(F_UTC), str)
                and isinstance(rec.get(F_STREAMS), dict)):
            out.append(rec)
    return out
