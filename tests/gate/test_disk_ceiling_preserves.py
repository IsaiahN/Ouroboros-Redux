"""THE CEILING MUST NEVER DESTROY, AND MUST NEVER TOUCH CLAIM-SUPPORTING DATA.

PREREG_DISK_CEILING.md falsifiers F2 and F3, owed as a real gate rather than the scratch
harness that first verified them.

  F2 · IT NEVER DESTROYS. After archive-then-truncate, every archived record is recoverable
       BYTE-IDENTICALLY. Asserted by round-trip on raw bytes, not by inspection -- because
       the first implementation PASSED inspection and still corrupted data: it read with
       errors="replace" and rewrote in text mode, which mangles invalid UTF-8 and translates
       newlines on Windows. An evidence-preserving tool was silently mutating evidence.
       **So the fixture deliberately contains invalid UTF-8 and bare CRLF.**

  F3 · IT NEVER TOUCHES CLAIM-SUPPORTING DATA. With levelup_frames (irreplaceable), an arm
       box (a control) and a cited stream present, a FORCED sweep leaves all three
       byte-identical. Fails if any keep-always path changes by one byte.

R4, both ways, and the negative is the one that matters: a test that only proves "the
protected file survived" would also pass if the sweep did nothing at all. **F2 is that
known-negative** -- it requires the sweepable stream to have ACTUALLY been truncated.
"""
from __future__ import annotations

import gzip
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import tools.disk_ceiling as dc  # noqa: E402

# Invalid UTF-8 (0xff), a bare CR, and a lone LF -- the three things a text-mode
# round-trip destroys on Windows.
NASTY = b'{"a":1,"raw":"\xff\xfe"}\r\n'
PLAIN = b'{"a":2}\n'


def _build(tmp, n_records):
    """A miniature .runs tree: one sweepable stream, three keep-always paths."""
    runs = os.path.join(str(tmp), "runs")
    box = os.path.join(runs, "swarm", "gg01", "ego_fabric", "collective")
    arm = os.path.join(runs, "arms", "deadbeef")
    os.makedirs(box)
    os.makedirs(arm)

    sweepable = os.path.join(box, "import_queue.jsonl")
    payload = b"".join(NASTY if i % 3 == 0 else PLAIN for i in range(n_records))
    with open(sweepable, "wb") as fh:
        fh.write(payload)

    protected = {
        # (c) IRREPLACEABLE -- the only genuine frame corpus; the link-3 finding rests on it
        os.path.join(box, "levelup_frames.jsonl"): b'{"level":2}\n' * 9,
        # (b) CITED by a live claim document
        os.path.join(box, "winning_sequences.jsonl"): b'{"seq":[1,2]}\n' * 5,
        # (d) A CONTROL -- a measurement's own box is never a cleanup target
        os.path.join(arm, "import_queue.jsonl"): payload,
    }
    for p, data in protected.items():
        with open(p, "wb") as fh:
            fh.write(data)
    return runs, sweepable, payload, protected


def _point_at(runs):
    dc.RUNS = runs
    dc.ARCHIVE = os.path.join(runs, "archive")


def test_f2_archive_then_truncate_is_byte_identical_round_trip(tmp_path, monkeypatch):
    n = dc.TAIL_KEEP_RECORDS + 500
    runs, sweepable, original, _ = _build(tmp_path, n)
    monkeypatch.setattr(dc, "RUNS", runs)
    monkeypatch.setattr(dc, "ARCHIVE", os.path.join(runs, "archive"))

    acts = dc.sweep(force=True)
    assert acts, "sweep did nothing -- F2 cannot be evaluated"

    tail = open(sweepable, "rb").read()
    # THE KNOWN-NEGATIVE: if the stream was not actually shortened, a passing F2 would
    # be proving nothing. Truncation must have really happened.
    assert len(tail) < len(original), "stream was not truncated; F2 would be vacuous"
    assert tail.count(b"\n") == dc.TAIL_KEEP_RECORDS

    arcs = [f for f in os.listdir(os.path.join(runs, "archive")) if f.endswith(".gz")]
    assert len(arcs) == 1, f"expected exactly one archive, got {arcs}"
    with gzip.open(os.path.join(runs, "archive", arcs[0]), "rb") as gz:
        archived = gz.read()

    # THE WHOLE POINT: archive + live tail reconstitutes the original EXACTLY, byte for
    # byte, including the invalid UTF-8 and the CRLF.
    assert archived + tail == original
    assert b"\xff\xfe" in archived, "invalid UTF-8 did not survive the archive"
    assert b"\r\n" in archived, "CRLF was translated -- text-mode regression"


def test_f3_forced_sweep_leaves_claim_supporting_paths_byte_identical(tmp_path, monkeypatch):
    n = dc.TAIL_KEEP_RECORDS + 500
    runs, _sweepable, _payload, protected = _build(tmp_path, n)
    monkeypatch.setattr(dc, "RUNS", runs)
    monkeypatch.setattr(dc, "ARCHIVE", os.path.join(runs, "archive"))

    before = {p: open(p, "rb").read() for p in protected}
    acts = dc.sweep(force=True)
    assert acts, "sweep did nothing -- F3 would be vacuous"

    for p, was in before.items():
        assert open(p, "rb").read() == was, f"KEEP-ALWAYS PATH MUTATED: {p}"


def test_f1_guard_stops_a_run_when_over_the_ceiling(tmp_path, monkeypatch):
    """F1 -- IT GATES, IT DOES NOT WARN. Non-zero/raise, never 'log and continue'."""
    runs, _s, _p, _pr = _build(tmp_path, 50)
    monkeypatch.setattr(dc, "RUNS", runs)
    monkeypatch.setattr(dc, "CEILING_GB", 1e-12)   # below any real usage
    assert dc.guard(raise_on_breach=False) is False
    try:
        dc.guard(raise_on_breach=True)
    except dc.DiskCeilingExceeded:
        pass
    else:
        raise AssertionError("guard did not raise when over the ceiling")

    # And the known-negative: a generous ceiling must NOT trip the gate.
    monkeypatch.setattr(dc, "CEILING_GB", 10_000.0)
    assert dc.guard(raise_on_breach=False) is True


def test_wal_is_measured_but_not_budgeted(tmp_path, monkeypatch):
    """Seat 3, 2026-08-18: the WAL is EXCLUDED from the budget and REPORTED anyway --
    because excluding a quantity must never make it invisible."""
    runs = os.path.join(str(tmp_path), "runs")
    os.makedirs(runs)
    with open(os.path.join(runs, "core_data.db"), "wb") as fh:
        fh.write(b"x" * 4096)
    with open(os.path.join(runs, "core_data.db-wal"), "wb") as fh:
        fh.write(b"y" * 8192)
    monkeypatch.setattr(dc, "RUNS", runs)

    total, by_kind = dc.usage_bytes()
    assert by_kind.get("wal") == 8192, "WAL was not MEASURED"
    assert total == 4096, "WAL was BUDGETED -- Seat 3's revision is not in force"
