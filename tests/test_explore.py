"""
redux-triality: the curiosity explorer (reclaimed from new-horse exploration.py, extended to CELL coverage)
sweeps the board and can't farm novelty. This is the empowerment bootstrap that manufactures a gradient when
reward = 0.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.explore import CuriosityExplorer

VECS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}   # stride 1


def test_prefers_the_unvisited_cell():
    ex = CuriosityExplorer()
    ex.visit("R", (5, 6))                                   # the cell to the RIGHT of (5,5) is now visited
    a, cell = ex.choose((5, 5), VECS, stride=1)             # every dir passable; should avoid the visited R cell
    assert cell != (5, 6) and a != "R", (a, cell)


def test_novelty_decays_and_cannot_be_farmed():
    ex = CuriosityExplorer()
    n0 = ex.cell_novelty((3, 3))
    for _ in range(9):
        ex.visit("X", (3, 3))
    assert ex.cell_novelty((3, 3)) < n0 / 5                 # revisiting drives the bonus down (no farming)


def test_coverage_grows_sweeping_an_open_grid():
    ex = CuriosityExplorer()
    pos = [5, 5]
    def passable(dest):                                     # a 12x12 open board
        return 0 <= dest[0] < 12 and 0 <= dest[1] < 12
    for _ in range(120):
        pick = ex.choose(tuple(pos), VECS, passable, stride=1)
        assert pick is not None
        a, cell = pick
        pos = [pos[0] + VECS[a][0], pos[1] + VECS[a][1]]
        ex.visit(a, cell)
    # curiosity should visit a large fraction of the 144 cells, far more than the ~1 a stay-put agent would
    assert ex.coverage() >= 40, ex.coverage()


def test_boxed_in_returns_none():
    ex = CuriosityExplorer()
    a = ex.choose((0, 0), VECS, passable=lambda d: False, stride=1)
    assert a is None
