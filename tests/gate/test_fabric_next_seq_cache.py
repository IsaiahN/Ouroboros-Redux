"""FABRIC I/O, THE PRIMARY TARGET (PREREG_FABRIC_IO.md, TARGET SHARPENED BY WINDOW 6-b):
`_next_seq` no longer parses the whole stream to find the next seq.

THE DEFECT, precisely (window 6-b, g50t: 1,220 appends -> 1.5M json.loads, 28.3%): the
pre-build `_next_seq` DID cache the high-water mark -- per INSTANCE, keyed by file size --
but the loop builds a fresh KnowledgeFabric per reachability seam and per game on the
SAME root (cognitive_loop.py: four construction sites), and every fresh instance paid a
whole-stream `_read_stream` on its first append to each stream. tests/gate/
test_fabric_seq_cache.py covers the one-instance steady state (0 re-reads after a priming
append) and the size-rule invalidations; it never counted the priming read, never put two
instances on one root, and its size rule is blind to a same-size rewrite.

THE CONTRACT NOW (fabric.py, module bottom):
  * one PROCESS-level seq tail per stream path, shared by every instance;
  * seeded from the stream's LAST record on first touch (`_tail_records`, O(tail)) --
    never a whole-file parse;
  * advanced in memory on every append; invalidated by the SAME anchor rule the read
    cache uses (`_anchor_size`: size AND the last 64 bytes) -- a shrink, a growth, a
    same-size rewrite each force exactly ONE re-seed;
  * reload_seqs() is the escape hatch: one full oracle scan on the next append.

THE ORACLE is a LITERAL TRANSCRIPTION of the pre-build writer (`_OracleWriter` below:
`_read_stream`, `_ends_in_newline`, `_next_seq`, `append`, the per-instance size-keyed
cache, warts included), never the live code. Every constructed sequence is run in
lockstep on two roots -- the live writer and the oracle -- and the seqs must agree at
every append, as must the bytes on disk. Where the oracle's size rule is BLIND (a
same-size rewrite) the live writer is held to the from-disk recomputation instead, and
the oracle's staleness is asserted as the known-positive.

Costs are asserted by COUNTING (full reads, tail seeds, json.loads), never wall-clock.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Tuple

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import fabric as _fabric_mod
from engines.egocentric.fabric import KnowledgeFabric

# ── THE ORACLE: the pre-build seq machinery, transcribed literally ────────────────

def _ORACLE_read_stream(path: str) -> List[Dict[str, Any]]:
    """VERBATIM `KnowledgeFabric._read_stream` (unchanged by this build)."""
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


class _OracleWriter:
    """VERBATIM the pre-build KnowledgeFabric's seq path: `_ends_in_newline`,
    `_next_seq` (per-instance cache keyed by file SIZE) and `append`'s bookkeeping,
    at commit 41886d6. `reads` counts the whole-stream parses it issues."""

    def __init__(self, root: str):
        self.root = str(root)
        self._seq_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.reads = 0

    def _stream_path(self, scope: str, topic: str) -> str:
        return os.path.join(self.root, scope, str(topic) + ".jsonl")

    def _read_stream(self, path: str) -> List[Dict[str, Any]]:
        self.reads += 1
        return _ORACLE_read_stream(path)

    @staticmethod
    def _ends_in_newline(path: str) -> bool:
        try:
            with open(path, "rb") as fh:
                fh.seek(-1, os.SEEK_END)
                return fh.read(1) == b"\n"
        except OSError:
            return True

    def _next_seq(self, scope: str, topic: str) -> int:
        key = (scope, str(topic))
        path = self._stream_path(scope, topic)
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        hit = self._seq_cache.get(key)
        if hit is not None and hit["size"] == size:
            return hit["seq"] + 1
        top = 0
        for rec in self._read_stream(path):
            try:
                top = max(top, int(rec.get("seq", 0)))
            except Exception:  # noqa: S112 -- VERBATIM
                continue
        self._seq_cache[key] = {"seq": top, "size": size,
                                "clean": self._ends_in_newline(path)}
        return top + 1

    def append(self, scope: str, topic: str, record: Dict[str, Any]) -> Dict[str, Any]:
        rec = dict(record)
        rec["seq"] = self._next_seq(scope, topic)
        path = self._stream_path(scope, topic)
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        key = (scope, str(topic))
        hit = self._seq_cache[key]
        if hit["clean"]:
            hit["seq"] = rec["seq"]
        hit["clean"] = True
        try:
            hit["size"] = os.path.getsize(path)
        except OSError:
            del self._seq_cache[key]
        return rec


def _from_disk_next(path: str) -> int:
    """The ground truth both writers approximate: 1 + max seq read fresh from disk."""
    top = 0
    for rec in _ORACLE_read_stream(path):
        try:
            top = max(top, int(rec.get("seq", 0)))
        except Exception:  # noqa: S112
            continue
    return top + 1


# ── the lockstep harness ─────────────────────────────────────────────────────────

SCOPE, TOPIC = "collective", "t"


def _live(root: str) -> KnowledgeFabric:
    return KnowledgeFabric(root, agent_id="a", kin_key="v4")


def _path(root: str) -> str:
    return os.path.join(root, SCOPE, TOPIC + ".jsonl")


def _raw_append(path: str, blob: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "ab") as fh:
        fh.write(blob)


def _rewrite(path: str, fn) -> None:
    """The janitor's atomic pattern: rewrite the whole file from its lines
    (nothing to rewrite before the first append: a no-op on both sides)."""
    if not os.path.isfile(path):
        return
    with open(path, "rb") as fh:
        lines = fh.read().splitlines(keepends=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.writelines(fn(lines))
    os.replace(tmp, path)


def _run_lockstep(tmp_path, ops, name="seq"):
    """Run `ops` on a live root and an oracle root; return (live seqs, oracle seqs,
    live path, oracle path). Op kinds: ("append", rec) | ("raw", bytes) |
    ("rewrite", fn) | ("reopen",) -- a fresh instance on each side."""
    lr, orr = str(tmp_path / (name + "_live")), str(tmp_path / (name + "_oracle"))
    live, oracle = _live(lr), _OracleWriter(orr)
    ls: List[int] = []
    os_: List[int] = []
    for op in ops:
        kind = op[0]
        if kind == "append":
            ls.append(live.append(SCOPE, TOPIC, op[1])["seq"])
            os_.append(oracle.append(SCOPE, TOPIC, op[1])["seq"])
        elif kind == "raw":
            _raw_append(_path(lr), op[1])
            _raw_append(_path(orr), op[1])
        elif kind == "rewrite":
            _rewrite(_path(lr), op[1])
            _rewrite(_path(orr), op[1])
        elif kind == "reopen":
            live, oracle = _live(lr), _OracleWriter(orr)
        else:
            raise AssertionError(op)
    return ls, os_, _path(lr), _path(orr)


def _same_bytes(a: str, b: str) -> bool:
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


def _rec(i: int) -> Dict[str, Any]:
    return {"agent": "a", "game": "g", "level": 1, "action": i % 7, "i": i,
            "note": "é中文" if i % 5 == 0 else ""}


class _Counters:
    """Full reads, tail seeds and json.loads -- the three costs, counted."""

    def __init__(self, monkeypatch):
        self.full = 0
        self.tail = 0
        self.loads = 0
        orig_read = KnowledgeFabric._read_stream
        orig_tail = KnowledgeFabric._tail_records
        real_loads = json.loads

        def counting_read(path):
            self.full += 1
            return orig_read(path)

        def counting_tail(path, n):
            self.tail += 1
            return orig_tail(path, n)

        def counting_loads(s, *a, **kw):
            self.loads += 1
            return real_loads(s, *a, **kw)

        monkeypatch.setattr(KnowledgeFabric, "_read_stream", staticmethod(counting_read))
        monkeypatch.setattr(KnowledgeFabric, "_tail_records", staticmethod(counting_tail))
        monkeypatch.setattr(_fabric_mod.json, "loads", counting_loads)

    def reset(self):
        self.full = self.tail = self.loads = 0


# ══ THE ORACLE EQUIVALENCE: every constructed sequence, in lockstep ═══════════════

class TestSeqSequenceMatchesTheOracle:

    def test_plain_appends(self, tmp_path):
        ops = [("append", _rec(i)) for i in range(40)]
        ls, os_, lp, op = _run_lockstep(tmp_path, ops, "plain")
        assert ls == os_ == list(range(1, 41))
        assert _same_bytes(lp, op)

    def test_reopen_continues(self, tmp_path):
        ops = ([("append", _rec(i)) for i in range(10)] + [("reopen",)]
               + [("append", _rec(i)) for i in range(10, 20)] + [("reopen",)]
               + [("append", _rec(20))])
        ls, os_, lp, op = _run_lockstep(tmp_path, ops, "reopen")
        assert ls == os_ == list(range(1, 22))
        assert _same_bytes(lp, op)

    def test_janitor_shrink_between_appends(self, tmp_path):
        ops = ([("append", _rec(i)) for i in range(10)]
               + [("rewrite", lambda lines: lines[:3])]
               + [("append", _rec(i)) for i in range(10, 15)])
        ls, os_, lp, op = _run_lockstep(tmp_path, ops, "shrink")
        assert ls == os_
        assert ls[10:] == [4, 5, 6, 7, 8]
        assert _same_bytes(lp, op)

    def test_rewrite_that_grows_the_file(self, tmp_path):
        extra = (json.dumps({"i": -1, "seq": 2}) + "\n").encode()
        ops = ([("append", _rec(i)) for i in range(5)]
               + [("rewrite", lambda lines: lines[:2] + [extra] * 4)]
               + [("append", _rec(i)) for i in range(5, 9)])
        ls, os_, lp, op = _run_lockstep(tmp_path, ops, "grow")
        assert ls == os_
        assert ls[5:] == [3, 4, 5, 6]
        assert _same_bytes(lp, op)

    def test_out_of_band_valid_record(self, tmp_path):
        ops = ([("append", _rec(0))]
               + [("raw", b'{"i": 1, "seq": 40}\n')]
               + [("append", _rec(2)), ("append", _rec(3))])
        ls, os_, lp, op = _run_lockstep(tmp_path, ops, "oob")
        assert ls == os_ == [1, 41, 42]
        assert _same_bytes(lp, op)

    def test_out_of_band_record_without_a_seq(self, tmp_path):
        """A tail record with NO "seq": the oracle's answer lives in earlier
        records, so the live seed must fall back to the full scan (and agree)."""
        ops = ([("append", _rec(i)) for i in range(6)]
               + [("raw", b'{"i": 99}\n')]
               + [("append", _rec(7))])
        ls, os_, lp, op = _run_lockstep(tmp_path, ops, "noseq")
        assert ls == os_ == [1, 2, 3, 4, 5, 6, 7]
        assert _same_bytes(lp, op)

    def test_out_of_band_unparseable_seq(self, tmp_path):
        ops = ([("append", _rec(i)) for i in range(4)]
               + [("raw", b'{"i": 9, "seq": "not-a-number"}\n')]
               + [("append", _rec(5))])
        ls, os_, lp, op = _run_lockstep(tmp_path, ops, "badseq")
        assert ls == os_ == [1, 2, 3, 4, 5]
        assert _same_bytes(lp, op)

    def test_crash_truncated_tail_merges_exactly_one_record(self, tmp_path):
        ops = ([("append", _rec(i)) for i in range(3)]
               + [("raw", b'{"i": 3, "half')]
               + [("append", _rec(4)), ("append", _rec(5)), ("append", _rec(6))])
        ls, os_, lp, op = _run_lockstep(tmp_path, ops, "torn")
        assert ls == os_ == [1, 2, 3, 4, 4, 5]
        assert _same_bytes(lp, op)
        rows = _ORACLE_read_stream(lp)
        assert [r["i"] for r in rows] == [0, 1, 2, 5, 6]

    def test_blank_corrupt_and_non_dict_lines(self, tmp_path):
        ops = ([("append", _rec(0))]
               + [("raw", b"\n   \n{\"half\": \n[1, 2, 3]\n\"s\"\n7\nnull\n")]
               + [("append", _rec(1))]
               + [("raw", b"\r\n")]
               + [("append", _rec(2))])
        ls, os_, lp, op = _run_lockstep(tmp_path, ops, "junk")
        assert ls == os_ == [1, 2, 3]
        assert _same_bytes(lp, op)

    def test_crlf_and_bare_cr_terminated_foreign_lines(self, tmp_path):
        ops = ([("append", _rec(0))]
               + [("raw", b'{"i": 10, "seq": 7}\r\n')]
               + [("append", _rec(1))]
               + [("raw", b'{"i": 11, "seq": 20}\r')]          # bare CR: not "clean"
               + [("append", _rec(2)), ("append", _rec(3))])
        ls, os_, lp, op = _run_lockstep(tmp_path, ops, "crlf")
        assert ls == os_
        assert _same_bytes(lp, op)
        assert ls[-1] == _from_disk_next(lp) - 1

    def test_invalid_utf8_and_multibyte_tail(self, tmp_path):
        ops = ([("append", _rec(0))]
               + [("raw", b'{"junk": "\xff\xfe\x80", "seq": 3}\n')]
               + [("append", _rec(5))]
               + [("raw", ('{"note": "' + "é中文\U0001f600" * 20 + '", "seq": 9}\n')
                   .encode("utf-8"))]
               + [("append", _rec(6))])
        ls, os_, lp, op = _run_lockstep(tmp_path, ops, "utf8")
        assert ls == os_ == [1, 4, 10]
        assert _same_bytes(lp, op)

    def test_mint_ids_agree_with_appended_seqs(self, tmp_path):
        f = _live(str(tmp_path / "mint"))
        ids = [f.mint({"k": i}, game="g", signal={"type": "level_up"}) for i in range(4)]
        rows = f.query("personal", "ideas")
        assert [r["seq"] for r in rows] == [1, 2, 3, 4]
        assert [r["id"] for r in rows] == ids

    def test_random_scripts_agree_with_the_oracle(self, tmp_path):
        """Random mixtures of appends, foreign lines (monotonic seqs), torn tails,
        shrinks and reopens -- the enumerated cases are the ones I thought of."""
        import random
        rng = random.Random(20260821)
        for trial in range(25):
            ops = []
            top = 0
            for i in range(rng.randint(3, 30)):
                k = rng.random()
                if k < 0.6:
                    ops.append(("append", _rec(i)))
                    top += 1
                elif k < 0.72:
                    top += rng.randint(1, 5)
                    sep = rng.choice([b"\n", b"\r\n", b"\r"])
                    ops.append(("raw", json.dumps({"i": i, "seq": top}).encode() + sep))
                elif k < 0.8:
                    ops.append(("raw", rng.choice([b"\n", b"{\"half\": \n", b"[1]\n",
                                                   b'{"bad": "\xff"}\n'])))
                elif k < 0.86:
                    ops.append(("raw", b'{"i": 1, "torn'))
                elif k < 0.93:
                    keep = rng.randint(0, 6)
                    ops.append(("rewrite", (lambda n: lambda lines: lines[:n])(keep)))
                else:
                    ops.append(("reopen",))
            ls, os_, lp, op = _run_lockstep(tmp_path, ops, "rand%d" % trial)
            assert ls == os_, "trial %d: live %r != oracle %r" % (trial, ls, os_)
            assert _same_bytes(lp, op), "trial %d: bytes differ" % trial


# ══ WHAT THE SIZE RULE COULD NOT SEE: the anchor rule, with its known-positive ═════

class TestSameSizeRewrite:

    def test_same_size_rewrite_is_seen_by_the_anchor_and_not_by_size(self, tmp_path):
        """Rewrite the LAST record's seq 10 -> 90 (same byte length): the live
        writer re-seeds (from-disk answer 91); the oracle's size-keyed cache is
        STALE (11) -- the blind spot the anchor rule closes, asserted both ways."""
        lr, orr = str(tmp_path / "ss_live"), str(tmp_path / "ss_oracle")
        live, oracle = _live(lr), _OracleWriter(orr)
        for i in range(10):
            live.append(SCOPE, TOPIC, _rec(i))
            oracle.append(SCOPE, TOPIC, _rec(i))
        for p in (_path(lr), _path(orr)):
            _rewrite(p, lambda lines: lines[:-1] + [lines[-1].replace(b'"seq": 10', b'"seq": 90')])
        assert _from_disk_next(_path(lr)) == 91
        assert live.append(SCOPE, TOPIC, _rec(10))["seq"] == 91
        assert oracle.append(SCOPE, TOPIC, _rec(10))["seq"] == 11, (
            "the KNOWN-POSITIVE: the pre-build size rule must be stale here, or "
            "this test is not testing the anchor")

    def test_non_monotonic_tail_is_the_stated_residue(self, tmp_path):
        """THE ONE DIVERGENCE CLASS, pinned so it is never mistaken for a surprise:
        a foreign record at the tail whose seq is LOWER than an earlier seq. The
        pre-build scan answers max+1; the last-record seed answers last+1. Only an
        out-of-band writer can produce it (append is monotonic; the janitor keeps
        order), and reload_seqs() -- the full oracle scan -- is the escape hatch."""
        lr = str(tmp_path / "nm")
        live = _live(lr)
        for i in range(5):
            live.append(SCOPE, TOPIC, _rec(i))
        _raw_append(_path(lr), b'{"i": 9, "seq": 2}\n')
        assert live.append(SCOPE, TOPIC, _rec(9))["seq"] == 3       # last + 1
        live.reload_seqs()
        assert live.append(SCOPE, TOPIC, _rec(10))["seq"] == 6       # max + 1, the oracle


# ══ THE COST: counted, not timed ═══════════════════════════════════════════════════

class TestTheCostCollapses:

    def test_first_touch_is_one_tail_read_not_a_parse(self, tmp_path, monkeypatch):
        lr = str(tmp_path / "cold")
        w = _live(lr)
        for i in range(3000):
            w.append(SCOPE, TOPIC, _rec(i))
        _fabric_mod._SEQ_TAIL.clear()                    # a fresh process's view
        c = _Counters(monkeypatch)
        assert _live(lr).append(SCOPE, TOPIC, _rec(0))["seq"] == 3001
        assert c.full == 0, "first touch parsed the whole stream (%d full reads)" % c.full
        assert c.tail == 1
        assert c.loads <= 4, "first touch parsed %d records to read the last one" % c.loads

    def test_appends_after_first_touch_read_nothing(self, tmp_path, monkeypatch):
        w = _live(str(tmp_path / "steady"))
        w.append(SCOPE, TOPIC, _rec(0))
        c = _Counters(monkeypatch)
        for i in range(100):
            w.append(SCOPE, TOPIC, _rec(i))
        assert (c.full, c.tail, c.loads) == (0, 0, 0), (
            "100 appends issued full=%d tail=%d loads=%d" % (c.full, c.tail, c.loads))

    @pytest.mark.parametrize("kind", ["shrink", "grow", "same_size"])
    def test_a_rewrite_forces_exactly_one_reseed(self, tmp_path, monkeypatch, kind):
        lr = str(tmp_path / kind)
        w = _live(lr)
        for i in range(12):
            w.append(SCOPE, TOPIC, _rec(i))
        if kind == "shrink":
            _rewrite(_path(lr), lambda lines: lines[:4])
            want = 5
        elif kind == "grow":
            extra = (json.dumps({"i": -1, "seq": 3}) + "\n").encode()
            _rewrite(_path(lr), lambda lines: lines[:2] + [extra] * 30)
            want = 4
        else:
            _rewrite(_path(lr), lambda lines: lines[:-1]
                     + [lines[-1].replace(b'"seq": 12', b'"seq": 50')])
            want = 51
        c = _Counters(monkeypatch)
        seqs = [w.append(SCOPE, TOPIC, _rec(i))["seq"] for i in range(5)]
        assert seqs == list(range(want, want + 5))
        assert c.full == 0, "a rewrite caused %d whole-stream parses" % c.full
        assert c.tail == 1, "a rewrite caused %d re-seeds (want exactly 1)" % c.tail

    def test_two_instances_on_one_root_share_the_tail(self, tmp_path, monkeypatch):
        """THE WINDOW-6-b SHAPE: instances alternating appends on one root. The
        oracle re-parses the stream on EVERY alternation (known-positive); the
        live writers share one process-level tail and read nothing."""
        lr, orr = str(tmp_path / "two_live"), str(tmp_path / "two_oracle")
        a, b = _live(lr), _live(lr)
        oa, ob = _OracleWriter(orr), _OracleWriter(orr)
        a.append(SCOPE, TOPIC, _rec(0))
        oa.append(SCOPE, TOPIC, _rec(0))
        c = _Counters(monkeypatch)
        live_seqs, oracle_seqs = [], []
        for i in range(1, 41):
            w, ow = (a, oa) if i % 2 else (b, ob)
            live_seqs.append(w.append(SCOPE, TOPIC, _rec(i))["seq"])
            oracle_seqs.append(ow.append(SCOPE, TOPIC, _rec(i))["seq"])
        assert live_seqs == oracle_seqs == list(range(2, 42))
        assert _same_bytes(_path(lr), _path(orr))
        assert (c.full, c.tail) == (0, 0), (
            "two instances on one root still re-read: full=%d tail=%d" % (c.full, c.tail))
        assert oa.reads + ob.reads >= 40, (
            "KNOWN-POSITIVE failed: the transcribed pre-build writer should re-parse on "
            "every alternation (got %d reads)" % (oa.reads + ob.reads))

    def test_fresh_instances_per_episode_read_nothing(self, tmp_path, monkeypatch):
        """The loop's actual pattern: a new KnowledgeFabric per episode on one root."""
        lr = str(tmp_path / "episodes")
        _live(lr).append(SCOPE, TOPIC, _rec(0))
        c = _Counters(monkeypatch)
        for _ep in range(30):
            f = _live(lr)
            for i in range(5):
                f.append(SCOPE, TOPIC, _rec(i))
        assert (c.full, c.tail) == (0, 0)
        assert _from_disk_next(_path(lr)) == 152

    def test_the_validity_rule_is_the_shared_one(self):
        """One definition: the seq path and the read path both call `_anchor_size`
        (asserted structurally, by source)."""
        import inspect
        src_seq = inspect.getsource(KnowledgeFabric._next_seq)
        src_read = inspect.getsource(_fabric_mod._cached_stream)
        assert "_anchor_size(" in src_seq and "_anchor_size(" in src_read
        assert _fabric_mod.ANCHOR_BYTES == 64                       # PINNED by the prereg
