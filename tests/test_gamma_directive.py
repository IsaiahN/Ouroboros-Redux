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
        assert (ev.gamma_reached
                == ev.gamma_noseam + ev.gamma_empty + ev.gamma_error + ev.gamma_consulted == 1)
        assert (p._g_reached, p._g_noseam, p._g_empty, p._g_error) == (0, 0, 0, 0)   # zeroed with the segment

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


def test_a_raising_gamma_is_counted_apart_from_an_empty_one(monkeypatch):
    """★ THE FOURTH WAY, FOUND INSIDE THE FIX FOR THE OTHER THREE.

    `echo.directives` is wrapped in a bare `except` so a broken library can never sink a run. That guard used to
    increment the SAME counter as the honest `if not dirs` path -- so a Γ RAISING on every call and a Γ with
    nothing to say printed the identical number. A library that is broken and a library that is working but has
    no evidence yet need opposite fixes, and the counters that exist to separate exactly that were themselves
    conflating it. The swallow must stay (a run must not die on Γ) and the COUNT must split."""
    p = _policy()
    _sign_gamma(p, +1)

    def _boom(_gid):
        raise RuntimeError("Γ is broken")

    # `monkeypatch`, NOT a bare attribute set. Γ is a PROCESS-WIDE singleton (`policy.SHARED_ECHO`) and
    # conftest's autouse fixture calls `reset()`, which clears the library's DATA and not a patched METHOD -- so
    # the first draft of this test left every later test in the file running against a Γ that raised, and two of
    # them failed for a reason that had nothing to do with what they were pinning. The singleton bites the tests
    # the same way it bites the runs.
    monkeypatch.setattr(p.echo, "directives", _boom)
    assert p._gamma_directive(["A4", "A1"]) is None             # swallowed: the run survives
    assert (p._g_reached, p._g_error, p._g_empty, p._g_consult) == (1, 1, 0, 0)
    p.chain.note_step()
    p._close_segment("death")
    ev = p.receipts[-1]
    assert ev.gamma_error == 1 and ev.gamma_empty == 0
    assert ev.gamma_reached == ev.gamma_noseam + ev.gamma_empty + ev.gamma_error + ev.gamma_consulted == 1
    from newhorse.redux_arch.receipt import summary
    s = summary(p.receipts)["gamma_decision"]
    assert s["steps_error"] == 1 and s["steps_empty"] == 0


def test_gamma_is_snapshotted_at_ENTRY_as_well_as_at_CLOSE():
    """★ WHEN Γ HAD NOTHING, not just THAT it had nothing.

    The sweep printed `Γ had nothing for this game=18` beside an END-OF-RUN snapshot showing eight games with a
    signed directive available. Two readings fit that pair and need opposite work: the sign ARRIVED AFTER the
    site stopped being entered (Γ warms up too late -- a timing finding about capability), or it was already
    there and the guard refused it anyway (a defect). A close-time snapshot alone cannot tell them apart, so it
    is not a measurement. This pins the entry snapshot as the earlier of the pair."""
    from newhorse.redux_arch.receipt import summary
    p = _policy()
    assert p._gamma_directive(["A4", "A1"]) is None             # entered while Γ was empty
    _sign_gamma(p, +1)                                          # ...Γ warms up only AFTERWARDS
    p.chain.note_step()
    p._close_segment("death")
    ev = p.receipts[-1]
    assert ev.gamma_sign_report_at_entry["signed_at_2_families"] == 0
    assert ev.gamma_sign_report["signed_at_2_families"] == 1     # the close-time view, contradicting nothing
    s = summary(p.receipts)["gamma_decision"]
    assert s["segments_entered"] == 1
    assert s["segments_entered_gamma_signed"] == 0               # READS AS: a TIMING finding, not a broken guard
    assert s["entry_close_contradiction"] == 0
    assert s["sign_report_at_first_entry"]["signed_at_2_families"] == 0


def test_the_entry_close_contradiction_detector_can_actually_fire():
    """A detector that has never been seen to fire is a detector that might be dead. The live path above cannot
    produce this state (that is the point), so it is constructed directly: a segment that took the EMPTY branch
    while its own entry snapshot said Γ was signed. If that is ever real it is a DEFECT in the guard, and the
    sweep must say so loudly rather than reporting it as a capability."""
    from newhorse.redux_arch.receipt import ResidualEvent, summary
    ev = ResidualEvent(game="cc33-cccc", gamma_reached=1, gamma_empty=1,
                       gamma_sign_report_at_entry={"signed_at_2_families": 1})
    s = summary([ev])["gamma_decision"]
    assert s["entry_close_contradiction"] == 1
    assert s["segments_entered_gamma_signed"] == 1


def test_a_dead_diff_receipt_is_keyed_by_whether_a_BOUNDARY_diff_explains_it():
    """★ THE OPEN DENOMINATOR, AS A COLUMN RATHER THAN A STORY.

    R_tau filed 25 break events with 19 `diff_ran` -- six dead -- beside only four DIED_PRE_DIFF segments. There
    are two different diffs: this receipt's bit is whether the transition/click residual ran on THIS break event,
    while the LEDGER's bit can also be set by the §3.5 boundary diff at a level advance, which files no receipt
    of its own and lands in the NEXT segment. `boundary_diff_ran` is set from that boundary's own call site, so
    the reconciliation is a reading. A `boundary_diff=NO` row is the part that is still UNEXPLAINED and must be
    published as its own finding rather than absorbed."""
    from newhorse.redux_arch.receipt import ResidualEvent, summary
    evs = [ResidualEvent(game="g", diff_ran=False, stage="DIED_PRE_DIFF"),
           ResidualEvent(game="g", diff_ran=False, stage="MINT_UNFIRED", boundary_diff_ran=True),
           ResidualEvent(game="g", diff_ran=False, stage="MINT_UNFIRED", boundary_diff_ran=False),
           ResidualEvent(game="g", diff_ran=True, stage="MINT_UNFIRED")]
    dds = summary(evs)["dead_diff_stages"]
    assert dds == {"DIED_PRE_DIFF": 1, "MINT_UNFIRED|boundary_diff=yes": 1, "MINT_UNFIRED|boundary_diff=NO": 1}
    assert sum(dds.values()) == 3                                # the live-diff receipt is not in this histogram


def test_the_boundary_diff_flag_is_set_at_the_boundarys_own_call_site():
    """DIRECTIVE 1, applied to the flag itself: it must be written where the boundary diff actually runs, not
    inferred by the reader from `reason == "advance"`. Pinning the call site is what stops the next beat from
    'simplifying' it into a derivation -- which is how the old proxy lied."""
    import inspect
    from newhorse.redux_arch import policy as _p
    src = inspect.getsource(_p.ReduxPolicy._on_level_change)
    assert "self._seg_boundary_diff = True" in src
    assert src.index("note_diff") < src.index("self._seg_boundary_diff = True")


def test_producer_and_consumer_agree_on_the_gamma_key_SET():
    """★ THE DEFECT CLASS, PINNED STRUCTURALLY -- not one instance of it.

    `swarm.echo_pool` used to seed its pooled gamma dict from a HARDCODED key list and sum with `gd.get(k) or 0`,
    so any key the producer (`receipt.summary`) had not computed was rendered as a confident measured zero. That
    is how `reuse_attempted: 0` got printed inside both streams beside a pooled total of 17. Union pooling means a
    dropped key goes VISIBLY ABSENT instead. This test is the guard that keeps the two sides in step: a new
    counter added to the producer and forgotten in the consumer, or vice versa, fails here rather than in a sweep
    printout six hours later."""
    from newhorse.redux_arch.receipt import summary
    from newhorse.redux_arch.swarm import echo_pool
    p = _policy()
    _sign_gamma(p, +1)
    p.chain.note_step()
    p._gamma_directive(["A4", "A1"])
    p._close_segment("death")
    prod = summary(p.receipts)["gamma_decision"]
    pooled = echo_pool({"cc33-cccc": {"game": "cc33-cccc", "echo": summary(p.receipts),
                                      "tether_stage": {}, "levels": 1}})["echo"]["gamma_decision"]
    snap = {"sign_report", "sign_report_at_first_entry",
            "sign_report_by_game", "sign_report_at_first_entry_by_game"}
    assert set(prod) - snap == set(pooled) - snap
    assert set(prod) & snap                                      # the snapshots exist on the producer side...
    assert "sign_report_by_game" in pooled                       # ...and cross as PER-GAME views, never summed
    assert pooled["steps_directed"] == prod["steps_directed"] == 1


# ==================================================================================================================
# THE DECIDE FUNNEL. Reach is upstream of behaviour, and last beat's zero at the Γ site was a fact about the
# agent's CONTROL FLOW read as a fact about Γ. These five pin the instrument that can tell those apart.
# ==================================================================================================================

def _decision_returns(fn):
    """Every `return` that belongs to `fn` ITSELF -- nested helper functions are excluded, because their returns
    exit the helper, not the decision path."""
    import ast, inspect, textwrap
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    outer = tree.body[0]
    out, stack = [], list(outer.body)
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue                                            # a nested helper's returns are not exits
        if isinstance(n, ast.Return) and n.value is not None:
            out.append(ast.unparse(n.value))
        stack.extend(ast.iter_child_nodes(n))
    return out


def _drive(p, n):
    """Run `n` real decide->choose steps. `_policy()` pre-seeds ONE frame with no matching action, and `observe`
    keeps `frames` and `acts` parallel, so the seed is dropped first -- otherwise the basis learner indexes past
    the end of `acts` and the test fails for a reason that has nothing to do with the funnel."""
    p.frames = []
    for _ in range(n):
        p.observe(_board(), [1, 2, 3, 4], 0)
        p.choose()
    return p


def test_every_return_in_the_decision_path_is_counted_at_ITS_OWN_exit_site():
    """★ DIRECTIVE 1, APPLIED TO REACH. The funnel only works if the count happens at the `return` that is taken.
    A later beat that 'simplifies' one of these into a name derived from `self.family`, or that adds a sixth
    directional guard and forgets to wrap it, would silently move steps into a bucket that did not answer them --
    the proxy defect, one layer down. So the shape is pinned structurally rather than by one example.

    The ONE deliberate exception is the `_act_directional` dispatch: that call has NOT exited the decision path,
    and its five own returns do the counting. Wrapping it as well would double every directional step and close
    `sum(exits) == calls` by inflation -- the identity-closed-by-merging-terms defect the instrument caught in its
    own printer last beat."""
    from newhorse.redux_arch.policy import ReduxPolicy
    dec = _decision_returns(ReduxPolicy._decide)
    unwrapped = [r for r in dec if not r.startswith("self._exit(")]
    assert unwrapped == ["self._act_directional(labels)"], unwrapped
    dirn = _decision_returns(ReduxPolicy._act_directional)
    assert dirn and all(r.startswith("self._exit(") for r in dirn), dirn
    # Every site names itself with a LITERAL. A computed name would make the funnel a derivation of the thing it
    # is meant to audit, so the first argument is required to be a plain string at the site.
    import ast
    for r in dec + dirn:
        if r.startswith("self._exit("):
            first = ast.parse(r).body[0].value.args[0]
            assert isinstance(first, ast.Constant) and isinstance(first.value, str), r
    # The two exits BELOW the Γ site are what measures its reach from outside; if they are ever renamed, the
    # summary's `gamma_site_reach_from_below` goes quietly to zero, so the names are pinned here too.
    names = {ast.parse(r).body[0].value.args[0].value for r in dirn}
    assert {"dir_gamma", "dir_explore"} <= names, names


def test_the_funnel_identity_holds_on_a_LIVE_policy_and_nothing_is_uncounted():
    """`sum(exits) == calls` is the whole warrant for reading any percentage in this block. `calls` is incremented
    at the TOP of `_decide`, before any guard, so an exit added without a counter shows up as a positive
    `uncounted` HERE rather than as a plausible-looking histogram in a sweep six hours later."""
    from newhorse.redux_arch.receipt import summary
    p = _drive(_policy(), 6)
    assert p._dec_calls == 6
    assert sum(p._dec_exits.values()) == p._dec_calls
    p._close_segment("death")
    ev = p.receipts[-1]
    assert ev.decide_calls == 6 and sum(ev.decide_exits.values()) == 6
    f = summary(p.receipts)["decide_funnel"]
    assert f["calls"] == 6 and f["uncounted"] == 0
    assert sum(f["exits"].values()) == 6
    # Per-segment scoping, same as the Γ counters: an exit taken in this segment must not decorate the next one.
    assert p._dec_calls == 0 and p._dec_exits == {}


def test_the_gamma_sites_reach_is_counted_TWICE_and_the_difference_is_published():
    """Two independent counters of one event: `gamma_reached` from INSIDE `_gamma_directive`, and
    `dir_gamma + dir_explore` from the two exits BELOW it. If they ever disagree one of them is wrong, and the
    receipt publishes the difference rather than arbitrating it -- the point of a receipt is that it can be
    contradicted."""
    from newhorse.redux_arch.receipt import summary
    from newhorse.redux_arch import policy as _p
    p = _policy()
    p.frames = []
    for i in range(12):
        p.observe(_board(), [1, 2, 3, 4], 0)
        if i == 3:
            p.family = _p.DIRECTIONAL      # the synthetic board routes to EFFECT on its own, and an agreement
        p.choose()                          # between two counters that are both ZERO is not a measurement
    p._close_segment("death")
    f = summary(p.receipts)["decide_funnel"]
    below = f["exits"].get("dir_gamma", 0) + f["exits"].get("dir_explore", 0)
    assert below > 0, f["exits"]            # the directional path really ran, so the agreement below has content
    assert f["gamma_site_reach_from_below"] == below
    assert f["gamma_site_reach_disagreement"] == 0
    assert summary(p.receipts)["gamma_decision"]["steps_reached"] == below
    # ...and the detector is not dead: a hand-built event where the two counters disagree must SAY so.
    from newhorse.redux_arch.receipt import ResidualEvent
    bad = ResidualEvent(game="g", gamma_reached=0, decide_calls=1, decide_exits={"dir_explore": 1})
    assert summary([bad])["decide_funnel"]["gamma_site_reach_disagreement"] == 1


def test_the_unscored_dead_diff_row_is_split_by_the_SEGMENTS_REASON():
    """★ 'PROBABLY THE ADVANCE CASE' IS NOT A RECEIPT. `end_segment` returns None for exactly two situations --
    a deliberate ADVANCE (an advance is not a stall) and an EMPTY segment with no steps -- and last beat's sixth
    dead-diff receipt landed in one undifferentiated `(unscored)` bucket with no way to say which. The reason is
    already on the event; keying by it closes the row."""
    from newhorse.redux_arch.receipt import ResidualEvent, summary
    evs = [ResidualEvent(game="g", diff_ran=False, stage=None, reason="advance"),
           ResidualEvent(game="g", diff_ran=False, stage=None, reason="death"),
           ResidualEvent(game="g", diff_ran=False, stage=None, reason=""),
           ResidualEvent(game="g", diff_ran=False, stage="DIED_PRE_DIFF", reason="death")]
    dds = summary(evs)["dead_diff_stages"]
    assert dds == {"(unscored:advance)": 1, "(unscored:death)": 1,
                   "(unscored:unrecorded)": 1, "DIED_PRE_DIFF": 1}


def test_producer_and_consumer_agree_on_the_decide_funnel_key_SET():
    """The same guard as the Γ key-set test, for the new block: a counter added to `receipt.summary` and forgotten
    in `swarm.echo_pool` fails here instead of being rendered as a confident measured zero in a sweep printout.
    `exits` and `exit_games` cross as DICTS pooled by union -- `exit_games` counts the distinct GAMES behind each
    exit, because a pooled step count cannot answer 'on how many games did this happen?', which is exactly the
    defect that made one game's 18 steps read as a statement about the whole sweep."""
    from newhorse.redux_arch.receipt import summary
    from newhorse.redux_arch.swarm import echo_pool
    p = _drive(_policy(), 4)
    p._close_segment("death")
    prod = summary(p.receipts)["decide_funnel"]
    pooled = echo_pool({"cc33-cccc": {"game": "cc33-cccc", "echo": summary(p.receipts),
                                      "tether_stage": {}, "levels": 1}})["echo"]["decide_funnel"]
    assert set(prod) == set(pooled)
    assert pooled["calls"] == prod["calls"] == 4
    assert pooled["exits"] == prod["exits"]
    # one game in, so every present exit is behind exactly one game -- and the counts are of GAMES, not steps
    assert set(pooled["exit_games"]) == set(pooled["exits"])
    assert set(pooled["exit_games"].values()) == {1}


# ---------------------------------------------------------------------------------------------------------------
# ★★★ THE OUTCOME COLUMN: REACH IS NOT COMPETENCE. ★★★
# The funnel above says WHICH exit answered. Last beat it said `dir_target_colour` answered 461 steps across twelve
# games and pre-empts the Γ site on every one of them -- and nothing measured whether those answers were any good.
# "Should Γ be reached more?" is unanswerable while the incumbent is unpriced, and the temptation to move the Γ
# site earlier is exactly the calibration this project keeps refusing. So the incumbent gets priced first, by the
# cheapest honest question available: did the board ANSWER the step that exit chose?
# These tests pin the three ways that measurement could quietly lie: crediting an exit with a step whose action the
# survival veto replaced, pricing a step across a segment boundary, and reading a ticking budget bar as an answer.
# ---------------------------------------------------------------------------------------------------------------

def test_the_outcome_column_CLOSES_against_the_exit_counts_and_a_frozen_board_reads_null():
    """`exits == priced + veto-replaced + unpriced`, exactly, with the residue published rather than absorbed.
    The synthetic board is IDENTICAL every step, so the honest reading is that nothing the agent did answered --
    a column that reported motion here would be reporting the mask, or the frame counter, or nothing at all."""
    from newhorse.redux_arch.receipt import summary
    p = _drive(_policy(), 6)
    assert sum(p._dec_attr.values()) + sum(p._dec_veto.values()) + p._dec_unattr == 5
    assert p._pend_exit is not None                     # the sixth decision is still in flight, priced by nobody yet
    p._close_segment("death")
    f = summary(p.receipts)["decide_funnel"]
    priced, vetoed, unpriced = sum(f["attr"].values()), sum(f["veto"].values()), f["unpriced"]
    assert priced + vetoed + unpriced == sum(f["exits"].values()) == 6
    assert unpriced == 1                                # exactly the in-flight decision, charged to its own segment
    assert sum(f["moved"].values()) == 0 and sum(f["moved_raw"].values()) == 0
    assert p._dec_attr == {} and p._dec_unattr == 0     # per-segment, like every other counter on the receipt


def test_a_step_the_SURVIVAL_VETO_REPLACED_is_not_credited_to_the_exit_that_chose_it(monkeypatch):
    """The veto runs in `choose`, AFTER the exit has already counted itself, and it is allowed to change the label.
    The board change that follows is then the VETO's outcome, not the exit's. Crediting it either way -- as an
    answer or as a null -- attributes one organ's result to another, which is the whole defect the funnel exists
    to prevent, so those steps get their own bucket and leave the denominator."""
    from newhorse.redux_arch.policy import ReduxPolicy
    monkeypatch.setattr(ReduxPolicy, "_survival_veto", lambda self, lbl, data: ("A9", None))
    p = _drive(_policy(), 5)
    assert p._dec_attr == {}, p._dec_attr             # nothing priced: every emitted action was the veto's
    assert sum(p._dec_veto.values()) == 4, p._dec_veto
    assert sum(p._dec_exits.values()) == 5


def test_a_board_that_CHANGES_reads_as_answered_and_the_name_comes_from_the_EXIT_not_the_label():
    """The complement of the frozen case: when the board really does answer, the column says so, and it says so
    under the exit's own literal name. `_pend_exit` is written by `_exit` at the return that takes it -- never
    recomputed at attribution time from `self.family` or from the action that happened to be emitted."""
    p = _policy()
    p.frames = []
    for i in range(8):
        # ★ THE CHANGE MUST BE IN THE INTERIOR. A first version of this test flickered a 2x2 block in the top-left
        # CORNER and read 6 of 7 -- because a ratcheting block flush with two edges is exactly what
        # `monotone_band_mask` is built to strike out, so on the prefixes where the fill happened to be monotone
        # the mask ate the change. That is the mask working, not the column failing; a synthetic answer has to sit
        # where a budget bar cannot.
        g = np.zeros((20, 20), dtype=int)
        g[3, 3], g[3, 4] = 4, 5
        g[9:11, 9:11] = i % 5 + 1                       # four interior cells, a new colour every step
        p.observe(g, [1, 2, 3, 4], 0)
        p.choose()
    assert sum(p._dec_moved_raw.values()) == sum(p._dec_attr.values()) == 7
    assert sum(p._dec_moved.values()) == 7              # four cells: at the MIN_CELLS floor, not under it
    assert set(p._dec_attr) <= set(p._dec_exits)        # every priced name is an exit name, not an invented one
