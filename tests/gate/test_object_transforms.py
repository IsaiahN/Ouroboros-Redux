"""B8 falsifier: OBJECT-LEVEL TRANSFORM CLASSIFIER -- one coherent object in clutter.

The whole-bbox classifier (classify_transform) demands the ENTIRE changed-region bbox to
transform exactly; a mover in cluttered context never satisfies that (typed=3/585). B8 adds
classify_object_transform: segment the CHANGED region into connected components and name the
single-object mechanism -- mover TRANSLATE (a component vanishes at A, an identical-shaped one
appears at B, background restored), object RECOLOUR (same cells, injective remap), OBJ_APPEAR /
OBJ_VANISH (component present in exactly one frame). Params carry the component's NORMALIZED
shape signature (relative cell offsets, never absolute coordinates). learn_effect falls back to
the object path when whole-bbox classification is NONE; typed application fires at new absolute
positions; each new ttype round-trips through invert_transform / apply_inverse.
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
    if not hasattr(E, "classify_object_transform"):
        pytest.fail("effects.classify_object_transform missing -- B8 has not landed")
    return E


def _mover_case():
    """A 2-cell asymmetric mover with clutter INSIDE the changed-region bbox: the case the
    whole-bbox classifier can never name."""
    before = np.zeros((12, 12), dtype=int)
    before[5, 2], before[5, 3] = 3, 7                 # the mover
    before[5, 4] = 9                                  # clutter between source and destination
    before[2, 9] = 4                                  # far clutter
    after = before.copy()
    after[5, 2], after[5, 3] = 0, 0                   # background restored at the source
    after[5, 5], after[5, 6] = 3, 7                   # identical shape appears 3 right
    return before, after


class TestMoverTranslateInClutter:

    def test_whole_bbox_classifier_fails_first(self):
        """The premise: on the changed-region bbox patches the OLD classifier is NONE --
        without this the object path proves nothing."""
        E = _E()
        before, after = _mover_case()
        bpatch = before[5:6, 2:7]
        apatch = after[5:6, 2:7]
        assert (bpatch != apatch).any()
        t = E.classify_transform(bpatch, apatch)
        assert t["ttype"] == "NONE", "whole-bbox must FAIL here or B8 is untestable"

    def test_object_classifier_names_the_translate(self):
        E = _E()
        before, after = _mover_case()
        t = E.classify_object_transform(before, after)
        assert t["ttype"] == "TRANSLATE"
        assert t["params"]["dx"] == 0 and t["params"]["dy"] == 3
        assert t["params"]["fill"] == 0

    def test_shape_signature_is_relative_never_absolute(self):
        E = _E()
        before, after = _mover_case()
        t = E.classify_object_transform(before, after)
        shape = t["params"]["shape"]
        assert sorted(shape) == [[0, 0, 3], [0, 1, 7]], (
            "the shape is the component normalized to its own origin -- offsets, "
            "never board coordinates (the mover sat at row 5, col 2)")

    def test_learn_effect_types_the_atom_via_the_object_path(self):
        E = _E()
        before, after = _mover_case()
        atom = E.learn_effect(before, 6, after)
        assert atom["kind"] == "EFFECT"
        assert atom.get("ttype") == "TRANSLATE", "learn_effect must fall back to the object path"
        assert atom["params"]["dx"] == 0 and atom["params"]["dy"] == 3
        for f in ("key", "context", "transform", "changed", "action"):
            assert f in atom, "raw field %s must survive -- the raw path is the fallback" % f

    def test_typed_application_fires_at_a_new_absolute_position(self):
        E = _E()
        before, after = _mover_case()
        atom = E.learn_effect(before, 6, after)
        frame = np.zeros((12, 12), dtype=int)
        frame[8, 1], frame[8, 2] = 3, 7               # same object, new absolute position
        frame[8, 3] = 4                               # NEW debris: breaks the literal window
        frame[0, 0] = 5

        raw = {k: v for k, v in atom.items() if k not in ("ttype", "params")}
        assert E.apply_effect(raw, frame) is None, (
            "the raw exact-context path must FAIL here or the test proves nothing")

        out = E.apply_effect(atom, frame)
        assert out is not None, "the typed object atom must fire in the never-seen context"
        assert out[8, 4] == 3 and out[8, 5] == 7, "object translated by (0,+3)"
        assert out[8, 1] == 0 and out[8, 2] == 0, "source cells vacated to fill"
        assert out[8, 3] == 4 and out[0, 0] == 5, "clutter untouched"

    def test_translate_round_trip(self):
        E = _E()
        before, after = _mover_case()
        atom = E.learn_effect(before, 6, after)
        forward = E.apply_effect(atom, before)
        assert forward is not None and (forward == after).all()
        back = E.apply_inverse(atom, forward)
        assert back is not None and (back == before).all(), "TRANSLATE object move inverts"


class TestObjAppearVanish:

    def _appear_case(self):
        before = np.zeros((9, 9), dtype=int)
        before[0, 0], before[7, 7] = 6, 2             # clutter: NOT a clean whole-bbox story
        after = before.copy()
        after[3, 3], after[3, 4], after[4, 3] = 4, 8, 4   # a multi-colour object materializes
        return before, after

    def test_appear_classifies_with_normalized_shape(self):
        E = _E()
        before, after = self._appear_case()
        assert E.classify_transform(before[3:5, 3:5], after[3:5, 3:5])["ttype"] == "NONE"
        t = E.classify_object_transform(before, after)
        assert t["ttype"] == "OBJ_APPEAR"
        assert t["params"]["fill"] == 0
        assert sorted(t["params"]["shape"]) == [[0, 0, 4], [0, 1, 8], [1, 0, 4]]

    def test_vanish_classifies_and_is_appear_reversed(self):
        E = _E()
        before, after = self._appear_case()
        t = E.classify_object_transform(after, before)     # the same event, played backward
        assert t["ttype"] == "OBJ_VANISH"
        assert t["params"]["fill"] == 0
        assert sorted(t["params"]["shape"]) == [[0, 0, 4], [0, 1, 8], [1, 0, 4]]

    def test_appear_and_vanish_are_mutual_inverses(self):
        E = _E()
        params = {"shape": [[0, 0, 4], [0, 1, 8], [1, 0, 4]], "fill": 0}
        inv = E.invert_transform("OBJ_APPEAR", params)
        assert inv is not None and inv[0] == "OBJ_VANISH" and inv[1] == params
        inv2 = E.invert_transform(inv[0], inv[1])
        assert inv2 is not None and inv2[0] == "OBJ_APPEAR" and inv2[1] == params

    def test_appear_round_trip_through_apply_inverse(self):
        E = _E()
        before, after = self._appear_case()
        atom = E.learn_effect(before, 6, after)
        assert atom.get("ttype") == "OBJ_APPEAR"
        forward = E.apply_effect(atom, before)
        assert forward is not None
        back = E.apply_inverse(atom, forward)
        assert back is not None and (back == before).all()

    def test_vanish_round_trip_on_a_cluttered_board(self):
        """Board of 7s, the only fill-coloured ground is where the object vanished -- the
        inverse APPEAR must restore it exactly there."""
        E = _E()
        before = np.full((9, 9), 7, dtype=int)
        before[4, 4], before[4, 5] = 1, 2
        after = np.full((9, 9), 7, dtype=int)
        after[4, 4], after[4, 5] = 0, 0
        atom = E.learn_effect(before, 6, after)
        assert atom.get("ttype") == "OBJ_VANISH"
        assert atom["params"]["fill"] == 0
        forward = E.apply_effect(atom, before)
        assert forward is not None and (forward == after).all()
        back = E.apply_inverse(atom, forward)
        assert back is not None and (back == before).all()


class TestObjectRecolour:

    def _recolour_case(self):
        """L-shaped object 1->5 with an UNCHANGED colour-1 clutter cell inside the bbox:
        the whole-bbox COLOUR_PERM sees one colour with two fates and gives up."""
        before = np.zeros((8, 8), dtype=int)
        before[2, 2], before[3, 2], before[3, 3] = 1, 1, 1   # the object
        before[2, 3] = 1                                     # clutter inside the bbox
        after = before.copy()
        after[2, 2], after[3, 2], after[3, 3] = 5, 5, 5      # object recoloured; clutter not
        return before, after

    def test_whole_bbox_fails_then_object_path_names_the_perm(self):
        E = _E()
        before, after = self._recolour_case()
        assert E.classify_transform(before[2:4, 2:4], after[2:4, 2:4])["ttype"] == "NONE", (
            "one colour, two fates across the bbox -- the old classifier must fail first")
        t = E.classify_object_transform(before, after)
        assert t["ttype"] == "COLOUR_PERM"
        assert t["params"]["mapping"] == [[1, 5]]
        assert sorted(t["params"]["shape"]) == [[0, 0, 1], [1, 0, 1], [1, 1, 1]]

    def test_recolour_round_trip(self):
        E = _E()
        before, after = self._recolour_case()
        atom = E.learn_effect(before, 6, after)
        assert atom.get("ttype") == "COLOUR_PERM"
        forward = E.apply_effect(atom, before)
        assert forward is not None and (forward == after).all(), (
            "the shape-bound perm must touch ONLY the object cells, never the clutter")
        back = E.apply_inverse(atom, forward)
        assert back is not None and (back == before).all(), "injective recolour inverts"


class TestNoFalsePositives:

    def test_unstructured_mess_is_still_none(self):
        E = _E()
        b = np.array([[1, 2], [3, 4]])
        a = np.array([[4, 1], [2, 2]])
        assert E.classify_object_transform(b, a)["ttype"] == "NONE"
        atom = E.learn_effect(b, 6, a)
        assert "ttype" not in atom, "raw storage must remain the honest fallback"

    def test_two_unrelated_changes_are_not_one_object(self):
        E = _E()
        before = np.zeros((8, 8), dtype=int)
        before[1, 1], before[6, 6] = 3, 4
        after = np.zeros((8, 8), dtype=int)
        after[1, 1], after[6, 6] = 8, 9               # two separate recolours, no shared story
        assert E.classify_object_transform(before, after)["ttype"] == "NONE"
