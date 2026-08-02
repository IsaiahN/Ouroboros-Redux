"""The membrane: only policy crosses (never playback), promotion needs cross-role ECHO, and
seed-down descends verified members plus their (discounted) generalizations."""
from nexus.kernel import make_atom, Predicate
from nexus.membrane.rules import may_cross, is_policy, ActionReplay
from nexus.membrane.promote import echo_promote
from nexus.membrane.seed import seed_down, generalizations


def _pred(*kinds):
    return Predicate(frozenset(make_atom(k) if isinstance(k, str) else make_atom(*k) for k in kinds))


def test_policy_crosses_playback_does_not():
    assert is_policy(_pred("TOUCH"))
    assert may_cross(_pred("TOUCH"))
    assert not may_cross(ActionReplay((1, 2, 3)))       # a remembered sequence is playback (§7.2)


def test_echo_needs_two_distinct_roles():
    p = _pred("TOUCH")
    items = {str(p): p}
    assert echo_promote({str(p): {"Pioneer"}}, items) == []              # one role -> not echo
    assert echo_promote({str(p): {"Pioneer", "Optimizer"}}, items) == [str(p)]   # cross-role -> echo


def test_playback_never_promotes_even_with_echo():
    replay = ActionReplay((4, 4))
    items = {"r": replay}
    assert echo_promote({"r": {"Pioneer", "Optimizer", "Generalist"}}, items) == []


def test_seed_down_descends_members_and_discounted_generalizations():
    p = _pred("TOUCH", ("HAS_COLOUR", 1))               # size-2 member of Γ
    gamma = {str(p): p}
    seeds = seed_down(gamma, w_i=0.3)                    # low w_i -> strong Γ trust
    assert p in seeds
    for g in generalizations(p):
        assert g in seeds and seeds[g] < seeds[p]        # generalizations descend, but discounted
    # a high-w_i (self-trusting) role leans on Γ less
    assert seed_down(gamma, w_i=0.8)[p] < seeds[p]
