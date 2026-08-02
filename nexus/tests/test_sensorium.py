"""The sensorium's headline product: a SELF-RELATIVE, minted danger signature that replaces the coarse
whole-board `local_signature`. Two globally-different boards where the self is surrounded the same way
share a signature (so a fatal generalizes); an open-space board does not (so it is not over-vetoed)."""
import numpy as np
from nexus.sensorium import build_sensorium, Sensorium
from nexus.sensorium.forward import ForwardModel


def _grid(cells, h=7, w=7, bg=0):
    g = np.full((h, w), bg, dtype=int)
    for (r, c), v in cells.items():
        g[r, c] = v
    return g


def test_signature_falls_back_without_a_self():
    s = Sensorium()
    sig = s.signature(_grid({(1, 1): 4}), [1, 2, 3, 4])
    assert sig[0] == "nobody"                     # no self learned -> honest whole-board fallback


def test_signature_is_self_relative_once_a_self_exists():
    s = build_sensorium()
    # teach the self (colour 5) a move so it is discovered
    s.observe(_grid({(3, 3): 5}), "A2", _grid({(3, 4): 5}), fatal=False, available=[1, 2, 3, 4])
    # board X: self at (3,4) hemmed by walls of colour 8 on the right; and board Y: same LOCAL wall
    # pattern but at a totally different place and with unrelated far-away decor.
    boardX = _grid({(3, 4): 5, (2, 5): 8, (3, 5): 8, (4, 5): 8})
    s.fwd.self_cells = {(3, 4)}
    sigX = s.signature(boardX, [1, 2, 3, 4])
    boardY = _grid({(3, 4): 5, (2, 5): 8, (3, 5): 8, (4, 5): 8, (0, 0): 2, (6, 6): 9})
    sigY = s.signature(boardY, [1, 2, 3, 4])
    assert sigX[0] == "self"
    assert sigX == sigY                            # same self-relative surroundings -> same signature

    boardOpen = _grid({(3, 4): 5})                 # same self, but open space around it
    sigOpen = s.signature(boardOpen, [1, 2, 3, 4])
    assert sigOpen != sigX                          # open space is a DIFFERENT situation -> not vetoed


def test_mint_sharpens_the_signature_from_grounded_outcomes():
    s = build_sensorium(min_evidence=4)
    s.observe(_grid({(3, 3): 5}), "A2", _grid({(3, 4): 5}), fatal=False, available=[1, 2, 3, 4])
    s.fwd.self_cells = {(3, 4)}
    # feed several grounded outcomes where a specific self-local wall pattern is fatal under A4
    walled = {(3, 4): 5, (3, 5): 8, (2, 5): 8, (4, 5): 8}
    for _ in range(5):
        s.observe(_grid(walled), "A4", _grid(walled), fatal=True, available=[1, 2, 3, 4])
    for _ in range(5):
        s.observe(_grid({(3, 4): 5}), "A4", _grid({(3, 5): 5}), fatal=False, available=[1, 2, 3, 4])
    # the mint should now find SELF_LOCAL informative about death
    report = s.mint.report()
    assert report["SELF_LOCAL"] > 0.0             # the ground priced the self-relative channel as informative
