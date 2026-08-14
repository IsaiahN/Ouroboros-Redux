"""B11 falsifier: the AGENT_MOTION predictor family (flagged AGENT_MOTION_ENABLED=True).

A class earns the family ONLY by self-propelled motion: it moves across steps with no acting
click adjacent to it (animacy). Once constructed, the family stakes two next-step bets --
constant-velocity extrapolation AND pursuit (one step toward a supplied target) -- and settles
like every other predictor: the winning bet's residual routes through the ResidualRouter, so a
true pursuer settles TRANSFERRED at the corner where constant velocity is wrong. A static
object never constructs the family; click-driven motion never counts; the module flag turns
the whole family off.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _B():
    from engines.egocentric import bank as B
    if not hasattr(B, "AGENT_MOTION_ENABLED"):
        pytest.fail("bank.AGENT_MOTION_ENABLED missing -- B11 has not landed")
    return B


class TestFamilyConstruction:

    def test_self_propelled_motion_constructs_the_family(self):
        B = _B()
        b = B.PredictorBank()
        cls = "critter"
        for pos in ((2, 3), (3, 3), (4, 3), (5, 3)):     # three unaided moves
            b.note_motion(cls, pos)
        assert b.agent_family(cls) is True

    def test_a_static_object_never_constructs_the_family(self):
        B = _B()
        b = B.PredictorBank()
        for _ in range(6):
            b.note_motion("rock", (4, 4))
        assert b.agent_family("rock") is False
        assert b.commit_agent("rock", (4, 4), target=(0, 0)) is False
        out = b.settle_agent("rock", (4, 4))
        assert out["bet"] is False, "no family, no bet"

    def test_click_driven_motion_does_not_count(self):
        B = _B()
        b = B.PredictorBank()
        pos = (2, 2)
        for step in range(1, 7):
            b.note_motion("token", pos, click_cell=pos)   # I clicked ON it; then it moved
            pos = (2, 2 + step)
        assert b.agent_family("token") is False, (
            "motion adjacent to the acting click is my doing, not the object's")

    def test_the_flag_gates_construction(self, monkeypatch):
        B = _B()
        monkeypatch.setattr(B, "AGENT_MOTION_ENABLED", False)
        b = B.PredictorBank()
        for pos in ((2, 3), (3, 3), (4, 3), (5, 3), (6, 3)):
            b.note_motion("critter", pos)
        assert b.agent_family("critter") is False


class TestPursuitBet:

    def test_a_pursuer_is_predicted_by_the_pursuit_bet_and_settles_transferred(self):
        from engines.egocentric.router import ResidualRouter
        B = _B()
        b = B.PredictorBank()
        cls = "chaser"
        for pos in ((2, 3), (3, 3), (4, 3), (5, 3)):     # marching down toward the corner
            b.note_motion(cls, pos)
        assert b.agent_family(cls) is True

        target = (5, 0)                                  # the prey sits left: the chaser turns
        assert b.commit_agent(cls, (5, 3), target=target) is True
        out = b.settle_agent(cls, (5, 2))                # it stepped toward the target
        assert out["bet"] is True and out["family"] == "AGENT_MOTION"
        assert out["bets"]["pursuit"]["predicted"] == (5, 2)
        assert out["bets"]["pursuit"]["residual"] == 0.0
        assert out["bets"]["constant_velocity"]["residual"] > 0.0, (
            "at the corner the straight-line extrapolation must be wrong -- otherwise this "
            "test cannot tell the two bets apart")
        assert out["winner"] == "pursuit" and out["residual"] == 0.0

        router = ResidualRouter()
        assert router.route("AGENT_MOTION", out) == "TRANSFERRED"

    def test_constant_velocity_wins_on_a_straight_liner(self):
        B = _B()
        b = B.PredictorBank()
        cls = "drifter"
        for pos in ((1, 1), (2, 1), (3, 1), (4, 1)):
            b.note_motion(cls, pos)
        assert b.commit_agent(cls, (4, 1)) is True       # no target supplied: velocity only
        out = b.settle_agent(cls, (5, 1))
        assert out["bet"] is True
        assert out["bets"]["constant_velocity"]["residual"] == 0.0
        assert "pursuit" not in out["bets"], "no target, no pursuit bet"
        assert out["residual"] == 0.0

    def test_a_wrong_bet_carries_its_residual(self):
        B = _B()
        b = B.PredictorBank()
        cls = "chaser"
        for pos in ((2, 3), (3, 3), (4, 3), (5, 3)):
            b.note_motion(cls, pos)
        b.commit_agent(cls, (5, 3), target=(5, 0))
        out = b.settle_agent(cls, (9, 9))                # it teleported: both bets wrong
        assert out["bet"] is True and out["residual"] > 0.0
