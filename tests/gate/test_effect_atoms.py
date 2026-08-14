"""W1a: the EFFECT constructor — arity two over TIME, one priced atom, canonically keyed.

The piece that changes what level 1 mints. Receipts behind the spec: spatial two-place atoms
won 30 mints and moved zero levels (the standing warning); conjunctions are priced out
(arity {1:46}); routes explain no residual (a different memory channel, membrane-barred from
Gamma). The n=1 gate at the bottom is the acceptance test for the whole notation.
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


def _E():
    try:
        from engines.egocentric import effects  # noqa: F401 -- the import IS the availability probe
    except Exception as e:
        pytest.fail("engines.egocentric.effects missing (%s) -- W1a has not landed" % e)
    from engines.egocentric import effects as E
    return E


class TestTheConstructor:

    def test_learn_from_one_contact_event(self):
        """One synthetic event: context patch around a site; contact; the patch after.
        learn_effect() must return ONE atom whose transform maps before->after."""
        E = _E()
        before = np.zeros((5, 5), dtype=int)
        before[2, 2] = 3
        after = before.copy()
        after[2, 2] = 4
        atom = E.learn_effect(before, action=6, after=after)
        assert atom is not None
        assert atom["arity"] == 2 and atom["kind"] == "EFFECT"
        out = E.apply_effect(atom, before)
        assert out is not None and (out == after).all(), "the atom must REPRODUCE the event"

    def test_canonical_keying_is_translation_invariant(self):
        """Same mechanism, different position, SAME key -- the keying choice is the
        abstraction choice."""
        E = _E()
        b1 = np.zeros((7, 7), dtype=int)
        b1[1, 1] = 3
        a1 = b1.copy()
        a1[1, 1] = 4
        b2 = np.zeros((7, 7), dtype=int)
        b2[5, 4] = 3
        a2 = b2.copy()
        a2[5, 4] = 4
        k1 = E.learn_effect(b1, 6, a1)["key"]
        k2 = E.learn_effect(b2, 6, a2)["key"]
        assert k1 == k2, "same mechanism, two positions, two keys -- the letters wall rebuilt"

    def test_different_mechanisms_get_different_keys(self):
        E = _E()
        b = np.zeros((5, 5), dtype=int)
        b[2, 2] = 3
        a_recolour = b.copy()
        a_recolour[2, 2] = 4
        a_vanish = b.copy()
        a_vanish[2, 2] = 0
        k1 = E.learn_effect(b, 6, a_recolour)["key"]
        k2 = E.learn_effect(b, 6, a_vanish)["key"]
        assert k1 != k2

    def test_inert_contact_marks_inert_not_effect(self):
        E = _E()
        b = np.zeros((5, 5), dtype=int)
        b[2, 2] = 3
        atom = E.learn_effect(b, 6, b.copy())
        assert atom is None or atom.get("kind") == "INERT", (
            "a contact that changes nothing is INERT (ground-priced), never an EFFECT")


class TestTypedGamma:

    def _g(self, tmp_path):
        E = _E()
        return E.Gamma(KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4"))

    def test_atoms_store_typed_and_regime_tagged(self, tmp_path):
        E = _E()
        g = self._g(tmp_path)
        b = np.zeros((5, 5), dtype=int)
        b[2, 2] = 3
        a = b.copy()
        a[2, 2] = 4
        atom = E.learn_effect(b, 6, a)
        aid = g.add(atom, game="g1", level=1)
        recs = [r for r in g.fabric.query("collective", "atoms") if r["id"] == aid]
        assert recs and recs[0]["type"] == "structural"
        assert recs[0]["game"] == "g1" and recs[0]["level"] == 1

    def test_a_composite_is_keyed_and_reusable_as_an_atom(self, tmp_path):
        """THE ANTI-LETTERS RULE: compose() of two atom ids yields an id that get/apply/compose
        accept exactly like an atom id -- memoization above the leaves."""
        E = _E()
        g = self._g(tmp_path)
        b = np.zeros((5, 5), dtype=int)
        b[2, 2] = 3
        mid = b.copy()
        mid[2, 2] = 4
        end = mid.copy()
        end[2, 2] = 5
        a1 = g.add(E.learn_effect(b, 6, mid), game="g1", level=1)
        a2 = g.add(E.learn_effect(mid, 6, end), game="g1", level=1)
        c = g.compose([a1, a2], game="g1", level=1)
        assert c is not None and g.get(c) is not None
        out = g.apply(c, b)
        assert out is not None and (out == end).all(), "the composite must run as one unit"
        c2 = g.compose([c, a1], game="g1", level=1)
        assert c2 is not None, "composites must compose further"

    def test_falsified_entries_narrow_never_delete(self, tmp_path):
        E = _E()
        g = self._g(tmp_path)
        b = np.zeros((5, 5), dtype=int)
        b[2, 2] = 3
        a = b.copy()
        a[2, 2] = 4
        aid = g.add(E.learn_effect(b, 6, a), game="g1", level=1)
        g.narrow(aid, game="g1", level=2)
        assert g.get(aid) is not None, "narrowed, not deleted"
        assert not g.valid_in(aid, game="g1", level=2)
        assert g.valid_in(aid, game="g1", level=1)


class TestTheN1Gate:

    def test_the_effect_beats_the_route_on_one_example(self):
        """THE ACCEPTANCE GATE (synthetic, zero game contamination). One event, both encodings;
        the notation must price the EFFECT below the route at n = 1."""
        E = _E()
        before = np.zeros((6, 6), dtype=int)
        before[3, 3] = 3
        after = before.copy()
        after[3, 3] = 4
        route = [(1,), (1,), (6, 3, 3)]
        cost_route = E.encoding_cost_route(route)
        atom = E.learn_effect(before, 6, after)
        cost_effect = E.encoding_cost_atom(atom)
        assert cost_effect < cost_route, (
            "the route is cheaper than the transform at n=1 -- the pricing is the bug, and "
            "L1 will mint literals forever (fix the notation before any game sees it)")
