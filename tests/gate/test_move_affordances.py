"""B2 GATE (BUILD_PROGRAM_2 W1): movement affordances — the six click-less games
stop re-exploring blind.

THE CONTRACT:
  * FrontierBook.record_moves(game, level, moves) banks ONE per-episode record of
    per-action (1-5) frame-changed vs unchanged counts into the SAME collective
    "frontier_harvest" stream, discriminated by "kind": "move";
  * FrontierBook.load_moves(game, level) sums counts across records (seeds+local),
    ignoring non-move records; load_harvest ignores move records symmetrically;
  * bias_moves(candidates, moves): a BOUNDED BIAS, never a veto — an action with
    >= MOVE_NOOP_MIN observed outcomes and a no-op rate >= MOVE_NOOP_RATE keeps
    weight 1 while every other candidate gets MOVE_BIAS copies; every candidate
    stays present; no data -> uniform;
  * wiring: the player banks moves at the SAME episode-end site as record_harvest;
    the loop's blind 1-5 chooser draws through the bias.

Run pre-build: failed (methods absent).
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric


def _book(tmp_path, name="f", agent="a", seeds=None):
    from engines.egocentric.frontier import FrontierBook
    return FrontierBook(KnowledgeFabric(str(tmp_path / name), agent_id=agent,
                                        kin_key="v4", seeds=seeds))


class TestTheMoveBank:

    def test_roundtrip_and_summation(self, tmp_path):
        b = _book(tmp_path)
        if not hasattr(b, "record_moves"):
            pytest.fail("FrontierBook.record_moves missing — B2 has not landed")
        b.record_moves("g1", 0, {1: (3, 0), 2: (0, 4)})
        b.record_moves("g1", 0, {2: (1, 2), 5: (0, 6)})
        m = b.load_moves("g1", 0)
        assert m == {"1": (3, 0), "2": (1, 6), "5": (0, 6)}, (
            "load_moves must SUM changed/unchanged counts across records")

    def test_game_and_level_scoping(self, tmp_path):
        b = _book(tmp_path)
        b.record_moves("g1", 0, {1: (0, 5)})
        b.record_moves("g1", 1, {2: (0, 5)})
        b.record_moves("g2", 0, {3: (0, 5)})
        assert set(b.load_moves("g1", 0)) == {"1"}

    def test_move_records_ride_the_harvest_stream_without_polluting_it(self, tmp_path):
        """SAME stream, "kind" discriminator: load_harvest ignores move records,
        load_moves ignores harvest records."""
        from engines.egocentric.frontier import HARVEST_TOPIC
        b = _book(tmp_path)
        b.record_moves("g1", 0, {1: (2, 2)})
        b.record_harvest("g1", 0, dead=[(1, 1)], effects=[], fatal=None, deltas={})
        recs = b.fabric.query("collective", HARVEST_TOPIC)
        assert len(recs) == 2, "move records must ride the SAME harvest stream"
        assert any(r.get("kind") == "move" for r in recs)
        h = b.load_harvest("g1", 0)
        assert h["tried"] == {(1, 1)}, "a move record is not a cell observation"
        assert b.load_moves("g1", 0) == {"1": (2, 2)}

    def test_population_union_via_seeds(self, tmp_path):
        sb = _book(tmp_path, "seed", agent="origin")
        sb.record_moves("g1", 0, {4: (0, 7)})
        live = _book(tmp_path, "live", agent="b", seeds=[str(tmp_path / "seed")])
        assert live.load_moves("g1", 0) == {"4": (0, 7)}


class TestTheBias:

    def _bias(self):
        from engines.egocentric.frontier import bias_moves
        return bias_moves

    def test_noop_heavy_actions_are_deprioritized_not_vetoed(self):
        from engines.egocentric.frontier import MOVE_BIAS
        out = self._bias()([1, 2, 3], {"1": (0, 10)})
        assert out.count(1) == 1, "a banked no-op action keeps exactly weight 1"
        assert out.count(2) == MOVE_BIAS and out.count(3) == MOVE_BIAS
        assert set(out) == {1, 2, 3}, "a bias, NOT a veto — every candidate stays"

    def test_no_data_means_uniform(self):
        out = self._bias()([1, 2], {})
        assert out.count(1) == out.count(2) > 0

    def test_below_the_observation_floor_no_action_is_judged(self):
        from engines.egocentric.frontier import MOVE_NOOP_MIN
        out = self._bias()([1, 2], {"1": (0, MOVE_NOOP_MIN - 1)})
        assert out.count(1) == out.count(2), (
            "an action under MOVE_NOOP_MIN observations must not be judged")

    def test_an_effectful_action_is_never_deprioritized(self):
        out = self._bias()([1, 2], {"1": (5, 5)})
        assert out.count(1) == out.count(2), (
            "a 50%% no-op rate is an affordance, not a dead action")

    def test_empty_candidates_survive(self):
        assert self._bias()([], {"1": (0, 9)}) == []


class TestTheWiring:

    def _src(self, f):
        return open(os.path.join(REPO, f), encoding="utf-8",
                    errors="replace").read()

    def test_the_player_banks_moves_at_the_harvest_site(self):
        src = self._src("cognitive_game_player.py")
        assert "record_moves" in src, (
            "the episode end never banks movement outcomes — the click-less "
            "games keep re-exploring blind (B2 unlanded)")
        i, j = src.find("record_harvest"), src.find("record_moves")
        assert abs(j - i) < 4000, "moves must bank at the SAME episode-end site"

    def test_the_loop_draws_blind_moves_through_the_bias(self):
        src = self._src("cognitive_loop.py")
        assert "bias_moves" in src and "load_moves" in src, (
            "the consumer is unwired — banked moves with no reader is the R3 "
            "sin (B2 unlanded)")
        assert src.count("self._movebias(") >= 3, (
            "the blind 1-5 chooser (unknown/open/fallback draws) must pass "
            "through the bounded bias")
