"""
THE SIGN: whether Γ carries a PREFERENCE, not just a partition.

A promoted φ says "these two groups of steps behave differently". That is not advice. To change an action you
also need to know WHICH SIDE to be on, and the offline audit (`tools/audit_gamma.py`) measured that Γ carried no
such quantity at all: promoting the same predicate through two Mints whose outcome-derived numbers differed
produced byte-identical library state. These tests pin the carriage that fixes that, and -- more importantly --
they pin the BAR, because the same audit found the one action-ranking φ that echoed across two families had
OPPOSITE signs on them (+0.70 on wa30, -0.98 on re86). Pooling those would have produced a confident number that
was maximally wrong on one of the two games. So: every voting family must agree, one dissent kills the sign, and
a killed sign is the correct output rather than a failure.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
from newhorse.redux_arch.dsl import Context, Predicate, make_atom
from newhorse.redux_arch.minting import Mint
from newhorse.redux_arch.consolidate import Consolidator
from newhorse.redux_arch import bridge


PHI = Predicate(frozenset({make_atom("INTENDED_FREE")}))


def _ctx(free: bool, vec=(0, 1)) -> Context:
    return Context(focus_rc=(2, 2), focus_colour=4, target_rc=(2, 2), action_vec=vec,
                   intended_free=free, intended_colour=(0 if free else 5))


def _split(pos_rate: float, neg_rate: float, n: int = 100):
    """A residual whose outcome depends on φ with the given rates on each side of the split."""
    out = []
    for i in range(n):
        out.append((_ctx(True), i < int(round(pos_rate * n))))
    for i in range(n):
        out.append((_ctx(False), i < int(round(neg_rate * n))))
    return out


def _mint(exc):
    return Mint(predicate=PHI, saved_bits=1.0, support=len(exc))


def test_agreeing_families_yield_a_signed_directive_for_a_third_game():
    con = Consolidator(echo_threshold=2)
    con.observe_mint("wa30-aaaa", _mint(_split(0.9, 0.2)), exceptions=_split(0.9, 0.2))
    con.observe_mint("sb26-bbbb", _mint(_split(0.8, 0.3)), exceptions=_split(0.8, 0.3))
    assert len(con.library) == 1
    assert con.sign(PHI) == 1
    dirs = con.directives("cc33-cccc")
    assert [str(p) for p, _ in dirs] == [str(PHI)] and dirs[0][1] == 1


def test_a_negative_delta_signs_negative():
    con = Consolidator(echo_threshold=2)
    con.observe_mint("wa30-aaaa", _mint(_split(0.1, 0.9)), exceptions=_split(0.1, 0.9))
    con.observe_mint("sb26-bbbb", _mint(_split(0.2, 0.8)), exceptions=_split(0.2, 0.8))
    assert con.sign(PHI) == -1
    assert con.directives("cc33-cccc")[0][1] == -1


def test_self_transfer_is_refused_by_the_sign_not_by_foreign():
    """φ signed only by the family of the game being advised is not transfer, it is memory.

    ★ THE TWO GUARDS ARE SCOPED DIFFERENTLY AND THIS TEST RECORDS WHICH ONE ACTUALLY DOES THE WORK. `foreign` is
    INSTANCE-scoped: it asks whether this exact game id minted φ, so `wa30-zzzz` counts a φ minted on
    `wa30-aaaa` as foreign and would happily offer it. `exclude_game` inside `sign` is FAMILY-scoped, so it drops
    wa30's vote entirely and the corroboration bar goes unmet. The refusal below therefore comes from the SIGN,
    not from `foreign` -- writing it down because a test that passes for the wrong reason is a mislabelled
    receipt, and because it means the instance-level `foreign` count is NOT a within-family transfer guard and
    must not be cited as one."""
    con = Consolidator(echo_threshold=2)
    con.observe_mint("wa30-aaaa", _mint(_split(0.9, 0.2)), exceptions=_split(0.9, 0.2))
    con.observe_mint("sb26-bbbb", _mint(_split(0.8, 0.3)), exceptions=_split(0.8, 0.3))
    assert len(con.foreign("wa30-zzzz")) == 1              # foreign does NOT refuse a sibling instance...
    assert con.sign(PHI, exclude_game="wa30-zzzz") is None  # ...the family-scoped sign does
    assert con.directives("wa30-zzzz") == []
    assert con.directives("wa30-aaaa") == []               # and the minting instance itself, doubly


def test_one_dissenting_family_kills_the_sign():
    """THE MEASURED FAILURE THIS BAR EXISTS FOR. Two families agree, a third reverses -- the pooled average would
    still look confident. The sign must die instead."""
    con = Consolidator(echo_threshold=2)
    con.observe_mint("wa30-aaaa", _mint(_split(0.9, 0.2)), exceptions=_split(0.9, 0.2))
    con.observe_mint("sb26-bbbb", _mint(_split(0.8, 0.3)), exceptions=_split(0.8, 0.3))
    assert con.sign(PHI) == 1
    con.observe_mint("re86-cccc", _mint(_split(0.05, 0.95)), exceptions=_split(0.05, 0.95))
    assert con.sign(PHI) is None
    assert con.directives("cc33-cccc") == []


def test_two_instances_of_one_family_are_one_vote():
    """`ls20-016295f7` and `ls20-99999999` are the same family and are declared to share semantics, so their
    agreement is not corroboration. Counting them twice would clear a two-family bar with a one-family claim --
    the source-amnesia error one layer up."""
    con = Consolidator(echo_threshold=2)
    con.observe_mint("ls20-aaaa", _mint(_split(0.9, 0.2)), exceptions=_split(0.9, 0.2))
    con.observe_mint("ls20-bbbb", _mint(_split(0.9, 0.2)), exceptions=_split(0.9, 0.2))
    assert len(con.library) == 1                            # two TASKS did echo it
    assert con.sign(PHI) is None                            # ...but only ONE family voted
    assert con.sign(PHI, min_families=1) == 1


def test_a_mint_without_exceptions_carries_no_sign():
    """The argument is optional and every existing call site omits it. Omitting it must leave Γ exactly as it was
    -- promoted, unsigned, silent -- rather than defaulting to some direction."""
    con = Consolidator(echo_threshold=2)
    con.observe_mint("wa30-aaaa", _mint(_split(0.9, 0.2)))
    con.observe_mint("sb26-bbbb", _mint(_split(0.9, 0.2)))
    assert len(con.library) == 1
    assert con.sign(PHI) is None and con.directives("cc33-cccc") == []


def test_sign_report_distinguishes_the_ways_a_zero_can_happen():
    """A zero that says nothing reads exactly like an unwired organ -- the failure this whole instrument exists to
    prevent. Each of these zeros has a different cause and the report must separate them."""
    con = Consolidator(echo_threshold=2)
    assert con.sign_report("cc33-cccc")["library"] == 0                       # nothing promoted at all
    con.observe_mint("wa30-aaaa", _mint(_split(0.9, 0.2)), exceptions=_split(0.9, 0.2))
    con.observe_mint("sb26-bbbb", _mint(_split(0.8, 0.3)), exceptions=_split(0.8, 0.3))
    own = con.sign_report("wa30-aaaa")
    assert own["library"] == 1 and own["foreign"] == 0                        # promoted, but all of it is ours
    other = con.sign_report("cc33-cccc")
    assert other["foreign"] == 1 and other["foreign_with_split"] == 1
    assert other["signed_at_1_family"] == 1 and other["signed_at_2_families"] == 1
    con.observe_mint("re86-cccc", _mint(_split(0.05, 0.95)), exceptions=_split(0.05, 0.95))
    rev = con.sign_report("cc33-cccc")
    assert rev["foreign_with_split"] == 1                                     # evidence is there...
    assert rev["signed_at_2_families"] == 0                                   # ...and it REVERSES


def test_an_empty_side_cannot_vote():
    """A family that only ever saw φ true has no ¬φ side to compare against. A delta computed off a zero
    denominator is not a weak signal, it is not a signal."""
    con = Consolidator(echo_threshold=2)
    one_sided = [(_ctx(True), True) for _ in range(50)]
    con.observe_mint("wa30-aaaa", _mint(one_sided), exceptions=one_sided)
    con.observe_mint("sb26-bbbb", _mint(_split(0.8, 0.3)), exceptions=_split(0.8, 0.3))
    assert con.sign(PHI, min_families=1) == 1               # sb26 can speak
    assert con.sign(PHI) is None                            # wa30 cannot, so the bar is unmet


# ---- the SECOND half of the wiring: the context a decision is made on must be the context φ was fitted to ----

def _board():
    g = np.zeros((7, 7), dtype=int)
    g[3, 3] = 4                                             # the cursor
    g[3, 4] = 5                                             # a wall to its right
    return g


def test_decision_context_is_the_same_construction_as_the_residual_site():
    """φ was fitted on contexts built by `affordance_step`. If a decision site built its own, φ would still
    evaluate and would silently be answering a DIFFERENT question -- `target_rc` meaning a goal instead of the
    focus itself, `intended_free` keyed off a background guess instead of the calibrated passable set. A
    predicate asked the wrong question still returns a bool, which is exactly why this must be one function."""
    before = _board()
    after = _board(); after[3, 3] = 0; after[2, 3] = 4      # the focus moved up
    passable = {0}
    for vec in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        step = bridge.affordance_step(before, after, 4, vec, stride=1, passable=passable)
        ctx = bridge.decision_context(before, 4, vec, stride=1, passable=passable)
        assert step is not None and ctx is not None
        assert step[0] == ctx                               # identical, field for field


def test_decision_context_distinguishes_the_candidate_actions():
    """The whole reason a φ can rank actions is that its inputs VARY across the candidates at one step. Here the
    wall makes exactly one direction non-free; a φ over `intended_free` therefore separates the moves. (A φ over
    `focus_colour` would not, which is why the audit ruled `colour==9` unable to rank anything.)"""
    before = _board()
    free = {v: bridge.decision_context(before, 4, v, stride=1, passable={0}).intended_free
            for v in ((-1, 0), (1, 0), (0, -1), (0, 1))}
    assert free[(0, 1)] is False                            # into the wall
    assert all(free[v] for v in ((-1, 0), (1, 0), (0, -1)))
    colours = {bridge.decision_context(before, 4, v, stride=1, passable={0}).focus_colour
               for v in ((-1, 0), (1, 0), (0, -1), (0, 1))}
    assert len(colours) == 1                                # constant across candidates -> cannot rank


def test_decision_context_is_none_when_the_focus_is_off_the_board():
    """No cursor, no before-state. Returning a fabricated Context here is how a φ ends up answering about a board
    that does not exist."""
    assert bridge.decision_context(np.zeros((5, 5), dtype=int), 4, (0, 1)) is None
    assert bridge.decision_context(_board(), 4, (0, 0)) is None
