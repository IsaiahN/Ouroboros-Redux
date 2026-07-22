"""
redux-arch P4.3 (code step): the leak-free passable read + motion-based cursor id that fix the retracted tu93
mint (docs/LAW0_ls20_tu93_passability.md). Three mechanisms, proven in isolation on synthetic frames before the
live replay:
  - PassabilityCalibrator: floor colours = the ones the cursor STEPPED ONTO (before-state), frozen after warmup;
    calibration and prediction on disjoint steps -> a regularity, not a peek.
  - _smallest_mover / CursorLocator: the cursor is the SMALL thing that translates, not the largest component of
    a colour (the tu93 misID that put 'the cell ahead' in the grey surround).
  - affordance_step: intended_free keyed off the calibrated passable SET, not core.bg.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.bridge import (PassabilityCalibrator, CursorLocator, _smallest_mover, affordance_step)


# ---- PassabilityCalibrator -------------------------------------------------------------------------------------
def test_calibrator_learns_floor_and_excludes_walls():
    cal = PassabilityCalibrator(warmup=10, min_hits=2)
    # cursor steps ONTO colour 3 when it moves; when blocked (moved=False) the cell ahead is a wall colour 4.
    for _ in range(6):
        cal.observe(entered_colour=3, moved=True)         # floor 3 -- entered
    for _ in range(6):
        cal.observe(entered_colour=4, moved=False)         # wall 4 -- blocked, NOT entered
    assert not cal.calibrating
    assert cal.passable_set() == frozenset({3})            # only the entered colour is floor
    assert cal.is_free(3) is True and cal.is_free(4) is False


def test_calibrator_noise_guard_drops_single_hits():
    cal = PassabilityCalibrator(warmup=8, min_hits=2)
    for _ in range(6):
        cal.observe(3, True)                               # 3 entered many times -> floor
    cal.observe(7, True)                                   # 7 entered ONCE -> below min_hits -> noise
    cal.observe(9, False)
    assert cal.passable_set() == frozenset({3})


def test_calibrator_freezes_after_warmup():
    cal = PassabilityCalibrator(warmup=4, min_hits=1)
    for _ in range(4):
        cal.observe(3, True)
    frozen = cal.passable_set()
    assert frozen == frozenset({3})
    for _ in range(20):                                    # a new floor colour appears AFTER the freeze
        cal.observe(8, True)
    assert cal.passable_set() == frozen                    # the passable read does NOT drift post-freeze


def test_calibrator_uncalibrated_returns_none():
    cal = PassabilityCalibrator(warmup=50)
    cal.observe(3, True)
    assert cal.calibrating and cal.is_free(3) is None      # unknown until the warmup window closes


# ---- cursor identification by motion ---------------------------------------------------------------------------
def _dot_and_block(dot_c, dot_rc, block_c, block_tl):
    g = np.zeros((16, 16), dtype=int)
    r, c = block_tl
    g[r:r + 6, c:c + 6] = block_c                           # a big 6x6 block
    g[dot_rc] = dot_c                                        # a 1-px dot
    return g


def test_smallest_mover_picks_the_dot_not_the_big_block():
    # both the dot (colour 4) AND the big block (colour 5) translate by one cell; the cursor is the SMALL one.
    before = _dot_and_block(4, (2, 2), 5, (8, 8))
    after = _dot_and_block(4, (2, 3), 5, (8, 9))            # dot +1 col, block +1 col
    assert _smallest_mover(before, after) == 4


def test_cursor_locator_freezes_the_small_mover():
    loc = CursorLocator(warmup=5)
    for k in range(5):
        before = _dot_and_block(4, (2, 2 + k), 5, (8, 8))   # dot moves each step; block static
        after = _dot_and_block(4, (2, 3 + k), 5, (8, 9))    # block also nudges so it's a 'mover' too
        loc.observe(before, after)
    assert loc.cursor() == 4                                # smallest persistent mover -> the cursor


# ---- affordance_step: passable SET, not bg ---------------------------------------------------------------------
def test_affordance_step_uses_passable_set_over_bg():
    # cursor (colour 4) at (5,5); the cell it would enter, (5,6), is FLOOR colour 7 (NOT background 0).
    before = np.zeros((10, 10), dtype=int); before[5, 5] = 4; before[5, 6] = 7
    after = np.zeros((10, 10), dtype=int); after[5, 6] = 4                     # the move succeeded
    # legacy bg=0 path MISjudges a colour-7 floor as blocked:
    ctx_bg, moved_bg = affordance_step(before, after, 4, (0, 1), 1, passable=None, bg=0)
    assert ctx_bg.intended_colour == 7 and ctx_bg.intended_free is False and moved_bg is True
    # calibrated passable={7} path correctly reads it as FREE:
    ctx_ps, moved_ps = affordance_step(before, after, 4, (0, 1), 1, passable=frozenset({7}))
    assert ctx_ps.intended_colour == 7 and ctx_ps.intended_free is True and moved_ps is True


def test_affordance_step_offboard_is_blocked():
    before = np.zeros((6, 6), dtype=int); before[0, 5] = 4                     # cursor at the right edge
    after = before.copy()                                                      # no move
    step = affordance_step(before, after, 4, (0, 1), 1, passable=frozenset({7}))
    ctx, moved = step
    assert ctx.intended_colour is None and ctx.intended_free is False and moved is False
