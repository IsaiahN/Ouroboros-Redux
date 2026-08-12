"""W3b + W3c: the discrepancy engine (d) and the planner — the objective and its spender.

d = role-aware MATCH between WORKSPACE and REFERENCE -> an axis-wise residual transform,
COMPUTED not perceived, and a HYPOTHESIS: d -> 0 without a level advance falsifies the
objective (the anti-elaboration check — d is self-authored and must never become a proxy).
The planner searches available EFFECT atoms for a multiset+order driving d -> identity,
feasibility-checked against measured cost; the stopping test is d == 0, never a period.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric
from engines.egocentric import effects as E


def _D():
    try:
        from engines.egocentric.discrepancy import compute_d, objective_falsified
    except Exception as e:
        pytest.fail("engines.egocentric.discrepancy missing (%s) -- W3b has not landed" % e)
    from engines.egocentric import discrepancy as D
    return D


def _P():
    try:
        from engines.egocentric.planner import plan_to_identity
    except Exception as e:
        pytest.fail("engines.egocentric.planner missing (%s) -- W3c has not landed" % e)
    from engines.egocentric import planner as P
    return P


class TestTheObjective:

    def test_identity_is_zero(self):
        D = _D()
        ws = np.zeros((4, 4), dtype=int)
        d = D.compute_d(ws, ws.copy())
        assert d["differing"] == 0 and D.is_identity(d)

    def test_d_is_axiswise(self):
        D = _D()
        ws = np.zeros((4, 4), dtype=int); ws[1, 1] = 3
        ref = np.zeros((4, 4), dtype=int); ref[1, 1] = 5
        d = D.compute_d(ws, ref)
        assert d["differing"] == 1
        assert d["by_value"].get((3, 5)) == 1, "d must say WHICH transformation is owed"

    def test_the_objective_is_falsifiable(self):
        D = _D()
        assert D.objective_falsified(d_is_zero=True, level_advanced=False) is True, (
            "d -> 0 with no level advance means the objective was WRONG -- pariah, not victory")
        assert D.objective_falsified(d_is_zero=True, level_advanced=True) is False
        assert D.objective_falsified(d_is_zero=False, level_advanced=False) is False


class TestThePlanner:

    def _gamma_with_increment(self, tmp_path):
        g = E.Gamma(KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4"))
        ids = []
        for v in (3, 4):
            b = np.zeros((5, 5), dtype=int); b[2, 2] = v
            a = b.copy(); a[2, 2] = v + 1
            ids.append(g.add(E.learn_effect(b, 6, a), game="g1", level=1))
        return g, ids

    def test_plans_a_multiset_to_identity(self, tmp_path):
        """WORKSPACE holds 3; REFERENCE wants 5; atoms 3->4 and 4->5 exist. The plan is both,
        in order, found by the stopping test d==0 -- no period was ever learned."""
        P = _P()
        g, _ = self._gamma_with_increment(tmp_path)
        ws = np.zeros((5, 5), dtype=int); ws[2, 2] = 3
        ref = np.zeros((5, 5), dtype=int); ref[2, 2] = 5
        out = P.plan_to_identity(ws, ref, g, game="g1", level=1,
                                 budget=100, cost_per_action=1)
        assert out is not None and out["feasible"] is True
        assert len(out["steps"]) == 2, "two applications drive d to identity"

    def test_no_operator_no_plan(self, tmp_path):
        P = _P()
        g = E.Gamma(KnowledgeFabric(str(tmp_path / "e"), agent_id="a", kin_key="v4"))
        ws = np.zeros((5, 5), dtype=int); ws[2, 2] = 3
        ref = np.zeros((5, 5), dtype=int); ref[2, 2] = 9
        out = P.plan_to_identity(ws, ref, g, game="g1", level=1,
                                 budget=100, cost_per_action=1)
        assert out is None, "a missing operator is an empty slot, not an invented step"

    def test_feasibility_against_measured_cost(self, tmp_path):
        P = _P()
        g, _ = self._gamma_with_increment(tmp_path)
        ws = np.zeros((5, 5), dtype=int); ws[2, 2] = 3
        ref = np.zeros((5, 5), dtype=int); ref[2, 2] = 5
        out = P.plan_to_identity(ws, ref, g, game="g1", level=1,
                                 budget=1, cost_per_action=1)
        assert out is not None and out["feasible"] is False, (
            "a correct plan can be unaffordable -- feasibility is part of the answer")

    def test_already_identity_plans_nothing(self, tmp_path):
        P = _P()
        g, _ = self._gamma_with_increment(tmp_path)
        ws = np.zeros((5, 5), dtype=int)
        out = P.plan_to_identity(ws, ws.copy(), g, game="g1", level=1,
                                 budget=10, cost_per_action=1)
        assert out is not None and out["steps"] == []
