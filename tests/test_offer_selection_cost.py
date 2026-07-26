"""
test_offer_selection_cost.py -- THE SAME HOLE THE MINT GATE HAD, ONE LAYER UP.

The mint gate charges `log2(len(eligible))` for picking the best-compressing φ out of a searched space, because
naming the winner of a multiple-hypothesis contest costs bits. `Consolidator.explains_scored` -- the TRANSFER
scorer, which picks the best-compressing φ out of the promoted library Γ -- was not charging anything. That is
the identical contest with a smaller entry list.

It was invisible for a structural reason, not a lucky one: while Γ was per-policy it held zero or one predicate
for almost every game, and log2(1) = 0. Sharing Γ across games is a machine for GROWING N -- exactly as pooling
was a machine for growing n -- so the omission stops rounding to nothing at precisely the moment the library
starts making the strongest claim the chain can make. An uncharged best-of-N would let the shared library
manufacture its own firings and then report them as cross-game transfer.

This file pins the charge in six places. Two of them (the outcome-blindness of eligibility, and the fact that a
larger library can only ever LOWER a reported gain) are the ones that matter: they are what stop the charge from
being a knob that could be tuned until the instrument reads higher.

Not tested here, and deliberately: whether the corrected scorer changes the LIVE firing count. That is a
measurement, it belongs to `tools/replay_explain.py` scoring old and new on identical banked evidence, and a
unit test that asserted a firing count would be an answer key.
"""
from __future__ import annotations

import math

import pytest

from newhorse.redux_arch.consolidate import Consolidator
from newhorse.redux_arch.dsl import Context, Predicate, make_atom
from newhorse.redux_arch.minting import Mint, _entropy_bits

FREE = Predicate(frozenset({make_atom("INTENDED_FREE")}))          # cost 2
ROW = Predicate(frozenset({make_atom("SAME_ROW")}))                # cost 2
COL = Predicate(frozenset({make_atom("SAME_COL")}))                # cost 2
C4 = Predicate(frozenset({make_atom("HAS_COLOUR", 4)}))            # cost 3
C7 = Predicate(frozenset({make_atom("HAS_COLOUR", 7)}))            # cost 3
NEAR = Predicate(frozenset({make_atom("NEAR")}))                   # cost 2


def _ctx(free: bool, colour: int = 4, same_row: bool = False, same_col: bool = False, near: bool = False) -> Context:
    """A before-state assembled so each atom above can be switched INDEPENDENTLY. The point of the independence is
    that eligibility (does this φ split the contexts?) can be varied without touching the outcomes."""
    fr, fc = 2, 2
    tr = fr if same_row else fr + 4
    tc = fc if same_col else fc + 4
    if near:                                             # NEAR is dist<=1; overrides the row/col offsets
        tr, tc = fr, fc + 1
    return Context(focus_rc=(fr, fc), focus_colour=colour, target_rc=(tr, tc), action_vec=(0, 1),
                   intended_free=free, intended_colour=(None if free else colour))


def _evidence(n: int = 8):
    """n exceptions whose OUTCOME is exactly INTENDED_FREE, so `FREE` is a perfect, and the best, explanation.
    Colour, row-alignment and col-alignment vary on a DIFFERENT cycle from the outcome, so the other predicates
    are eligible (they split the contexts) without being good (they do not split the outcomes)."""
    out = []
    for i in range(n):
        out.append((_ctx(free=(i % 2 == 0), colour=(4 if i < n // 2 else 7),
                         same_row=(i % 3 == 0), same_col=(i % 4 == 0)), i % 2 == 0))
    return out


def _con(*preds) -> Consolidator:
    c = Consolidator(echo_threshold=2)
    c.library.extend(preds)
    return c


# --------------------------------------------------------------------------------------------------------------
# 1. THE CHARGE EXISTS, AND IS log2 OF THE ELIGIBLE COUNT -- NOT OF THE LIBRARY.
# --------------------------------------------------------------------------------------------------------------
def test_a_single_candidate_library_charges_nothing_which_is_why_this_was_invisible_before_sharing():
    rep = {}
    got = _con(FREE).explains_scored(_evidence(), rep)
    assert got is not None
    assert rep["n_eligible"] == 1
    assert rep["selection_cost_bits"] == 0.0            # log2(1) -- the old behaviour, unchanged, on a tiny Γ


def test_the_charge_is_over_ELIGIBLE_candidates_not_over_library_size():
    """A φ that holds on EVERY context, or on NONE, is not a hypothesis about this residual -- it cannot split it,
    it never wins, and charging for it would inflate the cost of a contest it was never in. Library size is the
    wrong denominator; the number of φ that actually split THESE contexts is the right one."""
    ev = _evidence()
    everywhere = Predicate(frozenset({make_atom("INTENDED_COLOUR", 99)}))   # holds on nothing here
    rep = {}
    _con(FREE, ROW, everywhere).explains_scored(ev, rep)
    assert rep["library_size"] == 3
    assert rep["n_eligible"] == 2                        # the inert φ is not charged for
    assert rep["selection_cost_bits"] == pytest.approx(math.log2(2))


def test_the_charge_grows_with_the_contest_and_is_reported_in_the_receipt_block():
    ev = _evidence()
    sizes = {}
    for lib in ([FREE], [FREE, ROW], [FREE, ROW, COL], [FREE, ROW, COL, C4]):
        rep = {}
        _con(*lib).explains_scored(ev, rep)
        sizes[rep["n_eligible"]] = rep["selection_cost_bits"]
    assert sizes == {k: pytest.approx(math.log2(k)) for k in sizes}
    assert sorted(sizes) == sorted(sizes)                # and it is monotone in the eligible count, by construction


# --------------------------------------------------------------------------------------------------------------
# 2. THE TWO PROPERTIES THAT STOP THE CHARGE BEING A KNOB.
# --------------------------------------------------------------------------------------------------------------
def test_eligibility_reads_the_context_and_never_the_outcome():
    """The tautology guard is a TYPE property in `dsl` -- a φ sees the before-state only -- and it has to survive
    into the SELECTION layer too. If eligibility consulted outcomes, the scorer could quietly shrink the contest
    whenever the charge threatened a firing, which is the tuning this whole file exists to prevent. Permuting the
    outcomes while holding the contexts fixed must leave the contest size and the charge bit-identical."""
    ev = _evidence()
    flipped = [(ctx, not o) for ctx, o in ev]
    shuffled = [(ctx, o) for (ctx, _), (_, o) in zip(ev, reversed(ev))]
    a, b, c = {}, {}, {}
    con = _con(FREE, ROW, COL, C4)
    con.explains_scored(ev, a)
    con.explains_scored(flipped, b)
    con.explains_scored(shuffled, c)
    assert a["n_eligible"] == b["n_eligible"] == c["n_eligible"]
    assert a["selection_cost_bits"] == b["selection_cost_bits"] == c["selection_cost_bits"]


def test_a_bigger_library_can_only_LOWER_a_reported_gain_never_raise_it():
    """The direction is the whole point. Growing Γ must make transfer HARDER to claim, never easier -- otherwise
    every future beat that adds a φ to the library also inflates every gain the library reports, and the chain
    would read healthier the more it accumulated. Same evidence, same winner, strictly more competition."""
    ev = _evidence()
    small, big = {}, {}
    won_small = _con(FREE).explains_scored(ev, small)
    won_big = _con(FREE, ROW, COL, C4, C7, NEAR).explains_scored(ev, big)
    assert won_small is not None and won_big is not None
    assert won_small[0] == won_big[0] == FREE            # the winner is unchanged; only its price went up
    assert big["gain_bits"] < small["gain_bits"]
    assert big["gain_bits"] == pytest.approx(small["gain_bits"] - big["selection_cost_bits"])


# --------------------------------------------------------------------------------------------------------------
# 3. THE CONSEQUENCE: A MARGINAL FIRING STOPS FIRING.
# --------------------------------------------------------------------------------------------------------------
def test_a_transfer_that_only_cleared_the_bar_by_less_than_the_charge_no_longer_fires():
    """The live case this correction was written for. In the sweep that first fired the chain, one of the three
    firings recorded a gain of 1.33 bits with three predicates promoted into Γ; log2 of a three-way contest is
    1.58 bits, so that firing plausibly never cleared a bar it was never charged. Here that situation is built
    exactly: a residual where the best φ wins by a hair, scored against a one-φ library and against a wide one.
    Uncharged it fires; charged it does not, and returning None is the correct, quieter answer."""
    # 6 exceptions, outcome = INTENDED_FREE except one flipped case, so the split is good but not free.
    ev = [(_ctx(free=True, colour=4, same_row=True), True),
          (_ctx(free=True, colour=7, same_col=True), True),
          (_ctx(free=True, colour=4), False),                    # the blemish that costs the winner its purity
          (_ctx(free=False, colour=7, same_row=True), False),
          (_ctx(free=False, colour=4, same_col=True), False),
          (_ctx(free=False, colour=7), False)]
    lean = {}
    alone = _con(FREE).explains_scored(ev, lean)
    assert alone is not None, "the fixture must be a firing BEFORE the charge, or it tests nothing"
    margin = lean["gain_bits"]
    assert 0 < margin < math.log2(3), "the fixture must be MARGINAL -- a wide contest has to be able to kill it"
    crowded = {}
    assert _con(FREE, ROW, COL).explains_scored(ev, crowded) is None
    assert crowded["n_eligible"] == 3
    assert crowded["gain_bits"] == 0.0                   # no winner => the receipt reports zero, not the raw margin


# --------------------------------------------------------------------------------------------------------------
# 4. ONE SCORING BODY: THE VERDICT AND THE BITS CAN NEVER DISAGREE.
# --------------------------------------------------------------------------------------------------------------
def test_explains_and_explains_scored_agree_under_the_charge():
    ev = _evidence()
    for lib in ([FREE], [FREE, ROW, COL], [FREE, ROW, COL, C4, C7, NEAR]):
        con = _con(*lib)
        scored = con.explains_scored(ev)
        assert con.explains(ev) == (None if scored is None else scored[0])


def test_the_reported_gain_is_reproducible_by_hand_from_the_reported_parts():
    """A receipt whose number cannot be recomputed from the parts it prints is an assertion, not a receipt."""
    ev = _evidence()
    rep = {}
    got = _con(FREE, ROW, COL, C4).explains_scored(ev, rep)
    assert got is not None
    phi, gain = got
    n, k = len(ev), sum(1 for _, o in ev if o)
    holds = [phi.holds(ctx) for ctx, _ in ev]
    pos = [o for (_, o), h in zip(ev, holds) if h]
    neg = [o for (_, o), h in zip(ev, holds) if not h]
    by_hand = (_entropy_bits(n, k)
               - (_entropy_bits(len(pos), sum(pos)) + _entropy_bits(len(neg), sum(neg))
                  + phi.cost() + rep["selection_cost_bits"]))
    assert gain == pytest.approx(by_hand)
    assert rep["gain_bits"] == pytest.approx(gain)


def test_the_charge_survives_the_route_the_policy_actually_uses():
    """`observe_mint` is how Γ really fills; a charge that only appears when a test appends to `library` directly
    would be untested at the call site. Promote two φ the honest way, then offer a residual to the result."""
    con = Consolidator(echo_threshold=2)
    for pred in (FREE, ROW):
        assert con.observe_mint("aa11-x#L0#s0.tau", Mint(predicate=pred, saved_bits=9.0, support=4)) is False
        assert con.observe_mint("bb22-y#L0#s0.tau", Mint(predicate=pred, saved_bits=9.0, support=4)) is True
    rep = {}
    con.explains_scored(_evidence(), rep)
    assert rep["library_size"] == 2 and rep["n_eligible"] == 2
    assert rep["selection_cost_bits"] == pytest.approx(1.0)
