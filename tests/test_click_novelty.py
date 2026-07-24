"""Novelty-gated click prober. Beat I coverage diagnostic found ft09 stuck: 9 distinct board states over 80 clicks,
one state revisited 60x. Cause: the prober rewarded ANY change (`changed`), so a cell that merely TOGGLES between two
states scored "productive" every click and the budget was burned oscillating. Fix: prefer clicks that reach a board
state never seen before (`novel`); a toggler plateaus after it has shown its two states and must yield to a target
still discovering territory. Same insight as the EffectAffordance undo-fix, applied to WHERE-to-click. General; names
no game. (Honest scope: this is coverage hygiene -- it does NOT by itself solve a structured puzzle whose win needs a
novel predicate; it stops wasting the budget re-toggling one cell.)"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.click import ClickProber


def _s(marker):
    """A distinct 4x4 board keyed by an integer marker."""
    g = np.zeros((4, 4), dtype=int)
    g[0, 0] = marker
    return g


def test_prefers_novel_reaching_target_over_a_toggler():
    A, B = (1, 1), (2, 2)                    # A toggles between two states; B keeps reaching fresh states
    p = ClickProber([A, B])
    # A: S1,S2 then oscillates S1<->S2 (only 2 distinct states)
    for prev, new in [(_s(0), _s(1)), (_s(1), _s(2)), (_s(2), _s(1)), (_s(1), _s(2)), (_s(2), _s(1))]:
        p._last = A
        p.observe(prev, new)
    # B: reaches three brand-new states
    for prev, new in [(_s(2), _s(10)), (_s(10), _s(11)), (_s(11), _s(12))]:
        p._last = B
        p.observe(prev, new)
    assert p.novel[A] == 2                    # A only ever showed 2 novel states, then just toggled
    assert p.novel[B] == 3                    # B kept finding new territory
    assert p.changed[A] > p.changed[B]        # A "changed" more often (the toggle trap the OLD prober fell for)
    assert p.choose() == B                    # novelty-gated: pick the explorer, not the toggler


def test_falls_back_when_nothing_novel():
    A, B = (0, 0), (3, 3)
    p = ClickProber([A, B])
    # every click is a no-op (board never changes) -> no novelty, no change -> least-tried, no crash
    p._last = A; p.observe(_s(5), _s(5))
    pick = p.choose()
    assert pick in (A, B)


def test_untried_first_then_novelty():
    A, B = (1, 1), (2, 2)
    p = ClickProber([A, B])
    # A tried once and reached a novel state; B still untried -> choose() must sweep B first
    p._last = A; p.observe(_s(0), _s(1))
    assert p.choose() == B                    # untried target sampled before exploiting novelty
