"""The non-simulable self-hypothesis family (DESIGN §7): members span deliberately decorrelated
primitives, are priced by ground-facing residual, and the completeness critic fires when the whole
family fails together -- the fix for ls20, where a translation-only model found no self at all."""
import numpy as np
from nexus.sensorium.self_family import (SelfModelFamily, TranslationSelf, GrowthEdgeSelf,
                                         ValueLatentSelf, RegionToggleSelf)


def _grid(cells, h=12, w=12, bg=0):
    g = np.full((h, w), bg, dtype=int)
    for (r, c), v in cells.items():
        g[r, c] = v
    return g


def test_translation_member_wins_on_a_moving_sprite():
    fam = SelfModelFamily()
    r, c = 5, 2
    for _ in range(5):
        before = _grid({(r, c): 3}); after = _grid({(r, c + 1): 3})
        fam.observe(before, "A2", after); c += 1
    sel = fam.selected()
    assert sel is not None and sel.name == "translation"
    assert not fam.self_unmodeled()


def test_value_latent_member_wins_on_a_depleting_bar_ls20_shape():
    # A NON-SPATIAL self: a bright bar (colour 11) that RETRACTS one cell each step -- the ls20 shape
    # that the translation model was blind to. No single object translates; a colour count depletes.
    fam = SelfModelFamily()
    length = 10
    for _ in range(7):
        before = _grid({(11, j): 11 for j in range(length)})
        after = _grid({(11, j): 11 for j in range(length - 1)})    # bar one shorter
        fam.observe(before, "A1", after); length -= 1
    sel = fam.selected()
    assert sel is not None and sel.name == "value"           # the ground selected the value-latent self
    frame = sel.self_frame(_grid({(11, j): 11 for j in range(length)}), [1, 2, 3, 4])
    assert frame[0] == "val" and frame[1] == 11               # tracks the depleting colour, no self-cell needed


def test_completeness_critic_fires_when_no_member_predicts():
    # Full random repaint every step: nothing translates rigidly, grows monotonically, alternates,
    # nor moves a count consistently. Every member must fail together -> the critic surfaces it.
    rng = np.random.default_rng(0)
    fam = SelfModelFamily()
    grids = [rng.integers(0, 6, size=(12, 12)) for _ in range(10)]
    for i in range(len(grids) - 1):
        fam.observe(grids[i], "A%d" % (i % 4 + 1), grids[i + 1])
    assert fam.self_unmodeled()                               # whole family failed together -> surface the axiom
    assert fam.signature(grids[-1], [1, 2, 3, 4]) is None     # no dishonest self-frame is emitted


def test_members_have_decorrelated_names():
    fam = SelfModelFamily()
    names = {m.name for m in fam.members}
    assert names == {"translation", "growth", "value", "toggle"}   # four distinct primitives, not variants
