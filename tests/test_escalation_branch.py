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
apart from the designed cost of a fair trial. NOTHING IS FIXED HERE -- this beat measures.
"""
import numpy as np

from newhorse.redux_arch.policy import ReduxPolicy
from newhorse.redux_arch.receipt import summary


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
    """The safe half of the mechanism, and the reason the defect below is easy to miss. Drive a frozen board until
    the organ escalates to A6, then let the board answer. `answered("A6")` clears `_pre_esc_family`, and the next
    `_decide` is caught by the natively-routed click exit BEFORE this organ is reached -- so `hold_answered` is
    charged at most once and the agent is not held. Nothing here is broken; it is the control for the next test."""
    p = _policy("bb22-release")
    g = _board()
    _drive(p, g, 20, answer=False)                     # inside the A6 trial: it runs ~`window` steps then reverts
    assert p._escalated == "A6", (p._escalated, p._esc_branch)
    _drive(p, g, 40, answer=True)
    assert p._esc_branch.get("hold_answered", 0) <= 1, p._esc_branch
    assert p._dec_exits.get("click_native", 0) >= 20, p._dec_exits


def test_a_DIRECTIONAL_escalation_that_answers_is_never_released():
    """THE FINDING, stated as a mechanism and tested as one. The state is CONSTRUCTED -- `_escalated` is set
    directly to a directional label -- because whether this state is reached often is a question for the live
    sweep, not for a unit test, and pretending a synthetic frequency is a measured one is exactly the
    mis-labelled receipt this instrument exists to prevent. What is under test is the CONSEQUENCE of the state:

        `failed_trial` = `observations >= window AND best < min_cells`, and `best` is a MAX. One answer makes it
        False permanently. The hold branch is checked before the family dispatch and returns the escalated label.
        There is no directional counterpart to the A6 commit above, so nothing ever clears `_escalated`.

    So the organ holds the agent on ONE action for the rest of the episode -- an action chosen because it was the
    least-observed one on a frozen board, not because anything about it was understood."""
    from newhorse.redux_arch.policy import EFFECT

    p = _policy("cc33-lockin")
    p.family = EFFECT
    p._escalated = "A1"                                # the state, constructed; its FREQUENCY is the sweep's job
    g = _board()
    labels, _t = _drive(p, g, 60, answer=True, avail=(1, 2, 3, 4))
    assert p._esc_branch.get("hold_answered", 0) >= 40, p._esc_branch
    assert p._escalated == "A1", p._escalated          # nothing ever released it
    assert set(labels[10:]) == {"A1"}, sorted(set(labels[10:]))


def test_the_branch_split_sums_to_the_escalate_exits_on_the_receipt():
    """The identity, checked where every other identity in this instrument is checked: on the pooled receipt. The
    branch counts are written at three returns inside the organ and the exit counts at two returns inside
    `_decide`; they are independent counters of the same steps, so a non-zero residue means one of them is wrong
    and neither may be cited."""
    p = _policy("cc33-sums")
    g = _board()
    _drive(p, g, 60, answer=False)
    _drive(p, g, 40, answer=True)
    p._close_segment("death")
    dfn = summary(p.receipts)["decide_funnel"]
    esc = int(dfn["exits"].get("escalate", 0)) + int(dfn["exits"].get("escalate_click", 0))
    assert esc > 0, dfn["exits"]
    assert sum(dfn["esc_branch"].values()) == esc, dfn
    assert dfn["esc_branch_residue"] == 0, dfn


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
