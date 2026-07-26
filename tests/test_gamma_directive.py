"""
THE DECISION SITE: Γ -> ACTION.

`policy._gamma_directive` is the first and only place a rule learned on one game can choose what the agent does
on a different one. These tests pin the four refusals it is built out of -- no directives means no attempt, a tie
is not a preference, the context is the residual site's construction and not a fabricated one, and a negative
sign endorses ¬φ rather than meaning nothing -- and, most importantly, they pin the OVER-CREDIT GUARD: this
organ writes the same ledger signal the `explains` route writes, so it is exactly the kind of wiring that can
make the instrument read higher without the agent being better.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
from newhorse.redux_arch.dsl import Context, Predicate, make_atom
from newhorse.redux_arch.minting import Mint
from newhorse.redux_arch.abort_code import ChainSignals, Stage, classify
from newhorse.redux_arch.policy import ReduxPolicy

PHI = Predicate(frozenset({make_atom("INTENDED_FREE")}))
VECS = {"A1": (-1, 0), "A2": (1, 0), "A3": (0, -1), "A4": (0, 1)}
LABELS = ["A1", "A2", "A3", "A4"]


def _ctx(free: bool) -> Context:
    return Context(focus_rc=(3, 3), focus_colour=4, target_rc=(3, 3), action_vec=(0, 1),
                   intended_free=free, intended_colour=(0 if free else 5))


def _split(pos_rate: float, neg_rate: float, n: int = 100):
    return ([(_ctx(True), i < int(round(pos_rate * n))) for i in range(n)]
            + [(_ctx(False), i < int(round(neg_rate * n))) for i in range(n)])


def _board():
    """A 7x7 board, cursor 4 at (3,3), walled to the RIGHT only. Exactly one candidate action is non-free, so a
    φ over `intended_free` separates the four moves and can be observed to pick."""
    g = np.zeros((7, 7), dtype=int)
    g[3, 3] = 4
    g[3, 4] = 5
    return g


def _policy(game_id="cc33-cccc", walled_right=True):
    p = ReduxPolicy(game_id=game_id)
    p.frames = [_board()]
    p.cursor = 4
    p.vecs = dict(VECS)
    p.passable = {0}
    p.stride = 1
    return p


def _sign_gamma(p, direction=+1, families=("wa30-aaaa", "sb26-bbbb")):
    """Put ONE signed φ into the shared Γ, minted by families that are not the policy's own game."""
    exc = _split(0.9, 0.2) if direction > 0 else _split(0.1, 0.9)
    for t in families:
        p.echo.observe_mint(t, Mint(predicate=PHI, saved_bits=1.0, support=len(exc)), exceptions=exc)
    return p.echo


def test_no_directives_means_no_consult_and_no_ledger_signal():
    """REFUSAL (2). Γ is empty, so this is not an attempt. Counting it would manufacture MINTED_UNUSED -- the one
    code that indicts the architecture -- out of bookkeeping."""
    p = _policy()
    assert p._gamma_directive(LABELS) is None
    assert p._g_consult == 0 and p._g_act == 0
    assert p.chain._sig.reuse_attempted is False and p.chain._sig.reused is False


def test_an_unsigned_library_is_still_no_consult():
    """Γ non-empty but carrying no agreed sign. A partition is not advice, and the site must not fall back to
    'any promoted φ will do'."""
    p = _policy()
    for t in ("wa30-aaaa", "sb26-bbbb"):
        p.echo.observe_mint(t, Mint(predicate=PHI, saved_bits=1.0, support=10))   # no exceptions -> no sign
    assert len(p.echo.library) == 1
    assert p._gamma_directive(LABELS) is None
    assert p._g_consult == 0
    assert p.chain._sig.reuse_attempted is False


def test_a_signed_directive_picks_the_endorsed_action_and_emits_from_this_call_site():
    """A POSITIVE sign on INTENDED_FREE endorses the free moves. Three of the four are free and one is walled --
    so the three free moves TIE and Γ is refused the pick. Narrowing the offer to one free move and the wall is
    what makes the endorsement decidable, and the ledger must move only then."""
    p = _policy()
    _sign_gamma(p, +1)
    assert p._gamma_directive(["A4", "A1", "A2"]) is None       # A1 and A2 both free -> tie, no preference
    assert p._g_consult == 1 and p._g_act == 0
    assert p.chain._sig.reuse_attempted is True                 # Γ DID speak: that is an attempt
    assert p.chain._sig.reused is False                         # ...and it did not decide anything
    assert p._gamma_directive(["A4", "A1"]) == "A1"             # A4 walks into the wall, A1 does not
    assert p._g_act == 1 and p.chain._sig.reused is True


def test_a_negative_sign_endorses_not_phi():
    """A negative delta means the outcome lives on the ¬φ side. Reading that as 'no opinion' would discard half
    of what was measured; here it must pick the move INTO the wall."""
    p = _policy()
    _sign_gamma(p, -1)
    assert p.echo.sign(PHI) == -1
    assert p._gamma_directive(["A1", "A4"]) == "A4"
    assert p._g_act == 1


def test_a_game_is_never_advised_by_its_own_family():
    """φ signed only by the family of the game being advised is memory, not transfer."""
    p = _policy(game_id="wa30-zzzz")
    _sign_gamma(p, +1)
    assert p._gamma_directive(["A4", "A1"]) is None
    assert p._g_consult == 0


def test_no_learned_cursor_or_vecs_means_the_seam_cannot_evaluate():
    """The audit's second blocker, in code: every promoted φ reads a Context field the seam must SUPPLY. With no
    calibrated cursor there is no before-state, and a fabricated one would have φ answering about a board that
    does not exist."""
    p = _policy()
    _sign_gamma(p, +1)
    p.cursor = None
    assert p._gamma_directive(["A4", "A1"]) is None
    assert p._g_consult == 0                                    # not even a consult: nothing to consult WITH
    p2 = _policy()
    _sign_gamma(p2, +1)
    p2.frames = [np.zeros((7, 7), dtype=int)]                   # cursor colour absent from the board
    assert p2._gamma_directive(["A4", "A1"]) is None
    assert p2._g_consult == 1 and p2._g_uneval == 2             # consulted, and every candidate was unevaluable


def test_a_directive_cannot_lift_a_segment_that_never_computed_a_residual():
    """★ THE OVER-CREDIT GUARD, stated as the arithmetic rather than as an intention.

    `note_reuse` from this site sets the SAME segment signal the `explains` route sets, and `classify` coerces
    'reused implies minted'. If that coercion also bypassed the earlier links, a directive taken in a segment
    where perception was inert would report USED_NOCLEAR -- stage 5 -- on a stall that never computed anything.
    It does not: the diff and residual gates are checked first and a directive cannot forge them. This is the
    property that makes it safe to let this organ write to the ledger at all."""
    assert classify(ChainSignals(reused=True)) is Stage.DIED_PRE_DIFF
    assert classify(ChainSignals(diff_ran=True, reused=True)) is Stage.RESIDUAL_EMPTY
    # where the earlier links ARE real, a directive is a genuine transfer that cleared nothing
    assert classify(ChainSignals(diff_ran=True, residual_nonempty=True,
                                 reused=True)) is Stage.USED_NOCLEAR


def test_the_receipt_says_which_organ_reused_and_why_a_zero_is_a_zero():
    """A ledger signal with two possible authors is unattributable. `reuse_source` names the author, and
    `gamma_sign_report` says whether a zero came from an empty Γ, an all-ours Γ, or a Γ whose signs reversed."""
    p = _policy()
    _sign_gamma(p, +1)
    p.chain.note_step()
    p._gamma_directive(["A4", "A1"])
    p._close_segment("death")
    ev = p.receipts[-1]
    assert ev.reuse_source == "directive" and ev.gamma_actions == 1 and ev.gamma_consulted == 1
    assert ev.transferred is None                               # nothing EXPLAINED a residual
    assert ev.gamma_sign_report["foreign"] == 1
    assert ev.gamma_sign_report["signed_at_2_families"] == 1
    assert p._g_consult == 0 and p._g_act == 0                  # tally zeroed with the segment


def test_a_directive_is_not_counted_as_a_firing():
    """`fired` is defined as 'a promoted φ explained a residual it was not minted for'. A φ that steered an
    action explained nothing. Folding the two would make the single number this whole instrument is judged on go
    up for a reason it was never defined to count."""
    from newhorse.redux_arch.receipt import summary, firings
    p = _policy()
    _sign_gamma(p, +1)
    p.chain.note_step()
    p._gamma_directive(["A4", "A1"])
    p._close_segment("death")
    assert firings(p.receipts) == []
    s = summary(p.receipts)
    assert s["fired"] == 0
    assert s["gamma_decision"]["steps_directed"] == 1
    assert s["gamma_decision"]["reuse_by_directive"] == 1
    assert s["gamma_decision"]["reuse_by_explains"] == 0


def test_the_three_ways_a_zero_can_happen_are_distinguishable():
    """★ THE AMBIGUOUS ZERO, CLOSED.

    The first sweep of this organ printed `segments where Γ had advice=0` next to a Γ snapshot showing six games
    ending with a signed directive available, and no number on the record could say which of three findings it
    was: the site was never entered, it was entered without a calibrated seam, or it was entered with a live seam
    and Γ offered nothing. Each has a different fix, so a single zero is a silence printed as a measurement --
    the exact failure this instrument exists to prevent, introduced by me. These three counters separate them,
    and the funnel must ADD UP: reached == noseam + empty + advice."""
    from newhorse.redux_arch import policy as _pmod
    from newhorse.redux_arch.receipt import summary

    never = _policy()                                          # (a) never entered
    assert never._g_reached == 0

    empty = _policy()                                          # (c) entered, live seam, Γ silent
    assert empty._gamma_directive(["A4", "A1"]) is None
    assert (empty._g_reached, empty._g_noseam, empty._g_empty, empty._g_consult) == (1, 0, 1, 0)

    # Γ is a PROCESS-WIDE singleton (`policy.SHARED_ECHO`), so `_policy()` does not hand out a fresh library --
    # conftest resets it per TEST, not per policy. Signing it below would retroactively arm the `empty` case, so
    # the silent case is measured first and the reset is explicit rather than implied by construction order.
    _pmod.SHARED_ECHO.reset()

    noseam = _policy()
    _sign_gamma(noseam, +1)
    noseam.cursor = None                                       # (b) entered, no calibrated seam
    assert noseam._gamma_directive(["A4", "A1"]) is None
    assert (noseam._g_reached, noseam._g_noseam, noseam._g_empty, noseam._g_consult) == (1, 1, 0, 0)

    advised = _policy()
    assert advised._gamma_directive(["A4", "A1"]) == "A1"
    assert (advised._g_reached, advised._g_noseam, advised._g_empty, advised._g_consult) == (1, 0, 0, 1)

    # all three land on the receipt, and the funnel closes there too
    for p in (noseam, empty, advised):
        p.chain.note_step()
        p._close_segment("death")
        ev = p.receipts[-1]
        assert ev.gamma_reached == ev.gamma_noseam + ev.gamma_empty + ev.gamma_consulted == 1
        assert (p._g_reached, p._g_noseam, p._g_empty) == (0, 0, 0)         # zeroed with the segment

    s = summary([p.receipts[-1] for p in (noseam, empty, advised)])["gamma_decision"]
    assert (s["steps_reached"], s["steps_noseam"], s["steps_empty"], s["steps_consulted"]) == (3, 1, 1, 1)


def test_directives_are_last_resort_and_never_override_an_earned_drive():
    """Placed after every earned drive in `_act_directional`: Γ advises only where the agent had no reason of its
    own. A first wiring that could override a confirmed relation target would make any change in outcome
    unattributable between the two organs."""
    import inspect
    from newhorse.redux_arch import policy as _p
    src = inspect.getsource(_p.ReduxPolicy._act_directional)
    assert src.index("_gamma_directive") > src.index("_relation_selected")
    assert src.index("_gamma_directive") > src.index("target_colour")
    assert src.index("_gamma_directive") < src.index("self._explore(")
