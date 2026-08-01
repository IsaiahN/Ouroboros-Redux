"""★★★ THE CLICK ORGAN'S EXEMPTION: ONE PREDICATE, AND HOW WIDE IT IS. ★★★

HISTORY, KEPT BECAUSE IT IS THE REASON THIS FILE EXISTS. CLASSIFIER 14 read: "a natively click-routed game never
reaches the escalation organ; `_decide` returns at the `click_native` exit before `_modality_escalate` is called,"
and the NEXT list turned that into an arm -- move or scope the `click_native` return so the organ gets consulted,
because "the gate is OPEN and reachability is the whole of it."

That reasoning did not survive contact with the source (CLASSIFIER 16). `_decide` guarded its `click_native` return
with `self.family == CLICK and self._pre_esc_family is None`, and `_modality_escalate` opened with a COPY of the
same expression returning None. On exactly the population the arm targeted, control arriving at the organ changed
nothing: the organ refused the game on its own account, and the state was ABSORBING, because the only assignment of
a non-None value to `_pre_esc_family` lives INSIDE the organ, downstream of that guard. The arm was a no-op, and it
was killed by reading the code instead of by spending a sweep on it.

WHAT CHANGED ON 2026-08-01. The two copies became ONE method, `_click_organ_exempt()`, and the exemption it encodes
was NARROWED: the click organ owns a game outright only while that game ADVERTISES no non-click action. A
click-only game is unchanged, bit for bit, which is what protects the banked click win. A game that offers an
action it has never tried, while its board has been frozen for a full window, is no longer anybody's to own.

`NEWHORSE_CLICK_EXEMPT=broad` restores the old predicate EXACTLY, and is the control arm. Every test below that
cares about the difference states which setting it is asserting under, and the pair that must agree asserts
agreement rather than asserting a value twice.
"""
import inspect
import os
import pathlib

import numpy as np
import pytest

from newhorse.redux_arch.policy import ReduxPolicy, CLICK, EFFECT
from newhorse.redux_arch import policy as policy_mod


CLICK_ONLY_AVAIL = (6,)                    # the whole action set is click -- nothing exists to escalate TO
CLICK_PLUS_AVAIL = (6, 7)                  # no direction, but ONE untried alternative: the `su15` shape


@pytest.fixture
def broad(monkeypatch):
    """The control arm's predicate, in-process. The production read happens once at import; a test that wants the
    other setting patches the constant rather than re-importing, so both arms run against the same module object."""
    monkeypatch.setattr(policy_mod, "CLICK_EXEMPT", "broad")
    return "broad"


@pytest.fixture
def narrow(monkeypatch):
    monkeypatch.setattr(policy_mod, "CLICK_EXEMPT", "narrow")
    return "narrow"


def _policy(gid="cn01-native"):
    p = ReduxPolicy(game_id=gid)
    p.frames = []
    return p


def _board():
    g = np.zeros((20, 20), dtype=int)
    g[3, 3], g[3, 4] = 4, 5
    return g


def _drive_frozen(p, g, n, avail=CLICK_PLUS_AVAIL):
    """A board that never answers. Family CLICK by action-set routing, `frozen` True after the window."""
    labels = []
    for _ in range(n):
        p.observe(g.copy(), list(avail), 0)
        lbl, _d = p.choose()
        labels.append(lbl)
    return labels


# --------------------------------------------------------------------------------------------------------------
# 1. THE CONTROL ARM: the old predicate, still exactly the old behaviour.
# --------------------------------------------------------------------------------------------------------------

def test_broad_a_click_routed_game_stays_at_the_native_exit_forever(broad):
    """CLASSIFIER 14's half that IS true, pinned as the control. Under the old predicate every decision on this
    game leaves `_decide` at `click_native`, the organ is never called, and the untried label is never emitted."""
    p = _policy("cn01-route")
    emitted = _drive_frozen(p, _board(), 30)
    assert p.family == CLICK, p.family
    assert p._dec_exits.get("click_native", 0) >= 25, p._dec_exits
    assert set(emitted) == {"A6"}, sorted(set(emitted))
    assert p.n_modality_escalations == 0, p.n_modality_escalations


def test_broad_the_meter_WOULD_escalate_but_the_organ_refuses_the_game(broad):
    """The finding that killed the reachability arm. The meter is frozen and holds an untried available label, so
    `EngagementMeter.escalate` -- the thing the arm assumed was the decision -- hands back `A7`. The ORGAN, given
    the identical labels at the identical moment, returns None. Reachability was never the binding constraint."""
    p = _policy("cn01-refuse")
    _drive_frozen(p, _board(), 30)
    labels = p._labels(list(CLICK_PLUS_AVAIL))
    assert p.engage.frozen() is True, p.engage.report()
    assert p.engage.escalate(labels) == "A7", (labels, p.engage.report())
    assert p._modality_escalate(labels) is None, (p.family, p._pre_esc_family)


def test_broad_the_guard_not_the_reachability_is_what_excludes_the_game(broad):
    """The A/B that isolates the guard. Two policies driven through IDENTICAL histories -- same board, same action
    set, same 30 steps, so the meter state is the same object-for-object -- differing only in `_pre_esc_family`.
    The exempt one gets None; the non-exempt one gets `A7`. One field, opposite outcomes, no other change."""
    a = _policy("cn01-ab-exempt")
    b = _policy("cn01-ab-open")
    g = _board()
    _drive_frozen(a, g, 30)
    _drive_frozen(b, g, 30)
    labels = a._labels(list(CLICK_PLUS_AVAIL))
    assert labels == b._labels(list(CLICK_PLUS_AVAIL))
    assert a.engage.report()["recent_window"] == b.engage.report()["recent_window"]

    assert a._modality_escalate(labels) is None                  # exempt: `_pre_esc_family is None`
    b._pre_esc_family = EFFECT                                   # the ONLY difference
    assert b._modality_escalate(labels) == "A7", b._esc_branch


def test_broad_the_native_click_state_is_absorbing(broad):
    """`_pre_esc_family` never becomes non-None on a natively-routed click game, so under the old predicate the
    exemption can never lapse of its own accord. Driven long past the escalation window."""
    p = _policy("cn01-absorb")
    _drive_frozen(p, _board(), 120)
    assert p._pre_esc_family is None, p._pre_esc_family
    assert p.n_modality_escalations == 0, p.n_modality_escalations
    assert p._esc_branch == {}, p._esc_branch


# --------------------------------------------------------------------------------------------------------------
# 2. THE TREATMENT: a frozen click game that advertises an alternative gets to try it.
# --------------------------------------------------------------------------------------------------------------

def test_narrow_a_frozen_click_game_with_an_untried_action_escalates(narrow):
    """The intervention, at its cheapest instance. Same board, same action set, same 30 steps as the control above
    -- and now the untried label is actually emitted. The escalation is counted at the organ's own site."""
    p = _policy("cn01-narrow")
    emitted = _drive_frozen(p, _board(), 30)
    assert p.family == CLICK, p.family
    assert "A7" in set(emitted), sorted(set(emitted))
    assert p.n_modality_escalations > 0, p.n_modality_escalations
    assert p._dec_exits.get("escalate", 0) > 0, p._dec_exits


def test_narrow_the_escalation_is_bounded_and_hands_the_game_back(narrow):
    """REVERSIBILITY, which is the whole reason the narrowing is safe to ship. `A7` is null too, so once its fair
    trial completes the meter has no untried label left, the organ returns None, and the game falls through to the
    click dispatch. A change that could strand a click game in a dead modality would show up here as an emission
    set that never returns to `A6`."""
    p = _policy("cn01-bounded")
    emitted = _drive_frozen(p, _board(), 120)
    assert "A7" in set(emitted) and "A6" in set(emitted), sorted(set(emitted))
    assert emitted[-1] == "A6", emitted[-20:]
    assert p._dec_exits.get("family_click", 0) > 0, p._dec_exits
    # bounded: the untried modality gets its window, not the budget
    assert emitted.count("A7") <= 40, emitted.count("A7")


def test_narrow_a_click_only_action_set_is_untouched(narrow):
    """THE SAFETY PROOF FOR THE BANKED WIN, stated as an affordance and not as a game id. When the advertised
    action set is click-only there is nothing to escalate to, so the narrowed predicate returns exactly what the
    broad one returned: every decision still leaves at `click_native`, and no escalation is ever counted."""
    p = _policy("cn01-clickonly")
    emitted = _drive_frozen(p, _board(), 60, avail=CLICK_ONLY_AVAIL)
    assert p.family == CLICK, p.family
    assert set(emitted) == {"A6"}, sorted(set(emitted))
    assert p._dec_exits.get("click_native", 0) >= 55, p._dec_exits
    assert p._dec_exits.get("escalate", 0) == 0, p._dec_exits
    assert p.n_modality_escalations == 0, p.n_modality_escalations


def test_the_two_arms_AGREE_on_a_click_only_game(monkeypatch):
    """The pair that must agree, asserted as agreement rather than as two copies of a value. Same board, same
    action set, same length, both settings -- identical emissions and identical exit maps. This is the receipt
    that the narrowing cannot regress a game whose whole action set is click."""
    out = {}
    g = _board()
    for setting in ("broad", "narrow"):
        monkeypatch.setattr(policy_mod, "CLICK_EXEMPT", setting)
        p = _policy("cn01-agree-%s" % setting)
        out[setting] = (_drive_frozen(p, g, 60, avail=CLICK_ONLY_AVAIL), dict(p._dec_exits))
    assert out["broad"][0] == out["narrow"][0], (out["broad"][0][:8], out["narrow"][0][:8])
    assert out["broad"][1] == out["narrow"][1], (out["broad"][1], out["narrow"][1])


def test_the_two_arms_AGREE_off_the_click_family(monkeypatch):
    """CROSS-FAMILY VALIDATION. A game that advertises directions is routed somewhere other than CLICK, so the
    predicate cannot reach it under either setting. Identical emissions and identical exits, on a family the
    change has no business touching."""
    out = {}
    g = _board()
    for setting in ("broad", "narrow"):
        monkeypatch.setattr(policy_mod, "CLICK_EXEMPT", setting)
        p = _policy("cn01-dir-%s" % setting)
        out[setting] = (_drive_frozen(p, g, 40, avail=(1, 2, 3, 4, 5, 6)), dict(p._dec_exits))
    assert out["broad"][0] == out["narrow"][0], (out["broad"][0][:8], out["narrow"][0][:8])
    assert out["broad"][1] == out["narrow"][1], (out["broad"][1], out["narrow"][1])


# --------------------------------------------------------------------------------------------------------------
# 3. STRUCTURE: the properties the argument above rests on, pinned at the source.
# --------------------------------------------------------------------------------------------------------------

def test_every_non_None_assignment_to_pre_esc_family_lives_inside_the_organ():
    """The structural reason the absorbing-state argument holds, pinned so it cannot be quietly broken. If a future
    change assigns `_pre_esc_family` anywhere else -- in `_decide`, in routing, in a new organ -- the argument stops
    holding and this test fails, which is the notice that it must be re-derived rather than inherited."""
    src = inspect.getsource(policy_mod)
    organ = inspect.getsource(ReduxPolicy._modality_escalate)
    assigns = [ln.strip() for ln in src.splitlines()
               if "self._pre_esc_family =" in ln and not ln.strip().startswith("#")]
    non_none = [ln for ln in assigns if ln.split("=", 1)[1].split("#")[0].strip() != "None"]
    assert non_none, assigns                                     # the field is still assigned somewhere
    organ_lines = {o.strip() for o in organ.splitlines()}
    for ln in non_none:
        assert ln in organ_lines, (ln, sorted(organ_lines)[:5])


def test_the_exemption_has_exactly_one_definition_and_both_sites_call_it():
    """THE SUCCESSOR TO THE TWO-COPIES TEST, and strictly stronger than it. The old test asserted that a guard
    STRING appeared in both functions, which detects drift only after it happens. There is now one method, and both
    sites call it, so the two guards cannot differ at all. If someone inlines either call, this fails."""
    dec = inspect.getsource(ReduxPolicy._decide)
    organ = inspect.getsource(ReduxPolicy._modality_escalate)
    assert "self._click_organ_exempt()" in dec, dec[:400]
    assert "self._click_organ_exempt()" in organ, organ[:400]
    src = inspect.getsource(policy_mod)
    assert src.count("def _click_organ_exempt") == 1, src.count("def _click_organ_exempt")
    # and the old duplicated expression is gone from both, so it cannot be revived by copy-paste
    stale = "self.family == CLICK and self._pre_esc_family is None"
    assert stale not in dec.replace(inspect.getsource(ReduxPolicy._click_organ_exempt), ""), "guard re-inlined"


def test_a_click_game_that_is_not_exempt_has_its_own_dispatch_arm():
    """The trap this change had to avoid, written down. Before 2026-08-01 the `click_native` return was not only a
    guard, it was the CLICK family's ONLY dispatch: narrowing the guard without adding an arm would have dropped a
    non-exempt click game into `_act_fallback`. The exit literal `family_click` is that arm, and it is a DIFFERENT
    literal from `click_native` so the funnel can say which of the two paths answered."""
    dec = inspect.getsource(ReduxPolicy._decide)
    assert '"family_click"' in dec, dec[-800:]
    assert dec.index('"family_click"') < dec.index('"family_fallback"'), "fallback would shadow the click arm"


def test_the_switch_is_read_once_and_never_by_a_decision_function():
    """The control-arm hygiene rule this repo runs on: an environment switch is read ONCE, at import, and a
    decision function reads the constant, never the environment. If `os.environ` grows a second reader of this
    name anywhere in the package, the two arms stop being comparable and this fails."""
    root = pathlib.Path(policy_mod.__file__).resolve().parent.parent
    hits = []
    for path in root.rglob("*.py"):
        for i, ln in enumerate(path.read_text().splitlines(), 1):
            if "NEWHORSE_CLICK_EXEMPT" in ln and "environ" in ln:
                hits.append("%s:%d" % (path.relative_to(root), i))
    assert hits == ["redux_arch/policy.py:%d" % _switch_line()], hits
    assert policy_mod.CLICK_EXEMPT in ("narrow", "broad"), policy_mod.CLICK_EXEMPT


def _switch_line() -> int:
    p = pathlib.Path(policy_mod.__file__)
    for i, ln in enumerate(p.read_text().splitlines(), 1):
        if "NEWHORSE_CLICK_EXEMPT" in ln and "environ" in ln:
            return i
    raise AssertionError("the switch is not read anywhere")


def test_the_default_is_narrow_when_the_environment_says_nothing(monkeypatch):
    """A shipped default is a decision, so it gets a receipt too. With the variable unset the package must come up
    NARROW; the control arm must be something a reader has to ask for explicitly."""
    monkeypatch.delenv("NEWHORSE_CLICK_EXEMPT", raising=False)
    assert (os.environ.get("NEWHORSE_CLICK_EXEMPT") or "narrow").strip().lower() == "narrow"
