"""Locksmith L1: transform-aware MATCH. ls20 = a maze where the agent brings a KEY symbol to equal a LOCK symbol, and
the two differ by a dihedral ROTATION and/or a RECOLOUR (verified from the later-level frames: a hook shape cycling
blue->red->cyan and rotating). So the MATCH discrepancy must be measured in Lane-C's transform vocabulary (D4 + recolour)
-- the number of primitive operators still to apply -- not raw cell-for-cell. This makes the agent SEE edit-to-match /
locksmith games as MATCH. Names no game; the operator DRIVE is L2/L3."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.transform import panel_transform_distance
from newhorse.redux_arch.relation import RelationBank, RelationCtx
from newhorse.redux_arch.referent import Referent

R = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 1, 2, 3], [4, 5, 6, 7]])   # an asymmetric 4x4 symbol


def test_exact_match_is_zero():
    assert panel_transform_distance(R, R.copy()) == (0.0, None) or panel_transform_distance(R, R.copy())[0] == 0.0


def test_pure_rotation_is_cheaper_than_raw_hamming():
    d, t = panel_transform_distance(np.rot90(R, 1), R)        # key is the lock rotated 90 degrees
    assert d == 1.0                                           # one rotation operator away (not ~16 differing cells)
    assert t is not None and t.name in ("rot90", "rot270")   # residual = a quarter turn to undo


def test_pure_recolour_distance_counts_swapped_colours():
    key = np.where(R == 1, 90, R)                             # recolour just colour 1 -> 90 (one colour swapped)
    key = np.where(R == 2, 91, key)                          # and colour 2 -> 91 (a second)
    d, t = panel_transform_distance(key, R)
    assert d == 2.0                                           # two recolour operators
    assert t is not None and t.kind == "recolour"


def test_non_transform_same_shape_is_raw_edit_distance():
    b = R.copy(); b[0, 0] = 42; b[1, 1] = 43                  # two cells off, no clean global transform relates them
    d, t = panel_transform_distance(b, R)
    assert d == 2.0 and t is None                             # raw edit distance (the ft09 cell-edit case), no residual


def test_incomparable_shapes_return_none():
    assert panel_transform_distance(np.zeros((3, 4)), np.zeros((5, 5))) == (None, None)


# ---- the tester now SELECTS match as a key is transformed toward a lock ----------------------------------------
def _frame_with(refA, refB, a, b):
    g = np.zeros((6, 16), dtype=int)
    g[1:5, 1:5] = a; g[1:5, 9:13] = b
    return g


def test_match_selected_as_key_rotates_and_recolours_to_lock():
    bank = RelationBank(min_obs=4, min_range=1.0)
    ctx = RelationCtx(cursor=None, passable=frozenset(), bg=0)
    lock = Referent("panel", (1, 9, 4, 12), None, {})
    key = Referent("panel", (1, 1, 4, 4), None, {})
    # the key's transform-distance to the lock shrinks 3 -> 0 as operators (rotate, recolour) are applied
    recol = np.where(R == 1, 90, R)                          # a one-colour-off variant of R (distance 1 by recolour)
    seq = [np.rot90(recol, 2), np.rot90(recol, 2), np.rot90(R, 1), np.rot90(R, 1), R, R]  # dist ~3,3,1,1,0,0
    for a in seq:
        bank.observe(_frame_with(key, lock, a, R), [key, lock], ctx)
    assert bank.discrepancies()["MATCH"] == 0.0             # the key now equals the lock
    assert bank.selected() == "MATCH"                        # ...and the tester recognised the closing transform
