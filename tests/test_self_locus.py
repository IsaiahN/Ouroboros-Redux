"""Tests for self-locus (brick 10b): name the controllable by ACTION-CONTINGENT motion, Goodhart-guarded."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.self_locus import SelfLocus
from newhorse.perception import Object


def _obj(cells, colour):
    return Object(cells=frozenset(cells), colours=frozenset({colour}))


def test_contingent_object_is_named_self():
    # colour 4 moves DOWN under A1 and not under A2 -> its motion depends on the action -> it is self.
    loc = SelfLocus(min_events=2)
    # A1: the colour-4 dot moves from row0 to row1; colour-9 wall stays put
    loc.observe("A1", [_obj([(0, 0)], 4), _obj([(3, 3), (3, 4)], 9)],
                       [_obj([(1, 0)], 4), _obj([(3, 3), (3, 4)], 9)])
    # A2: the colour-4 dot does NOT move; wall stays put
    loc.observe("A2", [_obj([(1, 0)], 4), _obj([(3, 3), (3, 4)], 9)],
                       [_obj([(1, 0)], 4), _obj([(3, 3), (3, 4)], 9)])
    assert loc.controllable_colour() == 4                  # 4 is contingent on the action; 9 never moves


def test_autonomous_mover_is_not_self_goodhart_guard():
    # colour 7 moves the SAME amount under EVERY action -> not contingent on my choice -> NOT self
    # (this is the Goodhart trap: it correlates with 'a step happened' but not with WHICH action).
    loc = SelfLocus(min_events=2)
    loc.observe("A1", [_obj([(0, 0)], 7)], [_obj([(1, 0)], 7)])   # moved down by 1
    loc.observe("A2", [_obj([(1, 0)], 7)], [_obj([(2, 0)], 7)])   # moved down by 1 again -- regardless of action
    assert loc.controllable_colour() is None               # identical motion under all actions -> autonomous, not self


def test_static_object_is_not_self():
    loc = SelfLocus(min_events=2)
    loc.observe("A1", [_obj([(2, 2)], 5)], [_obj([(2, 2)], 5)])
    loc.observe("A2", [_obj([(2, 2)], 5)], [_obj([(2, 2)], 5)])
    assert loc.controllable_colour() is None               # never moves -> not the controllable


def test_needs_min_events_before_trusting():
    loc = SelfLocus(min_events=3)
    loc.observe("A1", [_obj([(0, 0)], 4)], [_obj([(1, 0)], 4)])   # only 1 event
    assert loc.controllable_colour() is None               # not enough evidence yet -> cold start (caller falls back)


def test_pick_returns_the_contingent_object():
    loc = SelfLocus(min_events=2)
    loc.observe("A1", [_obj([(0, 0)], 4), _obj([(5, 5)], 9)],
                       [_obj([(1, 0)], 4), _obj([(5, 5)], 9)])
    loc.observe("A2", [_obj([(1, 0)], 4), _obj([(5, 5)], 9)],
                       [_obj([(1, 0)], 4), _obj([(5, 5)], 9)])
    objs = [_obj([(1, 0)], 4), _obj([(5, 5)], 9)]
    picked = loc.pick(objs)
    assert picked is not None and 4 in picked.colours       # picks the colour-4 body, not the static wall


def test_nothing_silent():
    loc = SelfLocus()
    loc.observe("A1", [_obj([(0, 0)], 4)], [_obj([(1, 0)], 4)])
    assert any(s.startswith("LOCUS") for s in loc.log)
