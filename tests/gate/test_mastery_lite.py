"""Mastery-lite: replay probability is EARNED from replay reliability (v2's principle, scoped).

'Earn the right to sequence replay' (v2, inspected generic): a bank that keeps reproducing its
levels keeps its high replay rate; a bank that starts failing decays back to exploration.
"""
from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import pytest

from engines.egocentric.fabric import KnowledgeFabric


def _m(tmp_path, name="f"):
    try:
        from engines.egocentric.mastery import (
            MasteryLite,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.mastery missing (%s)" % e)
    from engines.egocentric.mastery import MasteryLite as ML
    return ML(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))


class TestTheContract:

    def test_no_bank_is_incumbent_rate(self, tmp_path):
        assert _m(tmp_path).replay_probability("g1", False) == 0.2

    def test_bank_without_history_is_optimistic(self, tmp_path):
        assert _m(tmp_path).replay_probability("g1", True) == 0.8

    def test_earned_rates(self, tmp_path):
        m = _m(tmp_path)
        for _ in range(10):
            m.record_replay_outcome("g1", True)
        assert abs(m.replay_probability("g1", True) - 0.8) < 1e-9
        m2 = _m(tmp_path, "f2")
        for i in range(10):
            m2.record_replay_outcome("g1", i % 2 == 0)
        assert abs(m2.replay_probability("g1", True) - 0.5) < 1e-9
        m3 = _m(tmp_path, "f3")
        for _ in range(10):
            m3.record_replay_outcome("g1", False)
        assert abs(m3.replay_probability("g1", True) - 0.2) < 1e-9

    def test_last_10_window_decays_stale_success(self, tmp_path):
        m = _m(tmp_path)
        for _ in range(10):
            m.record_replay_outcome("g1", True)
        for _ in range(10):
            m.record_replay_outcome("g1", False)
        assert abs(m.replay_probability("g1", True) - 0.2) < 1e-9, (
            "ten old successes must not outvote ten recent failures — decay is the point")

    def test_games_are_independent(self, tmp_path):
        m = _m(tmp_path)
        for _ in range(10):
            m.record_replay_outcome("g1", False)
        assert m.replay_probability("g2", True) == 0.8


class TestTheWiring:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_game_player.py"), encoding="utf-8",
                    errors="replace").read()

    def test_outcomes_are_recorded_after_replays(self):
        src = self._src()
        assert "record_replay_outcome" in src, "no outcome wire — mastery starves"

    def test_the_probability_routes_through_mastery(self):
        src = self._src()
        assert "replay_probability(" in src
        i = src.find("_replay_winning_sequences(")
        window = src[max(0, i - 2500):i]
        assert ".replay_probability(" in window or "mastery" in window.lower(), (
            "the replay branch still uses the flat constant — the earned rate is unwired")
