"""
Tests for brick 23: SALIENT-LANDMARK goal proposal.

The bug (measured live on tu93): `candidate_relations` sorted candidate targets by SIZE and kept the smallest
few. A maze board has 30+ tiny corridor/wall fragments of a repeated colour, so those fragments filled every
proposal slot and the UNIQUE static landmark (the actual goal) was never proposed at all — the avatar wandered
arbitrary corridor cells and timed out 6 cells short of the goal.

The fix: rank by (colour RARITY, size). A target whose colour appears as FEW objects is a distinct LANDMARK
(the figure) and a better goal hypothesis than one of MANY identical fragments of a repeated colour (the ground).
FMap: predictive_processing / information salience — a rare singleton is the high-information figure; goodhart
guard — 'smallest' is a gameable proxy for 'the goal', 'rare/distinct' is the honest one.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.relations import candidate_relations
from newhorse.perception import Object


def _obj(cells, colour):
    return Object(cells=frozenset(cells), colours=frozenset({colour}))


def test_unique_landmark_is_proposed_above_repeated_clutter():
    # a maze-like board: colour 3 appears as MANY tiny fragments (the repeated "ground"); colour 7 appears ONCE
    # as a small distinct landmark (the "figure" / goal). Cursor is colour 4.
    clutter = [_obj([(r, c)], 3) for r, c in [(0, 0), (0, 2), (2, 0), (2, 2), (4, 0), (4, 2), (6, 0), (6, 2)]]
    landmark = _obj([(9, 9), (9, 10)], 7)                 # unique colour 7, one object (slightly larger than a speck)
    cursor = _obj([(5, 5)], 4)
    objs = clutter + [landmark, cursor]

    cands = candidate_relations(objs, cursor_colour=4, stride=1)
    keys = [k for k, _rank in cands]
    # the landmark must be PROPOSED at all (the old size-sort buried it behind the 8 clutter specks)
    be_at_targets = [cell for (rel, cell) in keys if rel == "BE_AT"]
    assert landmark_cell_proposed(be_at_targets, landmark), "unique landmark never proposed: %s" % be_at_targets
    # and it must OUTRANK the clutter: the lowest rank (highest price) BE_AT is the landmark, not a clutter cell
    ranked = sorted(cands, key=lambda kr: kr[1])
    top_be_at = next((cell for (rel, cell), _r in ranked if rel == "BE_AT"), None)
    assert top_be_at in ((9, 9), (9, 10)), "top-ranked BE_AT is clutter, not the landmark: %s" % (top_be_at,)


def landmark_cell_proposed(be_at_targets, landmark):
    cells = set(landmark.cells)
    return any(t in cells for t in be_at_targets)


def test_big_singleton_ranks_below_small_marker_like_landmarks():
    # rarity ties broken by size: a big unique blob (e.g. a HUD bar) must NOT outrank a small unique landmark.
    hud = _obj([(63, c) for c in range(0, 30)], 6)         # a big unique object (a timer bar) — colour 6, once
    landmark = _obj([(3, 3)], 7)                           # a small unique landmark — colour 7, once
    cursor = _obj([(5, 5)], 4)
    cands = candidate_relations([hud, landmark, cursor], cursor_colour=4, stride=1)
    ranked = sorted(cands, key=lambda kr: kr[1])
    top_be_at = next((cell for (rel, cell), _r in ranked if rel == "BE_AT"), None)
    assert top_be_at == (3, 3), "big HUD-like singleton outranked the small landmark: %s" % (top_be_at,)
