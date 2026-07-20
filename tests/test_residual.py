"""Tests for the residual: the sense organ, the brake invariant, and the MDL mint test."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.residual import sense, Residual, ResidualBus, mdl_mint, TautologyError
from newhorse.perception import DownsampleError


def test_sense_finds_unpredicted_cells_full_res():
    pred = np.zeros((4, 4), dtype=int)
    actual = np.zeros((4, 4), dtype=int)
    actual[1, 1] = 5; actual[2, 3] = 7           # reality diverged in 2 cells the grammar predicted as 0
    r = sense(pred, actual)
    assert r.unexplained == frozenset({(1, 1), (2, 3)})
    assert r.bits == 2.0 and not r.is_empty


def test_sense_empty_when_prediction_perfect():
    g = np.arange(9).reshape(3, 3)
    assert sense(g, g.copy()).is_empty


def test_sense_refuses_downsampled_shapes():
    try:
        sense(np.zeros((8, 8), dtype=int), np.zeros((4, 8), dtype=int))
        assert False
    except DownsampleError:
        pass


def test_brake_invariant_pe_integral_is_monotone():
    # THE BRAKE (SS11): the time-integral of prediction error can only GROW; no method reduces it.
    bus = ResidualBus()
    bus.observe(Residual(frozenset({(0, 0)}), 1.0))
    i1 = bus.pe_integral()
    bus.observe(Residual(frozenset({(1, 1), (1, 2)}), 2.0))
    i2 = bus.pe_integral()
    assert i2 == i1 + 2.0 > i1
    # there is NO suppress()/reset() -- a drive cannot zero the record
    assert not hasattr(bus, "suppress") and not hasattr(bus, "reset")


def test_explain_reduces_aim_but_not_the_record():
    # explaining surprise reduces the OUTSTANDING aim, but the integral (we WERE surprised) is preserved.
    bus = ResidualBus()
    bus.observe(Residual(frozenset({(0, 0), (0, 1), (0, 2)}), 3.0))
    assert bus.outstanding() == 3.0 and bus.pe_integral() == 3.0
    bus.explain(2.0)
    assert bus.outstanding() == 1.0                 # aim shrinks as understanding grows
    assert bus.pe_integral() == 3.0                 # the record NEVER shrinks (brake invariant)


def test_explain_cannot_go_negative():
    bus = ResidualBus()
    bus.observe(Residual(frozenset({(0, 0)}), 1.0))
    bus.explain(100.0)
    assert bus.outstanding() == 0.0 and bus.pe_integral() == 1.0


def test_mdl_mint_accepts_when_predicate_is_cheaper():
    # ||phi|| + ||residual|phi|| < ||residual enumerated||  -> MINT
    assert mdl_mint(phi_cost_bits=2, residual_given_phi_bits=1, residual_enumerated_bits=10, phi_reads_after=False)
    # not cheaper -> a coincidence with a name on it -> do NOT mint
    assert not mdl_mint(phi_cost_bits=8, residual_given_phi_bits=5, residual_enumerated_bits=10, phi_reads_after=False)


def test_mdl_mint_refuses_after_state_predicate_tautology():
    # a predicate that reads the OUTCOME compresses perfectly and predicts nothing -> refused (SS10/III.10)
    try:
        mdl_mint(1, 0, 10, phi_reads_after=True)
        assert False, "should have raised"
    except TautologyError:
        pass


def test_nothing_silent():
    bus = ResidualBus()
    bus.observe(Residual(frozenset({(0, 0)}), 1.0))
    bus.explain(1.0)
    assert any(e.startswith("OBSERVE") for e in bus.log) and any(e.startswith("EXPLAIN") for e in bus.log)
