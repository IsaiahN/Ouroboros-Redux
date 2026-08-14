"""CK-1a falsifier: TYPED PARAMETERIZED TRANSFORMS on EFFECT atoms.

(1) classify_transform names each mechanism exactly (TRANSLATE/ROTATE/REFLECT/SCALE/
COLOUR_PERM) from the changed-bbox patches alone; (2) a typed TRANSLATE atom learned at
one absolute position fires at a DIFFERENT absolute position where the raw exact-context
fallback returns None -- the open variable bound to a role; (3) an unstructured diff is
NONE and the atom carries no ttype; (4) the raw path is untouched (raw fields always
present; the rest of the gate suite stays green).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _E():
    from engines.egocentric import effects as E
    if not hasattr(E, "classify_transform"):
        pytest.fail("effects.classify_transform missing -- CK-1a has not landed")
    return E


class TestClassification:

    def test_translate(self):
        E = _E()
        ctx = [[3, 7, 0, 0, 0]]
        out = [[0, 0, 0, 3, 7]]                     # asymmetric 2-cell object, right by 3
        t = E.classify_transform(ctx, out)
        assert t["ttype"] == "TRANSLATE"
        assert t["params"]["dx"] == 0 and t["params"]["dy"] == 3
        assert t["params"]["fill"] == 0

    def test_rotate(self):
        E = _E()
        b = np.array([[5, 0, 0], [5, 0, 0], [5, 5, 0]])
        t = E.classify_transform(b, np.rot90(b, 1))
        assert t["ttype"] == "ROTATE" and t["params"]["k"] == 1

    def test_reflect_both_axes(self):
        E = _E()
        b = np.array([[1, 2, 0], [0, 1, 1]])
        t = E.classify_transform(b, np.fliplr(b))
        assert t["ttype"] == "REFLECT" and t["params"]["axis"] == "v"
        b2 = np.array([[1, 2], [0, 1], [0, 0]])
        t2 = E.classify_transform(b2, np.flipud(b2))
        assert t2["ttype"] == "REFLECT" and t2["params"]["axis"] == "h"

    def test_scale_up_and_down(self):
        E = _E()
        b = np.array([[1, 2], [3, 4]])
        big = np.kron(b, np.ones((2, 3), dtype=int))
        t = E.classify_transform(b, big)
        assert t["ttype"] == "SCALE"
        assert (t["params"]["fx"], t["params"]["fy"], t["params"]["mode"]) == (2, 3, "up")
        t2 = E.classify_transform(big, b)
        assert t2["ttype"] == "SCALE"
        assert (t2["params"]["fx"], t2["params"]["fy"], t2["params"]["mode"]) == (2, 3, "down")

    def test_colour_perm(self):
        E = _E()
        b = np.array([[1, 2], [2, 1]])
        a = np.array([[5, 3], [3, 5]])              # 1->5, 2->3: consistent, injective
        t = E.classify_transform(b, a)
        assert t["ttype"] == "COLOUR_PERM"
        assert t["params"]["mapping"] == [[1, 5], [2, 3]]

    def test_colour_merge_is_not_a_perm(self):
        t = _E().classify_transform([[1, 2]], [[3, 3]])   # two colours collapse into one
        assert t["ttype"] == "NONE"

    def test_unstructured_diff_is_none(self):
        E = _E()
        t = E.classify_transform([[1, 2], [3, 4]], [[4, 1], [2, 2]])
        assert t["ttype"] == "NONE" and t["params"] == {}


class TestLearnedAtomsCarryTypes:

    def test_typed_translate_atom_keeps_raw_fields(self):
        E = _E()
        before = np.zeros((10, 10), dtype=int)
        before[2, 2], before[2, 3] = 3, 7
        after = np.zeros((10, 10), dtype=int)
        after[2, 5], after[2, 6] = 3, 7             # the object moved right by 3
        atom = E.learn_effect(before, 6, after)
        assert atom["kind"] == "EFFECT"
        assert atom.get("ttype") == "TRANSLATE"
        assert atom["params"] == {"dx": 0, "dy": 3, "fill": 0}
        for f in ("key", "context", "transform", "changed", "action"):
            assert f in atom, "raw field %s must survive -- the raw path is the fallback" % f
        out = E.apply_effect(atom, before)
        assert out is not None and (out == after).all(), "the atom must REPRODUCE the event"

    def test_unstructured_atom_carries_no_ttype(self):
        E = _E()
        b = np.array([[1, 2], [3, 4]])
        a = np.array([[4, 1], [2, 2]])
        atom = E.learn_effect(b, 6, a)
        assert atom["kind"] == "EFFECT"
        assert "ttype" not in atom and "params" not in atom


class TestNovelContextApplication:

    def test_typed_translate_fires_where_raw_cannot(self):
        """Learned at (2,2) with a clear corridor; the novel frame holds the object at
        (6,1) with debris at (6,3) inside the corridor. The raw exact-context scan finds
        no window; the typed op binds the object wherever it sits and moves it."""
        E = _E()
        before = np.zeros((10, 10), dtype=int)
        before[2, 2], before[2, 3] = 3, 7
        after = np.zeros((10, 10), dtype=int)
        after[2, 5], after[2, 6] = 3, 7
        atom = E.learn_effect(before, 6, after)
        assert atom.get("ttype") == "TRANSLATE"

        frame = np.zeros((10, 10), dtype=int)
        frame[6, 1], frame[6, 2] = 3, 7             # same object, different absolute position
        frame[6, 3] = 9                             # debris breaks the literal context window

        raw = {k: v for k, v in atom.items() if k not in ("ttype", "params")}
        assert E.apply_effect(raw, frame) is None, (
            "the raw exact-context path must FAIL here or the test proves nothing")

        out = E.apply_effect(atom, frame)
        assert out is not None, "the typed atom must fire in the never-seen context"
        assert out[6, 4] == 3 and out[6, 5] == 7, "object translated by (0,+3)"
        assert out[6, 1] == 0 and out[6, 2] == 0, "source cells vacated to fill"
        assert out[6, 3] == 9, "debris untouched"

    def test_typed_apply_still_reproduces_via_fallback_when_op_blocked(self):
        """If the typed op cannot fire (destination blocked everywhere) the exact-context
        fallback still runs -- nothing regresses."""
        E = _E()
        before = np.zeros((8, 8), dtype=int)
        before[1, 1], before[1, 2] = 3, 7
        after = np.zeros((8, 8), dtype=int)
        after[1, 4], after[1, 5] = 3, 7
        atom = E.learn_effect(before, 6, after)
        assert atom.get("ttype") == "TRANSLATE"
        # A frame where the literal learned window DOES match: typed or raw, it must apply.
        frame = np.zeros((8, 8), dtype=int)
        frame[5, 2], frame[5, 3] = 3, 7
        out = E.apply_effect(atom, frame)
        assert out is not None
        assert out[5, 5] == 3 and out[5, 6] == 7 and out[5, 2] == 0 and out[5, 3] == 0
