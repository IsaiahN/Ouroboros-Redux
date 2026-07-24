"""Lane C -- the R_T frame-transform bracket. Some games change the board by a GLOBAL transform (rotate / reflect /
recolour / whole-frame shift), which a per-object model mispredicts wholesale but a single transform T explains. The
detector must (a) identify each such T, (b) prefer the simplest one, and -- the precision point -- (c) return None
when the change is a per-OBJECT move (one cursor stepping), so Lanes A/B keep those games. Names no game."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.transform import detect_global_transform, TransformProbe, GEOMS


def _rand(h=6, w=6, seed=0):
    g = np.zeros((h, w), dtype=int)
    # a deterministic asymmetric pattern so each dihedral image is DISTINCT (no accidental symmetry)
    for i in range(h):
        for j in range(w):
            g[i, j] = (i * 3 + j * 7 + seed) % 5
    return g


def test_detects_each_dihedral():
    b = np.arange(36).reshape(6, 6) % 13                     # all-distinct-ish, no dihedral symmetry -> every op
    b[0, 0] = 15; b[0, 5] = 14                               # break any residual symmetry at the corners
    for name, g in GEOMS.items():
        if name == "identity":
            continue
        a = np.asarray(g(b))
        if a.shape != b.shape:
            continue                                          # (square board here, so all 8 apply)
        T = detect_global_transform(b, a)
        assert T is not None and T.kind == "geom", name
        # tolerant of symmetric coincidences: the detected transform must EXPLAIN the change (some dihedral images
        # can coincide for a given pattern -- any explaining T is correct)
        assert np.array_equal(np.asarray(GEOMS[T.name](b)), a), (name, T.name)


def test_detects_pure_recolour():
    b = _rand()
    a = b.copy()
    a[b == 1] = 8; a[b == 2] = 9                              # a consistent colour bijection
    T = detect_global_transform(b, a)
    assert T is not None and T.kind == "recolour"
    assert dict(T.detail)[1] == 8 and dict(T.detail)[2] == 9


def test_detects_geom_plus_recolour():
    b = _rand()
    a = np.rot90(b, 1).copy()
    a[np.rot90(b, 1) == 0] = 7                                 # rotate THEN recolour one class
    T = detect_global_transform(b, a)
    assert T is not None and T.kind == "geom+recolour" and T.name == "rot90"


def test_detects_translation():
    b = _rand(8, 8)
    a = np.roll(np.roll(b, 2, axis=0), 1, axis=1)             # whole-frame shift (dr=2, dc=1) -- torus roll matches
    T = detect_global_transform(b, a)
    assert T is not None and T.kind == "translate"


def test_no_change_returns_none():
    b = _rand()
    assert detect_global_transform(b, b.copy()) is None


def test_per_object_move_is_not_a_global_transform():
    """PRECISION: a single cursor stepping one cell is NOT a global transform -> None, so Lanes A/B keep the game."""
    b = np.zeros((12, 12), dtype=int); b[5, 5] = 3            # a lone cursor
    a = b.copy(); a[5, 5] = 0; a[5, 6] = 3                    # it moved one cell right
    T = detect_global_transform(b, a)
    assert T is None


def test_probe_reports_dominant_transform():
    b = _rand()
    probe = TransformProbe()
    cur = b
    for _ in range(5):
        nxt = np.rot90(cur, 1)                                 # each step rotates the whole frame 90
        probe.observe(cur, nxt); cur = nxt
    dom = probe.dominant()
    assert dom is not None and dom[0][0] == "geom" and dom[0][1] == "rot90"
    assert probe.frac_transform() == 1.0


def test_probe_silent_on_per_object_stream():
    probe = TransformProbe()
    g = np.zeros((12, 12), dtype=int); g[2, 2] = 4
    for c in range(2, 8):
        nxt = np.zeros((12, 12), dtype=int); nxt[2, c + 1] = 4
        probe.observe(g, nxt); g = nxt
    assert probe.dominant() is None                           # a moving cursor never reads as a global transform
    assert probe.frac_transform() == 0.0
