"""W2a: the predictor bank — one predictor per bound slot; every capable slot bets every action.

This is what makes settlement dense AND multi-workspace: the board was one slot; now BODY,
WORKSPACE, REFERENCE and RESOURCE each carry their own predictor and their own residual.
A slot that can't bet doesn't get read.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _bank():
    try:
        from engines.egocentric.bank import (
            PredictorBank,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.bank missing (%s) -- W2a has not landed" % e)
    from engines.egocentric.bank import PredictorBank as PB
    return PB


class TestBodyPredictor:

    def test_learns_the_delta_map_and_bets(self):
        b = _bank()()
        for _ in range(3):
            b.commit({"BODY": (2, 2)}, action=1)
            b.settle({"BODY": (2, 3)})                    # action 1 moves +1 col
        b.commit({"BODY": (5, 5)}, action=1)
        out = b.settle({"BODY": (5, 6)})
        assert out["BODY"]["bet"] is True
        assert out["BODY"]["residual"] == 0.0, "an established delta must predict exactly"

    def test_wrong_prediction_carries_residual(self):
        b = _bank()()
        for _ in range(3):
            b.commit({"BODY": (2, 2)}, action=1)
            b.settle({"BODY": (2, 3)})
        b.commit({"BODY": (5, 5)}, action=1)
        out = b.settle({"BODY": (5, 5)})                  # a wall: no move
        assert out["BODY"]["residual"] > 0.0

    def test_unestablished_action_does_not_bet(self):
        b = _bank()()
        b.commit({"BODY": (2, 2)}, action=4)
        out = b.settle({"BODY": (2, 1)})
        assert "BODY" not in out or out["BODY"]["bet"] is False


class TestReferenceAndResource:

    def test_reference_always_bets_no_change(self):
        b = _bank()()
        ref = np.zeros((3, 3), dtype=int)
        b.commit({"REFERENCE": ref}, action=1)
        out = b.settle({"REFERENCE": ref.copy()})
        assert out["REFERENCE"]["bet"] is True and out["REFERENCE"]["residual"] == 0.0
        changed = ref.copy()
        changed[1, 1] = 9
        b.commit({"REFERENCE": ref}, action=2)
        out2 = b.settle({"REFERENCE": changed})
        assert out2["REFERENCE"]["residual"] > 0.0, "a mutated reference is a loud residual"

    def test_resource_learns_the_per_action_cost(self):
        b = _bank()()
        for v in (42.0, 41.0, 40.0):
            b.commit({"RESOURCE": v}, action=1)
            b.settle({"RESOURCE": v - 1.0})
        b.commit({"RESOURCE": 30.0}, action=1)
        out = b.settle({"RESOURCE": 29.0})
        assert out["RESOURCE"]["bet"] is True and out["RESOURCE"]["residual"] == 0.0
        b.commit({"RESOURCE": 20.0}, action=1)
        out2 = b.settle({"RESOURCE": 20.0})               # a refill or a cost flip
        assert out2["RESOURCE"]["residual"] > 0.0


class TestWorkspacePredictor:

    def test_workspace_bets_via_gamma_atoms(self, tmp_path):
        from engines.egocentric import effects as E
        from engines.egocentric.fabric import KnowledgeFabric
        g = E.Gamma(KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4"))
        before = np.zeros((5, 5), dtype=int)
        before[2, 2] = 3
        after = before.copy()
        after[2, 2] = 4
        g.add(E.learn_effect(before, 6, after), game="g1", level=1)
        b = _bank()(gamma=g, game="g1", level=1)
        b.commit({"WORKSPACE": before}, action=6)
        out = b.settle({"WORKSPACE": after})
        assert out["WORKSPACE"]["bet"] is True
        assert out["WORKSPACE"]["residual"] == 0.0, "a known EFFECT atom must predict the contact"

    def test_no_matching_atom_means_no_bet(self, tmp_path):
        from engines.egocentric import effects as E
        from engines.egocentric.fabric import KnowledgeFabric
        g = E.Gamma(KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4"))
        b = _bank()(gamma=g, game="g1", level=1)
        ws = np.zeros((5, 5), dtype=int)
        ws[2, 2] = 7
        b.commit({"WORKSPACE": ws}, action=6)
        out = b.settle({"WORKSPACE": ws.copy()})
        assert "WORKSPACE" not in out or out["WORKSPACE"]["bet"] is False, (
            "a slot that can't bet doesn't get read")
