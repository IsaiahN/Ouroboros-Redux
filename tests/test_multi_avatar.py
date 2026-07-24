"""Brick 5 of the reasoning scaffold (G5): INDEPENDENT multi-avatar routing. Two avatars that are each separately
steerable but do NOT co-move under a conserved invariant -- the coupled two-body organ's `is_coupled` bar correctly
rejects them, leaving a gap the author fills by routing each avatar to its own target. General machinery: the per-body
maps + the not-coupled verdict + the goals are all read from the frame/action stream, never encoded. Names no game."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.coupled import TwoBodyAgency, independent_multi, multi_avatar_action


def _frame(p0, p1, shape=(24, 24)):
    g = np.zeros(shape, dtype=int); g[p0] = 3; g[p1] = 3
    return g


def _build_ag(true0, true1):
    """Learn a TwoBodyAgency from a warmup stream in which action a moves body0 by true0[a] and body1 by true1[a]
    (independently). Bodies are the two components of colour 3, ordered left-to-right (they never cross here)."""
    ag = TwoBodyAgency(3)
    p0, p1 = (2, 2), (2, 14)
    for a in ["A1", "A2", "A3", "A4", "A1", "A2", "A3", "A4"]:
        before = _frame(p0, p1)
        d0, d1 = true0.get(a, (0, 0)), true1.get(a, (0, 0))
        np0, np1 = (p0[0] + d0[0], p0[1] + d0[1]), (p1[0] + d1[0], p1[1] + d1[1])
        ag.observe(before, a, _frame(np0, np1))
        p0, p1 = np0, np1
    return ag


TRUE0 = {"A1": (1, 0), "A3": (0, 1)}      # body0: A1 = down, A3 = right
TRUE1 = {"A2": (1, 0), "A4": (0, 1)}      # body1: A2 = down, A4 = right (a DISJOINT control set -> independent)


def test_independent_multi_detects_uncoupled_pair():
    ag = _build_ag(TRUE0, TRUE1)
    assert ag.n_controllable() == 2 and ag.ready()
    assert not ag.is_coupled()                               # disjoint controls -> no co-move, no conserved invariant
    assert independent_multi(ag)                             # ...which is exactly the G5 independent-avatar case


def test_coupled_pair_is_not_independent_multi():
    """A genuinely COUPLED pair (both bodies move under the same actions, mirror-conserved) is NOT independent-multi --
    it belongs to the two-body organ, so the router must not steal it."""
    mirror = {"A1": (1, 0), "A2": (0, 1), "A3": (1, 0)}      # 3 co-moving actions (>= min_both) with a conserved sum
    ag = _build_ag(mirror, {"A1": (-1, 0), "A2": (0, -1), "A3": (-1, 0)})
    assert ag.is_coupled()
    assert not independent_multi(ag)


def test_co_moving_without_solo_control_is_not_independent_multi():
    """Precision (from the coverage census: Brick 5 mis-fired on a legend game): two components that move under the SAME
    actions -- no action steers one alone -- are NOT independently-steered avatars, even when they are not conserved-
    coupled. Without a SOLO control per body the router must not claim them."""
    a = {"A1": (1, 0), "A2": (0, 1), "A3": (1, 1)}
    b = {"A1": (0, 1), "A2": (1, 0), "A3": (1, 1)}          # same action set, no conserved invariant, NO solo action
    ag = _build_ag(a, b)
    assert not ag.is_coupled()                              # not conserved-coupled...
    assert not independent_multi(ag)                        # ...but rejected: neither body has an action that moves it alone


def test_multi_avatar_routes_both_avatars_to_their_targets():
    ag = _build_ag(TRUE0, TRUE1)
    p0, p1 = (3, 3), (3, 15)
    t0, t1 = (9, 3), (3, 20)                                 # body0 down 6; body1 right 5 (disjoint axes)
    passable = lambda i, dest: True
    for _ in range(40):
        bodies = [p0, p1]
        if p0 == t0 and p1 == t1:
            break
        a = multi_avatar_action(bodies, ag, passable, [t0, t1])
        assert a is not None
        d0, d1 = TRUE0.get(a, (0, 0)), TRUE1.get(a, (0, 0))
        p0, p1 = (p0[0] + d0[0], p0[1] + d0[1]), (p1[0] + d1[0], p1[1] + d1[1])
    assert [p0, p1] == [t0, t1]                              # both avatars independently routed home


def test_multi_avatar_none_when_targets_missing():
    ag = _build_ag(TRUE0, TRUE1)
    assert multi_avatar_action([(3, 3), (3, 15)], ag, lambda i, d: True, [(3, 3)]) is None   # fewer targets than bodies
    assert multi_avatar_action([(3, 3), (3, 15)], ag, lambda i, d: True, [(3, 3), (3, 15)]) is None  # both at target
