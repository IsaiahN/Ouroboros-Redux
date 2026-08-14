"""THE FRAME UNWRAP GATE (root cause of the ego blindness + BANK_SETTLE storm).

⭐ WHY. The ARC API delivers each frame as a LIST of animation grids
(list[list[list[int]]]). Perceiver._to_numpy only unwrapped the legacy
[ndarray] single-wrap, so a raw multi-grid list became a (k, 64, 64) stack
with k VARYING by animation phase. Every 2-D consumer downstream went blind:

* EgoObserver.observe threw internally on EVERY step of an animated episode
  ("[EGO] objects=0 colour=None" whole episodes) — the ego pipeline ran blind;
* the k-mismatch between commit and settle was the BANK_SETTLE storm
  (33 swallows/episode live; the settle side is already VOID-guarded in
  betting.py — this gate fixes the FEED so the guard becomes the rare case).

THE LAW: `unwrap_frame` (engines/egocentric/perception.py) reduces any
(k, H, W) stack to its LAST grid. Last, not first: the animation plays
oldest -> newest, so grid [-1] is the SETTLED board — the state the next
observation will corroborate; earlier grids are transients the world has
already left behind. k=1 unwraps trivially; 2-D passes through; the legacy
[ndarray] wrap and malformed->None behaviour are unchanged.

Run pre-build: the unwrap tests fail (helper absent; 3-D leaks through).
"""
from __future__ import annotations

import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _grid(h=8, w=8, mark=None, colour=3):
    """One 2-D board as a raw API list-of-lists; `mark` paints a 2x2 block."""
    g = np.zeros((h, w), dtype=np.uint8)
    if mark is not None:
        r, c = mark
        g[r:r + 2, c:c + 2] = colour
    return g.tolist()


class TestUnwrapLastGrid:
    """(1) A (3, 8, 8) list-frame unwraps to the LAST (8, 8) grid."""

    def test_3d_list_frame_unwraps_to_the_last_grid(self):
        from engines.egocentric.perception import unwrap_frame
        frame = [_grid(mark=(0, 0)), _grid(mark=(2, 2)), _grid(mark=(4, 4))]
        out = unwrap_frame(frame)
        assert out is not None, "a 3-grid animation frame must unwrap, not vanish"
        assert out.shape == (8, 8), "unwrap must yield the 2-D board, got %r" % (out.shape,)
        assert np.array_equal(out, np.asarray(frame[-1])), (
            "the LAST grid is the settled state — unwrap took a transient instead")
        assert not np.array_equal(out, np.asarray(frame[0])), (
            "unwrap took the FIRST grid (a mid-animation transient)")

    def test_perceiver_to_numpy_routes_through_the_same_unwrap(self):
        from engines.perception.perceiver import Perceiver
        frame = [_grid(mark=(0, 0)), _grid(mark=(2, 2)), _grid(mark=(4, 4))]
        out = Perceiver._to_numpy(frame)
        assert out is not None and out.shape == (8, 8), (
            "Perceiver._to_numpy still stacks the animation into 3-D: %r"
            % (None if out is None else out.shape,))
        assert np.array_equal(out, np.asarray(frame[-1]))

    def test_k1_unwraps_trivially(self):
        from engines.egocentric.perception import unwrap_frame
        frame = [_grid(mark=(1, 1))]
        out = unwrap_frame(frame)
        assert out is not None and out.shape == (8, 8)
        assert np.array_equal(out, np.asarray(frame[0]))

    def test_3d_ndarray_stack_unwraps_to_the_last_grid(self):
        from engines.egocentric.perception import unwrap_frame
        stack = np.stack([np.full((8, 8), i, dtype=np.uint8) for i in range(3)])
        out = unwrap_frame(stack)
        assert out is not None and out.shape == (8, 8)
        assert (out == 2).all(), "must take stack[-1]"


class TestObserverSeesThroughAnimation:
    """(2) EgoObserver.observe on animated frames returns objects — not the
    blind objects=0 error path that ran whole episodes live."""

    def test_observe_returns_objects_on_an_animated_sequence(self):
        from engines.egocentric.observer import EgoObserver
        obs = EgoObserver(background=0)
        # Each step's frame is a k-grid animation; the block settles one cell
        # further right each step (the LAST grid is the settled position).
        seq = [
            [_grid(mark=(3, 0)), _grid(mark=(3, 1))],                       # k=2
            [_grid(mark=(3, 1)), _grid(mark=(3, 1)), _grid(mark=(3, 2))],  # k=3
            [_grid(mark=(3, 2)), _grid(mark=(3, 3))],                       # k=2
        ]
        infos = [obs.observe(frame, 3) for frame in seq]
        assert obs.errors == 0, (
            "observe still throws internally on animated frames (the live "
            "[EGO] objects=0 blindness)")
        for info in infos:
            assert not info.get("error"), "observe fell into its blind error path"
            assert info["objects"] >= 1, "the block is on the board; sensing missed it"

    def test_observe_tracks_the_settled_position_not_a_transient(self):
        from engines.egocentric.observer import EgoObserver
        obs = EgoObserver(background=0)
        obs.observe([_grid(mark=(3, 0)), _grid(mark=(3, 4))], 3)
        picked = obs.tracker.tracks
        assert picked, "no track founded"
        cells = next(iter(picked.values())).cells
        cols = {c for _, c in cells}
        assert cols == {4, 5}, (
            "the tracked body sits at the FIRST grid's position — unwrap must "
            "take the LAST (settled) grid, got columns %r" % (sorted(cols),))


class TestKVaryingPerceivePath:
    """(3) A k-varying (2, 3, 2) sequence through the loop's perceive path
    yields consistent 2-D shapes every step."""

    K_PATTERN = (2, 3, 2)

    def test_perceive_path_yields_consistent_2d_shapes(self):
        from engines.perception.perceiver import Perceiver
        p = Perceiver()
        base = np.zeros((64, 64), dtype=np.uint8)
        base[::2, :] = 9
        for step, k in enumerate(self.K_PATTERN):
            settled = base.copy()
            settled[step, 0] = 1 + step
            frame = [base.tolist()] * (k - 1) + [settled.tolist()]
            pf = p.perceive(frame, actions_taken=step, max_actions=10)
            assert pf.frame is not None, "perceive lost the frame at k=%d" % k
            assert pf.frame.shape == (64, 64), (
                "perceive leaked a %r stack at k=%d — downstream consumers "
                "(binder feed, bank commit/settle pre-frames, mint "
                "before/after) need 2-D" % (pf.frame.shape, k))
            assert np.array_equal(pf.frame, settled), "not the settled grid"

    def test_to_numpy_shapes_are_stable_across_varying_k(self):
        from engines.perception.perceiver import Perceiver
        shapes = set()
        for k in self.K_PATTERN:
            frame = [_grid(64, 64, mark=(1, 1))] * k
            arr = Perceiver._to_numpy(frame)
            assert arr is not None
            shapes.add(arr.shape)
        assert shapes == {(64, 64)}, (
            "k-varying frames produced varying shapes %r — the exact "
            "commit-vs-settle mismatch behind the BANK_SETTLE storm" % (shapes,))


class TestUnchangedBehaviour:
    """(4) 2-D and legacy [ndarray] behaviour unchanged; malformed -> None."""

    def test_2d_ndarray_passes_through_as_itself(self):
        from engines.egocentric.perception import unwrap_frame
        from engines.perception.perceiver import Perceiver
        g = np.arange(16, dtype=np.uint8).reshape(4, 4)
        assert unwrap_frame(g) is g
        assert Perceiver._to_numpy(g) is g

    def test_legacy_single_ndarray_wrap_unwraps_to_that_array(self):
        from engines.egocentric.perception import unwrap_frame
        from engines.perception.perceiver import Perceiver
        g = np.arange(16, dtype=np.uint8).reshape(4, 4)
        assert unwrap_frame([g]) is g
        assert Perceiver._to_numpy([g]) is g

    def test_2d_list_becomes_a_uint8_array(self):
        from engines.perception.perceiver import Perceiver
        out = Perceiver._to_numpy([[0, 1], [2, 3]])
        assert out is not None and out.shape == (2, 2)
        assert out.dtype == np.uint8
        assert np.array_equal(out, [[0, 1], [2, 3]])

    def test_malformed_frames_stay_none(self):
        from engines.egocentric.perception import unwrap_frame
        from engines.perception.perceiver import Perceiver
        for bad in (None, [], [[1, 2], [3]], "nonsense",
                    np.zeros((2, 2, 2, 2), dtype=np.uint8)):
            assert unwrap_frame(bad) is None, "unwrap must return None for %r" % (bad,)
            assert Perceiver._to_numpy(bad) is None
