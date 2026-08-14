"""TORN-WRITES GATE: every reader skips a half-written JSONL line and reads
the rest.

The 25 workers cross-mount each other's LIVE fabrics: a reader can catch a
concurrent writer mid-line, and a crash can leave a truncated tail on disk
permanently. This suite builds one realistic fabric (atoms with sigma, an
import queue, settlements, mint verdicts, harvest + move + fatal records,
ideas + echo/falsify events, personal starvation/swallow), snapshots every
consumer-visible answer, then TEARS every stream two ways:

  * a truncated half-JSON line INSERTED mid-stream (terminated by newline);
  * a truncated half-JSON tail at EOF with NO newline (the reader catching
    the writer mid-line / a crash-truncated append).

Then every reader is re-asked: fabric.query, consumer.describe/pending/
consume/candidates/open_not_found, Gamma get/apply + the planner's atom load,
affect gains/narration/steer, frontier harvest/moves/avoid merges, the idea
economy's priors/credibility/reputation, and the janitor's forced sweep
(which must also PRESERVE the torn evidence and change no consumer answer).
A crash in any reader is a FINDING, not ours to fix.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer  # noqa: E402
from engines.egocentric.affect import AffectGains  # noqa: E402
from engines.egocentric.effects import Gamma, learn_effect  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.frontier import FrontierBook  # noqa: E402
from engines.egocentric.janitor import FabricJanitor  # noqa: E402
from engines.egocentric.planner import plan_to_identity  # noqa: E402
from engines.egocentric.starvation import StarvationBook  # noqa: E402
from engines.egocentric.swallow import SwallowBook  # noqa: E402

GAME = "torn_g"
TORN_MID = '{"seq": 999, "kind": "consumed", "src_'      # newline-terminated
TORN_TAIL = '{"slot": "WORKSPACE", "residual": 3.0, "bef'  # NO newline (EOF)


def _frames():
    before = np.zeros((8, 8), dtype=int)
    before[3, 3] = 3
    after = before.copy()
    after[3, 3] = 4
    return before, after


def _build_fabric(root):
    """A realistic little fabric: every stream a reader consults."""
    fab = KnowledgeFabric(str(root), agent_id="tornagent", kin_key="v4")
    before, after = _frames()
    gm = Gamma(fab)
    atom = learn_effect(before, 6, after)
    atom["sigma"] = consumer.sigma_of(before, after)
    aid = gm.add(atom, GAME, 1)
    # the import queue: one recognizable residual, one impoverished one
    fab.append("collective", "import_queue",
               {"slot": "WORKSPACE", "residual": 1.0,
                "before": before.tolist(), "after": after.tolist()})
    fab.append("collective", "import_queue",
               {"slot": "REFERENCE", "residual": 2.0})
    # settlements + verdicts (affect's food)
    for k in range(6):
        fab.append("collective", "settlements",
                   {"agent": "tornagent", "game": GAME, "level": 1, "action": 6,
                    "members": 1, "best": 0.5, "nontrivial": bool(k % 2),
                    "atom_key": None, "atom_bin": None})
    fab.append("collective", "mint_verdicts", {"verdict": "mint", "game": GAME,
                                               "level": 1, "key": atom["key"]})
    fab.append("collective", "mint_verdicts", {"verdict": "reject", "game": GAME,
                                               "level": 1})
    # frontier books
    book = FrontierBook(fab)
    book.record_harvest(GAME, 1, dead=[(2, 2)], effects=[(4, 4)],
                        fatal=(6, 6), deltas={"1": (0, 1)})
    book.record_harvest(GAME, 1, dead=[(2, 2)], effects=[], fatal=None, deltas={})
    book.record_moves(GAME, 1, {"1": (3, 1), "2": (0, 4)})
    book.record_fatal_opening(GAME, 1, (6, 6))
    # the idea economy
    idea_id = fab.mint({"kind": "CLICK_AT", "cell": [4, 4]}, game=GAME,
                       signal={"type": "level_up"}, scope="collective", level=1)
    fab.echo(idea_id, by="someone_else")
    fab.falsify(idea_id, by="a_critic")
    # personal books
    StarvationBook(fab).settle_episode({"bank_tried": 20, "bank_passed": 0},
                                       game=GAME, level=1, budget_spent=9)
    SwallowBook(fab).settle_episode({"OTHER": 2}, game=GAME, level=1)
    # drain the FIRST queue item now: the closed trio (raw+sigma+consumed)
    # gives the janitor something real to drop, and leaves one candidate
    report = consumer.consume(fab, GAME, 1, 1)
    assert report["candidates"] == 1, "fixture consume failed: %r" % (report,)
    return fab, gm, aid, idea_id, book


def _all_streams(root):
    out = []
    for r, _d, files in os.walk(str(root)):
        for f in files:
            if f.endswith(".jsonl"):
                out.append(os.path.join(r, f))
    return sorted(out)


def _tear(root):
    """Insert a torn line mid-stream in EVERY stream file, plus a torn tail:
    un-terminated (caught mid-line at EOF) on read-mostly streams; newline-
    terminated on the import queue, whose OWNER keeps appending -- a permanent
    un-terminated tail there would just merge with (and eat) the next append,
    which TestCrashTruncatedTailRecovery covers separately."""
    for path in _all_streams(root):
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        assert lines, "fixture stream %r unexpectedly empty" % path
        rebuilt = [lines[0], TORN_MID + "\n"] + lines[1:]
        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(rebuilt)
        with open(path, "a", encoding="utf-8") as fh:
            if path.endswith("import_queue.jsonl"):
                fh.write(TORN_TAIL + "\n")            # terminated torn line
            else:
                fh.write(TORN_TAIL)                   # no newline: caught mid-line


def _answers(fab, gm, aid, idea_id, book):
    """Every consumer-visible answer the prereg names, as one comparable blob."""
    g = Gamma(fab)
    return {
        "atoms": consumer.all_atoms(fab),
        "pending": consumer.pending(fab),
        "open_not_found": consumer.open_not_found(fab),
        "candidates": consumer.candidates(fab, GAME, 1),
        "gamma_get": g.get(aid),
        "gains": AffectGains(fab).gains(),
        "narrate": AffectGains(fab).narrate(),
        "steer": AffectGains(fab).starvation_steer(GAME),
        "seed_gain": AffectGains(fab).seed_gain(GAME),
        "harvest": {k: sorted(v) if isinstance(v, set) else v
                    for k, v in book.load_harvest(GAME, 1).items()},
        "moves": book.load_moves(GAME, 1),
        "avoid": sorted(book.avoid_set(GAME, 1)),
        "priors": fab.priors(GAME),
        "credibility": fab.credibility(idea_id),
        "reputation": fab.reputation("tornagent"),
    }


@pytest.fixture()
def torn(tmp_path):
    root = tmp_path / "fab"
    fab, gm, aid, idea_id, book = _build_fabric(root)
    pre = _answers(fab, gm, aid, idea_id, book)
    pre_counts = {p: sum(1 for ln in open(p, encoding="utf-8") if ln.strip())
                  for p in _all_streams(root)}
    _tear(root)
    return {"root": root, "fab": fab, "gm": gm, "aid": aid,
            "idea_id": idea_id, "book": book, "pre": pre,
            "pre_counts": pre_counts}


class TestFabricReadersSkipTornLines:

    def test_every_stream_query_returns_exactly_the_intact_records(self, torn):
        post = _answers(torn["fab"], torn["gm"], torn["aid"],
                        torn["idea_id"], torn["book"])
        for key in torn["pre"]:
            assert post[key] == torn["pre"][key], (
                "FINDING candidate -- reader %r changed its answer after torn "
                "lines were injected:\npre:  %r\npost: %r"
                % (key, torn["pre"][key], post[key]))

    def test_describe_survives_a_torn_queue_record(self, torn):
        for rec in consumer.pending(torn["fab"]):
            sig = consumer.describe(rec)
            assert isinstance(sig, dict) and "mag" in sig

    def test_next_seq_ignores_torn_lines(self, torn):
        fab = torn["fab"]
        rows = fab.query("collective", "settlements")
        top = max(int(r.get("seq", 0)) for r in rows)
        rec = fab.append("collective", "settlements",
                         {"agent": "tornagent", "game": GAME, "level": 1,
                          "action": 6, "members": 1, "best": 0.1,
                          "nontrivial": False, "atom_key": None,
                          "atom_bin": None})
        assert rec["seq"] == top + 1, (
            "a torn line perturbed the seq high-water mark: got %r after %r"
            % (rec["seq"], top))


class TestConsumerAndPlannerOverTornStreams:

    def test_consume_still_recognizes_the_atom(self, torn):
        fab = torn["fab"]
        before, after = _frames()
        fab.append("collective", "import_queue",
                   {"slot": "WORKSPACE", "residual": 1.0,
                    "before": before.tolist(), "after": after.tolist()})
        report = consumer.consume(fab, GAME, 1, 10)
        assert report["candidates"] >= 1, (
            "the consumer stopped matching once torn lines appeared: %r"
            % (report,))
        cands = consumer.candidates(fab, GAME, 1)
        assert cands and cands[-1]["atom"]["key"], "candidate lost its atom copy"

    def test_planner_loads_atoms_past_torn_lines(self, torn):
        before, after = _frames()
        plan = plan_to_identity(before, after, Gamma(torn["fab"]), GAME, 1,
                                budget=10.0, cost_per_action=1.0)
        assert plan is not None and plan["steps"] == [torn["aid"]], (
            "the planner lost the stored atom behind a torn line: %r" % (plan,))

    def test_gamma_apply_still_runs_the_atom(self, torn):
        before, after = _frames()
        out = Gamma(torn["fab"]).apply(torn["aid"], before)
        assert out is not None and (out == after).all()

    def test_seed_imports_still_enters_candidates(self, torn, tmp_path):
        fab = torn["fab"]
        consumer.consume(fab, GAME, 1, 10)
        fresh = KnowledgeFabric(str(tmp_path / "fresh"), agent_id="x",
                                kin_key="v4")
        n = consumer.seed_imports(Gamma(fresh), fab, GAME, 1)
        assert n >= 1, "seed_imports imported nothing over a torn fabric"


class TestBookWritersOverTornStreams:

    def test_episode_books_still_settle_after_a_torn_tail(self, torn, capsys):
        fab = torn["fab"]
        recs = StarvationBook(fab).settle_episode(
            {"mint_tried": 15, "mint_passed": 0}, game=GAME, level=2,
            budget_spent=3)
        assert len(recs) == 1 and recs[0]["code"] == "MINT_STARVED"
        srecs = SwallowBook(fab).settle_episode({"FABRIC": 1}, game=GAME, level=2)
        assert len(srecs) == 1 and srecs[0]["block"] == "FABRIC"
        capsys.readouterr()
        # NB: each personal stream's torn EOF tail merges with the first
        # append after it (both become one unparseable line) -- a crash tail
        # costs at most that one record; the streams above were re-read
        # through settle_episode's own append (which must not raise).

    def test_frontier_book_still_records(self, torn):
        book = torn["book"]
        book.record_harvest(GAME, 2, dead=[], effects=[(1, 1)], fatal=None,
                            deltas={})
        assert book.errors == 0
        # NB the (2-report) conservative rules on the freshly written level
        h = book.load_harvest(GAME, 2)
        assert (1, 1) in h["tried"] or h == {
            "dead": set(), "effects": set(), "fatal": set(),
            "tried": set(), "deltas": {}}


class TestJanitorOverTornStreams:

    def test_sweep_never_errors_and_preserves_consumer_answers(self, torn):
        fab, gm, aid = torn["fab"], torn["gm"], torn["aid"]
        idea_id, book = torn["idea_id"], torn["book"]
        pre = _answers(fab, gm, aid, idea_id, book)
        jan = FabricJanitor(fab, max_stream_bytes=0)     # force every policy
        report = jan.sweep()
        assert jan.errors == 0, (
            "FINDING -- the janitor crashed on a torn stream: %r" % (report,))
        for topic, entry in report.items():
            assert entry.get("action") != "ERROR", (
                "FINDING -- janitor errored on %r: %r" % (topic, entry))
        post = _answers(fab, gm, aid, idea_id, book)
        for key in pre:
            assert post[key] == pre[key], (
                "the janitor's sweep changed consumer answer %r over a torn "
                "stream:\npre:  %r\npost: %r" % (key, pre[key], post[key]))

    def test_sweep_keeps_torn_evidence_in_compacted_streams(self, torn):
        fab = torn["fab"]
        jan = FabricJanitor(fab, max_stream_bytes=0)
        jan.sweep()
        # import_queue was actually compacted (nothing consumed yet, so only
        # the policy's no-drop path may run) -- whatever happened, the torn
        # MID line must still be on disk: a crash mid-write is evidence.
        path = os.path.join(str(torn["root"]), "collective",
                            "import_queue.jsonl")
        content = open(path, encoding="utf-8").read()
        assert TORN_MID in content, (
            "the janitor deleted a torn line -- evidence, not garbage")


class TestCrashTruncatedTailRecovery:

    def test_append_after_unterminated_tail_loses_at_most_one_record(self, tmp_path):
        """A crash-truncated tail has NO newline; the next append merges with
        it into one unparseable line. The stream must stay readable, lose at
        most that first append, and resume cleanly afterwards."""
        fab = KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")
        for k in range(3):
            fab.append("collective", "t", {"k": k})
        path = os.path.join(str(tmp_path / "f"), "collective", "t.jsonl")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write('{"k": 3, "half')                 # the crash tail
        fab.append("collective", "t", {"k": 4})        # merges: lost with the tail
        fab.append("collective", "t", {"k": 5})        # clean again
        rows = fab.query("collective", "t")
        ks = [r["k"] for r in rows]
        assert ks == [0, 1, 2, 5], (
            "recovery after a crash-truncated tail should cost exactly the "
            "merged record -- stream reads back %r" % (ks,))
        assert [r["seq"] for r in rows] == [1, 2, 3, 4], (
            "seq accounting broke across the merged line")
