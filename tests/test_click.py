"""
redux-triality: the CLICK modality (ACTION6) + where-to-click perception. Closes the biggest coverage gap in the
dev-set survey -- 6/25 games are coordinate-click-only and the directional stack cannot act on them at all. These
tests pin the pure pieces (perception + curiosity prober) without the wire.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.click import click_targets, grid_sweep, ClickProber, _background


def _board():
    """32x32 field of colour 5 (background) with three distinct interactive tokens of rarer colours."""
    g = np.full((32, 32), 5, dtype=int)
    g[4:6, 4:6] = 2          # token A (colour 2), centroid (4,4)
    g[20:22, 25:27] = 3      # token B (colour 3), centroid (20,26) (round-half-to-even)
    g[10, 15] = 8            # single-pixel token C (colour 8) -> noise-penalised, ranks last
    return g


def test_background_is_the_dominant_colour():
    assert _background(_board()) == 5


def test_click_targets_finds_token_centroids_excludes_background():
    tgts = click_targets(_board())
    assert (4, 4) in tgts and (20, 26) in tgts           # both 2x2 tokens perceived
    # background (colour 5) is never a click target
    g = _board()
    for (r, c) in tgts:
        assert not (g[r, c] == 5 and (r, c) not in [(10, 15)])  # centroids sit on tokens, not the field


def test_click_targets_noise_pixel_ranks_after_real_tokens():
    tgts = click_targets(_board())
    # the single-pixel token C is penalised -> the two 2x2 tokens come before it
    iA, iB, iC = tgts.index((4, 4)), tgts.index((20, 26)), tgts.index((10, 15))
    assert iC > iA and iC > iB


def test_click_targets_drops_giant_fills():
    g = np.full((20, 20), 5, dtype=int)
    g[:, :10] = 7                                          # colour 7 covers half the board -> too big to be a token
    g[2:4, 15:17] = 3                                      # a real small token
    tgts = click_targets(g, max_frac=0.20)
    assert (2, 16) in tgts
    assert all(g[r, c] != 7 for (r, c) in tgts)           # the giant fill is never offered


def test_grid_sweep_lattice_size():
    pts = grid_sweep(np.zeros((64, 64)), n=8)
    assert len(pts) == 64 and len(set(pts)) == 64         # 8x8 distinct lattice points


def test_prober_sweeps_every_candidate_once_before_repeating():
    cand = [(1, 1), (2, 2), (3, 3)]
    p = ClickProber(cand, sweep=[])
    picks = []
    same = np.zeros((4, 4), dtype=int)
    for _ in range(3):
        t = p.choose(); picks.append(t)
        p.observe(same, same)                             # no change
    assert sorted(picks) == sorted(cand)                  # each candidate tried exactly once first


def test_prober_prefers_targets_that_changed_the_board():
    cand = [(1, 1), (2, 2)]
    p = ClickProber(cand, sweep=[])
    a = np.zeros((4, 4), dtype=int); b = a.copy(); b[0, 0] = 9
    # try (1,1) -> board changes; try (2,2) -> no change
    t1 = p.choose(); assert t1 == (1, 1); p.observe(a, b)
    t2 = p.choose(); assert t2 == (2, 2); p.observe(a, a)
    # both tried once now; the productive one (1,1) should be chosen next
    assert p.choose() == (1, 1)
    assert p.productive() == [(1, 1)]


def test_prober_refresh_folds_in_new_tokens_keeping_history():
    p = ClickProber([(1, 1)], sweep=[])
    p.choose(); p.observe(np.zeros((3, 3)), np.ones((3, 3)))   # (1,1) now has a change recorded
    added = p.refresh([(1, 1), (2, 2)])                        # (1,1) already known, (2,2) is new
    assert added == 1 and (2, 2) in p.tries
    assert p.changed[(1, 1)] == 1                              # history preserved
