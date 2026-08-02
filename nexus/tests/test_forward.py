"""The efference-copy forward model: discover the controllable self by watching what translates under
an action, predict the next grid, and attribute the UNPREDICTED remainder to the world as residual."""
import numpy as np
from nexus.sensorium.forward import ForwardModel, as_grid2d, background_colour


def _grid(cells, h=5, w=5, bg=0):
    g = np.full((h, w), bg, dtype=int)
    for (r, c), v in cells.items():
        g[r, c] = v
    return g


def test_discovers_self_and_displacement_from_a_move():
    fwd = ForwardModel()
    before = _grid({(2, 2): 3})                 # a single self-object (colour 3) at (2,2)
    after = _grid({(2, 3): 3})                  # it moved one cell right under A2
    dr, dc = fwd.observe(before, "A2", after)
    assert (dr, dc) == (0, 1)                    # displacement attributed to the action
    assert fwd.has_self() and fwd.self_colour == 3
    assert fwd.self_centroid() == (2, 3)         # self now at the arrival cell
    assert fwd.expected_disp("A2") == (0, 1)


def test_predicts_next_grid_by_translating_the_self():
    fwd = ForwardModel()
    fwd.observe(_grid({(2, 2): 3}), "A2", _grid({(2, 3): 3}))   # learn A2 = right
    # from a NEW board with the self at (1,1), predict A2 moves it to (1,2)
    cur = _grid({(1, 1): 3})
    fwd.self_cells = {(1, 1)}                    # place the known self
    pred = fwd.predict(cur, "A2")
    assert pred[1, 1] == 0 and pred[1, 2] == 3   # vacated + arrived, purely from the efference copy


def test_residual_is_the_unpredicted_change():
    fwd = ForwardModel()
    fwd.observe(_grid({(2, 2): 3}), "A2", _grid({(2, 3): 3}))
    fwd.self_cells = {(2, 3)}
    cur = _grid({(2, 3): 3})
    # reality: self moves right AND an unrelated world cell lights up at (0,0)
    actual = _grid({(2, 4): 3, (0, 0): 7})
    resid = fwd.residual(cur, "A2", actual)
    assert (0, 0) in resid                        # the world change is surprise
    assert (2, 4) not in resid                     # the self move was predicted, so it is NOT surprise


def test_no_self_means_everything_is_world():
    fwd = ForwardModel()                          # never observed a coherent move
    cur = _grid({(1, 1): 4})
    actual = _grid({(1, 1): 4, (3, 3): 9})        # something changed, but no self learned
    pred = fwd.predict(cur, "A1")
    assert np.array_equal(pred, cur)              # prediction = 'nothing changes'
    assert fwd.residual(cur, "A1", actual) == {(3, 3)}   # so all change is honestly world-surprise


def test_as_grid2d_takes_last_frame_of_a_stack():
    stacked = np.stack([_grid({(0, 0): 1}), _grid({(4, 4): 2})])   # [frames][H][W]
    g = as_grid2d(stacked)
    assert g.shape == (5, 5) and g[4, 4] == 2 and background_colour(g) == 0
