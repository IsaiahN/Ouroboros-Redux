"""★★★ THE GUARD BEHIND THE GUARD: WHY MAKING THE ESCALATION ORGAN REACHABLE IS A NO-OP. ★★★

CLASSIFIER 14 read: "a natively click-routed game never reaches the escalation organ; `_decide` returns at the
`click_native` exit before `_modality_escalate` is called," and the NEXT list turned that into an arm -- move or
scope the `click_native` return so the organ gets consulted, because "the gate is OPEN and reachability is the
whole of it."

The reasoning did not survive contact with the source, and this file is that failure written down as a receipt
instead of as prose. `_decide` guards its `click_native` return with

    self.family == CLICK and self._pre_esc_family is None

and `_modality_escalate` opens with the SAME predicate, returning None. So on exactly the population the arm
targets, control arriving at the organ changes nothing: the organ refuses the game on its own account. Worse, the
state is ABSORBING -- the only assignment of a non-None value to `_pre_esc_family` lives INSIDE
`_modality_escalate`, downstream of that guard -- so a game routed to CLICK by action-set routing can never leave
the exempt population by any path the code contains.

That second guard is not an accident. Its docstring says committed verified win organs, including "a
natively-routed click game," are exempt outright, and `tn36` is a banked click win. Removing the exemption is
therefore not a reachability tweak; it puts a win at risk and needs its own measurement.

These tests exist so that nobody can ship the reachability half alone and believe they changed something. The
A/B in `test_the_guard_not_the_reachability_is_what_excludes_the_game` holds the METER state fixed -- same frozen
window, same untried label, same `labels` list -- and varies only `_pre_esc_family`. If the exemption is ever
lifted deliberately, these tests fail, which is the point: it should not be possible to do it by accident.
"""
import inspect

import numpy as np

from newhorse.redux_arch.policy import ReduxPolicy, CLICK, EFFECT
from newhorse.redux_arch import policy as policy_mod


CLICK_ONLY_AVAIL = (6, 7)                  # no directional action -> action-set routing calls this a click game


def _policy(gid="cn01-native"):
    p = ReduxPolicy(game_id=gid)
    p.frames = []
    return p


def _board():
    g = np.zeros((20, 20), dtype=int)
    g[3, 3], g[3, 4] = 4, 5
    return g


def _drive_frozen(p, g, n, avail=CLICK_ONLY_AVAIL):
    """A board that never answers, on a game whose action set contains no direction. This is the `su15` shape:
    family CLICK by routing, `frozen` True, one label ever emitted, a second label available and never tried."""
    labels = []
    for _ in range(n):
        p.observe(g.copy(), list(avail), 0)
        lbl, _d = p.choose()
        labels.append(lbl)
    return labels


def test_a_click_only_action_set_routes_to_CLICK_and_stays_at_the_native_exit():
    """The precondition, measured rather than assumed: every decision on this game leaves `_decide` at
    `click_native`, so the organ is indeed never called. This is CLASSIFIER 14's half that IS true."""
    p = _policy("cn01-route")
    emitted = _drive_frozen(p, _board(), 30)
    assert p.family == CLICK, p.family
    assert p._dec_exits.get("click_native", 0) >= 25, p._dec_exits
    assert set(emitted) == {"A6"}, sorted(set(emitted))
    assert p.n_modality_escalations == 0, p.n_modality_escalations


def test_the_meter_WOULD_escalate_but_the_organ_refuses_the_game():
    """The finding. The meter is frozen and holds an untried available label, so `EngagementMeter.escalate` -- the
    thing the arm assumed was the decision -- hands back `A7`. The ORGAN, given the identical labels at the
    identical moment, returns None. Reachability was never the binding constraint."""
    p = _policy("cn01-refuse")
    _drive_frozen(p, _board(), 30)
    labels = p._labels(list(CLICK_ONLY_AVAIL))
    assert p.engage.frozen() is True, p.engage.report()
    assert p.engage.escalate(labels) == "A7", (labels, p.engage.report())
    assert p._modality_escalate(labels) is None, (p.family, p._pre_esc_family)


def test_the_guard_not_the_reachability_is_what_excludes_the_game():
    """The A/B that isolates the guard. Two policies driven through IDENTICAL histories -- same board, same action
    set, same 30 steps, so the meter state is the same object-for-object -- differing only in `_pre_esc_family`.
    The exempt one gets None; the non-exempt one gets `A7`. One field, opposite outcomes, no other change."""
    a = _policy("cn01-ab-exempt")
    b = _policy("cn01-ab-open")
    g = _board()
    _drive_frozen(a, g, 30)
    _drive_frozen(b, g, 30)
    labels = a._labels(list(CLICK_ONLY_AVAIL))
    assert labels == b._labels(list(CLICK_ONLY_AVAIL))
    assert a.engage.report()["recent_window"] == b.engage.report()["recent_window"]

    assert a._modality_escalate(labels) is None                  # exempt: `_pre_esc_family is None`
    b._pre_esc_family = EFFECT                                   # the ONLY difference
    assert b._modality_escalate(labels) == "A7", b._esc_branch


def test_the_native_click_state_is_absorbing():
    """`_pre_esc_family` never becomes non-None on a natively-routed click game, so the exemption above can never
    lapse of its own accord. Driven long past the escalation window; the field is still None and the escalation
    counter is still zero."""
    p = _policy("cn01-absorb")
    _drive_frozen(p, _board(), 120)
    assert p._pre_esc_family is None, p._pre_esc_family
    assert p.n_modality_escalations == 0, p.n_modality_escalations
    assert p._esc_branch == {}, p._esc_branch


def test_every_non_None_assignment_to_pre_esc_family_lives_inside_the_organ():
    """The structural reason the state above is absorbing, pinned at the source so it cannot be quietly broken.
    If a future change assigns `_pre_esc_family` anywhere else -- in `_decide`, in routing, in a new organ -- the
    absorbing-state argument stops holding and this test fails, which is the notice that the argument must be
    re-derived rather than inherited."""
    src = inspect.getsource(policy_mod)
    organ = inspect.getsource(ReduxPolicy._modality_escalate)
    assigns = [ln.strip() for ln in src.splitlines()
               if "self._pre_esc_family =" in ln and not ln.strip().startswith("#")]
    non_none = [ln for ln in assigns if ln.split("=", 1)[1].split("#")[0].strip() != "None"]
    assert non_none, assigns                                     # the field is still assigned somewhere
    organ_lines = {o.strip() for o in organ.splitlines()}
    for ln in non_none:
        assert ln in organ_lines, (ln, sorted(organ_lines)[:5])


def test_the_two_guards_are_the_same_predicate():
    """The no-op proof. `_decide`'s `click_native` return and `_modality_escalate`'s exemption test the identical
    condition, so moving or scoping the former cannot change behaviour on the population it targets. If someone
    edits one of them, this test fails and the no-op claim has to be re-checked before it is cited again."""
    guard = "self.family == CLICK and self._pre_esc_family is None"
    dec = inspect.getsource(ReduxPolicy._decide)
    organ = inspect.getsource(ReduxPolicy._modality_escalate)
    assert guard in dec, dec[:400]
    assert guard in organ, organ[:400]
