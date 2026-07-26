"""
test_receipt_provenance.py -- THE RECEIPT MUST NOT MISATTRIBUTE A PROVENANCE.

Found by reading the output of the first sweep in which the tether actually fired, not by a test. The receipt
printed:

    PHI RE-MINTED HERE INTENDED_FREE ... for the task(s) named below, which is where phi was actually created.
    EVALUATED BEFORE   phi was minted on sp80-...#L0#s0.tau, sp80-...#L0#s1.tau, ...

`minted_on` is the provenance of the φ that TRANSFERRED (`INTENDED_COLOUR==9`, from sp80). `minted_phi` is a
DIFFERENT predicate, freshly minted on this residual. The prose bridged them, so the artifact that exists to make
a firing checkable asserted that `INTENDED_FREE` was created on a game it had never been minted on.

Directive 5 says a firing is a RECEIPT, not a claim. A receipt that attributes one predicate's history to another
is strictly worse than no receipt -- it is fake evidence with a provenance line on it. These tests fail if the two
predicates' fields can ever be read as belonging to one.
"""
from __future__ import annotations

from newhorse.redux_arch.receipt import ResidualEvent, render_one

SP80 = ["sp80-589a99af#L0#s0.tau", "sp80-589a99af#L0#s1.tau"]


def _two_phi_event() -> ResidualEvent:
    """The exact shape of the real misreport: a φ transferred IN from sp80, a different φ minted here on re86."""
    return ResidualEvent(
        game="re86-8af5384d", level=0, segment=1, reason="death", steps=41,
        task_id="re86-8af5384d#L0#s1.tau", diff_ran=True, n_exceptions=30, n_positive=12,
        baseline_bits=29.1, residual_nonempty=True, library_size_before=3, library_foreign_before=3,
        reuse_attempted=True, reuse_attempted_foreign=True,
        transferred="INTENDED_COLOUR==9", transfer_gain_bits=1.33, echo_kind="cross-game", minted_on=list(SP80),
        minted=True, minted_phi="INTENDED_FREE", minted_bits=14.5, minted_support=18,
        stage="USED_NOCLEAR")


def _line_containing(text: str, needle: str) -> str:
    hits = [ln for ln in text.splitlines() if needle in ln]
    assert hits, "expected a line mentioning %r in:\n%s" % (needle, text)
    return hits[0]


def test_the_minted_phi_never_carries_the_transferred_phis_minting_tasks():
    """THE REGRESSION ITSELF. No line may name the freshly-minted φ and a task from the transferred φ's history."""
    out = render_one(_two_phi_event())
    for ln in out.splitlines():
        if "INTENDED_FREE" in ln:
            assert not any(t in ln for t in SP80), "minted φ's line borrowed the transferred φ's provenance: %r" % ln


def test_the_freshly_minted_phi_is_labelled_as_a_DIFFERENT_predicate_from_the_one_that_fired():
    out = render_one(_two_phi_event())
    ln = _line_containing(out, "INTENDED_FREE")
    assert "DIFFERENT phi" in ln


def test_the_minting_tasks_are_attached_to_the_phi_that_actually_fired():
    out = render_one(_two_phi_event())
    fired_ln = _line_containing(out, "PHI THAT FIRED")
    assert "INTENDED_COLOUR==9" in fired_ln
    prov = _line_containing(out, "WAS MINTED ON")
    assert all(t in prov for t in SP80)


def test_the_minting_GAMES_are_printed_so_a_cross_game_claim_is_checkable_without_parsing_task_ids():
    """The strongest claim the chain can make is 'minted on game A, fired on game B'. If the receipt only prints
    task ids, checking that claim means parsing an id format by eye -- which is how a within-game echo gets read as
    a cross-game one by a tired reader."""
    out = render_one(_two_phi_event())
    ln = _line_containing(out, "I.E. ON GAMES")
    assert "sp80-589a99af" in ln
    assert "NOT THIS GAME" in ln


def test_a_within_game_echo_is_never_dressed_up_as_a_crossing():
    ev = _two_phi_event()
    ev.minted_on = ["re86-8af5384d#L0#s0.tau"]           # same game as the firing
    ev.echo_kind = "within-run-across-segments"
    out = render_one(ev)
    ln = _line_containing(out, "I.E. ON GAMES")
    assert "NOT THIS GAME" not in ln
    assert "within-game echo" in ln


def test_a_re_mint_of_the_same_phi_is_named_as_agreement_not_as_a_second_piece_of_evidence():
    """When the minter re-derives the very φ that just transferred, that is the game agreeing with itself. Printed
    without comment next to a transfer it reads like corroboration from a second source."""
    ev = _two_phi_event()
    ev.minted_phi = "INTENDED_COLOUR==9"
    out = render_one(ev)
    ln = _line_containing(out, "SAME phi")
    assert "re-minted" in ln
    assert "agreeing with itself" in out


def test_a_firing_with_no_fresh_mint_says_so_rather_than_printing_an_empty_provenance():
    ev = _two_phi_event()
    ev.minted, ev.minted_phi, ev.minted_bits, ev.minted_support = False, None, 0.0, 0
    out = render_one(ev)
    assert "nothing was minted on this residual" in out
    assert "0.00 bits" not in out                        # no phantom mint with a zero delta attached to it
