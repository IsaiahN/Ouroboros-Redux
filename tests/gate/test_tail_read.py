"""PERF_AUDIT Q4 · THE TAIL READ — an O(tail) read that is BYTE-IDENTICAL to the O(stream) one.

THE DEFECT (measured, record/prereg/PERF_AUDIT.md:21-41): `affect.AffectGains._recent_settlements`
answers a question about the LAST 20 settlements by handing `fabric.query()` the whole
stream — a full-file parse, `json.loads` per line, no seek, no index — TWICE PER STEP
from `cognitive_loop.py:1849`. 0.314 ms at 20 records; 262.250 ms at 40,000.

THIS IS A RULE-R3 CHANGE: BEHAVIOUR-PRESERVING. The whole value of the fix is that
NOTHING downstream can tell it happened, so the gate is not "the new path looks right"
but "the new path returns EXACTLY what the old path returned". That is what this file
asserts, and it asserts it against a LITERAL TRANSCRIPTION of the pre-fix code
(`_ORACLE_read_stream` / `_oracle_query` / `_oracle_recent`, below) rather than against
the live implementation — an oracle that shares code with its subject proves nothing.

The pre-fix path had exactly two moving parts and the oracle reproduces both verbatim:
  * `KnowledgeFabric._read_stream` — text mode, encoding="utf-8", errors="replace",
    universal newlines, `line.strip()`, blank lines skipped, corrupt lines skipped,
    non-dict records skipped;
  * `KnowledgeFabric.query` — SEED roots first, in order, THEN the local root;
and the consumer took `rows[-WINDOW:]` off the end of that concatenation.

The edge cases below are the ones a reverse read gets wrong, and each is here because a
seek-based reader has a specific way of failing it: a stream shorter than the window; an
empty file; a missing file; a trailing partial line (a crash mid-write — the live boxes
have these); blank lines; corrupt lines; CRLF and bare-CR terminators (universal newlines
translate all three, `str.splitlines()` translates MORE than that and would be wrong);
invalid UTF-8 (errors="replace" must land on the same replacement characters, which it
only does if the read starts on a line boundary); multi-byte characters straddling the
block boundary the reverse reader chose; and a window that spans a seed root and the
local root at once.

SECOND ASSERTION, and it is the reason the change exists: the new path must read O(tail),
not O(stream). Measured here as PARSED RECORDS (a deterministic count — a wall-clock
assertion in a gate on a box whose load varies 20x would be a coin flip): the pre-fix path
parses every record in the file, the post-fix path must parse a bounded number regardless
of how long the stream is.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import fabric as _fabric_mod
from engines.egocentric.affect import AffectGains
from engines.egocentric.fabric import KnowledgeFabric

WINDOW = AffectGains.WINDOW


# ── THE ORACLE: the pre-fix code, transcribed literally, sharing nothing ──────────

def _ORACLE_read_stream(path: str) -> List[Dict[str, Any]]:
    """VERBATIM `KnowledgeFabric._read_stream` at the commit before the tail read."""
    out: List[Dict[str, Any]] = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:  # noqa: S112 -- VERBATIM: the pre-fix body, warts included
                continue
            if isinstance(rec, dict):
                out.append(rec)
    return out


def _oracle_query(fab: KnowledgeFabric, scope: str, topic: str) -> List[Dict[str, Any]]:
    """VERBATIM `KnowledgeFabric.query(scope, topic)`: seed roots FIRST, then local."""
    out: List[Dict[str, Any]] = []
    for base in list(fab.seeds) + [fab.root]:
        for rec in _ORACLE_read_stream(fab._stream_path(base, scope, topic)):
            out.append(rec)
    return out


def _oracle_recent(fab: KnowledgeFabric, n: int = WINDOW) -> List[Dict[str, Any]]:
    """VERBATIM `affect._recent_settlements`: the full parse, then `rows[-WINDOW:]`."""
    return _oracle_query(fab, "collective", "settlements")[-n:]


def _identical(got: List[Dict[str, Any]], want: List[Dict[str, Any]], why: str) -> None:
    """Byte-identity, not equality-of-meaning: same length, same order, same values AND
    same key order (dicts compare equal under reordered keys; a re-serialisation does
    not, and the replay contract in affect.py's docstring is about the trace)."""
    assert len(got) == len(want), (
        "%s: length %d != %d" % (why, len(got), len(want)))
    for i, (g, w) in enumerate(zip(got, want, strict=True)):
        assert json.dumps(g, ensure_ascii=False) == json.dumps(w, ensure_ascii=False), (
            "%s: record %d differs\n  got  %r\n  want %r" % (why, i, g, w))
        assert g == w, "%s: record %d unequal" % (why, i)


# ── live-SHAPED fixtures ──────────────────────────────────────────────────────────

def _settlement(i: int) -> Dict[str, Any]:
    """The shape actually on disk in .runs/swarm/ls20 (a real line, ids changed)."""
    return {"agent": "agent_d0c752e29aaf", "game": "ls20-9607627b", "level": 1,
            "action": 2, "members": 1, "best": 0.0, "nontrivial": bool(i % 3),
            "atom_key": None, "atom_bin": None, "seq": i + 1}


def _write_raw(root: str, scope_rel: str, topic: str, blob: bytes) -> str:
    d = os.path.join(root, scope_rel)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, topic + ".jsonl")
    with open(path, "wb") as fh:
        fh.write(blob)
    return path


def _lines(n: int, start: int = 0, sep: bytes = b"\n") -> bytes:
    return b"".join(
        json.dumps(_settlement(i), ensure_ascii=False).encode("utf-8") + sep
        for i in range(start, start + n))


def _fab(tmp_path, name: str = "box", seeds: Optional[List[str]] = None) -> KnowledgeFabric:
    return KnowledgeFabric(str(tmp_path / name), seeds=seeds,
                           agent_id="a", kin_key="v4")


# ── the O(tail) instrument ────────────────────────────────────────────────────────

class _ParseCounter:
    """Counts records actually PARSED off disk. Deterministic where a stopwatch is not."""

    def __init__(self, monkeypatch):
        self.n = 0
        real = json.loads

        def counting(s, *a, **kw):
            self.n += 1
            return real(s, *a, **kw)

        monkeypatch.setattr(_fabric_mod.json, "loads", counting)


# ══ F1 · BYTE-IDENTITY ════════════════════════════════════════════════════════════

class TestByteIdentity:
    """Every case where a reverse read can diverge from a forward read."""

    @pytest.mark.parametrize("n", [0, 1, 2, WINDOW - 1, WINDOW, WINDOW + 1, 200])
    def test_lengths_around_the_window(self, tmp_path, n):
        f = _fab(tmp_path, "n%d" % n)
        _write_raw(f.root, "collective", "settlements", _lines(n))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "stream of %d records" % n)

    def test_missing_file(self, tmp_path):
        f = _fab(tmp_path, "missing")
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "no stream file at all")
        assert f.query_tail("collective", "settlements", WINDOW) == []

    def test_missing_directory_tree(self, tmp_path):
        f = KnowledgeFabric(str(tmp_path / "never-created"), agent_id="a")
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "no fabric root on disk")

    def test_empty_file(self, tmp_path):
        f = _fab(tmp_path, "empty")
        _write_raw(f.root, "collective", "settlements", b"")
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "zero-byte stream")

    def test_only_blank_lines(self, tmp_path):
        f = _fab(tmp_path, "blankonly")
        _write_raw(f.root, "collective", "settlements", b"\n\n   \n\t\n\n")
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "whitespace-only stream")

    def test_trailing_partial_line(self, tmp_path):
        """A crash mid-write. The live boxes carry these (fabric.py:84-93 exists for it)."""
        f = _fab(tmp_path, "torn")
        blob = _lines(60) + json.dumps(_settlement(999), ensure_ascii=False)[:37].encode()
        _write_raw(f.root, "collective", "settlements", blob)
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "trailing partial line")

    def test_no_final_newline_but_complete_record(self, tmp_path):
        f = _fab(tmp_path, "nonl")
        _write_raw(f.root, "collective", "settlements", _lines(30).rstrip(b"\n"))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "last record with no terminator")

    def test_blank_lines_inside_the_window(self, tmp_path):
        """Blank lines are SKIPPED, so the window is 20 RECORDS, not 20 lines — a reverse
        reader that counts lines returns fewer than 20 records here."""
        f = _fab(tmp_path, "blanks")
        parts = []
        for i in range(40):
            parts.append(json.dumps(_settlement(i), ensure_ascii=False).encode() + b"\n")
            parts.append(b"\n" if i % 2 else b"   \n")
        _write_raw(f.root, "collective", "settlements", b"".join(parts))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "blank lines interleaved")

    def test_corrupt_lines_inside_the_window(self, tmp_path):
        """Same trap as blank lines: corrupt lines are skipped, not counted."""
        f = _fab(tmp_path, "corrupt")
        parts = []
        for i in range(40):
            parts.append(json.dumps(_settlement(i), ensure_ascii=False).encode() + b"\n")
            parts.append(b'{"half": ' + b"\n")
        _write_raw(f.root, "collective", "settlements", b"".join(parts))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "corrupt lines interleaved")

    def test_non_dict_json_lines_are_skipped(self, tmp_path):
        f = _fab(tmp_path, "nondict")
        parts = []
        for i in range(40):
            parts.append(json.dumps(_settlement(i), ensure_ascii=False).encode() + b"\n")
            parts.append(b'[1, 2, 3]\n"a string"\n7\nnull\n')
        _write_raw(f.root, "collective", "settlements", b"".join(parts))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "non-dict json lines interleaved")

    def test_crlf_terminators(self, tmp_path):
        f = _fab(tmp_path, "crlf")
        _write_raw(f.root, "collective", "settlements", _lines(50, sep=b"\r\n"))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "CRLF terminators")

    def test_bare_cr_terminators(self, tmp_path):
        """Universal newlines treat a lone \\r as a terminator. A reverse reader that
        splits on b"\\n" alone sees ONE enormous line here and returns one record."""
        f = _fab(tmp_path, "cr")
        _write_raw(f.root, "collective", "settlements", _lines(50, sep=b"\r"))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "bare-CR terminators")

    def test_mixed_terminators(self, tmp_path):
        f = _fab(tmp_path, "mixed")
        blob = (_lines(20, 0, b"\n") + _lines(20, 20, b"\r\n") + _lines(20, 40, b"\r"))
        _write_raw(f.root, "collective", "settlements", blob)
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "mixed terminators")

    def test_invalid_utf8_bytes(self, tmp_path):
        """errors="replace" must produce the SAME replacement characters, which only
        holds if the tail read resumes on a line boundary rather than mid-sequence."""
        f = _fab(tmp_path, "badutf8")
        parts = []
        for i in range(40):
            parts.append(json.dumps(_settlement(i), ensure_ascii=False).encode() + b"\n")
            parts.append(b'{"junk": "\xff\xfe\x80", "seq": %d}\n' % i)
        _write_raw(f.root, "collective", "settlements", b"".join(parts))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "invalid utf-8 in the window")

    def test_multibyte_characters(self, tmp_path):
        f = _fab(tmp_path, "utf8")
        parts = []
        for i in range(60):
            rec = _settlement(i)
            rec["note"] = "é中文\U0001f600 " * 3
            parts.append(json.dumps(rec, ensure_ascii=False).encode("utf-8") + b"\n")
        _write_raw(f.root, "collective", "settlements", b"".join(parts))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "multi-byte characters in the window")

    def test_records_longer_than_the_read_block(self, tmp_path):
        """One record bigger than whatever block the reverse reader grabs first: it must
        keep walking backwards, not truncate."""
        f = _fab(tmp_path, "huge")
        parts = []
        for i in range(30):
            rec = _settlement(i)
            rec["blob"] = "x" * 20000
            parts.append(json.dumps(rec, ensure_ascii=False).encode() + b"\n")
        _write_raw(f.root, "collective", "settlements", b"".join(parts))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "records larger than one read block")

    def test_long_stream(self, tmp_path):
        f = _fab(tmp_path, "long")
        _write_raw(f.root, "collective", "settlements", _lines(25000))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "25,000-record stream")

    def test_directory_instead_of_file(self, tmp_path):
        """_read_stream guards on os.path.isfile; the tail read must guard the same."""
        f = _fab(tmp_path, "isdir")
        os.makedirs(os.path.join(f.root, "collective", "settlements.jsonl"))
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "a directory where the stream should be")

    def test_unknown_scope_still_raises(self, tmp_path):
        f = _fab(tmp_path, "scope")
        with pytest.raises(ValueError):
            f.query_tail("nonsense", "settlements", WINDOW)


class TestSeedOverlay:
    """`query` reads SEED roots first, then the local root; the tail is the tail of THAT
    concatenation. A tail read that only ever looks at the local root silently drops the
    seeds — and OURO_FABRIC_SEEDS is live (cognitive_loop.py:1555-1560)."""

    def _seeded(self, tmp_path, seed_n, local_n, seeds=2):
        roots = []
        for s in range(seeds):
            r = str(tmp_path / ("seed%d" % s))
            _write_raw(r, "collective", "settlements", _lines(seed_n, start=1000 * (s + 1)))
            roots.append(r)
        f = _fab(tmp_path, "local", seeds=roots)
        _write_raw(f.root, "collective", "settlements", _lines(local_n))
        return f

    @pytest.mark.parametrize("seed_n,local_n", [
        (50, 50),      # window entirely inside the local root
        (50, 5),       # window straddles the last seed and the local root
        (3, 0),        # local root empty: the window is entirely seed records
        (0, 0),        # everything empty
        (2, 2),        # fewer records than the window across every root combined
        (1, 1),        # window spans all three roots at once
    ])
    def test_window_across_roots(self, tmp_path, seed_n, local_n):
        f = self._seeded(tmp_path, seed_n, local_n)
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "seeds=%d/%d local=%d" % (seed_n, 2, local_n))

    def test_missing_local_root_with_seeds(self, tmp_path):
        r = str(tmp_path / "s")
        _write_raw(r, "collective", "settlements", _lines(40))
        f = _fab(tmp_path, "absent", seeds=[r])
        _identical(f.query_tail("collective", "settlements", WINDOW),
                   _oracle_recent(f), "seeds present, local root absent")


class TestTheSeam:
    """The consumer side: `AffectGains._recent_settlements` is what the loop calls, and
    it must be the one that got faster — a fast fabric method nobody calls is the exact
    severed-organ shape BRIEF_STANDARD.md exists to stop."""

    def test_recent_settlements_matches_the_oracle(self, tmp_path):
        f = _fab(tmp_path, "seam")
        _write_raw(f.root, "collective", "settlements", _lines(5000))
        a = AffectGains(f)
        _identical(a._recent_settlements(), _oracle_recent(f), "the live consumer")
        assert a.errors == 0

    def test_gains_match_the_oracle(self, tmp_path):
        """The value that actually crosses into cognitive_loop.py:1849."""
        f = _fab(tmp_path, "gains")
        _write_raw(f.root, "collective", "settlements", _lines(5000))
        recent = _oracle_recent(f)
        rate = sum(1 for r in recent if r.get("nontrivial")) / float(len(recent))
        want = {"seed_bias": min(1.0, max(0.0, rate)),
                "mint_bar": 1.0 + 2.0 * (1.0 - rate),
                "persist": 0.0}     # no monitor attached: no live run
        assert AffectGains(f).gains() == want

    def test_the_consumer_reads_only_the_tail(self, tmp_path, monkeypatch):
        """The whole point, asserted at the consumer rather than at the fabric."""
        f = _fab(tmp_path, "seamcost")
        _write_raw(f.root, "collective", "settlements", _lines(20000))
        a = AffectGains(f)
        c = _ParseCounter(monkeypatch)
        a._recent_settlements()
        assert c.n <= 4 * WINDOW, (
            "the per-step affect read parsed %d records to answer a question about the "
            "last %d -- still O(stream)" % (c.n, WINDOW))

    def test_a_fabric_without_the_tail_read_still_works(self, tmp_path):
        """Duck-typed stand-in fabrics exist in the live tests (test_efference_copy.py
        :159). The consumer must degrade to the old full read, not raise."""

        class OldFabric:
            def __init__(self, rows):
                self.rows = rows

            def query(self, scope, topic, where=None, limit=None):
                return list(self.rows) if topic == "settlements" else []

        rows = [_settlement(i) for i in range(100)]
        a = AffectGains(OldFabric(rows))
        _identical(a._recent_settlements(), rows[-WINDOW:], "duck-typed fabric fallback")
        assert a.errors == 0

    def test_a_raising_fabric_is_still_swallowed(self, tmp_path):
        """The pre-fix contract: a fabric read failure counts an error and falls back to
        neutral channels; it never propagates into the loop."""

        class BrokenFabric:
            def query(self, *a, **kw):
                raise OSError("disk gone")

            def query_tail(self, *a, **kw):
                raise OSError("disk gone")

        a = AffectGains(BrokenFabric())
        assert a._recent_settlements() == []
        assert a.errors == 1
        assert a.gains() == {"seed_bias": 0.5, "mint_bar": 2.0, "persist": 0.0}


# ══ F2 · THE COST ACTUALLY MOVES ══════════════════════════════════════════════════

class TestCostIsBounded:

    @pytest.mark.parametrize("n", [100, 1000, 20000])
    def test_parses_are_bounded_by_the_window_not_the_stream(self, tmp_path, n,
                                                             monkeypatch):
        f = _fab(tmp_path, "cost%d" % n)
        _write_raw(f.root, "collective", "settlements", _lines(n))
        c = _ParseCounter(monkeypatch)
        got = f.query_tail("collective", "settlements", WINDOW)
        assert len(got) == WINDOW
        assert c.n <= 4 * WINDOW, (
            "%d records in the file, %d parsed to return the last %d" % (n, c.n, WINDOW))

    def test_cost_does_not_grow_with_the_stream(self, tmp_path, monkeypatch):
        """O(tail) stated as a shape, not a threshold: 100x the records, same work."""
        counts = []
        for n in (200, 20000):
            f = _fab(tmp_path, "shape%d" % n)
            _write_raw(f.root, "collective", "settlements", _lines(n))
            c = _ParseCounter(monkeypatch)
            f.query_tail("collective", "settlements", WINDOW)
            counts.append(c.n)
        assert counts[1] <= counts[0] + WINDOW, (
            "parses grew from %d to %d when the stream grew 100x" % tuple(counts))

    def test_bytes_read_are_bounded(self, tmp_path):
        """The other half of the cost: the old path READ the whole file. Asserted on the
        real 4 MiB shape so the number means something."""
        f = _fab(tmp_path, "bytes")
        blob = _lines(28772)
        _write_raw(f.root, "collective", "settlements", blob)
        assert len(blob) > 3 * 1024 * 1024, "fixture must be the live 4 MiB shape"
        seen = {"n": 0}
        real_open = open

        class _CountingFile:
            def __init__(self, fh):
                self._fh = fh

            def read(self, *a, **kw):
                data = self._fh.read(*a, **kw)
                seen["n"] += len(data)
                return data

            def __iter__(self):
                for line in self._fh:
                    seen["n"] += len(line)
                    yield line

            def __getattr__(self, name):
                return getattr(self._fh, name)

            def __enter__(self):
                self._fh.__enter__()
                return self

            def __exit__(self, *exc):
                return self._fh.__exit__(*exc)

        def counting_open(*a, **kw):
            return _CountingFile(real_open(*a, **kw))

        _fabric_mod.open = counting_open           # module-global shadow of builtins.open
        try:
            got = f.query_tail("collective", "settlements", WINDOW)
        finally:
            del _fabric_mod.open
        assert len(got) == WINDOW
        assert seen["n"] <= 256 * 1024, (
            "read %d bytes off a %d-byte stream to answer a 20-record question"
            % (seen["n"], len(blob)))


# ══ THE PROPERTY: randomised, because the enumerated cases are the ones I thought of ══

class TestTheProperty:

    def test_random_streams_agree_with_the_oracle(self, tmp_path):
        """Random mixtures of good/blank/corrupt/non-dict/bad-utf8 lines, random
        terminators, random torn tails, every window size from 1 to 25."""
        import random
        rng = random.Random(20260818)
        for trial in range(60):
            f = _fab(tmp_path, "prop%d" % trial)
            parts = []
            for i in range(rng.randint(0, 60)):
                sep = rng.choice([b"\n", b"\r\n", b"\r"])
                kind = rng.random()
                if kind < 0.70:
                    line = json.dumps(_settlement(i), ensure_ascii=False).encode("utf-8")
                elif kind < 0.78:
                    line = b""
                elif kind < 0.86:
                    line = b"   \t "
                elif kind < 0.92:
                    line = b'{"unterminated": '
                elif kind < 0.96:
                    line = b'[1,2,3]'
                else:
                    line = b'{"bad": "\xff\x80\xfe"}'
                parts.append(line + sep)
            if parts and rng.random() < 0.3:
                parts[-1] = parts[-1].rstrip(b"\r\n")[:rng.randint(0, 30)]
            _write_raw(f.root, "collective", "settlements", b"".join(parts))
            n = rng.randint(1, 25)
            _identical(f.query_tail("collective", "settlements", n),
                       _oracle_query(f, "collective", "settlements")[-n:],
                       "random trial %d (n=%d)" % (trial, n))

    def test_append_then_tail_read(self, tmp_path):
        """Through the real writer, not a hand-built blob: the tail read must agree with
        the full read after every single append."""
        f = _fab(tmp_path, "appended")
        for i in range(45):
            f.append("collective", "settlements", _settlement(i))
            _identical(f.query_tail("collective", "settlements", WINDOW),
                       _oracle_recent(f), "after append #%d" % i)
