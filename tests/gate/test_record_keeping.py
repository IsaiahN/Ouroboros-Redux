"""RECORD-KEEPING GATE (record/prereg/VICTORY_PROTOCOL.md): what costs nothing now is
unrecoverable later.

Three laws pinned here, dispatched on receipt of the protocol:
  (a) THE JANITOR ARCHIVES BEFORE IT FOLDS OR STRIPS — every record a sweep
      removes from a stream is appended VERBATIM to <stream>.archive.jsonl
      first (append-only, never a size trigger, never compacted itself).
      THE FALSIFIER: archive + surviving-original lines == the original
      stream, as a multiset of verbatim lines. History folded into counters
      without the side file is history LOST (gap (b) of the protocol).
  (b) LEVEL-UP PRE/POST FRAMES PERSIST — GoalBook.observe_levelup was
      extracting predicates from the frames and dropping the frames (gap (a));
      now each level-up appends exactly ONE record to the personal
      "levelup_frames" stream carrying the verbatim pre/post arrays.
  (c) SEEDED IMPORTED ATOMS RETAIN source_game — the import candidate knows
      its source fabric; seed_imports now writes it INTO the atom (additive:
      only when the atom does not already carry one), so the 25/25 census can
      name every atom's native + imported provenance.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer
from engines.egocentric import effects as E
from engines.egocentric.fabric import KnowledgeFabric
from engines.egocentric.goal_abduction import GoalBook
from engines.egocentric.janitor import FabricJanitor

GAME, LEVEL = "g_home", 1


def _lines(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [ln.rstrip("\n") for ln in fh if ln.strip()]


def _stream(root, topic):
    return os.path.join(str(root), "collective", topic + ".jsonl")


def _archive(root, topic):
    return os.path.join(str(root), "collective", topic + ".archive.jsonl")


def _settle_heavy(tmp_path, n=130):
    f = KnowledgeFabric(str(tmp_path / "fab"), agent_id="agentA", kin_key="kinA")
    for i in range(n):
        f.append("collective", "settlements", {"agent": "agentA", "game": GAME,
                                               "level": 1, "action": 1 + i % 5,
                                               "members": 2, "best": float(i % 7),
                                               "nontrivial": bool(i % 3)})
    return f


def _verdict_heavy(tmp_path, n=240):
    f = KnowledgeFabric(str(tmp_path / "fabv"), agent_id="agentA", kin_key="kinA")
    for i in range(n):
        v = "mint" if i % 8 == 0 else "reject"
        f.append("collective", "mint_verdicts",
                 {"verdict": v, "game": GAME, "level": 1, "key": "k%d" % i, "w": 0.5})
    return f


def _queue_with_consumed(tmp_path):
    f = KnowledgeFabric(str(tmp_path / "fabq"), agent_id="agentA", kin_key="kinA")
    b = np.full((5, 5), 2, dtype=int)
    a = b.copy()
    a[2, 2] = 3
    f.append("collective", "atoms", {
        "id": "eff-x:0", "type": "structural", "game": "g_src", "level": 1,
        "agent": "agentB",
        "atom": {"kind": "EFFECT", "arity": 2, "key": "eff-x", "action": 1,
                 "context": b.tolist(), "transform": {"before": b.tolist(),
                                                      "after": a.tolist()},
                 "changed": 1, "sigma": consumer.sigma_of(b, a)}})
    f.append("collective", "import_queue", {"slot": "WORKSPACE", "residual": 1.0,
                                            "before": b.tolist(), "after": a.tolist()})
    consumer.consume(f, GAME, LEVEL, 1)          # closes the item: droppable entries
    return f


class TestTheJanitorArchives:

    def _sweep_and_check(self, fab, topic):
        """Run a triggered sweep on `topic`; assert the falsifier:
        multiset(archive) + multiset(survivors-from-original) == multiset(original)."""
        path = _stream(fab.root, topic)
        original = _lines(path)
        FabricJanitor(fab, max_stream_bytes=1).sweep()
        after = _lines(path)
        archived = _lines(_archive(fab.root, topic))
        assert archived, "the sweep removed records without archiving them"
        orig = Counter(original)
        survivors = Counter()
        for ln in after:
            if orig[ln] > survivors[ln]:              # verbatim original survivor
                survivors[ln] += 1
        assert Counter(archived) + survivors == orig, (
            "%s: archive + survivors != original -- removed history was LOST" % topic)

    def test_settlement_folds_archive_first(self, tmp_path):
        """Gap (b) of the protocol, closed: the 30 folded settlement records
        land verbatim in settlements.archive.jsonl."""
        self._sweep_and_check(_settle_heavy(tmp_path), "settlements")

    def test_verdict_strips_archive_first(self, tmp_path):
        """A stripped reject's ORIGINAL line is archived (the in-place stub
        keeps the count; the archive keeps the record)."""
        self._sweep_and_check(_verdict_heavy(tmp_path), "mint_verdicts")

    def test_queue_drops_archive_first(self, tmp_path):
        self._sweep_and_check(_queue_with_consumed(tmp_path), "import_queue")

    def test_archive_is_append_only_across_sweeps(self, tmp_path):
        """A second triggered sweep APPENDS: the first batch survives as a prefix."""
        fab = _settle_heavy(tmp_path)
        FabricJanitor(fab, max_stream_bytes=1).sweep()
        first = _lines(_archive(fab.root, "settlements"))
        assert first
        for _i in range(120):                         # regrow past retention
            fab.append("collective", "settlements",
                       {"agent": "agentA", "game": GAME, "level": 1,
                        "action": 1, "members": 2, "best": 0.0,
                        "nontrivial": True})
        FabricJanitor(fab, max_stream_bytes=1).sweep()
        second = _lines(_archive(fab.root, "settlements"))
        assert len(second) > len(first)
        assert second[:len(first)] == first, "the archive was rewritten, not appended"

    def test_archive_never_triggers_and_is_never_compacted(self, tmp_path):
        """A monstrous archive beside an under-threshold stream changes NOTHING:
        the archive is outside the size trigger and outside every policy."""
        fab = _settle_heavy(tmp_path, n=5)
        apath = _archive(fab.root, "settlements")
        os.makedirs(os.path.dirname(apath), exist_ok=True)
        blob = json.dumps({"filler": "x" * 64})
        with open(apath, "w", encoding="utf-8") as fh:
            for _ in range(50000):
                fh.write(blob + "\n")
        size0 = os.path.getsize(apath)
        stream0 = _lines(_stream(fab.root, "settlements"))
        report = FabricJanitor(fab).sweep()           # default 2MB threshold
        assert report["settlements"]["action"] == "under-threshold", (
            "the archive's bytes leaked into the stream's size trigger")
        assert os.path.getsize(apath) == size0, "the archive itself was compacted"
        assert _lines(_stream(fab.root, "settlements")) == stream0

    def test_untriggered_sweep_archives_nothing(self, tmp_path):
        fab = _settle_heavy(tmp_path, n=5)
        FabricJanitor(fab).sweep()
        assert not os.path.isfile(_archive(fab.root, "settlements"))


class TestLevelupFramesPersist:

    def test_one_record_per_levelup_with_verbatim_frames(self, tmp_path):
        """Gap (a) of the protocol, closed: observe_levelup persists pre/post."""
        fab = KnowledgeFabric(str(tmp_path / "f"), agent_id="agentA", kin_key="kinA")
        pre = np.array([[1, 2], [3, 4]], dtype=int)
        post = np.full((2, 2), 5, dtype=int)
        GoalBook(fab).observe_levelup(GAME, 2, pre, post)
        recs = fab.query("personal", "levelup_frames")
        assert len(recs) == 1, "exactly ONE frame record per level-up"
        r = recs[0]
        assert r["game"] == GAME and r["level"] == 2
        assert r["pre"] == pre.tolist() and r["post"] == post.tolist(), (
            "the frames must persist VERBATIM -- they are unrecoverable later")

    def test_frames_persist_even_when_no_predicate_extracts(self, tmp_path):
        """The frames are the record; predicates are merely derivable from it.
        A delta that yields no hypothesis still persists the snapshot."""
        fab = KnowledgeFabric(str(tmp_path / "f2"), agent_id="agentA", kin_key="kinA")
        same = np.array([[1, 2], [3, 4]], dtype=int)
        banked = GoalBook(fab).observe_levelup(GAME, 1, same, same.copy())
        assert banked == []
        assert len(fab.query("personal", "levelup_frames")) == 1

    def test_garbage_frames_never_crash_and_never_fabricate(self, tmp_path):
        fab = KnowledgeFabric(str(tmp_path / "f3"), agent_id="agentA", kin_key="kinA")
        book = GoalBook(fab)
        assert book.observe_levelup(GAME, 1, None, None) == []
        assert fab.query("personal", "levelup_frames") == [], (
            "no frames -> no record (never invented)")


class TestImportedAtomsRetainSourceGame:

    def _fabric_with_candidate(self, tmp_path, atom_extra=None):
        fab = KnowledgeFabric(str(tmp_path / "home"), agent_id="agentA", kin_key="kinA")
        atom = {"kind": "EFFECT", "arity": 2, "key": "eff-y", "action": 1,
                "context": [[2]], "transform": {"before": [[2]], "after": [[3]]},
                "changed": 1}
        atom.update(atom_extra or {})
        fab.append("collective", "import_candidates", {
            "game": GAME, "level": LEVEL, "src_seq": 1, "atom": atom,
            "sigma": {}, "source_game": "g_src", "source_seq": 7,
            "source_id": "eff-y:0", "near_misses": [], "kin_echo": False})
        return fab

    def test_seeded_atom_carries_the_source_game(self, tmp_path):
        fab = self._fabric_with_candidate(tmp_path)
        gamma = E.Gamma(fab)
        assert consumer.seed_imports(gamma, fab, GAME, LEVEL) == 1
        recs = fab.query("collective", "atoms",
                         where=lambda r: (r.get("atom") or {}).get("imported"))
        assert len(recs) == 1
        assert recs[0]["atom"].get("source_game") == "g_src", (
            "the seeded atom lost its provenance -- the census cannot name it")

    def test_additive_only_an_existing_source_game_is_kept(self, tmp_path):
        """The retention is ADDITIVE: an atom already naming its source keeps it."""
        fab = self._fabric_with_candidate(tmp_path,
                                          atom_extra={"source_game": "g_origin"})
        gamma = E.Gamma(fab)
        assert consumer.seed_imports(gamma, fab, GAME, LEVEL) == 1
        recs = fab.query("collective", "atoms",
                         where=lambda r: (r.get("atom") or {}).get("imported"))
        assert recs[0]["atom"]["source_game"] == "g_origin", (
            "seed_imports overwrote an atom's own provenance")
