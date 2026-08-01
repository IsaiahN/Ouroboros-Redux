"""★★★ THE ESCALATION BRANCH: WHERE `escalate`'s STEPS ACTUALLY COME FROM. ★★★

`escalate` + `escalate_click` held ~14-16% of every decision the agent made last sweep and answered 4.4-5.1% of
them, and that rate was the SAME on all seven games it touched. Uniform-and-low across seven unrelated boards is
not seven findings about seven boards; it is one finding about the organ. But the exit name is a single literal,
so it could not say WHICH of `_modality_escalate`'s three returns produced any given step -- and a rate you
cannot attribute is a rate you cannot act on.

This file pins the split at the level of the ORGAN, not the printer. The claim under test is structural and was
found by reading, not by measuring:

    `failed_trial` is `observations >= window AND best < min_cells`. `best` is a MAX over the action's history,
    so ONE answer at any point makes `failed_trial` False for the rest of the episode. The hold branch is checked
    before anything else and returns the escalated label -- so from that moment the organ returns the same action
    at every single decision. `A6` is released by the click commit (`_pre_esc_family = None`, after which the
    natively-routed click exit catches the next `_decide` before this organ is reached). A DIRECTIONAL label has
    no such release.

So the organ built to refuse a null intervention can hold the agent on one action for the rest of the episode,
and the step it holds them on is one that answered ONCE. These tests prove the branch counter can tell that state
apart from the designed cost of a fair trial.

THE MEASUREMENT CAME BACK (sweep at fbd10df): `hold_answered` was 460 steps, 87.6% of every escalate step the
agent took, with a published residue of 0. So the state is not a corner case -- it is what the organ mostly DOES.

THE RELEASE (this beat) closes it at the same place the reading was taken. A label that has answered is not a
null intervention, so there is nothing left to refuse: `_escalated` is cleared and the game is handed back to its
family organ, which is the shape the A6 commit already had. A6 still holds for one step, because its commit has
already made the game a click game and the click organ is where it belongs. The tests below are the same tests,
with the DIRECTIONAL one inverted -- it now pins the release, and its A6 sibling is unchanged, which is how you
can see the fix did not widen `escalate` on the way past.
"""
import numpy as np

from newhorse.redux_arch.policy import ReduxPolicy
from newhorse.redux_arch.receipt import summary, _ESC_NOSTEP


def _policy(gid="ee55-eeee"):
    p = ReduxPolicy(game_id=gid)
    p.frames = []
    return p


def _board():
    g = np.zeros((20, 20), dtype=int)
    g[3, 3], g[3, 4] = 4, 5
    return g


def _drive(p, g, n, answer=False, tick=0, avail=(1, 2, 3, 4, 6)):
    """`answer=False` freezes the board (nothing the agent does changes it), which is the precondition the
    escalation organ waits for. `answer=True` moves four interior cells EVERY step regardless of what was sent --
    the board answering whatever the agent does, which is exactly the state that traps the hold branch.

    `avail` includes 6 by default because a directional game with no click action has nothing to escalate TO once
    the family organ has probed every direction twice, and the organ correctly does nothing. The escalation this
    instrument exists to measure needs an untried modality to exist."""
    labels = []
    for _ in range(n):
        p.observe(g.copy(), list(avail), 0)
        lbl, _d = p.choose()
        labels.append(lbl)
        if answer:
            tick += 1
            g[9:11, 9:11] = tick % 5 + 1              # interior cells, out of reach of the budget-band mask
    return labels, tick


def test_a_frozen_board_escalates_and_the_branch_is_new_plus_hold_untried():
    """The designed path. The board never answers, so every trial ends in `failed_trial` and the organ moves on to
    the next untried modality. `hold_answered` must be ZERO here: nothing ever answered, so the lock-in state is
    unreachable, and a counter that fired anyway would be measuring something other than what it names."""
    p = _policy("aa11-frozen")
    _drive(p, _board(), 60, answer=False)
    b = p._esc_branch
    assert b.get("new", 0) >= 1, b
    assert b.get("hold_untried", 0) >= 1, b
    assert b.get("hold_answered", 0) == 0, b


def test_an_escalation_to_click_that_answers_is_RELEASED_by_the_commit():
    """Drive a frozen board until the organ escalates to A6, then let the board answer. `answered("A6")` clears
    `_pre_esc_family` and the escalation is OVER: `_escalated` goes back to None and the game is handed to the
    click organ, exactly as a directional label is handed back to its family organ.

    THIS TEST CHANGED ON 2026-08-01 AND THE CHANGE IS THE POINT. It used to assert `hold_answered <= 1` and 20+
    `click_native` exits, because a committed click game was then caught by the `click_native` exit before ever
    reaching this organ -- so holding A6 was harmless. With the click exemption narrowed, the game DOES come back
    here, and holding would pin `_escalated` at "A6" for the rest of the episode. The A6 exception is gone;
    `hold_answered` is now charged by nothing at all, and the steps land on the click dispatch instead."""
    p = _policy("bb22-release")
    g = _board()
    _drive(p, g, 20, answer=False)                     # inside the A6 trial: it runs ~`window` steps then reverts
    assert p._escalated == "A6", (p._escalated, p._esc_branch)
    _drive(p, g, 40, answer=True)
    assert p._esc_branch.get("hold_answered", 0) == 0, p._esc_branch
    assert p._esc_branch.get("released_answered", 0) >= 1, p._esc_branch
    assert p._escalated is None, p._escalated
    assert p._dec_exits.get("family_click", 0) >= 20, p._dec_exits


def test_a_DIRECTIONAL_escalation_that_answers_is_RELEASED_to_its_family_organ():
    """THE RELEASE. This test was the finding, and it is the same construction inverted -- which is the point of
    keeping it here rather than writing a fresh one: the state that used to hold the agent for the rest of the
    episode is driven identically and must now end in a hand-back.

    The state is CONSTRUCTED -- `_escalated` is set directly to a directional label -- because whether this state
    is reached often is a question for the live sweep, not for a unit test. What is under test is the CONSEQUENCE:
    one answer, and the escalation is over. `hold_answered` must be ZERO, because that branch is now reachable
    only by A6 on the step its click commit lands, and `released_answered` must be exactly ONE -- the release
    fires once and then there is no escalation left to release. The board keeps answering, so `escalate()` (which
    requires `frozen()`) cannot re-arm, and every remaining step belongs to the family organ."""
    from newhorse.redux_arch.policy import EFFECT

    p = _policy("cc33-release")
    p.family = EFFECT
    p._escalated = "A1"                                # the state, constructed; its FREQUENCY is the sweep's job
    g = _board()
    _labels, _t = _drive(p, g, 60, answer=True, avail=(1, 2, 3, 4))
    assert p._esc_branch.get("hold_answered", 0) == 0, p._esc_branch
    assert p._esc_branch.get("released_answered", 0) == 1, p._esc_branch
    assert p._escalated is None, p._escalated          # the hand-back actually happened
    assert p._dec_exits.get("family_effect", 0) >= 40, p._dec_exits


def test_the_release_does_not_widen_escalate_on_a_board_that_never_answers():
    """The release is allowed to END escalations; it is not allowed to START any. A frozen board never satisfies
    `answered`, so the released branch must never be charged, and the organ must behave exactly as it did before
    the fix -- same escalate steps, same fair trials. This is the no-widening receipt."""
    p = _policy("cc33-nowiden")
    _drive(p, _board(), 60, answer=False)
    assert p._esc_branch.get("released_answered", 0) == 0, p._esc_branch
    assert p._esc_branch.get("hold_answered", 0) == 0, p._esc_branch
    assert p._esc_branch.get("new", 0) >= 1, p._esc_branch


def test_the_branch_split_sums_to_the_escalate_exits_on_the_receipt():
    """The identity, checked where every other identity in this instrument is checked: on the pooled receipt. The
    branch counts are written at the returns inside the organ and the exit counts at two returns inside
    `_decide`; they are independent counters of the same steps, so a non-zero residue means one of them is wrong
    and neither may be cited.

    Only the returns that HAND BACK A LABEL produce a step, so only those are in the identity. `released_answered`
    returns None and `_decide` falls through to the family organ, so it is excluded BY NAME (`_ESC_NOSTEP`) rather
    than by being added to both sides -- closing an identity by adding a term to both sides is the defect this
    instrument caught inside its own printer, and it would make the residue unable to fail."""
    p = _policy("cc33-sums")
    g = _board()
    _drive(p, g, 60, answer=False)
    _drive(p, g, 40, answer=True)
    p._close_segment("death")
    dfn = summary(p.receipts)["decide_funnel"]
    esc = int(dfn["exits"].get("escalate", 0)) + int(dfn["exits"].get("escalate_click", 0))
    assert esc > 0, dfn["exits"]
    assert sum(v for k, v in dfn["esc_branch"].items() if k not in _ESC_NOSTEP) == esc, dfn
    assert dfn["esc_branch_residue"] == 0, dfn


def test_a_nostep_branch_is_excluded_from_the_identity_by_name_only():
    """The exclusion must be a NAMED list, not a wildcard: anything added to the branch dict without a reading has
    to break the residue, which is the only reason the residue is worth publishing. Injecting an unnamed branch
    must move it; injecting a named no-step branch must not."""
    p = _policy("cc33-guard")
    g = _board()
    _drive(p, g, 60, answer=False)
    p._esc_branch["some_new_return"] = 7
    p._close_segment("death")
    dfn = summary(p.receipts)["decide_funnel"]
    assert dfn["esc_branch_residue"] == -7, dfn


def test_the_branch_counter_does_not_change_what_the_organ_returns():
    """An instrument that alters the thing it measures is not an instrument. Two identical runs, one with the
    branch dict swapped for a sink that discards every write: the emitted action sequences must be identical."""
    class _Sink(dict):
        def __setitem__(self, k, v):                   # accept and discard
            pass

    a, _t = _drive(_policy("dd44-a"), _board(), 80, answer=False)
    p = _policy("dd44-a")
    p._esc_branch = _Sink()
    b, _t = _drive(p, _board(), 80, answer=False)
    assert a == b, (a, b)
