"""THE COMPOSER DEFENDS ITS OBJECTIVE (cycle 21, stage 2a).

`self._posed_goal = posed` was UNCONDITIONAL: the newest window's argmax always won. Measured at equal budget on
the public set, one game posed target 14, 8, 14, 8, ... eleven times, another four times, with `saved_bits`
climbing monotonically throughout. It climbs because `saved_bits` is an ABSOLUTE bit count over a window that is
still filling -- a later pose is scored on more data than the incumbent ever was -- so the alternation was not a
mind changing, it was two incomparable numbers being compared. These pin the two corrections:

  * DENSITY (bits per step of SUPPORT) is the comparand, so window length and candidate-presence divide out;
  * the incumbent is RE-SCORED ON THE CURRENT WINDOW, so both sides are read off the same steps and labels;
  * a challenger must clear POSE_COMMIT_MARGIN to unseat -- below it, the incumbent HOLDS;
  * the incumbent's TARGET is defended, its PREDICATE is not: same target under a better relation is a REFINEMENT;
  * an incumbent absent from the current window has no evidence to defend with and yields unopposed;
  * `pose_goal` still returns exactly what it returned before -- `score_goals` is a superset, not a change of
    selection (this is the non-regression pin for every existing composer test).

Nothing here names a game.
"""
import os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.policy import ReduxPolicy, POSE_COMMIT_MARGIN
from newhorse.redux_arch.goal import pose_goal, score_goals, PosedGoal
from newhorse.redux_arch.dsl import Predicate, make_atom

TOWARD = Predicate(frozenset({make_atom("ACTS_TOWARD")}))
SAMEROW = Predicate(frozenset({make_atom("SAME_ROW")}))


class _M:                                                 # a stand-in Mint: the commitment logic reads .predicate
    def __init__(self, pred):
        self.predicate = pred


def _pg(target, bits, support, pred=TOWARD):
    return PosedGoal(target=target, mint=_M(pred), saved_bits=bits, support=support)


def _stream(n=40):
    """A synthetic progress stream: the avatar walks toward candidate 7; candidate 8 sits still in a corner."""
    steps = []
    prev = None
    for k in range(n):
        av = (20 - (k % 18), 3 + (k % 18))
        d = abs(av[0] - 3) + abs(av[1] - 20)
        steps.append((av, (-1, 1), {7: (3, 20), 8: (21, 3)}, prev is not None and d < prev))
        prev = d
    return steps


# ---- density: the comparand ---------------------------------------------------------------------------------

def test_density_divides_out_the_window_length_confound():
    """The SAME per-step regularity scored on a longer window yields more absolute bits and identical density.
    This is the arithmetic that made the live composer alternate forever."""
    early, late = _pg(7, 6.0, 12), _pg(7, 60.0, 120)
    assert late.saved_bits > early.saved_bits             # the confound, reproduced
    assert late.density == pytest.approx(early.density)   # and divided out


def test_zero_support_is_zero_density():
    """No evidence, no claim -- never a ZeroDivisionError and never a free win."""
    assert _pg(7, 99.0, 0).density == 0.0


def test_score_goals_records_the_support_it_actually_had():
    steps = _stream(30)
    steps[0][2].pop(8)                                    # candidate 8 absent for one step
    sc = score_goals(steps, avatar_colour=3)
    assert sc, "the stream must score at all for this test to mean anything"
    for cid, pg in sc.items():
        assert pg.support == sum(1 for _, _, cmap, _ in steps if cid in cmap)


def test_pose_goal_is_still_exactly_the_argmax_of_score_goals():
    """NON-REGRESSION: refactoring `pose_goal` through `score_goals` must not change WHICH goal is posed."""
    steps = _stream(40)
    sc = score_goals(steps, avatar_colour=3)
    p = pose_goal(steps, avatar_colour=3)
    if not sc:
        assert p is None
    else:
        assert p is not None
        assert p.saved_bits == max(g.saved_bits for g in sc.values())
        assert p.target == max(sc.values(), key=lambda g: g.saved_bits).target


# ---- the defence --------------------------------------------------------------------------------------------

def _pol():
    return ReduxPolicy(game_id="test")


def test_a_marginal_challenger_does_not_unseat_the_incumbent():
    p = _pol()
    p._posed_goal = _pg(7, 10.0, 10)                      # incumbent density 1.0
    scores = {7: _pg(7, 20.0, 20), 8: _pg(8, 24.0, 20)}   # re-scored: 1.0 vs challenger 1.2 (< 1.25)
    out, rec = p._commit_goal(scores[8], scores)
    assert out.target == 7 and rec is not None
    assert rec["over"] == 8 and p.n_defended == 1


def test_a_challenger_that_clears_the_margin_takes_over():
    p = _pol()
    p._posed_goal = _pg(7, 10.0, 10)
    scores = {7: _pg(7, 20.0, 20), 8: _pg(8, 30.0, 20)}   # 1.0 vs 1.5 -- earned
    out, rec = p._commit_goal(scores[8], scores)
    assert out.target == 8 and rec is None and p.n_defended == 0


def test_the_margin_boundary_is_the_declared_constant():
    """No hidden second threshold: exactly POSE_COMMIT_MARGIN, and >= is a take-over."""
    p = _pol()
    p._posed_goal = _pg(7, 10.0, 10)
    scores = {7: _pg(7, 10.0, 10), 8: _pg(8, 10.0 * POSE_COMMIT_MARGIN, 10)}
    out, _ = p._commit_goal(scores[8], scores)
    assert out.target == 8


def test_the_incumbent_is_rescored_not_remembered():
    """The stale score must NOT be what defends. Here the incumbent was posed at a huge absolute bit count, but on
    THIS window its density is poor -- and it must lose, exactly as if it had always been poor."""
    p = _pol()
    p._posed_goal = _pg(7, 500.0, 100)                    # stale density 5.0 -- would defend against anything
    scores = {7: _pg(7, 1.0, 20), 8: _pg(8, 20.0, 20)}    # current: 0.05 vs 1.0
    out, rec = p._commit_goal(scores[8], scores)
    assert out.target == 8 and rec is None


def test_the_predicate_is_refined_while_the_target_is_defended():
    """Defending the TARGET is committing to what the game is about; freezing the PREDICATE would just freeze a
    worse reading of a target we still believe in."""
    p = _pol()
    p._posed_goal = _pg(7, 10.0, 10, pred=TOWARD)
    scores = {7: _pg(7, 20.0, 20, pred=SAMEROW), 8: _pg(8, 22.0, 20)}
    out, rec = p._commit_goal(scores[8], scores)
    assert out.target == 7 and rec is not None
    assert str(out.mint.predicate) == str(SAMEROW)        # the incumbent target, this window's best relation


def test_an_incumbent_absent_from_the_window_yields_unopposed():
    """It left the board or left salience. An objective with no current evidence cannot outvote one that has some."""
    p = _pol()
    p._posed_goal = _pg(7, 999.0, 10)
    scores = {8: _pg(8, 1.0, 20)}
    out, rec = p._commit_goal(scores[8], scores)
    assert out.target == 8 and rec is None and p.n_defended == 0


def test_the_same_target_is_never_a_contest():
    p = _pol()
    p._posed_goal = _pg(7, 10.0, 10)
    scores = {7: _pg(7, 11.0, 20)}
    out, rec = p._commit_goal(scores[7], scores)
    assert out.target == 7 and rec is None and p.n_defended == 0


def test_the_flag_restores_the_unconditional_argmax(monkeypatch):
    monkeypatch.setenv("OURO_POSE_COMMIT", "0")
    p = ReduxPolicy(game_id="test")
    p._posed_goal = _pg(7, 100.0, 10)
    scores = {7: _pg(7, 100.0, 10), 8: _pg(8, 1.0, 10)}
    out, rec = p._commit_goal(scores[8], scores)
    assert out.target == 8 and rec is None               # the pre-cycle-21 behaviour, exactly


def test_no_incumbent_means_nothing_to_defend():
    p = _pol()
    assert p._posed_goal is None
    out, rec = p._commit_goal(_pg(8, 1.0, 10), {8: _pg(8, 1.0, 10)})
    assert out.target == 8 and rec is None
