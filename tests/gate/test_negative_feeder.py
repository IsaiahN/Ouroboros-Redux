"""B6 GATE (BUILD_PROGRAM_2 W1): the NO_NEGATIVE_INSTANCES feeder.

⭐ WHY. The starvation spec reserved the counter keys neg_tried/neg_passed at
R1, but nothing ever fed them: NO_NEGATIVE_INSTANCES could not fire even in a
world with zero falsifying evidence. B6 feeds them in the W4c-1 binder-feed
block — every per-class comparison examined counts neg_tried; a mutated=False
comparison (the class did NOT change: a genuine negative instance) counts
neg_passed. The socket then starves exactly when many observations were
examined and NONE ever offered negative evidence.

Run pre-build: the wiring tests failed (counters never fed).
"""
from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric


class TestTheCodeCanFire:

    def test_fed_counters_fire_the_socket(self, tmp_path):
        """With the feeder live, an episode of all-mutating observations
        starves the negatives socket — and ONLY then."""
        from engines.egocentric.starvation import PLAN_N, StarvationBook
        got = StarvationBook.starved({"neg_tried": PLAN_N, "neg_passed": 0})
        assert [g["code"] for g in got] == ["NO_NEGATIVE_INSTANCES"]
        assert StarvationBook.starved({"neg_tried": PLAN_N,
                                       "neg_passed": 1}) == []

    def test_the_record_reaches_the_stream(self, tmp_path):
        from engines.egocentric.starvation import PLAN_N, StarvationBook
        f = KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")
        StarvationBook(f).settle_episode({"neg_tried": PLAN_N, "neg_passed": 0},
                                         game="g1", level=0, budget_spent=50)
        stored = f.query("personal", "starvation")
        assert len(stored) == 1 and stored[0]["code"] == "NO_NEGATIVE_INSTANCES"


class TestTheWiring:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def test_the_binder_feed_block_feeds_the_counters(self):
        src = self._src()
        i = src.find("W4c-1: FEED THE BINDER")
        assert i != -1, "the binder-feed block vanished"
        window = src[i:i + 4000]
        assert "_neg_feed(self, _mut)" in window, (
            "the reserved neg_tried/neg_passed keys are still never fed — "
            "NO_NEGATIVE_INSTANCES can never fire (B6 unlanded)")
        j = src.find("def _neg_feed")
        assert j != -1, "the feeder helper is missing"
        helper = src[j:j + 900]
        assert "neg_tried" in helper and "neg_passed" in helper

    def test_the_counters_are_initialised_with_the_episode_sockets(self):
        src = self._src()
        i = src.find('"mint_tried"')
        assert i != -1
        window = src[max(0, i - 200):i + 400]
        assert "neg_tried" in window and "neg_passed" in window, (
            "the per-episode counter dict must carry the negative-evidence keys")

    def test_negative_evidence_is_the_unmutated_case(self):
        src = self._src()
        i = src.find("def _neg_feed")
        window = src[i:i + 900]
        assert "if not mut" in window, (
            "neg_passed must key off the mutated=False comparison — that IS "
            "the negative instance")

    def test_the_feeder_behaves(self):
        """Functional: examined comparisons count; only unmutated ones accrue."""
        import cognitive_loop as cl

        class _L:
            pass
        loop = _L()
        loop._w4c_counters = {"neg_tried": 0, "neg_passed": 0}
        cl._neg_feed(loop, True)
        cl._neg_feed(loop, False)
        cl._neg_feed(loop, True)
        assert loop._w4c_counters == {"neg_tried": 3, "neg_passed": 1}
        cl._neg_feed(None, False)  # containment: hostile host never raises
