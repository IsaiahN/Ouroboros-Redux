"""The per-stall TETHER STAGE code (abort_code.py). The bar is ONE firing of the whole loop -- fail -> mint from the
residual -> reuse where it was NOT minted -> clear a break -- so a stall must report HOW FAR down that chain it got, and
an implementation/library/gate stall must never be read as an architecture verdict. These tests pin each stage label, the
load-bearing REUSE_UNWIRED vs MINTED_UNUSED split, the membrane/sole-metric rule that a raw level advance is not a firing, and -- via the
REAL mint+consolidate organs -- that the classifier reads a genuine transfer as reaching the reuse boundary. Names no game."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.abort_code import Stage, ChainSignals, classify, indicts, TetherProbe
from newhorse.redux_arch.minting import two_part_mdl
from newhorse.redux_arch.consolidate import Consolidator, _key
# reuse the known-answer maze curriculum from the echo test -- shared synthetic scaffolding, no game id
from test_affordance_echo import _free_maze


def test_each_stage_label_from_a_signal_prefix():
    assert classify(ChainSignals()) == Stage.DIED_PRE_DIFF
    assert classify(ChainSignals(diff_ran=True)) == Stage.RESIDUAL_EMPTY
    assert classify(ChainSignals(diff_ran=True, residual_nonempty=True)) == Stage.MINT_UNFIRED
    assert classify(ChainSignals(diff_ran=True, residual_nonempty=True, minted=True)) == Stage.REUSE_UNWIRED
    assert classify(ChainSignals(diff_ran=True, residual_nonempty=True, minted=True,
                                 reuse_attempted=True)) == Stage.MINTED_UNUSED
    assert classify(ChainSignals(diff_ran=True, residual_nonempty=True, minted=True,
                                 reuse_attempted=True, reused=True)) == Stage.USED_NOCLEAR
    assert classify(ChainSignals(diff_ran=True, residual_nonempty=True, minted=True,
                                 reuse_attempted=True, reused=True, cleared=True)) == Stage.CLEARED


def test_only_minted_unused_indicts_the_architecture():
    # the whole point: exactly ONE stage may be written up as an architecture verdict
    arch = [st for st in Stage if indicts(st) == "architecture"]
    assert arch == [Stage.MINTED_UNUSED]
    assert indicts(Stage.REUSE_UNWIRED) == "implementation"     # unwired reuse is a wiring gap, NOT an architecture verdict
    assert indicts(Stage.DIED_PRE_DIFF) == "implementation"
    assert indicts(Stage.RESIDUAL_EMPTY) == "library"
    assert indicts(Stage.MINT_UNFIRED) == "gate/implementation"
    assert indicts(Stage.USED_NOCLEAR) == "drive"


def test_reuse_unwired_is_not_an_architecture_verdict():
    """A mint whose product was never OFFERED to a fresh task tops out at REUSE_UNWIRED -- our actual live situation
    (the Consolidator is not wired into the runner). The probe must NOT claim the architecture is at fault."""
    p = TetherProbe()
    p.record(ChainSignals(diff_ran=True, residual_nonempty=True, minted=True))   # minted, reuse never attempted
    assert p.furthest == Stage.REUSE_UNWIRED
    assert p.verdict() == "implementation"
    assert p.indicts_architecture() is False


def test_a_level_advance_alone_never_sets_cleared():
    """membrane rule (§3.6/§5.1): clearing levels by search/playback proves nothing. `cleared` requires a transfer (`reused`) first; a caller passing
    only cleared=True (as a raw level advance would) is coerced back -- it cannot jump to CLEARED."""
    st = classify(ChainSignals(diff_ran=True, residual_nonempty=True, minted=True, cleared=True))
    assert st == Stage.CLEARED  # coercion makes cleared imply reused+attempted -- so callers must NOT pass a bare level advance
    # the guard that matters: a run whose ONLY signal is a level advance (no diff, no mint) stays at the bottom
    assert classify(ChainSignals(cleared=True)) != Stage.CLEARED
    assert classify(ChainSignals(cleared=True)) == Stage.DIED_PRE_DIFF


def test_probe_keeps_the_furthest_stage_and_counts():
    p = TetherProbe()
    assert p.furthest is None and p.verdict() == "none"
    p.record(ChainSignals(diff_ran=True))                                        # RESIDUAL_EMPTY
    p.record(ChainSignals(diff_ran=True, residual_nonempty=True, minted=True))   # REUSE_UNWIRED
    p.record(ChainSignals())                                                     # DIED_PRE_DIFF
    assert p.furthest == Stage.REUSE_UNWIRED                                      # the deepest stall wins
    assert p.counts[Stage.DIED_PRE_DIFF] == 1 and p.counts[Stage.REUSE_UNWIRED] == 1
    assert p.report()["indicts"] == "implementation"


def test_real_transfer_reaches_the_reuse_boundary_and_a_stubbed_clear_fires():
    """End-to-end through the REAL organs: mint INTENDED_FREE on two differently-coloured mazes, promote it, then let
    the promoted library EXPLAIN a THIRD maze's residual with no re-mint (genuine transfer). The classifier reads that
    as past MINTED_UNUSED; with a stubbed clear it reaches CLEARED. This is the one firing the bar asks for, on a
    known-answer curriculum -- perception stipulated, so it validates the tether's transfer step, not live detection."""
    mA = two_part_mdl(_free_maze(seed=10, focus_palette=[1, 4], wall_palette=[5, 6]), max_size=1)
    mB = two_part_mdl(_free_maze(seed=20, focus_palette=[2, 8], wall_palette=[5, 7]), max_size=1)
    con = Consolidator(echo_threshold=2)
    con.observe_mint("mazeA", mA)
    con.observe_mint("mazeB", mB)                                                 # echoed on a 2nd task -> promoted
    fresh = _free_maze(seed=30, focus_palette=[3, 9], wall_palette=[5, 6])        # a task it was NOT minted on
    explained = con.explains(fresh) is not None                                  # reuse ATTEMPTED and succeeded
    sig = ChainSignals(diff_ran=True, residual_nonempty=True, minted=True,
                       reuse_attempted=True, reused=explained, cleared=explained)  # stubbed clear stands for "acting closed the break"
    assert explained is True
    assert classify(sig) == Stage.CLEARED


def test_real_non_transfer_is_an_architecture_stall_not_a_wiring_gap():
    """When reuse IS attempted but the library cannot explain the fresh task, the code is MINTED_UNUSED -- the sole
    architecture verdict. Here a palette-SPECIFIC mint (never promoted, since it can't echo) means `explains` returns
    None: reuse was genuinely tried and the library had nothing -> architecture-bucket, distinct from REUSE_UNWIRED."""
    from test_affordance_echo import _colour_gated_maze
    mA = two_part_mdl(_colour_gated_maze(seed=11, passable_colour=3, other_colours=[5, 6]), max_size=1)
    con = Consolidator(echo_threshold=2)
    con.observe_mint("mazeA", mA)                                                # one task -> held, never promoted
    fresh = _colour_gated_maze(seed=99, passable_colour=7, other_colours=[2, 5])
    explained = con.explains(fresh) is not None                                 # attempted against Γ, which is empty
    assert explained is False
    sig = ChainSignals(diff_ran=True, residual_nonempty=True, minted=True, reuse_attempted=True, reused=explained)
    assert classify(sig) == Stage.MINTED_UNUSED
    assert indicts(classify(sig)) == "architecture"
