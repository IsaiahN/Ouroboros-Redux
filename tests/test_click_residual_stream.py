"""
test_click_residual_stream.py -- THE SECOND EVIDENCE STREAM, AND WHY IT IS A SECOND STREAM AND NOT A WIDER FIRST ONE.

Last beat established the classifier behind the biggest pile on the board: `DIED_PRE_DIFF` is not a perception
failure and not "segments too short". It measures how much of the game set R_τ is STRUCTURALLY UNABLE TO ADDRESS.
`policy._route` learns a focus colour and a displacement map at exactly one site, and that site is the same one
that commits `family = DIRECTIONAL`; every non-directional family reaches its branch only AFTER both basis
learners have already returned nothing. So R_τ cannot run on click / effect / two-body / multi-avatar games, and
neither can the residual bank, which is fed from the residual pass.

The fork was named last beat and is CHOSEN here: option (b), a second stream. The refusals are recorded in the
HEARTBEAT and, for the one that needs code to make sense of it, in `click_residual`'s own docstring:

  (a) WIDEN R_τ'S PRECONDITION -- refused. There is nothing to widen. `learn_basis` and `learn_basis_trailaware`
      have BOTH already run and failed by the time a game is called CLICK or EFFECT, and a click-only game has no
      directional actions at all, so no action -> displacement map exists to be wrong about. Widening therefore
      means either lowering the bar inside the basis learners until they report a cursor that is not there -- which
      is calibrating the instrument to make it read higher, the one thing the discipline forbids outright -- or
      writing a new detector, which directive 4 has frozen. Cheapest-by-directive-2 was cheap only until it was
      looked at.

  (b) A SECOND STREAM -- CHOSEN, on the condition that it needs no new vocabulary and has a live carrier. Both hold.
      The predicate a click game wants ("clicking colour c does something") is ALREADY constructible from
      HAS_COLOUR / INTENDED_COLOUR / INTENDED_FREE, so no atom, referent kind, relation or `_find_*` is added; the
      freeze is intact. The carrier check found the one real gap and it was instrumentation, not perception: the
      clicked CELL was thrown away the instant it was emitted, so `self.click_rc` now records it beside `self.acts`.

  (c) RE-SCOPE THE NORTH-STAR TO DIRECTIONAL GAMES -- refused. The standing directive is "chase coverage of all
      games; we need a generalized agent", and accepting the scope at the exact moment a zero-vocabulary carrier
      turned out to have a live instance would be conceding coverage that was available.

§5.3 is load-bearing here and is tested below: A STREAM IS A GROUND, AND GROUNDS ARE ASSESSED PER STREAM. R_κ is
tried ONLY where R_τ could not run, its receipts are TAGGED, its bank is keyed separately, and `summary()` reports
per stream -- so the next sweep stays attributable and a second stream arriving can never be read as the first
stream improving.
"""
from __future__ import annotations

import numpy as np

from newhorse.redux_arch.bridge import click_residual, transition_residual
from newhorse.redux_arch.minting import two_part_mdl
from newhorse.redux_arch.policy import ReduxPolicy
from newhorse.redux_arch.receipt import ResidualEvent, summary

BG, LIVE, DEAD = 0, 3, 7


def _blank(h: int = 10, w: int = 10):
    return np.full((h, w), BG, dtype=int)


def _scene():
    """A board with LIVE buttons on row 2 and DEAD decoration on row 6. Clicking LIVE changes the board; clicking
    anything else does not. The rule is colour-gated and lives in the EXISTING atom vocabulary."""
    g = _blank()
    g[2, 2] = g[2, 4] = g[2, 6] = LIVE
    g[6, 2] = g[6, 4] = g[6, 6] = DEAD
    return g


def _click_run(cells):
    """Play `cells` as a sequence of clicks on `_scene()`; a click on a LIVE cell paints one background pixel."""
    g = _scene()
    frames, acts, rcs, paint = [g.copy()], ["RESET"], [None], 0
    for (r, c) in cells:
        if int(g[r, c]) == LIVE:
            paint += 1
            g = g.copy()
            g[8, paint] = LIVE                          # the board answered
        frames.append(g.copy()); acts.append("A6"); rcs.append((r, c))
    return frames, acts, rcs


# ---- the stream itself: every silence has a NAMED reason, exactly as R_τ's does -----------------------------
def test_no_coordinate_anywhere_is_named_not_silent():
    rep = {}
    frames = [_blank(), _blank()]
    assert click_residual(frames, ["RESET", "A1"], [None, None], report=rep) is None
    assert rep["reason"] == "no_click_coords"


def test_a_one_frame_segment_is_named_too_short():
    rep = {}
    assert click_residual([_blank()], ["RESET"], [(1, 1)], report=rep) is None
    assert rep["reason"] == "segment_too_short"


def test_every_coordinate_off_board_is_no_testable_step_not_no_coords():
    """The two silences indict different layers: 'the agent took no coordinate actions' is a routing fact, 'it took
    them and every one was off the board' is an aiming bug. Collapsing them would repeat the DIED_PRE_DIFF mistake
    one layer down."""
    rep = {}
    frames = [_blank(), _blank(), _blank()]
    out = click_residual(frames, ["RESET", "A6", "A6"], [None, (99, 99), (-4, 2)], report=rep)
    assert out is None
    assert rep["reason"] == "no_testable_step"
    assert rep["scan_off_board"] == 2 and rep["scan_no_coord"] == 0


def test_the_scan_counters_are_an_identity_the_instrument_must_satisfy():
    rep = {}
    frames, acts, rcs = _click_run([(2, 2), (6, 2), (2, 4), (5, 5)])
    frames.append(frames[-1]); acts.append("A1"); rcs.append(None)      # a non-coordinate action in the middle
    frames.append(frames[-1]); acts.append("A6"); rcs.append((77, 3))   # ...and one off the board
    exc = click_residual(frames, acts, rcs, report=rep)
    assert exc is not None
    assert rep["scan_pairs"] == rep["scan_no_coord"] + rep["scan_off_board"] + len(exc)


def test_the_context_carries_the_before_state_colour_under_the_clicked_cell():
    frames, acts, rcs = _click_run([(2, 2), (6, 2)])
    exc = click_residual(frames, acts, rcs)
    assert [ctx.focus_colour for ctx, _ in exc] == [LIVE, DEAD]
    assert [ctx.focus_rc for ctx, _ in exc] == [(2, 2), (6, 2)]
    assert [moved for _, moved in exc] == [True, False]
    # degenerate BY CONSTRUCTION and said out loud: no displacement, no landmark
    assert all(ctx.action_vec == (0, 0) and ctx.target_rc == ctx.focus_rc for ctx, _ in exc)


def test_background_clicks_are_marked_intended_free_and_coloured_ones_are_not():
    frames, acts, rcs = _click_run([(9, 9), (2, 2)])
    exc = click_residual(frames, acts, rcs)
    assert [ctx.intended_free for ctx, _ in exc] == [True, False]


# ---- the load-bearing check: the EXISTING vocabulary already contains the click rule ------------------------
def test_the_click_residual_mints_from_the_frozen_atom_vocabulary():
    """THE CHECK THAT MADE (b) THE CHEAP OPTION. If minting a click residual had needed a new atom, this would have
    been a taxonomy extension wearing a stream's clothes and directive 4 would have refused it. It does not: the
    colour-gated affordance is already expressible, so the second stream costs zero vocabulary."""
    cells = [(2, 2), (6, 2), (2, 4), (6, 4), (2, 6), (6, 6), (9, 9), (2, 2), (5, 1), (6, 2)]
    frames, acts, rcs = _click_run(cells)
    exc = click_residual(frames, acts, rcs)
    assert exc is not None and len({o for _, o in exc}) == 2, "the residual must be MIXED or there is nothing to split"
    mint = two_part_mdl(exc, max_size=2)
    assert mint is not None, "a perfectly colour-separable click residual must be mintable from the frozen DSL"
    assert "3" in str(mint.predicate), "the minted φ should key on the colour that actually gates the effect"


def test_a_residual_with_no_structure_still_refuses_to_mint():
    """The gate is not a rubber stamp just because a new stream feeds it: every click inert -> uniform -> no mint."""
    frames, acts, rcs = _click_run([(6, 2), (6, 4), (6, 6), (9, 9), (5, 5), (4, 4)])
    exc = click_residual(frames, acts, rcs)
    assert exc is not None and not any(o for _, o in exc)
    assert two_part_mdl(exc, max_size=2) is None


# ---- the policy wiring: ordering, tagging, attribution ------------------------------------------------------
def _feed(pol, frames, acts, rcs):
    for f, a, rc in zip(frames, acts, rcs):
        pol.frames.append(np.asarray(f)); pol.acts.append(a); pol.click_rc.append(rc); pol.chain.note_step()


def test_a_click_segment_now_files_a_receipt_tagged_to_the_second_stream():
    pol = ReduxPolicy("g")
    frames, acts, rcs = _click_run([(2, 2), (6, 2), (2, 4), (6, 4), (2, 6), (9, 9)])
    _feed(pol, frames, acts, rcs)
    ev = pol._residual_pass("death")
    assert ev is not None and ev.diff_ran is True
    assert ev.stream == "R_click", "R_τ cannot run here, so the receipt must name the stream that did"
    assert ev.n_exceptions == len(rcs) - 1


def test_the_second_stream_is_only_ever_tried_where_the_first_could_not_run():
    """THE ATTRIBUTION GUARANTEE. R_κ runs strictly downstream of an R_τ that returned None, so it cannot inflate
    any stage R_τ already reached -- which is what lets the next sweep read ALL movement out of DIED_PRE_DIFF as
    R_κ's and nothing else's. If this ordering is ever reversed, that reading is void."""
    pol = ReduxPolicy("g")
    cur, wall = 4, 8
    def board(r, c):
        g = np.full((8, 8), BG, dtype=int)
        g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = wall
        g[r, c] = cur
        return g
    frames, acts, rcs, c = [board(3, 3)], ["RESET"], [None], 3
    for _ in range(6):
        c = min(6, c + 1)
        frames.append(board(3, c)); acts.append("RIGHT"); rcs.append((3, c))   # a coordinate is present ANYWAY
    pol.cursor, pol.vecs = cur, {"RIGHT": (0, 1)}
    _feed(pol, frames, acts, rcs)
    ev = pol._residual_pass("death")
    assert ev is not None and ev.diff_ran is True
    assert ev.stream == "R_tau", "a segment R_τ can answer must never be re-attributed to the second stream"


def test_when_both_streams_are_silent_BOTH_classifiers_are_recorded():
    """No receipt means no diagnosis -- and one receipt carrying only half the diagnosis is the same failure at half
    scale. A segment neither stream could address must say so twice."""
    pol = ReduxPolicy("g")
    frames = [_blank(), _blank(), _blank()]
    _feed(pol, frames, ["RESET", "A1", "A1"], [None, None, None])
    ev = pol._residual_pass("death")
    assert ev is not None and ev.diff_ran is False
    assert ev.no_diff_reason == "no_focus_colour"          # R_τ's classifier, unchanged
    assert ev.click_no_diff_reason == "no_click_coords"    # ...and R_κ's beside it


def test_the_two_streams_are_banked_under_separate_keys():
    """Pooling an R_κ residual with an R_τ one would sum two grounds INSIDE the mint, invisibly, since the pool is
    only ever seen as a count."""
    pol = ReduxPolicy("g")
    frames, acts, rcs = _click_run([(2, 2), (6, 2), (2, 4), (6, 4), (2, 6), (9, 9)])
    _feed(pol, frames, acts, rcs)
    seen = {}
    pol.bank.deposit = lambda key, tid, exc, _s=seen: _s.setdefault("key", key)
    pol.bank.pool = lambda key, exclude_task=None: ([], [])
    pol._residual_pass("death")
    assert seen["key"] == "g:R_click"


# ---- the reporting layer: streams are never summed ----------------------------------------------------------
def test_summary_reports_per_stream_and_never_adds_them():
    evs = [ResidualEvent(game="g", stream="R_tau", diff_ran=True, residual_nonempty=True, minted=True,
                         stage="MINT_UNFIRED"),
           ResidualEvent(game="g", stream="R_tau", diff_ran=False, stage="DIED_PRE_DIFF"),
           ResidualEvent(game="h", stream="R_click", diff_ran=True, stage="RESIDUAL_EMPTY"),
           ResidualEvent(game="h", stream="R_click", diff_ran=True, residual_nonempty=True, stage="MINT_UNFIRED")]
    s = summary(evs)
    assert s["break_events"] == 4
    bs = s["by_stream"]
    assert set(bs) == {"R_tau", "R_click"}
    assert bs["R_tau"]["diff_ran"] == 1 and bs["R_click"]["diff_ran"] == 2
    assert bs["R_tau"]["stages"] == {"DIED_PRE_DIFF": 1, "MINT_UNFIRED": 1}
    assert bs["R_click"]["stages"] == {"MINT_UNFIRED": 1, "RESIDUAL_EMPTY": 1}
    assert sum(v["break_events"] for v in bs.values()) == s["break_events"], \
        "the per-stream breakdown must ACCOUNT for every receipt -- partition, not sample"


def test_a_click_game_that_never_clicked_is_distinguishable_from_one_whose_clicks_all_missed():
    evs = [ResidualEvent(game="g", diff_ran=False, no_diff_reason="no_focus_colour",
                         click_no_diff_reason="no_click_coords"),
           ResidualEvent(game="g", diff_ran=False, no_diff_reason="no_focus_colour",
                         click_no_diff_reason="no_testable_step", scan_off_board=9)]
    s = summary(evs)
    assert s["click_no_diff_reasons"] == {"no_click_coords": 1, "no_testable_step": 1}
    assert s["click_scan"]["off_board"] == 9


# ---- cross-family validation: the stream must stay silent where it has no business speaking -----------------
def test_the_click_stream_refuses_a_directional_segment_that_carried_no_coordinates():
    """Cross-family: a DIRECTIONAL game emits labels with no coordinate, so R_κ must return None rather than invent
    a cell. A second stream that answers everywhere would be a proxy, not a ground."""
    frames = [_blank(), _blank(), _blank(), _blank()]
    rep = {}
    assert click_residual(frames, ["RESET", "UP", "DOWN", "LEFT"], [None] * 4, report=rep) is None
    assert rep["reason"] == "no_click_coords"


def test_the_first_stream_is_untouched_by_any_of_this():
    """The R_τ path must read EXACTLY as it did before the second stream existed, or the sweep-to-sweep comparison
    the whole measurement rests on is broken."""
    cur = 4
    def board(r, c):
        g = np.full((8, 8), BG, dtype=int)
        g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = 8
        g[r, c] = cur
        return g
    frames, acts, c = [board(3, 3)], ["RESET"], 3
    for _ in range(6):
        c = min(6, c + 1)
        frames.append(board(3, c)); acts.append("RIGHT")
    rep = {}
    exc = transition_residual(frames, acts, cur, {"RIGHT": (0, 1)}, report=rep)
    assert exc is not None and rep["reason"] is None
    assert rep["scan_pairs"] == rep["scan_no_vec"] + rep["scan_unlocatable"] + len(exc)


# ---- the label must match the stream, in the task id AND on the printed receipt ------------------------------
def test_the_task_id_carries_the_stream_so_an_echo_cannot_cross_streams_unlabelled():
    """`task_id` has carried a `stream` field since R_ρ was described, exactly so a φ that echoed ACROSS streams is
    readable as having echoed on different evidence. The first live sweep of R_κ filed everything under `.tau`,
    which is not a cosmetic slip: the echo clock counts DISTINCT task ids, so a click segment and a transition
    segment would have counted as two sightings with nothing in the record saying they came from different grounds."""
    pol = ReduxPolicy("g")
    frames, acts, rcs = _click_run([(2, 2), (6, 2), (2, 4), (6, 4), (2, 6), (9, 9)])
    _feed(pol, frames, acts, rcs)
    ev = pol._residual_pass("death")
    assert ev.stream == "R_click" and ev.task_id.endswith(".click")


def test_the_printed_firing_receipt_names_the_stream_it_actually_used():
    from newhorse.redux_arch.receipt import render_one
    ev = ResidualEvent(game="g", stream="R_click", diff_ran=True, residual_nonempty=True,
                       n_exceptions=30, n_positive=2, baseline_bits=10.6,
                       transferred="INTENDED_COLOUR==9", minted_on=["h#L0#s0.click"], task_id="g#L0#s2.click")
    out = render_one(ev)
    assert "R_click:" in out and "R_tau:" not in out
