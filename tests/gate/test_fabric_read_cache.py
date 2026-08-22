"""FABRIC I/O STAGE 1 (PREREG_FABRIC_IO.md): the parsed-stream read cache.

THE DEFECT (window five / 6-b, g50t): `fabric.query` re-parsed whole JSONL streams ~4x
per cycle (572 `_read_stream` calls / 130 cycles, 32.3%) -- produced once, parsed many.

THE CONTRACT (fabric.py, module bottom, `_cached_stream`): one process-level entry per
stream path holding the parsed dicts of every TERMINATED line, `upto` (the byte offset
past the last terminator), and the 64-byte anchor before it. Every call: stat, then
exactly one of MISSING -> drop + []; VALID (size >= upto AND anchor matches) -> decode
only the appended bytes, cache the terminated lines, return-but-never-cache the
unterminated remainder; INVALID -> full read, re-seed. Bounded LRU by stream bytes
(RIDER 1, KNOBS G35). Records are SHALLOW copies (RIDER 2: nested values shared by
contract, every consumer audited). `READ_CACHE = False` is the undo.

THIS IS A RULE-R3 CHANGE: the gate is "returns EXACTLY what the old path returned".
THE ORACLE is a literal transcription of the pre-build `_read_stream` + `query`
(`_ORACLE_read_stream` / `_oracle_query` below), sharing nothing with the live code.
F1 asserts cached == oracle at EVERY read of every constructed sequence and on every
stream of one real box (read-only); F2/F3 count full reads, tail reads and bytes
decoded (never wall-clock); R4 + known-negatives + the two riders + the undo follow.
"""
from __future__ import annotations

import ast
import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import fabric as _fabric_mod
from engines.egocentric.fabric import KnowledgeFabric

# ── THE ORACLE: the pre-build read path, transcribed literally ────────────────────

def _ORACLE_read_stream(path: str) -> List[Dict[str, Any]]:
    """VERBATIM `KnowledgeFabric._read_stream` at 41886d6."""
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
            except Exception:  # noqa: S112 -- VERBATIM
                continue
            if isinstance(rec, dict):
                out.append(rec)
    return out


def _oracle_query(fab: KnowledgeFabric, scope: str, topic: str,
                  where: Optional[Callable[[Dict[str, Any]], Any]] = None,
                  limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """VERBATIM `KnowledgeFabric.query` at 41886d6: seeds FIRST, then local;
    where/limit over the concatenation."""
    out: List[Dict[str, Any]] = []
    for base in list(fab.seeds) + [fab.root]:
        for rec in _ORACLE_read_stream(fab._stream_path(base, scope, topic)):
            if where is not None and not where(rec):
                continue
            out.append(rec)
            if limit is not None and len(out) >= limit:
                return out
    return out


def _identical(got, want, why: str) -> None:
    """Byte-identity: same length, order, values AND key order."""
    assert len(got) == len(want), "%s: length %d != %d" % (why, len(got), len(want))
    for i, (g, w) in enumerate(zip(got, want, strict=True)):
        assert json.dumps(g, ensure_ascii=False) == json.dumps(w, ensure_ascii=False), (
            "%s: record %d differs\n  got  %r\n  want %r" % (why, i, g, w))
        assert g == w


def _check(fab: KnowledgeFabric, why: str, scope="collective", topic="s", **kw) -> None:
    _identical(fab.query(scope, topic, **kw), _oracle_query(fab, scope, topic, **kw), why)


# ── fixtures ─────────────────────────────────────────────────────────────────────

def _settlement(i: int) -> Dict[str, Any]:
    return {"agent": "agent_d0c752e29aaf", "game": "ls20-9607627b", "level": 1,
            "action": 2, "members": 1, "best": 0.0, "nontrivial": bool(i % 3),
            "atom_key": None, "atom_bin": None, "seq": i + 1}


def _line(i: int, sep: bytes = b"\n", **extra) -> bytes:
    rec = _settlement(i)
    rec.update(extra)
    return json.dumps(rec, ensure_ascii=False).encode("utf-8") + sep


def _lines(n: int, start: int = 0, sep: bytes = b"\n") -> bytes:
    return b"".join(_line(i, sep) for i in range(start, start + n))


def _write(root: str, blob: bytes, scope="collective", topic="s") -> str:
    d = os.path.join(root, scope)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, topic + ".jsonl")
    with open(p, "wb") as fh:
        fh.write(blob)
    return p


def _app(root: str, blob: bytes, scope="collective", topic="s") -> None:
    with open(os.path.join(root, scope, topic + ".jsonl"), "ab") as fh:
        fh.write(blob)


def _fab(tmp_path, name: str, seeds=None) -> KnowledgeFabric:
    return KnowledgeFabric(str(tmp_path / name), seeds=seeds, agent_id="a", kin_key="v4")


@pytest.fixture(autouse=True)
def _clean_caches():
    KnowledgeFabric.drop_read_cache()
    _fabric_mod._SEQ_TAIL.clear()
    for k in _fabric_mod.READ_STATS:
        _fabric_mod.READ_STATS[k] = 0
    yield
    KnowledgeFabric.drop_read_cache()
    _fabric_mod._SEQ_TAIL.clear()


def _stats() -> Dict[str, int]:
    return dict(_fabric_mod.READ_STATS)


def _delta(before: Dict[str, int]) -> Dict[str, int]:
    now = _stats()
    return {k: now[k] - before.get(k, 0) for k in now}


# ══ F1 · EQUIVALENCE: the corpus, every item, at every read ════════════════════════

class TestF1Corpus:
    """Each item is a SEQUENCE of file states; cached == oracle after every state
    (the cache warm from the previous state, which is the point)."""

    def _run(self, tmp_path, name, states):
        f = _fab(tmp_path, name)
        for k, st in enumerate(states):
            st(f.root)
            for rnd in range(2):                            # read twice: warm path too
                _check(f, "%s state %d read %d" % (name, k, rnd))
        return f

    def test_empty_file(self, tmp_path):
        f = self._run(tmp_path, "empty", [lambda r: _write(r, b"")])
        assert f.query("collective", "s") == []

    def test_missing_file(self, tmp_path):
        f = _fab(tmp_path, "missing")
        _check(f, "missing")
        assert f.query("collective", "s") == []
        assert not _fabric_mod._READ_CACHE, "a missing file must leave no entry"

    def test_one_record(self, tmp_path):
        self._run(tmp_path, "one", [lambda r: _write(r, _line(0))])

    def test_blank_lines(self, tmp_path):
        self._run(tmp_path, "blank", [
            lambda r: _write(r, b"\n\n   \n\t\n" + _line(0) + b"\n" + _line(1) + b"   \n")])

    def test_corrupt_lines(self, tmp_path):
        self._run(tmp_path, "corrupt", [
            lambda r: _write(r, _line(0) + b'{"half": \n' + _line(1) + b"{\n"),
            lambda r: _app(r, b'{"more": ' + b"\n" + _line(2))])

    def test_non_dict_lines(self, tmp_path):
        self._run(tmp_path, "nondict", [
            lambda r: _write(r, b'[1, 2, 3]\n' + _line(0) + b'"a string"\n7\nnull\n' + _line(1))])

    def test_crlf(self, tmp_path):
        self._run(tmp_path, "crlf", [lambda r: _write(r, _lines(30, sep=b"\r\n")),
                                     lambda r: _app(r, _lines(5, 30, sep=b"\r\n"))])

    def test_bare_cr(self, tmp_path):
        self._run(tmp_path, "cr", [lambda r: _write(r, _lines(30, sep=b"\r")),
                                   lambda r: _app(r, _lines(5, 30, sep=b"\r"))])

    def test_mixed_terminators(self, tmp_path):
        self._run(tmp_path, "mixed", [
            lambda r: _write(r, _lines(10, 0, b"\n") + _lines(10, 10, b"\r\n") + _lines(10, 20, b"\r")),
            lambda r: _app(r, _lines(3, 30, b"\r\n"))])

    def test_split_crlf_across_reads(self, tmp_path):
        """The "\\r" lands, the reader runs, THEN the "\\n" lands."""
        self._run(tmp_path, "splitcrlf", [
            lambda r: _write(r, _lines(3) + _line(3, sep=b"\r")),
            lambda r: _app(r, b"\n" + _line(4, sep=b"\r")),
            lambda r: _app(r, b"\n")])

    def test_invalid_utf8(self, tmp_path):
        self._run(tmp_path, "badutf8", [
            lambda r: _write(r, _line(0) + b'{"junk": "\xff\xfe\x80", "seq": 2}\n' + _line(2)),
            lambda r: _app(r, b'{"junk": "\xc3", "seq": 4}\n'),          # truncated sequence
            lambda r: _app(r, b'{"junk": "\xe2\x82'),                    # torn mid-character
            lambda r: _app(r, b'\xac", "seq": 5}\n')])

    def test_multibyte_at_the_anchor_boundary(self, tmp_path):
        """Place a 4-byte character straddling (size - 64) at the first read, so the
        anchor starts mid-character; the anchor is raw bytes and must still hold."""
        f = _fab(tmp_path, "mbanchor")
        base = _lines(5)
        pad = b'{"note": "'
        fill = ("x" * (64 - len(pad) - 2)).encode()
        rec = pad + "\U0001f600".encode("utf-8") + fill + b'"}\n'
        _write(f.root, base + rec)
        size = os.path.getsize(os.path.join(f.root, "collective", "s.jsonl"))
        a0 = size - 64
        assert (rec[:a0 - len(base)] if a0 > len(base) else b"") is not None
        _check(f, "multibyte anchor 0")
        ent = _fabric_mod._READ_CACHE[os.path.abspath(os.path.join(f.root, "collective", "s.jsonl"))]
        assert len(ent["anchor"]) == 64
        _app(f.root, _line(9))
        _check(f, "multibyte anchor 1")
        _app(f.root, _line(10))
        _check(f, "multibyte anchor 2")
        d = _delta({})
        assert d["full"] == 1, "the anchor did not hold across a multibyte boundary"

    def test_terminated_tail(self, tmp_path):
        self._run(tmp_path, "term", [lambda r: _write(r, _lines(20)),
                                     lambda r: _app(r, _lines(1, 20))])

    def test_torn_tail(self, tmp_path):
        self._run(tmp_path, "torn", [
            lambda r: _write(r, _lines(20) + json.dumps(_settlement(99))[:37].encode()),
            lambda r: _app(r, b"\n" + _lines(2, 21))])

    def test_complete_but_unterminated_tail(self, tmp_path):
        self._run(tmp_path, "nonl", [lambda r: _write(r, _lines(20).rstrip(b"\n")),
                                     lambda r: _app(r, b"\n"),
                                     lambda r: _app(r, _lines(1, 20).rstrip(b"\n"))])

    def test_tail_that_grows_into_a_record(self, tmp_path):
        whole = _line(50)
        self._run(tmp_path, "grows", [
            lambda r: _write(r, _lines(10) + whole[:20]),
            lambda r: _app(r, whole[20:40]),
            lambda r: _app(r, whole[40:]),
            lambda r: _app(r, _line(51))])

    def test_append_between_reads(self, tmp_path):
        def appender(i):
            return lambda r: _app(r, _line(i))
        self._run(tmp_path, "appended", [lambda r: _write(r, _lines(10))]
                  + [appender(i) for i in range(10, 30)])

    def test_rewrite_shrink(self, tmp_path):
        self._run(tmp_path, "shrink", [lambda r: _write(r, _lines(40)),
                                       lambda r: _write(r, _lines(7)),
                                       lambda r: _app(r, _lines(3, 7))])

    def test_rewrite_that_grows(self, tmp_path):
        self._run(tmp_path, "grow", [lambda r: _write(r, _lines(10)),
                                     lambda r: _write(r, _lines(10, 100) + _lines(10, 200)),
                                     lambda r: _app(r, _lines(1, 300))])

    def test_same_size_rewrite(self, tmp_path):
        self._run(tmp_path, "samesize", [lambda r: _write(r, _lines(10)),
                                         lambda r: _write(r, _lines(10, 20)),
                                         lambda r: _app(r, _lines(1, 30))])

    def test_seed_and_local_roots(self, tmp_path):
        s1, s2 = str(tmp_path / "seed1"), str(tmp_path / "seed2")
        _write(s1, _lines(5, 1000))
        _write(s2, _lines(3, 2000))
        f = _fab(tmp_path, "local", seeds=[s1, s2])
        _check(f, "seeds only, local absent")
        _write(f.root, _lines(4))
        _check(f, "seeds + local")
        _app(s2, _lines(2, 2003))                          # a seed grows (out-of-band)
        _check(f, "seed grew")
        _check(f, "limit across roots", limit=6)
        _check(f, "limit = 1", limit=1)
        _check(f, "where", where=lambda r: r["seq"] % 2 == 0)
        _check(f, "where + limit", where=lambda r: r["seq"] > 1001, limit=3)

    def test_where_sees_the_same_records_in_the_same_order(self, tmp_path):
        f = _fab(tmp_path, "whereorder")
        _write(f.root, _lines(50))
        seen_c, seen_o = [], []
        f.query("collective", "s", where=lambda r: seen_c.append(r["seq"]) or True)
        _oracle_query(f, "collective", "s", where=lambda r: seen_o.append(r["seq"]) or True)
        assert seen_c == seen_o

    def test_random_sequences(self, tmp_path):
        """Random file-state sequences: writes, appends of good/blank/corrupt/torn
        material with random terminators, shrinks, same-size rewrites."""
        import random
        rng = random.Random(20260821)
        for trial in range(40):
            f = _fab(tmp_path, "rand%d" % trial)
            _write(f.root, b"")
            for step in range(rng.randint(1, 14)):
                k = rng.random()
                sep = rng.choice([b"\n", b"\r\n", b"\r"])
                if k < 0.55:
                    _app(f.root, b"".join(_line(rng.randint(0, 99), sep)
                                          for _ in range(rng.randint(1, 6))))
                elif k < 0.7:
                    _app(f.root, rng.choice([b"", b"   " + sep, b'{"t": ' , b"[1]" + sep,
                                             b'{"bad": "\xff\x80"}' + sep,
                                             json.dumps(_settlement(7)).encode()[:rng.randint(1, 40)]]))
                elif k < 0.8:
                    _app(f.root, sep)
                elif k < 0.9:
                    _write(f.root, _lines(rng.randint(0, 8), sep=sep))
                else:
                    _app(f.root, "é中文\U0001f600".encode("utf-8")[:rng.randint(1, 9)])
                _check(f, "trial %d step %d" % (trial, step))
                if rng.random() < 0.3:
                    _check(f, "trial %d step %d re-read" % (trial, step))


class TestF1RealBox:

    def test_every_stream_of_one_real_box(self):
        """Read-only replay of every stream under the smallest real box that has at
        least 100 streams (population: .runs/swarm/*/ego_fabric as found on this
        machine; skipped where absent)."""
        swarm = os.path.join(REPO, ".runs", "swarm")
        if not os.path.isdir(swarm):
            pytest.skip("no .runs/swarm on this machine")
        boxes = []
        for b in sorted(os.listdir(swarm)):
            ef = os.path.join(swarm, b, "ego_fabric")
            if not os.path.isdir(ef):
                continue
            files, total = [], 0
            for r, _d, fs in os.walk(ef):
                for fn in fs:
                    if fn.endswith(".jsonl"):
                        p = os.path.join(r, fn)
                        files.append(p)
                        total += os.path.getsize(p)
            if len(files) >= 100:
                boxes.append((total, b, files))
        if not boxes:
            pytest.skip("no box with >= 100 streams")
        total, box, files = min(boxes)
        n = 0
        for p in sorted(files):
            _identical(_fabric_mod._cached_stream(p), _ORACLE_read_stream(p),
                       "%s %s (cold)" % (box, os.path.relpath(p, swarm)))
            _identical(_fabric_mod._cached_stream(p), _ORACLE_read_stream(p),
                       "%s %s (warm)" % (box, os.path.relpath(p, swarm)))
            n += 1
        assert n >= 100, "box %s: %d streams" % (box, n)


# ══ F2 · THE READ COUNT COLLAPSES ═════════════════════════════════════════════════

class TestF2ReadCount:

    def test_hundred_cycles_of_todays_query_set(self, tmp_path, monkeypatch):
        """Growing streams, the per-cycle query set (atoms x3, mint_verdicts x2,
        import_queue, settlements): full reads per cycle ~4 -> 0 after warm-up;
        bytes decoded per cycle <= bytes appended since the previous cycle plus the
        volatile remainder (0 here: the writer terminates every line)."""
        f = _fab(tmp_path, "cycles")
        calls = {"read_stream": 0}
        orig = KnowledgeFabric._read_stream

        def counting(path):
            calls["read_stream"] += 1
            return orig(path)
        monkeypatch.setattr(KnowledgeFabric, "_read_stream", staticmethod(counting))
        topics = {"atoms": 3, "mint_verdicts": 5, "import_queue": 2, "settlements": 4}
        queries = ["atoms", "atoms", "atoms", "mint_verdicts", "mint_verdicts",
                   "import_queue", "settlements"]

        def sizes():
            return {t: os.path.getsize(f._stream_path(f.root, "collective", t))
                    for t in topics}
        fulls, tails = [], []
        prev = dict.fromkeys(topics, 0)
        for cycle in range(100):
            for t, k in topics.items():
                for i in range(k):
                    f.append("collective", t, _settlement(cycle * 10 + i))
            now = sizes()
            appended = {t: now[t] - prev[t] for t in topics}
            before = _stats()
            for t in queries:
                _identical(f.query("collective", t), _oracle_query(f, "collective", t),
                           "cycle %d %s" % (cycle, t))
            d = _delta(before)
            fulls.append(d["full"])
            tails.append(d["tail"])
            assert d["bytes"] <= sum(appended.values()), (
                "cycle %d decoded %d bytes for %d appended" % (cycle, d["bytes"], sum(appended.values())))
            prev = now
        assert fulls[0] == len(topics), "warm-up: one full read per stream, got %r" % fulls[0]
        assert fulls[1:] == [0] * 99, "full reads per cycle after warm-up: %r" % fulls[1:]
        assert all(t == len(topics) for t in tails[1:]), "tail reads per cycle: %r" % tails[1:]
        assert calls["read_stream"] == 0, (
            "_read_stream was called %d times under the cache (the undo path leaked)"
            % calls["read_stream"])


# ══ F3 · INVALIDATION BOTH WAYS ════════════════════════════════════════════════════

class TestF3Invalidation:

    def test_append_does_not_invalidate(self, tmp_path):
        f = _fab(tmp_path, "app")
        _write(f.root, _lines(100))
        _check(f, "seed")
        before = _stats()
        for i in range(100, 120):
            _app(f.root, _line(i))
            _check(f, "append %d" % i)
        d = _delta(before)
        assert d["full"] == 0 and d["tail"] == 20

    def test_rewrite_invalidates_exactly_once(self, tmp_path):
        f = _fab(tmp_path, "rw")
        _write(f.root, _lines(100))
        _check(f, "seed")
        before = _stats()
        _write(f.root, _lines(30, 500))
        for i in range(5):
            _check(f, "after rewrite %d" % i)
        d = _delta(before)
        assert d["full"] == 1, "a rewrite caused %d full reads (want 1)" % d["full"]
        _app(f.root, _line(600))
        _check(f, "append after rewrite")
        assert _delta(before)["full"] == 1

    def test_truncated_between_stat_and_anchor_read(self, tmp_path, monkeypatch):
        """The file shrinks AFTER the stat and BEFORE the anchor read: path 3, and
        the answer is the oracle's on the file as it now is."""
        f = _fab(tmp_path, "race")
        p = _write(f.root, _lines(200))
        _check(f, "seed")
        real = os.path.getsize
        fired = {"n": 0}

        def stat_then_shrink(path):
            size = real(path)
            if fired["n"] == 0 and os.path.abspath(path) == os.path.abspath(p):
                fired["n"] += 1
                with open(p, "wb") as fh:
                    fh.write(_lines(5))                 # shrunk below `upto`
            return size
        monkeypatch.setattr(os.path, "getsize", stat_then_shrink)
        before = _stats()
        got = f.query("collective", "s")
        monkeypatch.undo()
        assert fired["n"] == 1
        _identical(got, _oracle_query(f, "collective", "s"), "truncated mid-read")
        assert len(got) == 5
        assert _delta(before)["full"] == 1

    def test_vanished_entry_is_dropped_not_served(self, tmp_path):
        f = _fab(tmp_path, "vanish")
        p = _write(f.root, _lines(10))
        _check(f, "seed")
        assert os.path.abspath(p) in _fabric_mod._READ_CACHE
        os.remove(p)
        assert f.query("collective", "s") == []
        assert os.path.abspath(p) not in _fabric_mod._READ_CACHE
        _check(f, "after vanish")


# ══ R4 + KNOWN-NEGATIVES ═══════════════════════════════════════════════════════════

class TestR4:

    def test_known_record_sets_reproduce_exactly(self, tmp_path):
        f = _fab(tmp_path, "r4")
        want = [f.append("collective", "s", {"k": i, "v": [i, {"n": i}]}) for i in range(25)]
        got = f.query("collective", "s")
        _identical(got, want, "writer -> reader")
        _check(f, "vs oracle")

    def test_empty_stream_is_empty(self, tmp_path):
        f = _fab(tmp_path, "neg")
        _write(f.root, b"")
        assert f.query("collective", "s") == []
        assert f.query("collective", "s", limit=3) == []

    def test_directory_where_the_stream_should_be(self, tmp_path):
        f = _fab(tmp_path, "isdir")
        os.makedirs(os.path.join(f.root, "collective", "s.jsonl"))
        _check(f, "a directory in the stream's place")


# ══ RIDER 1 · BOUNDED ══════════════════════════════════════════════════════════════

class TestRider1Bounded:

    def test_the_cap_is_the_registered_knob(self):
        assert _fabric_mod.READ_CACHE_CAP_BYTES == 32 * 1024 * 1024       # KNOBS G35

    def test_a_stream_over_the_cap_is_served_but_never_retained(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_fabric_mod, "READ_CACHE_CAP_BYTES", 4096)
        f = _fab(tmp_path, "big")
        p = _write(f.root, _lines(200))
        assert os.path.getsize(p) > 4096
        for i in range(3):
            _check(f, "over-cap read %d" % i)
        assert os.path.abspath(p) not in _fabric_mod._READ_CACHE
        assert _fabric_mod._READ_CACHE_BYTES[0] == 0
        d = _delta({})
        assert d["uncached"] == 3 and d["full"] == 3

    def test_lru_by_bytes_evicts_the_least_recently_served(self, tmp_path, monkeypatch):
        f = _fab(tmp_path, "lru")
        paths = {}
        for t in ("a", "b", "c", "d"):
            paths[t] = os.path.abspath(_write(f.root, _lines(10), topic=t))
        one = os.path.getsize(paths["a"])
        monkeypatch.setattr(_fabric_mod, "READ_CACHE_CAP_BYTES", int(one * 2.5))
        for t in ("a", "b"):
            _check(f, t, topic=t)
        assert set(_fabric_mod._READ_CACHE) == {paths["a"], paths["b"]}
        _check(f, "a again", topic="a")                        # a is now the most recent
        _check(f, "c", topic="c")                              # evicts b, not a
        assert set(_fabric_mod._READ_CACHE) == {paths["a"], paths["c"]}
        _check(f, "d", topic="d")                              # evicts a
        assert set(_fabric_mod._READ_CACHE) == {paths["c"], paths["d"]}
        assert _fabric_mod._READ_CACHE_BYTES[0] <= _fabric_mod.READ_CACHE_CAP_BYTES
        assert _fabric_mod._READ_CACHE_BYTES[0] == sum(
            e["upto"] for e in _fabric_mod._READ_CACHE.values())
        for t in ("a", "b", "c", "d"):
            _check(f, "correct under eviction " + t, topic=t)

    def test_an_entry_growing_past_the_cap_is_released(self, tmp_path, monkeypatch):
        f = _fab(tmp_path, "growpast")
        p = os.path.abspath(_write(f.root, _lines(10)))
        monkeypatch.setattr(_fabric_mod, "READ_CACHE_CAP_BYTES", os.path.getsize(p) + 300)
        _check(f, "fits")
        assert p in _fabric_mod._READ_CACHE
        _app(f.root, _lines(10, 10))
        _check(f, "grew past the cap")
        assert p not in _fabric_mod._READ_CACHE
        assert _fabric_mod._READ_CACHE_BYTES[0] == 0
        _check(f, "still correct")

    def test_accounting_stays_exact_under_drop(self, tmp_path):
        f = _fab(tmp_path, "drop")
        _write(f.root, _lines(10))
        _check(f, "seed")
        assert _fabric_mod._READ_CACHE_BYTES[0] > 0
        KnowledgeFabric.drop_read_cache()
        assert not _fabric_mod._READ_CACHE and _fabric_mod._READ_CACHE_BYTES[0] == 0
        before = _stats()
        _check(f, "after drop")
        assert _delta(before)["full"] == 1


# ══ RIDER 2 · SHALLOW COPIES: the falsifier + the documented contract ══════════════

class TestRider2Copies:

    def test_top_level_mutation_cannot_poison_the_next_read(self, tmp_path):
        f = _fab(tmp_path, "shallow")
        _write(f.root, _lines(5))
        rows = f.query("collective", "s")
        rows[0]["agent"] = "POISON"
        rows[1]["injected"] = True
        del rows[2]["seq"]
        rows.clear()
        _check(f, "after top-level mutation")
        assert f.query("collective", "s")[0]["agent"] == "agent_d0c752e29aaf"

    def test_nested_values_are_shared_by_contract(self, tmp_path):
        """THE CHOICE (RIDER 2): audit + contract, not deep copies. Every production
        consumer of `query` was audited (44 sites: planner, mint x2, mastery,
        lp_drive x2, latents, goal_abduction x2, gate x2, frontier x3, fabric x3,
        effects x3, consumer x10, composer x3, binder, bank, affect x4,
        cognitive_loop x3, cold_ship x2): 40 read-only, 4 copy-before-write
        (consumer.seed_imports dict(atom) :977; composer.live_settle dict(rec)
        :929; composer -> mint._reinstate dict(atom)/dict(rec) :680/:688;
        mint._refresh_sig_index -> _merge_context dict(rec) :601), 0 nested
        writes. Deep-copying 80k records per call would cost what the cache
        saves. So the contract is: a returned record's nested values are the
        cache's own objects and are READ-ONLY -- pinned here so a future nested
        write is a loud gate failure, not a silent poison."""
        f = _fab(tmp_path, "nested")
        f.append("collective", "s", {"atom": {"key": "k", "cells": [1, 2]}})
        a = f.query("collective", "s")[0]
        b = f.query("collective", "s")[0]
        assert a is not b and a == b                                 # the envelope is copied
        assert a["atom"] is b["atom"], "the contract: nested values are shared"
        assert a["atom"] is _fabric_mod._cached_stream(
            f._stream_path(f.root, "collective", "s"))[0]["atom"]


# ══ PIN 1 · THE NESTED-WRITE WALL (AST over the production globs) ══════════════════
#
# The exemplar is gate.py's no-posthoc wall (engines/egocentric/gate.py:220,
# check_no_posthoc): an AST walk that NAMES an invariant so the next builder sees it
# red rather than discovering it in a poisoned cache. This one: no production call site
# writes into a container that a fabric.query / Gamma.get result shares with the cache.
#
# The model is ALIAS DEPTH: for a name bound from a source call, `shared_at` is the
# subscript depth at which a write first lands on an object the cache owns --
#   query(...)            -> 3  (a list of COPIED envelopes; their children are shared)
#   an envelope (for-loop / [i] over the list)           -> 2
#   rec["atom"] / rec.get("atom") / Gamma.get(aid)        -> 1  (the atom IS shared)
#   dict(x) / list(x) / copy(x)                            -> max(shared_at(x), 2)
# and a write whose target object sits at chain depth d from such a name violates iff
# d >= shared_at - 1. It cannot prove the absence of future writes (a write through a
# container that STORES an alias -- composer's `atoms[aid] = rec.get("atom")` -- is out
# of reach, as is a write behind a function boundary); it names the invariant.

_GAMMA_NAMES = {"gamma", "_gamma", "gm", "_gm", "_gamma_ref"}
_LIST_SOURCES = {"all_atoms", "pending", "candidates", "open_not_found"}   # consumer.*
_MUTATORS = {"update", "setdefault", "pop", "popitem", "clear", "append", "extend",
             "insert", "remove", "sort", "reverse", "__setitem__", "__delitem__"}
_COPIERS = {"dict", "list", "copy", "deepcopy", "sorted", "tuple", "set"}


def _chain(node):
    """(root, depth) of a subscript/attribute/.get() chain: root is the Name it
    hangs off, or the source Call it hangs off (`fab.query(...)[0]`), else None."""
    depth = 0
    while True:
        if isinstance(node, ast.Call) and _source_shared_at(node):
            return node, depth
        if isinstance(node, ast.Subscript):
            node, depth = node.value, depth + 1
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr == "get" and node.args):
            node, depth = node.func.value, depth + 1
        elif isinstance(node, ast.Attribute) and node.attr not in _MUTATORS:
            node, depth = node.value, depth + 1
        elif isinstance(node, ast.Name):
            return node, depth
        else:
            return None, 0


def _root_shared_at(root, taint: Dict[str, int]) -> int:
    if isinstance(root, ast.Name):
        return taint.get(root.id, 0)
    if isinstance(root, ast.Call):
        return _source_shared_at(root)
    return 0


def _dotted(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _dotted(node.value) + "." + node.attr
    if isinstance(node, ast.Call):
        return _dotted(node.func) + "()"
    if isinstance(node, ast.Subscript):
        return _dotted(node.value) + "[...]"
    return "?"


def _source_shared_at(call: ast.Call) -> int:
    """0 if `call` is not a cache source, else the alias depth of its result."""
    f = call.func
    if not isinstance(f, ast.Attribute):
        return 0
    if f.attr == "query" and len(call.args) >= 2:
        a0 = call.args[0]
        scoped = ((isinstance(a0, ast.Constant) and a0.value in ("personal", "kin", "collective"))
                  or (isinstance(a0, ast.Name) and a0.id == "scope"))
        return 3 if scoped else 0
    if f.attr in _LIST_SOURCES:
        return 3
    if f.attr == "get" and call.args:
        recv = f.value
        last = _dotted(recv).split(".")[-1]
        if last in _GAMMA_NAMES or last == "Gamma()":
            return 1
    return 0


def _value_shared_at(node, taint: Dict[str, int]) -> int:
    """Alias depth of an expression, 0 = not an alias of the cache."""
    if isinstance(node, ast.Call):
        s = _source_shared_at(node)
        if s:
            return s
        if isinstance(node.func, ast.Name) and node.func.id in _COPIERS and node.args:
            inner = _value_shared_at(node.args[0], taint)
            return max(inner, 2) if inner else 0
    if isinstance(node, ast.BoolOp) and node.values:
        return _value_shared_at(node.values[0], taint)
    root, depth = _chain(node)
    s = _root_shared_at(root, taint)
    return max(1, s - depth) if s else 0


def nested_write_violations(src: str, rel: str = "<src>") -> List[str]:
    """Every write in `src` that lands on an object the fabric cache owns."""
    out: List[str] = []
    tree = ast.parse(src)

    def scan(body_node, taint: Dict[str, int]):
        for n in ast.walk(body_node):
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                if n.value is not None:
                    s = _value_shared_at(n.value, taint)
                    for t in targets:
                        if isinstance(t, ast.Name):
                            if s:
                                taint[t.id] = s
                            else:
                                taint.pop(t.id, None)
            if isinstance(n, (ast.For, ast.comprehension)):
                s = _value_shared_at(n.iter, taint)
                if isinstance(n.target, ast.Name):
                    if s:
                        taint[n.target.id] = max(1, s - 1)
                    else:
                        taint.pop(n.target.id, None)
        for n in ast.walk(body_node):
            writes = []
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                writes = [t for t in targets if isinstance(t, (ast.Subscript, ast.Attribute))]
            elif isinstance(n, ast.Delete):
                writes = [t for t in n.targets if isinstance(t, (ast.Subscript, ast.Attribute))]
            elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr in _MUTATORS):
                root, depth = _chain(n.func.value)
                s = _root_shared_at(root, taint)
                if s and depth >= s - 1:
                    out.append("%s:%d %s.%s() on a cache-shared object (depth %d, shared_at %d)"
                               % (rel, n.lineno, _dotted(n.func.value), n.func.attr, depth, s))
                continue
            for t in writes:
                root, depth = _chain(t.value)          # the OBJECT being written into
                s = _root_shared_at(root, taint)
                if s and depth >= s - 1:
                    out.append("%s:%d write into %s (depth %d, shared_at %d)"
                               % (rel, n.lineno, _dotted(t.value), depth, s))

    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scan(n, {})
    return out


def _production_sources() -> List[str]:
    skip = {".git", ".venv", "venv", "__pycache__", "tests", "docs", ".pytest_cache",
            ".runs", ".gamma_library", ".residual_bank", ".claude", ".github", "node_modules"}
    out = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in sorted(dirs)
                   if d not in skip and "train set answers" not in d.lower()]
        for name in sorted(files):
            if name.endswith(".py"):
                out.append(os.path.join(root, name))
    return out


class TestPin1NestedWriteWall:

    POSITIVE = '''
def a(gamma, aid):
    atom = gamma.get(aid)
    atom["verified"] = True                       # 1: the atom IS the cache's object
def b(fab):
    for rec in fab.query("collective", "atoms"):
        rec["atom"]["x"] = 1                      # 2: nested subscript-assign
def c(fab):
    recs = fab.query("collective", "atoms")
    recs[0]["atom"].update({"k": 1})              # 3: .update on a nested container
def d(fab):
    rec = fab.query("collective", "atoms")[0]
    atom = rec.get("atom")
    del atom["key"]                               # 4: del through a derived alias
def e(self):
    for rec in self.gamma.fabric.query("collective", self.gamma.TOPIC):
        cells = rec["atom"]["cells"]
        cells.append(3)                           # 5: a list two levels down
def f(gm, aid):
    atom = dict(gm.get(aid))
    atom["transform"]["after"] = None             # 6: dict() copies one layer only
'''
    NEGATIVE = '''
def a(fab):
    for rec in fab.query("collective", "atoms"):
        rec["seen"] = True                        # top-level: the envelope is a copy
        rec.update({"x": 1})
        del rec["seq"]
def b(gamma, aid):
    atom = dict(gamma.get(aid))
    atom["imported"] = True                       # consumer.seed_imports' idiom
def c(fab):
    sup = dict(fab.query("collective", "atoms")[0])
    sup["settled"] = True                         # composer.live_settle's idiom
def d(fab):
    counts = {}
    for rec in fab.query("collective", "idea_events"):
        pair = counts.setdefault(str(rec.get("id")), [0, 0])
        pair[0] += 1                              # a LOCAL list, not the record's
def e(fab):
    local = {"atom": {}}
    local["atom"]["k"] = 1                        # untainted name
def f(fab):
    recs = fab.query("collective", "atoms")
    out = [dict(r) for r in recs]
    out[0]["x"] = 1
    rows = list(recs)
    rows.sort(key=lambda r: r["seq"])             # sorting a copied list
'''

    def test_known_positive_fires_on_every_shape(self):
        v = nested_write_violations(self.POSITIVE, "pos")
        lines = sorted(int(x.split(":")[1].split()[0]) for x in v)
        assert lines == [4, 7, 10, 14, 18, 21], "wall missed a shape: %r" % (v,)

    def test_known_negative_is_silent(self):
        v = nested_write_violations(self.NEGATIVE, "neg")
        assert v == [], "the wall over-fires (R4 specificity): %r" % (v,)

    def test_no_production_site_writes_into_the_cache(self):
        viol: List[str] = []
        for path in _production_sources():
            with open(path, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
            if ".query(" not in src and ".get(" not in src:
                continue
            try:
                viol += nested_write_violations(
                    src, os.path.relpath(path, REPO).replace("\\", "/"))
            except SyntaxError:
                continue
        assert viol == [], (
            "THE CONTRACT (fabric.query docstring; WIRING_REGISTRY fabric-read-cache): "
            "a query/Gamma.get result's nested values are the cache's own objects and "
            "are READ-ONLY -- dict(atom) before any write. Violations:\n  "
            + "\n  ".join(viol))


# ══ PIN 2 · THE MINT'S INDEX vs THE CACHE (an invariant the cache did not create) ═══

def _mint_fixture(tmp_path, n=10):
    import numpy as np

    from engines.egocentric.effects import Gamma, learn_effect
    from engines.egocentric.mint import MDLMint

    def atom(i):
        b = np.zeros((8, 8), dtype=int)
        b[i % 8, (i * 3) % 8] = 1 + (i % 5)
        a = b.copy()
        a[i % 8, (i * 3) % 8] = 6 + (i % 3)
        return learn_effect(b, 1 + i % 6, a)
    fab = _fab(tmp_path, "mint")
    gm = Gamma(fab)
    ids = [gm.add(atom(i), "g%d" % i, 1) for i in range(n)]
    m = MDLMint(gm)
    m._refresh_sig_index()
    path = fab._stream_path(fab.root, "collective", Gamma.TOPIC)
    return fab, gm, ids, m, path, atom


def _mint_agrees_with_cache(m, fab) -> List[str]:
    from engines.egocentric.effects import Gamma
    last: Dict[str, Dict[str, Any]] = {}
    for rec in _fabric_mod._cached_stream(fab._stream_path(fab.root, "collective", Gamma.TOPIC)):
        if rec.get("id"):
            last[rec["id"]] = rec
    bad = ["stale %s" % aid for aid, rec in m._rec_by_id.items()
           if aid not in last or json.dumps(rec, sort_keys=True)
           != json.dumps(last[aid], sort_keys=True)]
    bad += ["missing %s" % aid for aid in last if aid not in m._rec_by_id]
    return bad


def _supersede(fab, gm, aid, note):
    from engines.egocentric.effects import Gamma
    fab.append("collective", Gamma.TOPIC,
               {"id": aid, "atom": dict(gm.get(aid), note=note), "game": "x", "level": 1})


class TestPin2MintIndexVsCache:
    """mint._refresh_sig_index keeps `_rec_by_id` (envelopes from query) and advances
    `_scan_pos`, resetting it only when the stream is SHORTER at refresh time. The
    cache re-seeds by anchor. The two agree whenever the mint's incremental scan is
    sound -- which the control shows, and the two xfails show it is not after a
    rewrite: a FINDING about the mint's index (the pre-build `query` returned the
    identical list, so the cache neither causes nor hides it), dispositioned as
    strict xfails so a mint fix flips them loud."""

    def test_control_plain_supersede_agrees(self, tmp_path):
        fab, gm, ids, m, path, atom = _mint_fixture(tmp_path)
        for i in range(3):
            _supersede(fab, gm, ids[i], "v2")
        m._refresh_sig_index()
        assert _mint_agrees_with_cache(m, fab) == []

    @pytest.mark.xfail(strict=True, reason=(
        "FINDING (pre-existing, mint.py:535-554): a shrink-then-grow between two "
        "refreshes that ends LONGER than _scan_pos is not detected (records in "
        "[old len, new len) are skipped) and a re-base never evicts ids the stream "
        "no longer carries"))
    def test_shrink_then_grow_past_scan_pos(self, tmp_path):
        fab, gm, ids, m, path, atom = _mint_fixture(tmp_path)
        _write(fab.root, b"".join(open(path, "rb").read().splitlines(keepends=True)[:4]),
               topic="atoms")
        for i in range(4):
            _supersede(fab, gm, ids[i], "v2")
        for i in range(20, 24):
            gm.add(atom(i), "g%d" % i, 1)
        m._refresh_sig_index()
        assert _mint_agrees_with_cache(m, fab) == []

    @pytest.mark.xfail(strict=True, reason=(
        "FINDING (pre-existing, mint.py:535-554): a same-size rewrite of the LAST "
        "record re-seeds the cache (anchor) but not the mint's index (length unchanged)"))
    def test_same_size_rewrite_of_the_last_record(self, tmp_path):
        fab, gm, ids, m, path, atom = _mint_fixture(tmp_path)
        _supersede(fab, gm, ids[0], "v2")
        m._refresh_sig_index()
        assert _mint_agrees_with_cache(m, fab) == []
        lines = open(path, "rb").read().splitlines(keepends=True)
        assert b'"note": "v2"' in lines[-1]
        _write(fab.root, b"".join(lines[:-1] + [lines[-1].replace(b'"note": "v2"', b'"note": "v3"')]),
               topic="atoms")
        m._refresh_sig_index()
        assert _mint_agrees_with_cache(m, fab) == []


# ══ THE UNDO ════════════════════════════════════════════════════════════════════════

class TestUndo:

    def test_read_cache_false_routes_to_read_stream(self, tmp_path, monkeypatch):
        f = _fab(tmp_path, "undo")
        _write(f.root, _lines(10))
        calls = {"n": 0}
        orig = KnowledgeFabric._read_stream

        def counting(path):
            calls["n"] += 1
            return orig(path)
        monkeypatch.setattr(KnowledgeFabric, "_read_stream", staticmethod(counting))
        monkeypatch.setattr(KnowledgeFabric, "READ_CACHE", False)
        before = _stats()
        _check(f, "uncached")
        assert calls["n"] == 1 and _delta(before) == dict.fromkeys(before, 0)
        assert not _fabric_mod._READ_CACHE
        monkeypatch.setattr(KnowledgeFabric, "READ_CACHE", True)
        _check(f, "cached again")
        assert calls["n"] == 1 and _delta(before)["full"] == 1

    def test_query_tail_is_not_on_the_cache(self, tmp_path):
        f = _fab(tmp_path, "tail")
        _write(f.root, _lines(100))
        before = _stats()
        got = f.query_tail("collective", "s", 20)
        assert got == _oracle_query(f, "collective", "s")[-20:]
        assert _delta(before) == dict.fromkeys(before, 0)
