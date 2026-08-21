"""PLANNER NODE BUDGET GATE: a too-big search is a shadow, not a stall.

plan_to_identity had _MAX_DEPTH but NO node budget: a handful of context-
matches-anywhere atoms (1-cell COLOUR_PERMs match wherever their colour sits)
make every frontier state offer every atom, and the branching product hung a
live-shaped run for minutes inside the frontier loops. The contract now:

  * a hard node-expansion cap (planner._MAX_NODES, a module constant) counted
    across BOTH frontiers; on exhaustion the planner returns None -- plans are
    speculation, and an unaffordable search is the same empty slot as a
    missing operator, never a stall;
  * per-atom applicability is memoized per state-key within one call (the
    anchor scans inside apply_effect run at most once per (atom, state) pair),
    so the capped search is cheap as well as bounded;
  * small solvable searches never feel the cap: identical plans, same order.

Run pre-build: the _MAX_NODES probe failed and the explosion case hung.
"""
from __future__ import annotations

import os
import sys
import time  # noqa: F401  (kept: other tests in this file time politely)
from unittest import mock

import numpy as np
import pytest

from engines.egocentric import effects as _effects

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import effects as E
from engines.egocentric.fabric import KnowledgeFabric


def _P():
    try:
        from engines.egocentric.planner import (
            plan_to_identity,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.planner missing (%s)" % e)
    from engines.egocentric import planner as P
    return P


def _recolour_gamma(tmp_path, name: str, pairs) -> E.Gamma:
    """One 1-cell recolour atom per (src, dst) pair. Each atom is a typed
    COLOUR_PERM whose 1x1 context matches ANYWHERE its colour appears -- the
    context-matches-anywhere shape that exploded live."""
    g = E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))
    for src, dst in pairs:
        atom = E.learn_effect(np.array([[src]]), 6, np.array([[dst]]))
        assert atom.get("ttype") == "COLOUR_PERM", "fixture atom must be typed"
        g.add(atom, game="boom", level=1)
    return g


class TestTheNodeBudget:

    def test_the_budget_is_a_module_constant(self):
        P = _P()
        n = getattr(P, "_MAX_NODES", None)
        assert isinstance(n, int) and n > 0, (
            "planner._MAX_NODES missing -- the search has no node budget and can stall")

    def test_exploding_branching_returns_none_within_the_cap(self, tmp_path):
        """A 3x3 WORKSPACE over colours {1..4} and 10 recolour atoms branch the
        forward frontier ~10 ways per node with an all-9s REFERENCE no atom can
        reach. Verified UNCAPPED (pre-fix): this exact search runs away past a
        60s kill. Capped, it must come back None in seconds -- a shadow, not a
        stall. (Bound 8s: the cap itself costs ~4s of honest expansion on this
        Gamma; anything near a minute is the old hang.)"""
        P = _P()
        pairs = [(s, d) for s in (1, 2, 3, 4) for d in (1, 2, 3, 4)
                 if s != d and (s, d) not in ((2, 1), (4, 3))]
        g = _recolour_gamma(tmp_path, "boom", pairs)
        ws = np.array([[1, 2, 3],
                       [4, 1, 2],
                       [3, 4, 1]])
        ref = np.full((3, 3), 9)                          # colour 9: unreachable
        # No wall-clock bound: seconds change meaning with box load (the canon's
        # no-threshold-in-wall-clock rule, caught flaking at 100% CPU under the
        # live swarm, 2026-08-20). The budget's own unit is the bound: count the
        # applications the search actually performs and assert the cap held.
        calls = {"n": 0}
        real_apply = _effects.apply_effect
        def counting_apply(atom, before):
            calls["n"] += 1
            return real_apply(atom, before)
        with mock.patch.object(_effects, "apply_effect", counting_apply), \
             mock.patch.object(P, "apply_effect", counting_apply, create=True):
            out = P.plan_to_identity(ws, ref, g, game="boom", level=1,
                                     budget=1000, cost_per_action=1)
        assert out is None, "an exhausted budget is an empty slot, never a guess"
        assert calls["n"] <= 25_000, (
            "the node budget did not bound the search: %d applications for an "
            "engineered branching explosion (uncapped runs past 60s; the capped "
            "search performs a bounded count regardless of box load)" % calls["n"])

    def test_small_solvable_case_still_solves_identically(self, tmp_path):
        """The exact pre-budget plan: 3 -> 4 -> 5 via two typed increments, the
        same two steps in the same order. The cap must never touch a small search."""
        P = _P()
        g = E.Gamma(KnowledgeFabric(str(tmp_path / "small"), agent_id="a", kin_key="v4"))
        ids = []
        for v in (3, 4):
            b = np.zeros((5, 5), dtype=int)
            b[2, 2] = v
            a = b.copy()
            a[2, 2] = v + 1
            ids.append(g.add(E.learn_effect(b, 6, a), game="g1", level=1))
        ws = np.zeros((5, 5), dtype=int)
        ws[2, 2] = 3
        ref = np.zeros((5, 5), dtype=int)
        ref[2, 2] = 5
        out = P.plan_to_identity(ws, ref, g, game="g1", level=1,
                                 budget=100, cost_per_action=1)
        assert out == {"steps": ids, "feasible": True}, (
            "the budget changed a small solvable search: %r" % (out,))

    def test_already_identity_is_untouched(self, tmp_path):
        P = _P()
        g = _recolour_gamma(tmp_path, "idty", pairs=((1, 2), (2, 3), (3, 4)))
        ws = np.array([[1, 2], [3, 4]])
        out = P.plan_to_identity(ws, ws.copy(), g, game="boom", level=1,
                                 budget=10, cost_per_action=1)
        assert out == {"steps": [], "feasible": True}
