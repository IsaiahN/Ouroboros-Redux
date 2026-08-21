"""COMPOSER STAGE 2: THE ENABLES INDICES (PREREG_COMPOSER_STAGE2_ENABLES.md).

Stage 1 factored the signatures (applicability.psig/csig, live at ce84040).
This module builds the two edges that make composition FINDABLE rather than
merely priceable (PROPOSAL_COMPOSER_DESIGN.md par.2-3):

1. THE WITHIN-GAMMA ENABLES EDGE (enables_edges): A -> B iff A's psig
   `written` colours intersect B's required palette AND B's requirement is
   not satisfiable in the current frame without A. Concretely, with
   missing_B = required_B - frame_palette: an edge exists iff missing_B is
   non-empty and missing_B intersects written_A -- the frame alone cannot
   supply some colour B demands, and A writes it. A sparse directed graph
   computed from STORED SIGNATURES only (signature_of / psig_of, both
   backfill-on-read): no execution, no numpy, no arrays -- the same
   pure-python discipline as applicability's per-atom filter path. Doubt
   produces ABSENCE: an underivable requirement reads NO-REQUIREMENT (empty
   palette -> nothing missing -> no in-edges), an underivable postcondition
   reads NO-CLAIM (writes nothing -> no out-edges). The edge never lies; it
   only ever fails to exist. Empty Gamma -> empty graph.

2. THE ACT-RELATIVE OFFSET (act_offset / act_offset_of): per atom,
   act_offset = act_cell - matched_anchor_origin, stamped by the mint at
   write time (mint.py, beside psig) when the minting action carried
   coordinates. At mint time the matched anchor origin IS the changed-cell
   bbox origin -- learn_effect crops the context patch there, so the patch
   matches the before-frame at exactly that cell. THE READ SIDE IS HONEST
   ABOUT ITS LIMIT: unlike asig/psig, the offset is NOT a function of the
   atom's stored content (the click cell lives nowhere in the patches --
   confirmed on live boxes: no atom record carries coordinates), so there is
   no content derivation to backfill from. act_offset_of serves the stored
   stamp when valid and returns None otherwise -- absence stated, never
   approximated (the prereg's "absent otherwise"). The offset survives
   minimisation and conflict reinstatement by construction: both preserve
   the patch bbox, and the offset is anchor-relative.

3. THE CROSS-SHELF REACH (cross_shelf_reach): given a Gamma atom, its
   matching anchors A, and the avatar at v (all frame cells, (row, col)),
   the cheapest BODY chain landing the atom's ACT CELL (anchor +
   act_offset) on some a in A -- breadth-first shortest path over the
   per-action (dr, dc) delta algebra, masked by the frontier book's fatal
   cells. Cost = chain length (the delta algebra carries no per-action
   price here). Returns the chain and its cost, or None (unreachable /
   offset absent), NEVER A GUESS. Every returned chain is marked
   verified=False -- THE CONTRACT (Seat 4's amendment): the algebra
   PROPOSES, the simulation DECIDES. Sum-of-deltas is exact for free
   movement and false wherever the world blocks; the fatal mask covers
   known-fatal cells only, not walls the agent has not died on. Nothing in
   this module can set the flag True.

COORDINATE CONVENTIONS, PINNED (the seam this module owns): everything here
works in (row, col) -- frame[row][col], matching learn_effect's bbox and
effects' anchors. The loop's click coordinates are (x, y) = (col, row)
(spine.remap_avoided's contract: "shape is (h, w) with cell=(x, y)";
cognitive_loop indexes frame[y, x]); callers convert at capture. The
frontier book banks cells in the click convention -- fatal_cells() is the
ONE conversion point for the mask.

DELTA SOURCES, STATED: book_deltas() reads per-action (dr, dc) from the
action book (action_book.load_action_book / effect_summary), taking each
action's highest-evidence TRANSLATE entry; effects applies TRANSLATE as
`tr, tc = r + dx, c + dy` (effects.py), so the book's (dx, dy) IS (dr, dc)
verbatim. Where the book lacks an action, the caller may pass the bank's
established deltas (bank.PredictorBank's BODY evidence) directly to
cross_shelf_reach -- the reach itself is source-agnostic and pure.

Both indices are DERIVED STATE, rebuildable from Gamma + the bank; the
reach query is a pure function (UNDO: remove the call sites, nothing stored
is lost). Deterministic throughout; stdlib only, no numpy anywhere in this
module. Total: malformed inputs degrade to absence, never raise.

WIRING: enables_edges and cross_shelf_reach ship SEVERED (a stated promise
-- the named consumer is the STAGE-3 COMPOSE LOOP, PROPOSAL_COMPOSER_DESIGN
par.6.3); act_offset is LIVE at the mint's write site.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from engines.egocentric import applicability as _applicability

__all__ = ["ACT_OFFSET_FIELD", "ACT_OFFSET_VERSION", "act_offset",
           "act_offset_of", "enables_edges", "cross_shelf_reach",
           "fatal_cells", "book_deltas"]

# The field the mint stamps on the atom dict at write time, beside psig.
# Anything in the stream without it reads ABSENT (act_offset_of -> None):
# the offset is not derivable from atom content, so absence is permanent
# until an evidence-carrying re-mint -- stated, never approximated.
ACT_OFFSET_FIELD = "act_offset"
ACT_OFFSET_VERSION = 1


# ── THE ACT-RELATIVE OFFSET: write side + read side ───────────────────────────

def act_offset(act_cell: Any, anchor_origin: Any) -> Optional[Dict[str, int]]:
    """THE WRITE SIDE: the stored offset dict {"v", "dr", "dc"} from the
    acting cell and the matched anchor origin (both (row, col)), or None
    when either is unreadable -- the mint then stamps nothing (a malformed
    capture must never move a verdict). Offsets may be negative: a click
    outside the changed bbox is a real geometry, not an error."""
    try:
        ar, ac = int(act_cell[0]), int(act_cell[1])
        orow, ocol = int(anchor_origin[0]), int(anchor_origin[1])
    except (TypeError, ValueError, IndexError):
        return None
    return {"v": ACT_OFFSET_VERSION, "dr": ar - orow, "dc": ac - ocol}


def _valid_offset(off: Any) -> bool:
    return (isinstance(off, dict) and off.get("v") == ACT_OFFSET_VERSION
            and isinstance(off.get("dr"), int)
            and isinstance(off.get("dc"), int))


def act_offset_of(atom: Optional[Dict[str, Any]]) -> Optional[Tuple[int, int]]:
    """THE READ SIDE: the stored mint-time offset (dr, dc) when present and
    well-formed, else None. NO content backfill exists -- the click cell is
    not a function of the atom's patches (the one derived field where
    backfill-on-read is impossible, and the prereg says so): an atom that
    predates the field, or whose mint carried no coordinates, reads ABSENT.
    Every consumer must treat None as "no cross-shelf edge", never guess."""
    if isinstance(atom, dict):
        stored = atom.get(ACT_OFFSET_FIELD)
        if _valid_offset(stored):
            return int(stored["dr"]), int(stored["dc"])
    return None


# ── 1 · THE WITHIN-GAMMA ENABLES EDGE ────────────────────────────────────────

def enables_edges(ids: List[str], atoms: Dict[str, Optional[Dict[str, Any]]],
                  fsig: Optional[Dict[str, Any]] = None) -> Dict[str, List[str]]:
    """The sparse directed ENABLES graph over the given atoms: {A_id ->
    [B_ids A enables]}, edges in input order, only non-empty adjacency
    lists. A -> B iff (required_B - frame_palette) is non-empty AND
    intersects written_A: B's requirement is not satisfiable in the current
    frame without a writer, and A is one. Self-edges are excluded (an atom
    "enabling" its own precondition orders nothing).

    STORED SIGNATURES ONLY: required_B = signature_of(B)["pal"] (the
    weakest requirement over every application path, backfill-on-read;
    COMPOSITEs read their stored csig precondition), written_A =
    psig_of(A)["written"] (COMPOSITEs and anything unreadable read NO-CLAIM
    -- no out-edges, never a false edge). No execution, no numpy: per-edge
    cost is pure-python set arithmetic.

    fsig is applicability.frame_signature's dict (the once-per-call numpy
    read stays in THAT module); fsig=None degrades to an EMPTY frame
    palette -- every required colour then counts as missing, and the edge
    condition collapses to the prereg's clause 1 alone (written intersects
    required), stated here rather than guessed. Empty ids -> {} (the
    known-negative: an empty Gamma yields an empty graph, not an
    exception)."""
    frame_pal: Set[int] = set()
    if isinstance(fsig, dict):
        frame_pal = {int(v) for v in (fsig.get("pal") or ())}
    required: Dict[str, Set[int]] = {}
    written: Dict[str, Set[int]] = {}
    for aid in ids:
        atom = atoms.get(aid)
        required[aid] = {int(v) for v in _applicability.signature_of(atom)["pal"]}
        written[aid] = {int(v) for v in _applicability.psig_of(atom)["written"]}
    edges: Dict[str, List[str]] = {}
    for a in ids:
        wa = written[a]
        if not wa:
            continue                       # NO-CLAIM: writes nothing, enables nothing
        outs = [b for b in ids
                if b != a and (required[b] - frame_pal) & wa]
        if outs:
            edges[a] = outs
    return edges


# ── 3 · THE CROSS-SHELF REACH ────────────────────────────────────────────────

def cross_shelf_reach(atom: Optional[Dict[str, Any]],
                      anchors: Iterable[Tuple[int, int]],
                      avatar: Tuple[int, int],
                      deltas: Dict[int, Tuple[int, int]],
                      shape: Tuple[int, int],
                      fatal: Optional[Set[Tuple[int, int]]] = None,
                      ) -> Optional[Dict[str, Any]]:
    """The cheapest BODY chain landing the atom's ACT CELL on a matching
    anchor: breadth-first shortest path from `avatar` over the per-action
    (dr, dc) deltas, on the (row, col) grid of `shape` = (h, w), never
    entering a `fatal` cell (the frontier book's mask, already converted --
    fatal_cells below). Targets are {anchor + act_offset(atom)} for each
    matching anchor, in-bounds and non-fatal.

    Returns {"chain": [action, ...], "cost": len(chain), "start", "target",
    "anchor", "cells": [every cell the chain visits, start included],
    "verified": False} -- or None when the atom carries no act_offset, the
    avatar starts out of bounds or on a fatal cell, no target survives the
    mask, or no chain exists. NEVER A GUESS: None means unreachable-as-far-
    as-the-algebra-knows, and a chain means PROPOSED, nothing more.

    verified=False IS THE CONTRACT (Seat 4): the delta algebra is exact for
    free movement and false wherever the world blocks -- the fatal mask
    covers known-fatal cells only. Every returned chain must be
    simulation-checked at the seams before anything stands on it; this
    module has no way to set the flag True.

    Deterministic: actions are tried in ascending id order, BFS is FIFO --
    among equal-cost chains the lexicographically-first by action order is
    returned. States are grid cells, so the search is bounded by h*w."""
    off = act_offset_of(atom)
    if off is None:
        return None                        # no offset, no translation: stated
    try:
        h, w = int(shape[0]), int(shape[1])
        start = (int(avatar[0]), int(avatar[1]))
    except (TypeError, ValueError, IndexError):
        return None
    if h <= 0 or w <= 0:
        return None
    blocked: Set[Tuple[int, int]] = set(fatal or ())
    if not (0 <= start[0] < h and 0 <= start[1] < w) or start in blocked:
        return None
    targets: Dict[Tuple[int, int], Tuple[int, int]] = {}
    for anch in sorted((int(a[0]), int(a[1])) for a in anchors):
        cell = (anch[0] + off[0], anch[1] + off[1])
        if (0 <= cell[0] < h and 0 <= cell[1] < w
                and cell not in blocked and cell not in targets):
            targets[cell] = anch           # first anchor (sorted) wins a collision
    if not targets:
        return None
    moves: List[Tuple[int, Tuple[int, int]]] = []
    for action in sorted(deltas):
        try:
            d = (int(deltas[action][0]), int(deltas[action][1]))
        except (TypeError, ValueError, IndexError):
            continue
        if d != (0, 0):
            moves.append((int(action), d))

    def _result(end: Tuple[int, int],
                prev: Dict[Tuple[int, int],
                           Optional[Tuple[Tuple[int, int], int]]],
                ) -> Dict[str, Any]:
        chain: List[int] = []
        cells: List[Tuple[int, int]] = [end]
        cur = end
        while prev[cur] is not None:
            cur, action = prev[cur]        # type: ignore[misc]
            chain.append(action)
            cells.append(cur)
        chain.reverse()
        cells.reverse()
        return {"chain": chain, "cost": len(chain), "start": start,
                "target": end, "anchor": targets[end], "cells": cells,
                "verified": False}         # the algebra proposes; simulation decides

    prev: Dict[Tuple[int, int], Optional[Tuple[Tuple[int, int], int]]] = {
        start: None}
    if start in targets:
        return _result(start, prev)
    queue: deque = deque([start])
    while queue:
        cell = queue.popleft()
        for action, (dr, dc) in moves:
            nxt = (cell[0] + dr, cell[1] + dc)
            if (nxt in prev or not (0 <= nxt[0] < h and 0 <= nxt[1] < w)
                    or nxt in blocked):
                continue
            prev[nxt] = (cell, action)
            if nxt in targets:
                return _result(nxt, prev)
            queue.append(nxt)
    return None                            # exhausted: unreachable, never a guess


# ── the mask + delta feeders (the two stated sources) ─────────────────────────

def fatal_cells(book: Any, game: str, level: int) -> Set[Tuple[int, int]]:
    """The frontier book's avoid-set as (row, col) cells -- THE ONE
    CONVERSION POINT for the reach mask. FrontierBook.avoid_set banks cells
    in the loop's click convention (x, y) = (col, row) (spine.remap_avoided:
    "shape is (h, w) with cell=(x, y)"); the reach grid is (row, col).
    Empty set on any doubt -- an unreadable book must never invent a wall
    (it also never hides one it actually holds: avoid_set itself degrades
    to empty on error, stated in frontier.py)."""
    try:
        return {(int(y), int(x)) for x, y in book.avoid_set(game, level)}
    except Exception:
        return set()


def book_deltas(game: Any,
                actions: Iterable[int] = (1, 2, 3, 4, 5),
                ) -> Dict[int, Tuple[int, int]]:
    """Per-action (dr, dc) from the ACTION BOOK (the stated primary source):
    each action's highest-evidence TRANSLATE entry, read via
    action_book.effect_summary (the book sorts translate entries by -n, so
    element 0 is the dominant delta). effects.py applies TRANSLATE as
    `tr, tc = r + dx, c + dy`, so the book's (dx, dy) IS (dr, dc) verbatim
    -- no axis swap. An action the book holds no translate evidence for is
    ABSENT from the result (never a guessed delta); callers may fill gaps
    from the bank's established BODY deltas, the stated fallback source.
    Empty dict when no book is loaded for `game`."""
    out: Dict[int, Tuple[int, int]] = {}
    try:
        from engines.egocentric import action_book as _action_book
        for action in actions:
            entry = _action_book.effect_summary(game, action)
            translate = ((entry or {}).get("atoms") or {}).get("translate")
            if not translate:
                continue
            top = translate[0]
            out[int(action)] = (int(top["dx"]), int(top["dy"]))
    except Exception:
        return out
    return out
