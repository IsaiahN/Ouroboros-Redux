"""Tests for full-resolution perception + object permanence. Each pins a map principle."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.perception import (check_no_downsampling, DownsampleError, segment,
                                 Object, ObjectTracker)


def test_no_downsampling_hard_bound():
    check_no_downsampling((64, 64), (64, 64))      # same resolution is fine
    check_no_downsampling((64, 64), (128, 64))     # upscaling is fine
    for bad in [(32, 64), (64, 32), (16, 16)]:
        try:
            check_no_downsampling((64, 64), bad); assert False, "should have raised"
        except DownsampleError:
            pass


def test_segment_finds_objects_ignores_background():
    g = np.zeros((5, 5), dtype=int)                # background 0
    g[0, 0] = 3                                     # one object
    g[4, 4] = 5; g[4, 3] = 5                        # another (2 cells)
    objs = segment(g)
    assert len(objs) == 2
    sizes = sorted(o.size for o in objs)
    assert sizes == [1, 2]
    assert all(o.belief for o in objs)             # segmentation is a REVISABLE belief


def test_near_decomposability_separates_by_symbol():
    # two touching blobs of DIFFERENT colours are TWO near-decomposable objects, not one.
    g = np.zeros((3, 4), dtype=int)
    g[1, 0] = 3; g[1, 1] = 3                        # colour-3 blob
    g[1, 2] = 4; g[1, 3] = 4                        # colour-4 blob, adjacent
    objs = segment(g)
    assert len(objs) == 2
    # a single same-colour connected blob is ONE object
    g2 = np.zeros((3, 4), dtype=int); g2[1, 0:4] = 3
    assert len(segment(g2)) == 1


def _obj(cells, colour=3):
    return Object(cells=frozenset(cells), colours=frozenset({colour}))


def test_identity_survives_recolour():
    # same position, different paint -> SAME id (matched by overlap, not colour). Object permanence.
    T = ObjectTracker()
    o1 = T.update([_obj([(1, 1), (1, 2)], colour=3)])[0]
    o2 = T.update([_obj([(1, 1), (1, 2)], colour=9)])[0]   # recoloured in place
    assert o1.oid == o2.oid


def test_identity_survives_reshape():
    # grows a cell -> still mostly overlapping -> SAME id.
    T = ObjectTracker()
    a = T.update([_obj([(2, 2), (2, 3)])])[0]
    b = T.update([_obj([(2, 2), (2, 3), (2, 4)])])[0]      # reshaped (grew)
    assert a.oid == b.oid


def test_new_object_gets_new_identity():
    T = ObjectTracker()
    T.update([_obj([(0, 0)])])
    res = T.update([_obj([(0, 0)]), _obj([(5, 5)])])       # a second, disjoint object appears
    oids = sorted(o.oid for o in res)
    assert len(set(oids)) == 2


def test_occlusion_keeps_track_then_reidentifies():
    # disappears for a frame (not overwritten) -> track survives -> same id on return.
    T = ObjectTracker()
    a = T.update([_obj([(3, 3), (3, 4)])])[0]
    T.update([])                                            # occluded / unobserved, nothing overwrote it
    assert a.oid in T.tracks                                # survived non-observation
    b = T.update([_obj([(3, 3), (3, 4)])])[0]               # reappears at same place
    assert a.oid == b.oid


def test_track_dies_when_cells_taken_over():
    # its cells become >=50% occupied by ANOTHER object now -> dead (evidence, not guesswork).
    T = ObjectTracker(death_occupancy=0.5)
    a = T.update([_obj([(1, 1), (1, 2)], colour=3)])[0]
    # a different object now fully occupies a's old cells
    res = T.update([_obj([(1, 1), (1, 2)], colour=7)])
    # because IoU=1.0 >= birth_min_overlap, it is actually judged the SAME object (recolour) -> id kept.
    assert res[0].oid == a.oid
    # but if the overlap is LOW and the cells are taken, the old track dies:
    T2 = ObjectTracker(death_occupancy=0.5, birth_min_overlap=0.9)
    x = T2.update([_obj([(1, 1), (1, 2)])])[0]
    T2.update([_obj([(1, 1), (1, 2), (1, 3), (1, 4)])])    # overlaps a's cells fully but IoU=0.5<0.9 -> not 'same'
    assert x.oid not in T2.tracks                           # x's cells taken over -> retired


def test_nothing_silent_events_narrated():
    T = ObjectTracker()
    T.update([_obj([(0, 0)])])
    assert any(e.startswith("BORN") for e in T.events)
