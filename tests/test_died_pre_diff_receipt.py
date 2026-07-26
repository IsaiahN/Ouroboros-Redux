"""
test_died_pre_diff_receipt.py -- THE BIGGEST PILE ON THE BOARD HAD NO EVIDENCE UNDER IT.

The measured distribution on sweep f07399d5 was:

    DIED_PRE_DIFF 21 · RESIDUAL_EMPTY 4 · MINT_UNFIRED 8 · REUSE_UNWIRED 2 · MINTED_UNUSED 5 · USED_NOCLEAR 3

DIED_PRE_DIFF is the largest by a factor of two and a half, and it was the ONLY stage that wrote no receipt:
`_residual_pass` returned None before constructing one. Two consequences, both of the same shape the previous two
beats already found:

  1. There was nothing to read. "The diff never ran" is not a diagnosis, it is the absence of one -- and the four
     causes behind it (`no_focus_colour`, `no_learned_vecs`, `segment_too_short`, `no_testable_step`) indict four
     different layers. Perception losing the cursor and a planner pressing unmodelled actions are not the same bug.

  2. `summary()["break_events"]`, defined as `len(receipts)`, therefore did not mean break events. It meant break
     events WHERE THE DIFF RAN -- which is exactly why every sweep printed `break_events=19 | diff_ran=19`. Two
     numbers that cannot disagree are one number wearing two names, and the second name was load-bearing: it is
     the denominator a reader divides by to decide how often the residual organ speaks at all.

These tests pin the fixed shape. The emission is REPORTING ONLY -- `note_diff` is still never called on this path,
so `classify` still returns DIED_PRE_DIFF and nothing about what the chain DOES has changed.
"""
from __future__ import annotations

import numpy as np

from newhorse.redux_arch.abort_code import Stage
from newhorse.redux_arch.bridge import transition_residual
from newhorse.redux_arch.policy import ReduxPolicy
from newhorse.redux_arch.receipt import ResidualEvent, summary

BG, CUR, WALL = 0, 4, 8
VECS = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}


def _board(r: int, c: int, h: int = 8, w: int = 8):
    g = np.full((h, w), BG, dtype=int)
    g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = WALL
    g[r, c] = CUR
    return g


def _walk(n: int = 6):
    frames, acts, r, c = [_board(3, 3)], ["RESET"], 3, 3
    for i in range(n):
        c = min(6, c + 1)
        frames.append(_board(r, c))
        acts.append("RIGHT")
    return frames, acts


def _feed(pol: ReduxPolicy, frames, acts):
    """Push frames straight onto the segment window, exactly as test_tether_brick does -- `observe` is the live
    harness path and drags the whole engagement layer in with it, which this file is not testing."""
    for f, a in zip(frames, acts):
        pol.frames.append(np.asarray(f))
        pol.acts.append(a)
        pol.chain.note_step()


# ---- the reason classifier -----------------------------------------------------------------------------------

def test_the_four_causes_of_a_dead_diff_are_reported_separately():
    """One None, four causes, four different layers. Collapsing them is what made the pile unreadable."""
    frames, acts = _walk()
    rep = {}
    assert transition_residual(frames, acts, None, VECS, report=rep) is None
    assert rep["reason"] == "no_focus_colour"

    rep = {}
    assert transition_residual(frames, acts, CUR, {}, report=rep) is None
    assert rep["reason"] == "no_learned_vecs"

    rep = {}
    assert transition_residual(frames[:1], acts[:1], CUR, VECS, report=rep) is None
    assert rep["reason"] == "segment_too_short"

    rep = {}
    assert transition_residual(frames, acts, CUR, {"NOPE": (0, 1)}, report=rep) is None
    assert rep["reason"] == "no_testable_step", "it RAN and found nothing testable -- not the same as never running"
    assert rep["scan_pairs"] > 0, "and it must say it walked the segment, or the reason is unfalsifiable"
    assert rep["scan_no_vec"] == rep["scan_pairs"], "every pair was skipped for want of a learned vector"


def test_a_successful_residual_still_reports_its_scan_and_the_counts_are_an_identity():
    """scan_pairs == no_vec + unlocatable + len(exc). If that ever fails the scan counters are decoration."""
    frames, acts = _walk()
    rep = {}
    exc = transition_residual(frames, acts, CUR, VECS, passable={BG}, report=rep)
    assert exc, "this fixture is supposed to produce a live residual"
    assert rep["reason"] is None
    assert rep["scan_pairs"] == rep["scan_no_vec"] + rep["scan_unlocatable"] + len(exc)


def test_the_report_out_param_cannot_change_what_the_function_returns():
    """Reporting only. If passing `report` altered the residual, every number measured before this change would
    become incomparable to every number measured after it."""
    frames, acts = _walk()
    a = transition_residual(frames, acts, CUR, VECS, passable={BG})
    b = transition_residual(frames, acts, CUR, VECS, passable={BG}, report={})
    assert a == b


# ---- the receipt ---------------------------------------------------------------------------------------------

def test_a_dead_segment_files_a_receipt_that_credits_nothing():
    pol = ReduxPolicy(game_id="synthetic")                 # cursor/vecs never learned
    frames, acts = _walk()
    _feed(pol, frames, acts)
    pol._close_segment("death")
    assert len(pol.receipts) == 1
    ev = pol.receipts[0]
    assert (ev.diff_ran, ev.residual_nonempty, ev.minted, ev.promoted, ev.fired) == (False, False, False, False, False)
    assert ev.reuse_attempted is False, "a dead segment must never register a reuse ATTEMPT -- that is the code "\
                                        "that indicts the architecture"
    assert ev.stage == Stage.DIED_PRE_DIFF.name
    assert ev.no_diff_reason in {"no_focus_colour", "no_learned_vecs", "segment_too_short", "no_testable_step"}


def test_emitting_the_dead_receipt_does_not_move_the_stage_distribution():
    """The whole change is reporting. The ledger's own counts must be exactly what they were, or this beat has
    measured its own edit instead of the agent."""
    pol = ReduxPolicy(game_id="synthetic")
    frames, acts = _walk()
    _feed(pol, frames, acts)
    pol._close_segment("death")
    rep = pol.chain.report()
    assert rep["counts"] == {Stage.DIED_PRE_DIFF.name: 1}
    assert rep["stalls"] == 1 and rep["advances"] == 0
    assert rep["indicts"] == "implementation", "DIED_PRE_DIFF must still indict implementation, not architecture"


def test_an_empty_segment_still_files_nothing():
    """An empty segment is an accounting artefact, not a task that failed. Filing a receipt for it would
    manufacture a DIED_PRE_DIFF out of bookkeeping -- fixing an undercount with an overcount."""
    pol = ReduxPolicy(game_id="synthetic")
    pol._close_segment("run_end")
    assert pol.receipts == []
    assert pol.chain.report()["stalls"] == 0


# ---- the denominator -----------------------------------------------------------------------------------------

def _dead(reason: str, steps: int = 30, pairs: int = 0, no_vec: int = 0, unloc: int = 0):
    return ResidualEvent(game="g", steps=steps, diff_ran=False, no_diff_reason=reason,
                         scan_pairs=pairs, scan_no_vec=no_vec, scan_unlocatable=unloc)


def _live():
    return ResidualEvent(game="g", steps=30, diff_ran=True, n_exceptions=5, residual_nonempty=True)


def test_break_events_and_diff_ran_can_now_disagree():
    """The bug in one line: `break_events` was `len(receipts)` and only diff-ran segments made receipts, so the
    two were equal BY CONSTRUCTION on every sweep ever printed. A count that cannot differ from its own subset is
    not measuring the superset."""
    evs = [_live(), _live(), _dead("no_focus_colour"), _dead("segment_too_short")]
    s = summary(evs)
    assert s["break_events"] == 4
    assert s["diff_ran"] == 2
    assert s["break_events"] != s["diff_ran"]


def test_the_reason_histogram_covers_every_non_running_segment():
    evs = [_live(), _dead("no_focus_colour"), _dead("no_focus_colour"), _dead("no_testable_step", pairs=9, no_vec=9)]
    s = summary(evs)
    assert s["no_diff_reasons"] == {"no_focus_colour": 2, "no_testable_step": 1}
    assert sum(s["no_diff_reasons"].values()) == s["break_events"] - s["diff_ran"]


def test_the_scan_totals_are_summed_only_over_segments_that_actually_scanned():
    """A segment that died at `no_focus_colour` never walked a frame pair. Averaging its zeros into the scan
    totals would flatten the exact distinction -- planner vs perception -- the counters exist to draw."""
    evs = [_dead("no_focus_colour"), _dead("no_testable_step", steps=40, pairs=10, no_vec=7, unloc=3)]
    s = summary(evs)
    assert s["no_diff_scan"] == dict(segments=1, pairs=10, no_vec=7, unlocatable=3, steps_median=40)


def test_the_residual_stream_can_only_ever_run_on_a_DIRECTIONAL_game():
    """WHAT THE FIRST READ OF THE PILE ACTUALLY SAID, pinned so it cannot be forgotten.

    Sweep d1359347 measured DIED_PRE_DIFF=22 with reasons {no_focus_colour: 22, no_testable_step: 6} and
    `segment_too_short: 0`, `unlocatable: 0`. So it is NOT that the segments were too short, and NOT that
    perception lost the cursor mid-play. `focus_colour` was never learned at all.

    And that is not an accident of those games -- it is an IDENTITY IN THIS SOURCE. `self.cursor` and `self.vecs`
    are assigned a real value at exactly ONE site, and that site sets `self.family = DIRECTIONAL` in the same
    branch; the only other assignment sets them back to None/{} on reset. `transition_residual`'s first two guards
    are precisely `focus_colour is None` and `not vecs`. Therefore R_τ -- the tether's ONLY evidence stream --
    is structurally unable to run on a click, effect, two-body, multi-avatar or undrivable game, whatever those
    games do on the board.

    DIED_PRE_DIFF is therefore not a perception verdict and not an implementation bug. It is the measure of how
    much of the game set the residual organ is not wired to speak about at all: 9 of the 25 environments in this
    sweep reached no further, and every one of them was `click` or `effect`.

    HOW TO OVERTURN: make a non-DIRECTIONAL family learn a focus colour and a non-zero displacement vector. If the
    diff then still refuses to run, this classifier is wrong and the cause is elsewhere. This test failing means
    the coupling has been broken or moved -- which is fine, but the finding above must then be re-measured, not
    inherited."""
    import inspect
    from newhorse.redux_arch import policy as pol_mod

    src = inspect.getsource(pol_mod).splitlines()
    live = [i for i, ln in enumerate(src)
            if "self.cursor =" in ln and "self.cursor = None" not in ln]
    assert len(live) == 1, "cursor is assigned a real value in %d places; the identity below assumes one" % len(live)
    window = "\n".join(src[max(0, live[0] - 8):live[0] + 1])
    assert "self.family = DIRECTIONAL" in window, \
        "the ONLY site that learns a focus colour must be the site that commits DIRECTIONAL -- if that stops being "\
        "true, R_tau's coverage has changed and DIED_PRE_DIFF must be re-read from a fresh sweep"


def test_a_receipt_with_no_recorded_reason_is_named_not_dropped():
    """An older receipt, or a path that forgets to fill the field, must show up as `unrecorded` rather than
    silently leaving the histogram short of the count it is supposed to explain."""
    s = summary([_live(), ResidualEvent(game="g", diff_ran=False)])
    assert s["no_diff_reasons"] == {"unrecorded": 1}
