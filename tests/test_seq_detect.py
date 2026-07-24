"""Referent-detector fix (the cross-family bottleneck): detect an ELONGATED framed token strip ANYWHERE (an interior
sequence bar, e.g. family-B tr87/sb26) as an ordered `legend`, not just thin EDGE bands. General: aspect-ratio +
>=3-distinct-token gated, no per-game pixel threshold. A square framed SYMBOL display stays a panel (not a sequence)."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.referent import find_referents, _panel_sequence


def _ring(g, colour, r0, c0, r1, c1):
    g[r0, c0:c1 + 1] = colour; g[r1, c0:c1 + 1] = colour; g[r0:r1 + 1, c0] = colour; g[r0:r1 + 1, c1] = colour


def test_interior_framed_token_row_becomes_ordered_legend():
    g = np.zeros((6, 16), dtype=int)
    _ring(g, 2, 1, 1, 3, 13)                                  # a 3x13 framed box in the INTERIOR (not at an edge)
    g[2, 2] = 3; g[2, 5] = 4; g[2, 8] = 5; g[2, 11] = 6      # a row of 4 distinct tokens inside the frame
    legs = [r for r in find_referents(g) if r.kind == "legend"]
    assert any(r.detail.get("sequence") == [3, 4, 5, 6] for r in legs)   # read as an ordered sequence


def test_square_framed_symbol_stays_a_panel_not_a_sequence():
    g = np.zeros((10, 10), dtype=int)
    _ring(g, 2, 1, 1, 5, 5)                                   # a 5x5 framed SYMBOL display (square, not elongated)
    g[3, 3] = 7
    kinds = {r.kind for r in find_referents(g)}
    assert "panel" in kinds
    seqs = [r for r in find_referents(g) if r.kind == "legend"]
    assert not seqs                                          # a square display is not a token sequence


def test_panel_sequence_precision_on_shapes():
    g = np.zeros((14, 14), dtype=int)
    assert _panel_sequence(g, (2, 2, 4, 4), 0) is None       # square region -> not elongated -> no sequence
    row = np.zeros((1, 12), dtype=int); row[0, 1] = 3; row[0, 4] = 4  # only 2 distinct tokens
    assert _panel_sequence(np.pad(row, 1), (1, 1, 1, 12), 0) is None   # <3 tokens -> not a sequence


def test_plain_board_yields_no_sequence():
    g = np.zeros((12, 12), dtype=int); g[5, 5] = 3
    assert not [r for r in find_referents(g) if r.kind == "legend"]
