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
from collections import Counter
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


def quantified_candidates(objs: List[Object], cursor_colour: Optional[int], stride: int,
                          *, min_members: int = 2, max_classes: int = 3) -> List[Tuple[Key, int]]:
    """QUANTIFIED win-hypotheses: `ALL(x in COLOUR-CLASS)` -- the cursor must reach EVERY instance of a colour
    that appears >= min_members times (visit-all / collect / all-markers). Key = ("ALL", colour).

    FMap: ostrom_iad_framework (d=0.104) -- the objective is a rule over the whole SET; lindblom (reduce
    violators one at a time); goodharts_law GUARD -- reaching ONE member must NOT count as satisfying the
    whole set (only zero violators does). Returns [(("ALL", colour), rank), ...], most-numerous class first."""
    from collections import Counter
    non_self = [o for o in objs if cursor_colour is None or cursor_colour not in o.colours]
    counts: Counter = Counter()
    for o in non_self:
        for c in o.colours:
            counts[c] += 1
    classes = sorted((c for c, n in counts.items() if n >= min_members), key=lambda c: -counts[c])
    return [(("ALL", int(c)), rank) for rank, c in enumerate(classes[:max_classes])]


def class_member_cells(objs: List[Object], colour: int, stride: int) -> List[Tuple[int, int]]:
    """The logical cells of every instance of `colour` -- the members of an ALL-class the cursor must reach."""
    return [_cell(o.centroid, stride) for o in objs if colour in o.colours]


def candidate_relations(objs: List[Object], cursor_colour: Optional[int], stride: int,
                        *, max_objs: int = 5, static_colours: Optional[frozenset] = None) -> List[Tuple[Key, int]]:
    """Propose typed relation-hypotheses (as (relation, target_cell) keys) for the market, most SALIENT
    landmarks first. Each object yields BE_AT + TOUCH, plus COVER if it is a hollow slot. Reward disposes.

    SALIENCE, ranked by (NOT static, colour RARITY, size):
      * STATIC (brick 24) -- a fixed distinct object is a goal/landmark; the cursor and any HUD/animation MOVE.
        Preferring static-first breaks the price TIES that otherwise let the agent commit to an arbitrary
        corridor cell instead of the real goal (measured on tu93: rare objects colour 4 (a moving 1px marker),
        colour 6 (the depleting HUD bar) and colour 14 (the STATIC goal square) all tied at price 1.0, and the
        market locked onto a corridor cell 6 cells from the goal; static-first makes colour 14 uniquely top).
      * RARITY (brick 23) -- a colour appearing as FEW objects is the distinct LANDMARK (figure) vs many
        identical fragments of a repeated colour (ground: a maze's 30+ corridor/wall pieces). Without it a
        maze's tiny 1-2px fragments fill every slot and BURY the unique landmark so it is never proposed.
      * size -- final tiebreak, marker-like small first (keeps a big HUD bar below marker-like objects).
    FMap: predictive_processing / information salience (a rare STATIC singleton is the high-information figure);
    goodharts_law guard -- 'smallest object' is a gameable proxy for 'the goal'; 'rare + fixed + distinct' is
    the honest one. `static_colours` is passed by the loop from cross-frame centroid tracking; empty is fine."""
    non_self = [o for o in objs if cursor_colour is None or cursor_colour not in o.colours]
    static = static_colours or frozenset()
    colour_count: Counter = Counter()
    for o in non_self:
        for c in o.colours:
            colour_count[c] += 1
    def _rarity(o: Object) -> int:                      # fewest siblings sharing any of the object's colours
        return min((colour_count[c] for c in o.colours), default=10 ** 6)
    def _landmark(o: Object) -> int:                    # 0 iff a UNIQUE (rarity-1) STATIC object -- a singleton
        # goal. A static member of a REPEATED colour is a class (handled by the ALL/quantified path), NOT a
        # single BE_AT landmark -- restricting the static boost to rarity-1 keeps it from hijacking m0r0's
        # ALL(colour) visit-all win. So only a lone fixed distinct object earns the top-of-market boost.
        return 0 if (_rarity(o) == 1 and any(c in static for c in o.colours)) else 1
    non_self.sort(key=lambda o: (_landmark(o), _rarity(o), o.size))  # unique static landmark FIRST, then rare, small
    out: List[Tuple[Key, int]] = []
    rank = 0
    for o in non_self[:max_objs]:
        for key in (("BE_AT", _onobject_cell(o, stride)), ("TOUCH", _touch_cell(o, stride))):
            if key[1][0] >= 0 and key[1][1] >= 0:       # skip OFF-BOARD targets (e.g. TOUCH above a top-row object
                out.append((key, rank)); rank += 1      # is row -1) -- an unreachable cell is a stall sink, not a goal
        hi = _hollow_interior(o, stride)
        if hi is not None and hi[0] >= 0 and hi[1] >= 0:
            out.append((("COVER", hi), rank)); rank += 1
    return out
