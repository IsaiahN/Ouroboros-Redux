"""B14 GATE: FABRIC_JANITOR — smart compaction that changes NO consumer answer.

⭐ WHY (PREREG_SMART_CLEANUP.md). 25 fabrics grow in parallel; telemetry is capped,
knowledge is kept forever. Size-triggered (never cadence), loud (a manifest every run,
the silent-failure fix), compaction not deletion where data has summary value.

⭐ THE FALSIFIER (the gate's centre): BYTE-EQUALITY of every consumer-visible answer
pre/post compaction — the queries consumers actually run are enumerated in _answers()
below. Any changed answer means the tool is WRONG (revert), per the prereg. Streams
compacted: consumed import_queue entries, settlements beyond retention, aged
mint_verdict rejects (stripped in place — record counts preserved). atoms, ideas,
priors, harvest, starvation and import_candidates are NEVER compacted.

Run pre-build: these failed (engines.egocentric.janitor absent).
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer
from engines.egocentric.affect import AffectGains
from engines.egocentric.fabric import KnowledgeFabric
from engines.egocentric.frontier import FrontierBook
from engines.egocentric.janitor import FabricJanitor
from engines.egocentric.mastery import MasteryLite

GAME, LEVEL = "g_home", 1


def _fabric(tmp_path):
    """A synthetic fabric with EVERY consumer-fed stream populated: a consumed queue
    item, an open not-found, aged settlements, aged mint_verdict rejects, ideas with
    events, harvest, starvation, replay outcomes."""
    f = KnowledgeFabric(str(tmp_path / "fab"), agent_id="agentA", kin_key="kinA")
    # atoms: one sigma-carrying atom so the consumer lands a hit
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
    # import queue: one item that will HIT, one that stays not-found, one pending
    f.append("collective", "import_queue", {"slot": "WORKSPACE", "residual": 1.0,
                                            "before": b.tolist(), "after": a.tolist()})
    a2 = b.copy()
    a2[1, 1] = 9
    a2[3, 3] = 9
    f.append("collective", "import_queue", {"slot": "WORKSPACE", "residual": 2.0,
                                            "before": b.tolist(), "after": a2.tolist()})
    consumer.consume(f, GAME, LEVEL, 2)          # closes #1 (candidate), #2 not-found
    f.append("collective", "import_queue", {"slot": "WORKSPACE", "residual": 3.0})
    # settlements: 130 aged + recent (affect's window is 20; retention 100)
    for i in range(130):
        f.append("collective", "settlements", {"agent": "agentA", "game": GAME,
                                               "level": 1, "action": 1 + i % 5,
                                               "members": 2, "best": float(i % 7),
                                               "nontrivial": bool(i % 3)})
    # mint_verdicts: 240 records, rejects dominant (the high-churn stream)
    for i in range(240):
        if i % 8 == 0:
            f.append("collective", "mint_verdicts",
                     {"verdict": "mint", "game": GAME, "level": 1, "key": "k%d" % i,
                      "w": 1.0})
        else:
            f.append("collective", "mint_verdicts",
                     {"verdict": "reject", "game": GAME, "level": 1, "key": "k%d" % i,
                      "w": 0.5})
    # the idea economy + the other knowledge streams (NEVER compacted)
    iid = f.mint({"note": "x"}, GAME, signal={"win": True}, level=1)
    f.echo(iid, by="agentB")
    f.falsify(iid, by="agentC")
    fr = FrontierBook(f)
    fr.record_harvest(GAME, LEVEL, dead=[(1, 1)], effects=[(2, 2)], fatal=(3, 3),
                      deltas={"1": (0, 1)})
    fr.record_harvest(GAME, LEVEL, dead=[(1, 1)])
    fr.record_fatal_opening(GAME, LEVEL, (3, 3))
    f.append("personal", "starvation", {"game": GAME, "code": "NO_EFFECTS"})
    MasteryLite(f).record_replay_outcome(GAME, True)
    return f, iid


def _answers(root, iid):
    """EVERY consumer-visible answer, serialized: the janitor's falsifier surface."""
    f = KnowledgeFabric(str(root), agent_id="agentA", kin_key="kinA")
    aff = AffectGains(f)
    fr = FrontierBook(f)
    return json.dumps({
        "pending": consumer.pending(f),
        "open_not_found": consumer.open_not_found(f),
        "candidates": consumer.candidates(f, GAME, LEVEL),
        "gains": aff.gains(),
        "narrate": aff.narrate(),
        "steer": aff.starvation_steer(GAME),
        "priors": f.priors(GAME),
        "credibility": f.credibility(iid),
        "reputation": f.reputation("agentA"),
        "harvest": fr.load_harvest(GAME, LEVEL),
        "avoid": fr.avoid_set(GAME, LEVEL),
        "mastery": MasteryLite(f).replay_probability(GAME, True),
        "atoms": f.query("collective", "atoms"),
    }, sort_keys=True, default=sorted)


def _stream(root, topic):
    return os.path.join(str(root), "collective", topic + ".jsonl")


class TestTheFalsifier:

    def test_every_consumer_answer_is_byte_equal_pre_post(self, tmp_path):
        f, iid = _fabric(tmp_path)
        pre = _answers(f.root, iid)
        FabricJanitor(f, max_stream_bytes=1).sweep()
        post = _answers(f.root, iid)
        assert pre == post, (
            "a consumer answer CHANGED under compaction -- the tool is wrong, revert")

    def test_compaction_actually_shrinks_the_churn_streams(self, tmp_path):
        f, _iid = _fabric(tmp_path)
        sizes = {t: os.path.getsize(_stream(f.root, t))
                 for t in ("import_queue", "settlements", "mint_verdicts")}
        rep = FabricJanitor(f, max_stream_bytes=1).sweep()
        for t, before in sizes.items():
            assert os.path.getsize(_stream(f.root, t)) < before, "%s did not shrink" % t
            assert rep[t]["action"] == "compacted"

    def test_consumed_queue_entries_are_gone_open_items_stay(self, tmp_path):
        f, _iid = _fabric(tmp_path)
        FabricJanitor(f, max_stream_bytes=1).sweep()
        rows = KnowledgeFabric(f.root, agent_id="agentA",
                               kin_key="kinA").query("collective", "import_queue")
        raw = [r for r in rows if "kind" not in r]
        # the hit item's raw entry is dropped; the not-found item and the pending
        # item survive (defeasible: never deleted while open -- the Chaitin rule)
        assert [r["seq"] for r in raw] == [2, 7]
        assert not any(r.get("kind") == "consumed" for r in rows)
        assert len([r for r in rows if r.get("kind") == "not_found"]) == 1

    def test_settlement_retention_with_a_fold_record(self, tmp_path):
        f, _iid = _fabric(tmp_path)
        FabricJanitor(f, max_stream_bytes=1).sweep()
        rows = KnowledgeFabric(f.root).query("collective", "settlements")
        folds = [r for r in rows if r.get("kind") == "fold"]
        assert len(folds) == 1 and folds[0]["n"] == 30, "summary value lost"
        assert len(rows) == FabricJanitor.SETTLE_KEEP + 1

    def test_aged_rejects_are_stripped_counts_preserved(self, tmp_path):
        f, _iid = _fabric(tmp_path)
        pre = KnowledgeFabric(f.root).query("collective", "mint_verdicts")
        FabricJanitor(f, max_stream_bytes=1).sweep()
        post = KnowledgeFabric(f.root).query("collective", "mint_verdicts")
        assert len(post) == len(pre), "verdict counts moved -- narration would lie"
        aged = post[:-FabricJanitor.VERDICT_KEEP]
        assert all(set(r) == {"verdict", "seq"} for r in aged
                   if r["verdict"] == "reject"), "aged rejects kept their bulk"
        assert all(r.get("key") for r in aged if r["verdict"] == "mint"), (
            "a MINT verdict was stripped -- mints are knowledge, not churn")

    def test_seq_high_water_mark_survives_compaction(self, tmp_path):
        """Appends after compaction must not REUSE a dropped seq -- candidates
        reference src_seq/match_seq by number forever."""
        f, _iid = _fabric(tmp_path)
        rows = f.query("collective", "import_queue")
        top = max(r["seq"] for r in rows)
        FabricJanitor(f, max_stream_bytes=1).sweep()
        nxt = f.append("collective", "import_queue", {"slot": "X", "residual": 0.5})
        assert nxt["seq"] == top + 1, "a seq was reused after compaction"


class TestTheDiscipline:

    def test_loud_manifest_every_run(self, tmp_path, capsys):
        f, _iid = _fabric(tmp_path)
        FabricJanitor(f, max_stream_bytes=1).sweep()
        out = capsys.readouterr().out
        assert "[JANITOR]" in out
        for t in ("import_queue", "settlements", "mint_verdicts"):
            assert t in out, "the manifest must name %s" % t
        capsys.readouterr()
        FabricJanitor(f, max_stream_bytes=1 << 30).sweep()
        assert "[JANITOR]" in capsys.readouterr().out, (
            "an under-threshold run must still be loud (the silent-failure fix)")

    def test_size_trigger_untouched_below_threshold(self, tmp_path):
        f, _iid = _fabric(tmp_path)
        files = {t: open(_stream(f.root, t), "rb").read()
                 for t in ("import_queue", "settlements", "mint_verdicts")}
        rep = FabricJanitor(f, max_stream_bytes=1 << 30).sweep()
        for t, blob in files.items():
            assert open(_stream(f.root, t), "rb").read() == blob
            assert rep[t]["action"] == "under-threshold"

    def test_bak_files_written(self, tmp_path):
        f, _iid = _fabric(tmp_path)
        FabricJanitor(f, max_stream_bytes=1).sweep()
        for t in ("import_queue", "settlements", "mint_verdicts"):
            assert os.path.isfile(_stream(f.root, t) + ".bak"), "%s has no .bak" % t

    def test_knowledge_streams_never_touched(self, tmp_path):
        f, _iid = _fabric(tmp_path)
        protected = ["atoms", "ideas", "idea_events", "frontier_paths",
                     "frontier_harvest", "import_candidates"]
        pre = {}
        for t in protected:
            p = _stream(f.root, t)
            pre[t] = open(p, "rb").read() if os.path.isfile(p) else None
        starv = os.path.join(f.root, "personal", "agentA", "starvation.jsonl")
        pre_starv = open(starv, "rb").read()
        FabricJanitor(f, max_stream_bytes=1).sweep()
        for t in protected:
            p = _stream(f.root, t)
            post = open(p, "rb").read() if os.path.isfile(p) else None
            assert post == pre[t], "PROTECTED stream %s was touched" % t
        assert open(starv, "rb").read() == pre_starv

    def test_second_sweep_is_stable(self, tmp_path):
        f, iid = _fabric(tmp_path)
        FabricJanitor(f, max_stream_bytes=1).sweep()
        mid = _answers(f.root, iid)
        FabricJanitor(f, max_stream_bytes=1).sweep()
        assert _answers(f.root, iid) == mid
