"""
test_tether_brick.py -- the FIRST FIRING brick, tested at its real call sites.

What is under test is not "does a Consolidator work" (it did, unwired) but the four joints the measurement said were
missing: a residual that exists at a break event, a library that is offered that residual BEFORE anything is minted,
a Predicate OBJECT that survives the mint site, and a rendered receipt. Each test names the failure it would catch.
"""
from __future__ import annotations
import numpy as np
import pytest

from newhorse.redux_arch.abort_code import ChainSignals, Stage, classify
from newhorse.redux_arch.bridge import transition_residual
from newhorse.redux_arch.receipt import ResidualEvent, echo_kind, render, render_one, task_id
from newhorse.redux_arch.policy import ReduxPolicy

BG, WALL, CUR = 0, 3, 7
H = W = 9
VECS = {"RIGHT": (0, 1), "DOWN": (1, 0), "LEFT": (0, -1), "UP": (-1, 0)}


def _board(rc, walls=()):
    g = np.zeros((H, W), dtype=int)
    for w in walls:
        g[w] = WALL
    g[rc] = CUR
    return g


def _room(seed=0, n=44, wall_frac=0.30):
    """A room with scattered walls and a scripted action stream. Gamma's base rule -- 'the action displaces the
    cursor by its learned vector' -- is right on open cells and WRONG on a wall or a board edge, so the residual is
    mixed and INTENDED_FREE is the one before-state fact that predicts it exactly (an edge is blocked but has NO
    occupying colour, so INTENDED_COLOUR cannot match it -- the split is uniquely affordance's).

    Deterministic: same seed, same board, same script. Frames + the acts that produced them, with acts[i] the action
    taken FROM frames[i-1] (the alignment ReduxPolicy.observe maintains)."""
    rng = np.random.RandomState(seed)
    walls = set()
    for r in range(H):
        for c in range(W):
            if rng.rand() < wall_frac:
                walls.add((r, c))
    start = (H // 2, W // 2)
    walls.discard(start)
    labels = ["RIGHT", "DOWN", "LEFT", "UP"]
    script = [labels[i] for i in rng.randint(0, 4, size=n)]
    rc = start
    frames, acts = [_board(rc, walls)], ["RESET"]
    for lbl in script:
        dr, dc = VECS[lbl]
        nr, nc = rc[0] + dr, rc[1] + dc
        if 0 <= nr < H and 0 <= nc < W and (nr, nc) not in walls:
            rc = (nr, nc)
        frames.append(_board(rc, walls))
        acts.append(lbl)
    return frames, acts


# ---- 1. the residual organ itself -------------------------------------------------------------------------------

def test_transition_residual_distinguishes_could_not_run_from_found_nothing():
    """The failure this catches: collapsing 'no observable' into 'empty residual'. They indict different layers --
    DIED_PRE_DIFF is implementation, RESIDUAL_EMPTY is library/grain -- and a build that conflates them cannot be
    told which one it is suffering from."""
    frames, acts = _room()
    assert transition_residual(frames, acts, None, VECS) is None                   # no learned cursor colour
    assert transition_residual(frames, acts, CUR, {}) is None                      # no learned vecs
    assert transition_residual(frames, acts, CUR, {"NOPE": (0, 1)}) is None        # no TESTABLE step
    exc = transition_residual(frames, acts, CUR, VECS, passable={BG})
    assert exc is not None and len(exc) >= 20


def test_transition_residual_is_mixed_exactly_where_the_base_rule_fails():
    frames, acts = _room()
    exc = transition_residual(frames, acts, CUR, VECS, passable={BG})
    outcomes = [o for _, o in exc]
    assert set(outcomes) == {True, False}, "walls and edges must produce a MIXED residual"
    for ctx, moved in exc:
        assert ctx.intended_free == moved, "intended_free must be the before-state fact that predicts the move"


def test_uniform_stream_is_residual_empty_not_a_free_pass():
    """An empty room -> Γ is right every time -> pure residual -> nothing to mint. If this ever reported
    non-empty, the trigger would be manufacturing reach and the overturn test would have to revert it."""
    frames, acts = _room(wall_frac=0.0)
    exc = transition_residual(frames, acts, CUR, {"RIGHT": (0, 1)}, passable={BG})
    exc = [e for e in exc if e[0].intended_free]
    assert exc and all(o for _, o in exc)


# ---- 2. the classifier coercion ---------------------------------------------------------------------------------

def test_a_transfer_implies_a_mint():
    """Without this coercion a segment that TRANSFERRED without re-minting would be scored MINT_UNFIRED -- reporting
    the deepest thing the chain did as one of the shallowest."""
    s = ChainSignals(diff_ran=True, residual_nonempty=True, minted=False,
                     reuse_attempted=True, reused=True)
    assert classify(s) == Stage.USED_NOCLEAR


def test_classifier_still_cannot_be_over_credited_from_below():
    assert classify(ChainSignals()) == Stage.DIED_PRE_DIFF
    assert classify(ChainSignals(diff_ran=True)) == Stage.RESIDUAL_EMPTY
    assert classify(ChainSignals(diff_ran=True, residual_nonempty=True)) == Stage.MINT_UNFIRED
    assert classify(ChainSignals(diff_ran=True, residual_nonempty=True, minted=True)) == Stage.REUSE_UNWIRED
    assert classify(ChainSignals(diff_ran=True, residual_nonempty=True, minted=True,
                                 reuse_attempted=True)) == Stage.MINTED_UNUSED


# ---- 3. the echo-kind classifier (the weaker-claim caveat is DATA, not prose) ------------------------------------

def test_echo_kind_ranks_the_three_granularities():
    cur = task_id("aaa", 1, 7)
    assert echo_kind(cur, [task_id("bbb", 0, 1)]) == "cross-game"
    assert echo_kind(cur, [task_id("aaa", 0, 1)]) == "within-run-across-levels"
    assert echo_kind(cur, [task_id("aaa", 1, 1)]) == "within-run-across-segments"
    # STRONGEST, not average: one cross-game minting task makes the transfer a cross-game one
    assert echo_kind(cur, [task_id("aaa", 1, 1), task_id("bbb", 1, 2)]) == "cross-game"


def test_stream_tag_does_not_masquerade_as_a_different_game():
    """R_ρ and R_τ tasks on the SAME game must not render as 'cross-game'. Tagging the stream onto the game id
    would have done exactly that."""
    assert echo_kind(task_id("aaa", 0, 3, stream="tau"),
                     [task_id("aaa", 0, 1, stream="rho")]) == "within-run-across-segments"


# ---- 4. the brick end-to-end, driven through ReduxPolicy's REAL segment-close path -------------------------------

def _feed(pol, frames, acts):
    for f, a in zip(frames, acts):
        pol.frames.append(np.asarray(f))
        pol.acts.append(a)
        pol.chain.note_step()


def _armed_policy(gid="synthetic"):
    pol = ReduxPolicy(game_id=gid)
    pol.cursor, pol.vecs, pol.passable, pol.stride = CUR, dict(VECS), {BG}, 1
    return pol


def test_residual_pass_mints_and_echo_promotes_then_a_third_task_FIRES():
    """The whole brick. Three break events on structurally-identical-but-distinct tasks:
      seg 0 -- residual computed, φ minted, HELD (1/2 tasks). Γ empty => NOT counted as a reuse attempt.
      seg 1 -- φ minted again on a different task => PROMOTED into Γ.
      seg 2 -- the FRESH residual is offered to Γ BEFORE minting, and a promoted φ explains it => a FIRING.
    The failure this catches is the one the last six passes shipped: a mechanism that is correct, wired, and inert."""
    pol = _armed_policy()
    for seed in (1, 2, 3):
        frames, acts = _room(seed=seed)
        _feed(pol, frames, acts)
        pol._close_segment("death")

    evs = pol.receipts
    assert len(evs) == 3
    assert all(e.diff_ran and e.residual_nonempty for e in evs), "R_tau must exist at a DEATH, not only at an advance"
    assert evs[0].minted and not evs[0].promoted and not evs[0].reuse_attempted
    assert evs[1].minted and evs[1].promoted, "a second distinct task must push phi over the echo threshold"
    assert evs[2].reuse_attempted, "a non-empty library must be offered the FRESH residual"
    assert evs[2].fired, "a promoted phi that compresses a residual it was not minted for is a FIRING"
    assert evs[2].transfer_gain_bits > 0.0
    assert evs[2].echo_kind == "within-run-across-segments"
    assert evs[2].stage == Stage.USED_NOCLEAR.name, "transfer without acting on it tops out at USED_NOCLEAR"
    assert evs[2].minted_on and all("#" in t for t in evs[2].minted_on)


def test_reuse_attempt_is_never_noted_against_an_empty_library():
    """MINTED_UNUSED is the ONLY code that indicts the architecture. Noting an 'attempt' against an empty Γ would
    manufacture it out of a wiring gap -- the precise dishonesty this instrument exists to prevent."""
    pol = _armed_policy()
    frames, acts = _room()
    _feed(pol, frames, acts)
    pol._close_segment("death")
    assert pol.receipts[0].reuse_attempted is False
    assert pol.receipts[0].stage == Stage.REUSE_UNWIRED.name


def test_no_observable_reports_died_pre_diff_and_writes_no_receipt():
    pol = ReduxPolicy(game_id="synthetic")          # cursor/vecs never learned
    frames, acts = _room()
    _feed(pol, frames, acts)
    pol._close_segment("death")
    assert pol.receipts == []
    assert pol.chain.report()["furthest_stage"] == Stage.DIED_PRE_DIFF.name


def test_empty_segment_is_a_no_op_not_a_stall():
    pol = _armed_policy()
    pol._close_segment("run_end")
    assert pol.chain.report()["stalls"] == 0
    assert pol.receipts == []


def test_segment_window_rebases_so_one_residual_cannot_be_counted_twice():
    pol = _armed_policy()
    frames, acts = _room(seed=1)
    _feed(pol, frames, acts)
    pol._close_segment("death")
    first = pol.receipts[0].n_exceptions
    frames2, acts2 = _room(seed=2)
    _feed(pol, frames2, acts2)
    pol._close_segment("death")
    assert pol.receipts[1].n_exceptions == first, "the second segment must see ONLY its own steps"


def test_advance_close_keeps_the_redraw_frame_and_is_never_scored():
    pol = _armed_policy()
    frames, acts = _room()
    _feed(pol, frames, acts)
    pol._close_segment("advance")
    assert pol.chain.report()["advances"] == 1
    assert pol.chain.report()["stalls"] == 0
    assert pol.receipts[0].stage is None, "an advance is a clear by SEARCH/DRIVE and is never a tether stage"
    assert pol._seg0 == len(pol.frames) - 1


def test_echo_report_never_sums_firing_kinds_together():
    pol = _armed_policy()
    for seed in (1, 2, 3):
        frames, acts = _room(seed=seed)
        _feed(pol, frames, acts)
        pol._close_segment("death")
    rep = pol.echo_report()
    assert rep["fired"] == 1
    assert rep["firing_kinds"] == {"within-run-across-segments": 1}
    assert rep["library"], "a promoted phi must be visible in Gamma"


# ---- 5. the receipt ---------------------------------------------------------------------------------------------

def test_render_of_a_firing_carries_all_six_fields_and_the_weaker_claim_caveat():
    pol = _armed_policy("m0r0")
    for seed in (1, 2, 3):
        frames, acts = _room(seed=seed)
        _feed(pol, frames, acts)
        pol._close_segment("death")
    ev = [e for e in pol.receipts if e.fired][0]
    txt = render_one(ev)
    for field in ("BASE FAILED HERE", "RESIDUAL WAS", "PHI RE-MINTED HERE", "EVALUATED BEFORE",
                  "PHI FIRED HERE", "THAT CLEARED", "ECHO KIND", "CAVEAT"):
        assert field in txt
    assert "WEAKEST" in txt, "a within-run echo must carry its weaker-claim caveat IN the receipt"
    assert "USED_NOCLEAR" in txt


def test_no_firing_renders_a_count_not_a_verdict():
    txt = render([ResidualEvent(game="x", diff_ran=True), ResidualEvent(game="x", diff_ran=True, minted=True)])
    assert "NO FIRING" in txt and "break events=2" in txt
    assert "TETHER FIRING RECEIPT" not in txt, "no receipt may be rendered for an event that did not fire"


def test_receipt_roundtrips_through_the_dict_the_swarm_ships():
    pol = _armed_policy("m0r0")
    for seed in (1, 2, 3):
        frames, acts = _room(seed=seed)
        _feed(pol, frames, acts)
        pol._close_segment("death")
    ds = pol.firing_receipts()
    assert len(ds) == 1
    back = [ResidualEvent(**{k: v for k, v in d.items() if k != "fired"}) for d in ds]
    assert back[0].fired and render(back).count("TETHER FIRING RECEIPT") == 1


def test_the_uncleared_note_stays_true_or_this_test_fails():
    """USED_NOCLEAR's `indicts` field reads 'drive'. That reading is WRONG while `note_transfer_clear` has no call
    site -- the ceiling is a wiring fact, not a verdict on the drive layer. The receipt says so in words; this test
    is what keeps those words true. When the operator layer IS wired, this fails and the note must be rewritten."""
    import pathlib
    from newhorse.redux_arch.receipt import UNCLEARED_NOTE
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "newhorse"
    callers = [p.name for p in root.rglob("*.py")
               if p.name not in ("abort_code.py", "receipt.py") and "note_transfer_clear(" in p.read_text()]
    assert callers == [], (
        "note_transfer_clear now has call sites %s -- USED_NOCLEAR is no longer a wiring ceiling, so "
        "receipt.UNCLEARED_NOTE is stale and must be rewritten before this can pass." % callers)
    assert "no call site" in UNCLEARED_NOTE
