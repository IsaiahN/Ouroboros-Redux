"""FABRIC SEQ CACHE GATE: append stops re-reading the whole stream; answers unchanged.

Every append used to re-read the ENTIRE stream just to recover the seq high-water
mark (measured live: 87s of a 98s run inside those file opens, under antivirus).
The contract now:

  * KnowledgeFabric caches the last local seq per stream after the first read and
    advances it IN MEMORY on append -- a size stat replaces the full re-read;
  * the cache is dropped and the stream re-read whenever the file's size stops
    matching the writer's own bookkeeping (a janitor rewrite shrinks it; ANY
    out-of-band byte is a reason to re-read), or on explicit reload_seqs();
  * CROSS-PROCESS INVARIANT (documented in fabric.py): each stream has a single
    WRITER process by design -- own-scope appends only; seed mounts are read-only
    and never appended to -- so the in-memory advance can never hand two
    processes the same seq;
  * output is byte-identical: same records, same seqs as an uncached writer.

Run pre-build: the no-re-read probe failed (one full stream read per append).
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _F():
    try:
        from engines.egocentric.fabric import (
            KnowledgeFabric,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.fabric missing (%s)" % e)
    from engines.egocentric.fabric import KnowledgeFabric as KF
    return KF


def _mk(tmp_path, name="f", **kw):
    kw.setdefault("agent_id", "agentA")
    kw.setdefault("kin_key", "kinX")
    return _F()(str(tmp_path / name), **kw)


def _stream(tmp_path, name="f", topic="t"):
    return os.path.join(str(tmp_path / name), "collective", topic + ".jsonl")


def _count_reads(monkeypatch, KF):
    """Count full-stream reads (the cost the cache exists to remove)."""
    calls = {"n": 0}
    orig = KF._read_stream

    def counting(path):
        calls["n"] += 1
        return orig(path)

    monkeypatch.setattr(KF, "_read_stream", staticmethod(counting))
    return calls


class TestTheCacheRemovesTheReRead:

    def test_appends_read_the_stream_at_most_once(self, tmp_path, monkeypatch):
        KF = _F()
        f = _mk(tmp_path)
        f.append("collective", "t", {"i": -1})            # priming append
        calls = _count_reads(monkeypatch, KF)
        for i in range(50):
            f.append("collective", "t", {"i": i})
        assert calls["n"] == 0, (
            "%d full stream reads for 50 appends -- the seq cache is not caching"
            % calls["n"])

    def test_reload_seqs_forces_exactly_one_re_read(self, tmp_path, monkeypatch):
        KF = _F()
        f = _mk(tmp_path)
        f.append("collective", "t", {"i": 0})
        calls = _count_reads(monkeypatch, KF)
        f.reload_seqs()                                   # the explicit escape hatch
        rec = f.append("collective", "t", {"i": 1})
        assert calls["n"] == 1, "reload_seqs must drop the cache (got %d reads)" % calls["n"]
        assert rec["seq"] == 2


class TestByteIdenticalOutput:

    def test_cached_writer_matches_a_fresh_rereading_writer(self, tmp_path):
        """N appends through ONE instance vs N appends each through a FRESH
        instance (a cold cache every time IS the old re-reading behaviour):
        the two stream files must be byte-identical -- same records, same seqs."""
        cached = _mk(tmp_path, "cached")
        for i in range(20):
            cached.append("collective", "t", {"i": i})
        for i in range(20):                               # uncached: re-read every time
            _mk(tmp_path, "fresh").append("collective", "t", {"i": i})
        with open(_stream(tmp_path, "cached"), "rb") as fh:
            a = fh.read()
        with open(_stream(tmp_path, "fresh"), "rb") as fh:
            b = fh.read()
        assert a == b, "the cache changed the bytes on disk"

    def test_seqs_stay_monotonic_and_reopen_continues(self, tmp_path):
        f = _mk(tmp_path)
        seqs = [f.append("collective", "t", {"i": i})["seq"] for i in range(30)]
        assert seqs == list(range(1, 31))
        f2 = _mk(tmp_path)                                # reopen: read from disk once
        assert f2.append("collective", "t", {"i": 30})["seq"] == 31

    def test_mint_ids_and_seqs_survive_the_cache(self, tmp_path):
        f = _mk(tmp_path)
        ids = [f.mint({"k": i}, game="g", signal={"type": "level_up"})
               for i in range(3)]
        rows = f.query("personal", "ideas")
        assert [r["seq"] for r in rows] == [1, 2, 3]
        assert [r["id"] for r in rows] == ids, (
            "mint's precomputed seq diverged from the appended record's seq")


class TestInvalidation:

    def test_janitor_style_rewrite_then_append_continues_correctly(self, tmp_path):
        """A rewrite that SHRINKS the stream (compaction) must not be trusted:
        the next append re-reads and continues from the surviving high-water
        mark, exactly as an uncached writer would."""
        f = _mk(tmp_path)
        for i in range(10):
            f.append("collective", "t", {"i": i})
        path = _stream(tmp_path)
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        tmp = path + ".tmp"                               # the janitor's atomic pattern
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.writelines(lines[:3])                      # keep seqs 1..3 only
        os.replace(tmp, path)
        rec = f.append("collective", "t", {"i": 99})
        assert rec["seq"] == 4, (
            "after a shrinking rewrite the seq must continue from what SURVIVED "
            "on disk (wanted 4, got %r)" % rec["seq"])

    def test_out_of_band_growth_is_re_read_not_trusted(self, tmp_path):
        """Any byte the writer did not put there invalidates the cache -- the
        next append must agree with a from-disk read, never a stale counter."""
        f = _mk(tmp_path)
        f.append("collective", "t", {"i": 0})
        with open(_stream(tmp_path), "a", encoding="utf-8") as fh:
            fh.write('{"i": 1, "seq": 40}\n')             # out-of-band valid record
        assert f.append("collective", "t", {"i": 2})["seq"] == 41


class TestConcurrentReader:

    def test_a_reader_instance_sees_every_append_consistently(self, tmp_path):
        """Readers never consult the writer's cache: a second instance on the
        same root re-reads the disk and sees exactly the appended records, in
        order, with the writer's seqs."""
        w = _mk(tmp_path)
        r = _mk(tmp_path)                                 # separate instance = the reader
        for i in range(5):
            w.append("collective", "t", {"i": i})
            rows = r.query("collective", "t")
            assert [x["i"] for x in rows] == list(range(i + 1))
            assert [x["seq"] for x in rows] == list(range(1, i + 2))
