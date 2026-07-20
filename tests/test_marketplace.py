"""Tests for the marketplace: propose->vote->resolve priced by prediction error, Goodhart-guarded."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.marketplace import Marketplace, Hypothesis, informative_salience


def _before():
    g = np.zeros((4, 4), dtype=int); g[0, 0] = 1
    return g


def test_best_predictor_of_real_change_wins():
    before = _before()
    actual = before.copy(); actual[2, 2] = 5           # a real change happened at (2,2)
    right = Hypothesis("right", lambda b: (lambda a: (a.__setitem__((2, 2), 5), a)[1])(b.copy()))
    nochange = Hypothesis("nochange", lambda b: b.copy())
    res = Marketplace().resolve(before, actual, [right, nochange])
    assert res.winner == "right" and res.drove
    assert res.scores["right"] > res.scores["nochange"]


def test_goodhart_guard_trivial_nochange_earns_zero_on_change():
    # a hypothesis that games "low pixel error" by predicting NOTHING changes gets ZERO salience when change occurred.
    before = _before()
    actual = before.copy(); actual[3, 3] = 7
    nochange = Hypothesis("nochange", lambda b: b.copy())
    res = Marketplace().resolve(before, actual, [nochange])
    assert res.scores["nochange"] == 0.0               # cannot win by saying nothing
    assert not res.drove                               # no confident driver -> explore


def test_hallucinated_change_is_penalised():
    before = _before()
    actual = before.copy(); actual[1, 1] = 3           # only (1,1) really changed
    honest = Hypothesis("honest", lambda b: (lambda a: (a.__setitem__((1, 1), 3), a)[1])(b.copy()))
    # over-claimer: gets (1,1) right BUT also hallucinates change at (3,3)
    def over(b):
        a = b.copy(); a[1, 1] = 3; a[3, 3] = 9; return a
    overclaim = Hypothesis("overclaim", over)
    res = Marketplace().resolve(before, actual, [honest, overclaim])
    assert res.scores["honest"] > res.scores["overclaim"]
    assert res.winner == "honest"


def test_no_change_frame_low_stakes_scoring():
    before = _before()
    actual = before.copy()                             # nothing changed
    nochange = Hypothesis("nochange", lambda b: b.copy())
    res = Marketplace().resolve(before, actual, [nochange])
    assert res.scores["nochange"] == 1.0               # correctly predicted the static frame


def test_currency_is_pluggable_invariant_is_not():
    # SS7: only the currency binding changes; propose->vote->resolve stays fixed.
    before = _before(); actual = before.copy(); actual[2, 2] = 5
    calls = {"n": 0}
    def custom(b, p, a):
        calls["n"] += 1
        return float((p == a).mean())                  # a different (weaker) currency
    h = Hypothesis("h", lambda b: b.copy())
    Marketplace(currency=custom).resolve(before, actual, [h])
    assert calls["n"] == 1                              # the custom currency was used


def test_nothing_silent():
    before = _before(); actual = before.copy(); actual[2, 2] = 5
    m = Marketplace()
    m.resolve(before, actual, [Hypothesis("h", lambda b: b.copy())])
    assert any(e.startswith("VOTE") for e in m.log) and any(e.startswith("RESOLVE") for e in m.log)


def test_prediction_committed_before_outcome():
    # a hypothesis only sees BEFORE; it cannot read the actual (the III.10 guard, by construction of predict()).
    before = _before(); actual = before.copy(); actual[0, 3] = 4
    seen = {}
    def peeker(b):
        seen["shape"] = b.shape
        return b.copy()                                # can only use `before`
    Marketplace().resolve(before, actual, [Hypothesis("p", peeker)])
    assert seen["shape"] == before.shape
