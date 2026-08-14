"""W2b: the residual router — every settled residual lands in exactly one of four bins.

TRANSFERRED confirms; NOVEL extends perception (the import queue); BROKEN·rebinding re-fits
the binder; BROKEN·mechanism owes the mint one atom. The router is the loop's boundary diff:
where to look, decided by what kind of surprise arrived.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _R():
    try:
        from engines.egocentric.router import (
            ResidualRouter,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.router missing (%s) -- W2b has not landed" % e)
    from engines.egocentric.router import ResidualRouter as R
    return R


def _s(residual, bet=True, from_known_atom=False, binding_stale=False):
    return {"residual": float(residual), "bet": bet,
            "from_known_atom": from_known_atom, "binding_stale": binding_stale}


class TestTheFourBins:

    def test_zero_residual_transfers(self):
        r = _R()()
        assert r.route("BODY", _s(0.0)) == "TRANSFERRED"

    def test_known_atom_wrong_owes_a_mint(self):
        r = _R()()
        out = r.route("WORKSPACE", _s(3.0, from_known_atom=True))
        assert out == "BROKEN_MECHANISM"
        assert len(r.mint_queue) == 1, "a mint is owed and the queue must show the debt"

    def test_stale_binding_routes_to_refit(self):
        r = _R()()
        out = r.route("REFERENCE", _s(2.0, binding_stale=True))
        assert out == "BROKEN_REBINDING"
        assert len(r.refit_queue) == 1

    def test_unexplained_surprise_is_novel(self):
        r = _R()()
        out = r.route("WORKSPACE", _s(4.0, from_known_atom=False))
        assert out == "NOVEL"
        assert len(r.import_queue) == 1, (
            "NOVEL extends perception -- the import queue is the endogenous build agenda")

    def test_no_bet_routes_nowhere(self):
        r = _R()()
        assert r.route("BODY", _s(1.0, bet=False)) is None
        assert not r.mint_queue and not r.import_queue and not r.refit_queue

    def test_queues_carry_the_evidence(self):
        r = _R()()
        r.route("WORKSPACE", _s(3.0, from_known_atom=True))
        item = r.mint_queue[0]
        assert item["slot"] == "WORKSPACE" and item["residual"] == 3.0

    def test_queue_ordering_is_by_residual_mass(self):
        """The import queue ranks by unexplained residual -- biggest debt first."""
        r = _R()()
        r.route("WORKSPACE", _s(1.0))
        r.route("WORKSPACE", _s(5.0))
        r.route("BODY", _s(3.0))
        masses = [i["residual"] for i in r.import_queue_ranked()]
        assert masses == sorted(masses, reverse=True)
