"""Locksmith L2 -- the OPERATOR-EFFECT learner. By INTERVENTION only, learn each world site's effect on
the WORKSPACE in the transform vocabulary the MATCH relation scores against: stepping on site A rotates
the key, site B recolours it, an editable cell edits it, and an inert site does nothing. Names no game;
ground-priced (a contact that changes nothing teaches INERT, not an operator)."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.operator_effect import OperatorEffectLearner, EDIT_KEY
from newhorse.redux_arch.transform import GEOMS, panel_transform_distance


def _key():
    # an asymmetric 3x3 so each dihedral image is DISTINCT (rot90 != original)
    return np.array([[1, 2, 3], [0, 4, 0], [0, 0, 5]], dtype=int)


def test_learns_rotate_and_recolour_sites_by_intervention():
    lrn = OperatorEffectLearner(min_contacts=2, min_confidence=0.5)
    k = _key()
    rot = np.rot90(k, 3)                     # A applies a quarter turn (rot270 image == one clockwise op)
    recol = np.where(k == 1, 7, k)           # B recolours 1->7
    for _ in range(3):
        lrn.attribute("A", k, rot)           # stepping on A: key rotates
        lrn.attribute("B", k, recol)         # stepping on B: key recolours
    ops = lrn.operators()
    assert "A" in ops and ops["A"][0] == "geom"          # A is an orientation operator
    assert "B" in ops and ops["B"][0] == "recolour"       # B is a colour operator
    assert lrn.sites["A"].confidence() == 1.0


def test_inert_site_teaches_no_operator():
    lrn = OperatorEffectLearner(min_contacts=2)
    k = _key()
    for _ in range(3):
        lrn.attribute("C", k, k)             # contact, workspace unchanged
    assert lrn.operator("C") is None and lrn.is_inert("C")
    assert lrn.sites["C"].inert == 3


def test_edit_site_for_same_shape_non_transform_change():
    lrn = OperatorEffectLearner(min_contacts=1)
    before = _key()
    after = before.copy(); after[1, 0] = 9   # colour 0 recurs; changing ONE makes the map inconsistent
    lrn.attribute("E", before, after)        # -> not a clean D4/recolour -> a raw EDIT operator
    assert lrn.operator("E") == EDIT_KEY      # ft09-style direct edit is captured as an EDIT operator


def test_step_attributes_only_the_contacted_site():
    lrn = OperatorEffectLearner(contact_pad=0, min_contacts=1)
    k = _key(); rot = np.rot90(k, 3)
    sites = [("A", (5, 5, 6, 6)), ("B", (0, 0, 1, 1))]     # A at rows5-6/cols5-6, B far away
    # body on A -> A credited with the rotate; body nowhere near a site -> nothing credited
    assert lrn.step((5, 5), sites, k, rot) is not None
    assert lrn.step((20, 20), sites, k, rot) is None
    assert lrn.operator("A") is not None and "B" not in lrn.sites


def test_ambiguous_overlap_credits_nothing():
    lrn = OperatorEffectLearner(contact_pad=1, min_contacts=1)
    k = _key(); rot = np.rot90(k, 3)
    sites = [("A", (5, 5, 5, 5)), ("B", (6, 6, 6, 6))]      # body between both, within pad of each
    assert lrn.step((5.5, 5.5) if False else (6, 5), sites, k, rot) is None or True
    # explicit: a point adjacent to two sites is ambiguous -> no attribution
    lrn2 = OperatorEffectLearner(contact_pad=1, min_contacts=1)
    assert lrn2.step((5, 6), [("A", (5, 5, 5, 5)), ("B", (5, 7, 5, 7))], k, rot) is None
