"""B4 GATE (BUILD_PROGRAM_2 W1, G1): SWALLOW counters — the containment pattern
gets a ledger.

⭐ WHY. EGO code never crashes the host loop (house law) — but a swallowed
exception is invisible: a broken block can starve silently for generations.
B4 counts swallows per guarded block (fixed enum), settles <= 1 enum-coded
record per block per episode to the PERSONAL "swallow" stream at the SAME
episode boundary as starvation, narrates ([SWALLOW]), and is a pure function
of the counts. Consumer (one-currency law): the affect seed-gain read path —
effort only, never a price.

Run pre-build: failed (module absent).
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric


def _mod():
    try:
        import engines.egocentric.swallow as m
    except Exception as e:
        pytest.fail("engines.egocentric.swallow missing (%s) — B4 has not landed" % e)
    return m


class TestTheEnum:

    def test_the_block_enum_is_fixed(self):
        m = _mod()
        assert isinstance(m.BLOCKS, tuple)
        assert set(m.BLOCKS) == {"OBSERVER", "SPINE", "FABRIC", "BINDER_FEED",
                                 "BANK_SETTLE", "MINT_DRAIN", "PLANNER",
                                 "FRONTIER", "AFFECT", "STARVATION", "OTHER"}, (
            "the guarded-block enum is preregistered — no additions on the fly")


class TestTheCounter:

    def test_an_instrumented_raise_increments_its_block(self):
        """The tiny helper an except branch calls: counts on the host, maps
        unknown names to OTHER, never raises."""
        m = _mod()

        class _Host:
            pass
        h = _Host()
        m.swallow_note(h, "OBSERVER")
        m.swallow_note(h, "OBSERVER")
        m.swallow_note(h, "not-a-block")
        assert h._swallow_counts == {"OBSERVER": 2, "OTHER": 1}
        m.swallow_note(None, "SPINE")  # host without attrs: swallowed, no raise


class TestTheSettle:

    def _fab(self, tmp_path):
        return KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")

    def test_settle_emits_at_most_one_enum_record_per_block(self, tmp_path, capsys):
        m = _mod()
        b = m.SwallowBook(self._fab(tmp_path))
        recs = b.settle_episode({"OBSERVER": 3, "MINT_DRAIN": 1}, game="g1", level=2)
        assert len(recs) == 2
        assert all(r["block"] in m.BLOCKS for r in recs), "enum-coded only"
        blocks = [r["block"] for r in recs]
        assert len(blocks) == len(set(blocks)), "<= 1 record per block per episode"
        stored = b.fabric.query("personal", "swallow")
        assert len(stored) == 2 and {r["block"] for r in stored} == {"OBSERVER",
                                                                    "MINT_DRAIN"}
        outp = capsys.readouterr().out
        assert "[SWALLOW]" in outp and "OBSERVER" in outp, (
            "no record without its narration — the legibility law")

    def test_a_healthy_episode_emits_none(self, tmp_path, capsys):
        m = _mod()
        b = m.SwallowBook(self._fab(tmp_path))
        assert b.settle_episode({}, game="g1", level=0) == []
        assert b.fabric.query("personal", "swallow") == []
        assert "[SWALLOW]" not in capsys.readouterr().out

    def test_the_record_is_a_pure_function_of_the_counts(self, tmp_path):
        m = _mod()
        c = {"BINDER_FEED": 2}
        assert m.SwallowBook.swallowed(c) == m.SwallowBook.swallowed(dict(c))
        r1 = m.SwallowBook(KnowledgeFabric(str(tmp_path / "x"), agent_id="a",
                                           kin_key="v4")).settle_episode(
            c, game="g1", level=1)
        r2 = m.SwallowBook(KnowledgeFabric(str(tmp_path / "y"), agent_id="a",
                                           kin_key="v4")).settle_episode(
            dict(c), game="g1", level=1)
        assert r1 == r2, "replayability: identical counts -> identical records"


class TestTheLoopBoundary:

    def test_end_game_settles_the_swallow_book(self, tmp_path, capsys):
        """A REAL loop instance with counted swallows settles exactly one
        record per block at the episode boundary."""
        _mod()
        from cognitive_loop import CognitiveLoop
        loop = CognitiveLoop()
        loop._ego_fabric = KnowledgeFabric(str(tmp_path / "f"), agent_id="a",
                                           kin_key="v4")
        loop._game_id = "g1"
        loop._swallow_counts = {"PLANNER": 4}
        loop.end_game()
        stored = loop._ego_fabric.query("personal", "swallow")
        assert len(stored) == 1 and stored[0]["block"] == "PLANNER"
        assert stored[0]["count"] == 4
        assert "[SWALLOW]" in capsys.readouterr().out
        loop.end_game()  # the settled flag: never twice per episode
        assert len(loop._ego_fabric.query("personal", "swallow")) == 1

    def test_a_healthy_loop_episode_emits_none(self, tmp_path, capsys):
        _mod()
        from cognitive_loop import CognitiveLoop
        loop = CognitiveLoop()
        loop._ego_fabric = KnowledgeFabric(str(tmp_path / "f"), agent_id="a",
                                           kin_key="v4")
        loop.end_game()
        assert loop._ego_fabric.query("personal", "swallow") == []
        assert "[SWALLOW]" not in capsys.readouterr().out


class TestTheInstrumentation:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def test_the_largest_ego_blocks_are_instrumented(self):
        src = self._src()
        assert src.count("_swal(self, ") >= 10, (
            "fewer than 10 guarded EGO blocks feed the swallow counter — the "
            "containment pattern stays invisible (B4 unlanded)")

    def test_only_enum_blocks_are_named_at_call_sites(self):
        import re
        m = _mod()
        names = re.findall(r'_swal\(self, "([A-Z_]+)"\)', self._src())
        assert names, "no instrumented call sites found"
        assert set(names) <= set(m.BLOCKS)
