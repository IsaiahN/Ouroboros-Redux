"""The sensorium's headline product: a SELF-RELATIVE, minted danger signature driven by the
non-simulable self-hypothesis family. The self-frame comes from whichever member the ground selected
for this game; when the whole family fails, the signature falls back honestly (completeness critic)."""
import numpy as np
from nexus.sensorium import build_sensorium, Sensorium


def _grid(cells, h=12, w=12, bg=0):
    g = np.full((h, w), bg, dtype=int)
    for (r, c), v in cells.items():
        g[r, c] = v
    return g


def test_signature_falls_back_before_any_self_is_modelled():
    s = Sensorium()
    sig = s.signature(_grid({(1, 1): 4}), [1, 2, 3, 4])
    assert sig[0] == "nobody"                     # no self selected yet -> honest whole-board fallback


def test_signature_becomes_self_relative_once_a_member_is_selected():
    s = build_sensorium()
    c = 2
    for _ in range(5):                            # teach a translating self so a member is selected
        s.observe(_grid({(5, c): 3}), "A2", _grid({(5, c + 1): 3}), fatal=False, available=[1, 2, 3, 4])
        c += 1
    assert not s.self_unmodeled()
    sig = s.signature(_grid({(5, c): 3}), [1, 2, 3, 4])
    assert sig[0] == "self"                        # now perceives from a self-frame
    assert s.report()["selected"] == "translation"


def test_value_latent_self_gives_ls20_shape_a_signature():
    s = build_sensorium()
    length = 10
    for _ in range(7):
        before = _grid({(11, j): 11 for j in range(length)})
        after = _grid({(11, j): 11 for j in range(length - 1)})
        s.observe(before, "A1", after, fatal=False, available=[1, 2, 3, 4]); length -= 1
    assert s.report()["selected"] == "value"       # the member that translation was blind to
    sig = s.signature(_grid({(11, j): 11 for j in range(length)}), [1, 2, 3, 4])
    assert sig[0] == "self"                         # ls20's non-spatial self now yields a real signature


def test_observe_does_not_crash_on_degenerate_grids():
    s = build_sensorium()
    s.observe([], "A1", [], fatal=False, available=[])       # empty grids -> no self, no error
    assert s.self_unmodeled()
