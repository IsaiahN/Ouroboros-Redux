"""
relations.py -- brick 17: a SPACE OF TYPED WIN-RELATIONS (harvested from Redux `objective_grammar`).

The multi-game experiment (brick 16) proved "BE_AT a distinct object" is too narrow: across ls20/ka59 the
agent navigates onto the obvious target and does NOT win. Real ARC-3 wins are specific typed relations that
must be DISCOVERED. So instead of one goal per object, propose SEVERAL typed relation-hypotheses per object
and let the reward-priced market (brick 14) arbitrate which relation actually wins.

Relations (generic predicates over objects -- no game identity; Redux objective_grammar vocabulary):
  * BE_AT(cursor, o)  -- be ON the object's cell (the old, narrow hypothesis).
  * TOUCH(cursor, o)  -- be ADJACENT to the object (contact, not onto) -- e.g. a walled target you can only
                         reach the edge of.
  * COVER(cursor, o)  -- be INSIDE the object's enclosed interior (a hollow outline / slot -- e.g. ka59's
                         hollow yellow square: go INTO it, not onto its frame).
(COLLECT/NONE.EXIST -- visit-all-of-a-colour -- is a follow-on; this brick establishes the priced space.)

FMap: hayek_price_system (d=0.108) -- the reward is the PRICE that reveals which relation-hypothesis is
true. Each relation yields a NAVIGATION TARGET CELL; the market prices (relation, cell) keys and reward
confirms the winner, demotes the rest (defeasibly). Nothing silent; never encodes any game's answer.
"""
from __future__ import annotations
from typing import List, Optional, Tuple
from .perception import Object

Key = Tuple[str, Tuple[int, int]]     # (relation_name, target_cell)


def _cell(centroid: Tuple[float, float], stride: int) -> Tuple[int, int]:
    s = max(1, stride)
    return (int(round(centroid[0] / s)), int(round(centroid[1] / s)))


def _bbox(o: Object) -> Tuple[int, int, int, int]:
    rs = [c[0] for c in o.cells]; cs = [c[1] for c in o.cells]
    return min(rs), max(rs), min(cs), max(cs)


def _onobject_cell(o: Object, stride: int) -> Tuple[int, int]:
    """The BE_AT target: an ACTUAL object cell nearest the centroid (be ON the object, not in its hole -- for
    a hollow frame the centroid is background, so BE_AT must snap to the frame, keeping it distinct from COVER)."""
    cr, cc = o.centroid
    nearest = min(o.cells, key=lambda p: (p[0] - cr) ** 2 + (p[1] - cc) ** 2)
    return _cell((float(nearest[0]), float(nearest[1])), stride)


def _touch_cell(o: Object, stride: int) -> Tuple[int, int]:
    """A cell ADJACENT to the object (just above its top edge) -- a distinct approach target from BE_AT."""
    r0, r1, c0, c1 = _bbox(o)
    s = max(1, stride)
    return (int(round(r0 / s)) - 1, int(round(((c0 + c1) / 2) / s)))


def _hollow_interior(o: Object, stride: int) -> Optional[Tuple[int, int]]:
    """If `o` is an OUTLINE/frame (object cells on all four bbox edges, hollow centre), return the interior
    centre cell -- the COVER target (go INSIDE). Else None."""
    r0, r1, c0, c1 = _bbox(o)
    h, w = r1 - r0 + 1, c1 - c0 + 1
    if h < 3 or w < 3:
        return None
    cr, cc = (r0 + r1) // 2, (c0 + c1) // 2
    cells = o.cells
    if (cr, cc) in cells:                                    # centre filled -> solid, not a slot
        return None
    top = any((r0, c) in cells for c in range(c0, c1 + 1))
    bot = any((r1, c) in cells for c in range(c0, c1 + 1))
    left = any((r, c0) in cells for r in range(r0, r1 + 1))
    right = any((r, c1) in cells for r in range(r0, r1 + 1))
    if top and bot and left and right:                      # a frame enclosing a hollow centre -> a slot
        return _cell((cr, cc), stride)
    return None


def candidate_relations(objs: List[Object], cursor_colour: Optional[int], stride: int,
                        *, max_objs: int = 5) -> List[Tuple[Key, int]]:
    """Propose typed relation-hypotheses (as (relation, target_cell) keys) for the market, marker-like objects
    first. Each object yields BE_AT + TOUCH, plus COVER if it is a hollow slot. Reward disposes."""
    non_self = [o for o in objs if cursor_colour is None or cursor_colour not in o.colours]
    non_self.sort(key=lambda o: o.size)
    out: List[Tuple[Key, int]] = []
    rank = 0
    for o in non_self[:max_objs]:
        out.append((("BE_AT", _onobject_cell(o, stride)), rank)); rank += 1
        out.append((("TOUCH", _touch_cell(o, stride)), rank)); rank += 1
        hi = _hollow_interior(o, stride)
        if hi is not None:
            out.append((("COVER", hi), rank)); rank += 1
    return out
