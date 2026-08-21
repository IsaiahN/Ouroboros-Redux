"""action_book.py -- STAGE 0 of the reasoning gate (PROPOSAL_REASONING_GATE.md §3):
THE ACTION BOOK, the read side.

Per (game, action) semantics the agent can CITE, derived ENTIRELY from the
agent's own recorded history -- the Γ atoms stream (each atom carries its
action int, its patches, sigma.colour_delta, ttype) and the action_traces DB
(frame pairs, score changes, and the budget columns that were produced-and-
unread until this build). Authored action semantics would be checking-against-
us; derived ones are the agent's history made citable. NOTHING in this module
knows what any action "means" -- every field of the book flows from records
(the gate test asserts this structurally AND by permutation equivariance).

THE ARTIFACT: one JSON file per game box at
<game_dir>/ego_fabric/collective/action_book.json, written only by
tools/build_action_book.py, which REBUILDS IT FROM SCRATCH each run and says
so in a header field carrying the source stream positions. Like the
applicability index it is derived state -- rebuildable at any time, never the
sole holder of anything.

HONESTY RULES (the book's own, enforced by the builder and preserved here):
every derived claim carries its evidence count; absence of evidence is an
explicit null with a NAMED reason ("no traces with non-null budget", "no
repeated frame pairs ..."), never a guess or an authored default. inverse_of
reports evidence n VERBATIM -- an n=1 pairing returns n=1, never promoted.

Pure reads; one in-memory dict (_BOOKS), no other caching. Stdlib only.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

__all__ = ["ARTIFACT", "BOOK_VERSION", "BOOK_RELPATH", "book_path",
           "load_action_book", "effect_summary", "inverse_of", "cost_of"]

ARTIFACT = "action_book"
BOOK_VERSION = 1

# The one artifact location inside a game box (the collective scope: the book
# derives from collective streams and is readable by every worker on the box).
BOOK_RELPATH = os.path.join("ego_fabric", "collective", "action_book.json")

# game key (box name or recorded game id) -> loaded book. The ONE in-memory
# dict; load_action_book replaces entries wholesale (last load wins).
_BOOKS: Dict[str, Dict[str, Any]] = {}

# The read-side reason for an action the book never saw: a named absence,
# never a guess (mirrors the builder's discipline).
NO_EVIDENCE = "no recorded evidence for this action in this game's book"


def book_path(game_dir: str) -> str:
    """Where the derived artifact lives inside one game box."""
    return os.path.join(str(game_dir), BOOK_RELPATH)


def load_action_book(game_dir: str) -> Optional[Dict[str, Any]]:
    """Load one box's action book and register it under every game key it
    carries (the box name and each recorded game id). Returns the book dict,
    or None when the artifact is absent or unreadable -- never raises, never
    invents an empty book (absence is absence)."""
    path = book_path(game_dir)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            book = json.load(fh)
    except Exception:
        return None
    if not isinstance(book, dict) or book.get("artifact") != ARTIFACT:
        return None
    for key in _book_keys(book):
        _BOOKS[key] = book
    return book


def _book_keys(book: Dict[str, Any]) -> Tuple[str, ...]:
    keys = []
    box = book.get("box")
    if box:
        keys.append(str(box))
    for gid in book.get("game_ids") or []:
        keys.append(str(gid))
    return tuple(keys)


def _entry(game: Any, action: Any) -> Optional[Dict[str, Any]]:
    book = _BOOKS.get(str(game))
    if book is None:
        return None
    return (book.get("actions") or {}).get(str(int(action)))


def effect_summary(game: Any, action: Any) -> Optional[Dict[str, Any]]:
    """The per-(game, action) entry: observed effect distribution from atoms,
    observed frequency / frame-change rate / score distribution from traces,
    and cost evidence -- each an explicit null with a named reason where the
    records hold nothing. None when NO book is loaded for `game` (an unloaded
    book is not evidence of anything, either way)."""
    if str(game) not in _BOOKS:
        return None
    entry = _entry(game, action)
    if entry is None:
        # The book exists and this action was never recorded in it: the
        # explicit-null shape, with the named read-side reason.
        return {"atoms": None, "atoms_absent": NO_EVIDENCE,
                "traces": None, "traces_absent": NO_EVIDENCE,
                "cost": None, "cost_absent": NO_EVIDENCE}
    return entry


def inverse_of(game: Any, action: Any) -> Optional[Tuple[int, int]]:
    """(action b, evidence n) for the b with the MOST recorded evidence of
    undoing `action` (n = n_traces + n_atoms, reported VERBATIM: an n=1 claim
    returns n=1, never promoted). Ties break to the smallest b
    (deterministic). None when the book holds no inverse evidence."""
    book = _BOOKS.get(str(game))
    if book is None:
        return None
    inv = (book.get("inverses") or {}).get(str(int(action))) or {}
    pairs = inv.get("pairs")
    if not pairs:
        return None
    best: Optional[Tuple[Tuple[int, int], int, int]] = None
    for b, ev in pairs.items():
        try:
            n = int(ev.get("n_traces", 0)) + int(ev.get("n_atoms", 0))
            bi = int(b)
        except Exception:
            continue
        if n <= 0:
            continue
        rank = (-n, bi)
        if best is None or rank < best[0]:
            best = (rank, bi, n)
    if best is None:
        return None
    return best[1], best[2]


def cost_of(game: Any, action: Any) -> Optional[Dict[str, Any]]:
    """Recorded cost evidence for (game, action) -- the traces' budget columns
    aggregated with their evidence count -- or None. The book's own entry
    carries the named reason when the evidence is absent (e.g. "no traces with
    non-null budget"); this helper returns the evidence dict or None, never a
    default price."""
    entry = _entry(game, action)
    if not entry:
        return None
    return entry.get("cost")
