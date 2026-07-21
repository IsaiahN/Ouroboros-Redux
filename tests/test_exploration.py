"""Tests for the exploration drive (brick 10a): guarantee coverage early, converge late, never collapse."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.exploration import Explorer


def test_untried_action_gets_full_bonus():
    e = Explorer(novelty_weight=1.0)
    assert e.bonus("A") == 1.0 and e.bonus("Z") == 1.0     # everything unknown is maximally novel


def test_bonus_decays_with_visits():
    e = Explorer(novelty_weight=1.0)
    b0 = e.bonus("A")
    e.visit("A"); b1 = e.bonus("A")
    e.visit("A"); b2 = e.bonus("A")
    assert b0 > b1 > b2 > 0.0                              # decays monotonically, never to exactly zero (still reconsiderable)


def test_untried_outranks_a_converged_action():
    # THE ANTI-COLLAPSE PROPERTY: after one action is hammered, an untried one still outranks it on novelty.
    e = Explorer(novelty_weight=1.0)
    for _ in range(10):
        e.visit("A")
    assert e.bonus("B") > e.bonus("A")                     # B (untried) must still get pulled in


def test_coverage_rises_as_actions_are_tried():
    e = Explorer()
    acts = ["A", "B", "C"]
    assert e.coverage(acts) == 0.0
    e.visit("A"); e.visit("B")
    assert abs(e.coverage(acts) - 2 / 3) < 1e-9
    e.visit("C")
    assert e.coverage(acts) == 1.0


def test_nothing_silent():
    e = Explorer(); e.visit("A")
    assert any(s.startswith("VISIT") for s in e.log)
