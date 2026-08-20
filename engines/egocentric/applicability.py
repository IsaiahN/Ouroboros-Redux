"""W2a STAGE 1: the APPLICABILITY INDEX (PREREG_W2_APPLICABILITY_INDEX.md).

D5 named the term (D5_PROFILE_RESULT.md): 95.3% of a slow worker's runtime inside
effects.apply_effect -- every atom applied at every anchor, 77.7M numpy `.all()`
scans in a 420s window, five planner calls, zero plans. The cost is NOT KNOWING
which atoms can possibly apply. This module is that knowledge: a per-atom ANCHOR
SIGNATURE -- context-patch dimensions, palette set, and a cheap content key --
written at mint time (mint.py stamps it on the atom before Gamma.add) and DERIVED
ON READ for every atom that predates the field. Backfill-on-read, never a
migration: the index is DERIVED STATE, rebuildable from the atoms stream at any
time, never the sole holder of anything.

THE PRE-FILTER (prune_candidates): per planner call the frame's signature is
computed ONCE (frame_signature -- the only function here that touches numpy);
each candidate then costs O(1) dim/set comparisons. An atom is pruned only when
NO application path can fire:

* DIMS -- apply_effect writes in place on a copy, so frame dimensions are
  invariant across the whole search; a requirement exceeding every target frame
  can never fit, on any reachable state.
* PALETTE CLOSURE -- colours are NOT invariant (an applied atom can write
  colours the frame never showed), so the check runs to a fixpoint: start from
  the union of the workspace and reference palettes, admit any candidate whose
  required colours are covered, add the colours that candidate can WRITE (its
  colour universe), repeat. Multi-step paths through introduced colours are
  retained by construction (F2: nothing legal is lost).
* THE INVERSE PATH -- in reference mode the planner also walks BACKWARD via
  computable inverses (CK-2b); an atom the forward frame cannot feed can still
  verify forward after its own inverse writes its context colours near the
  reference. An invertible candidate is therefore kept whenever the INVERSE's
  requirement is coverable.

CONSERVATIVE BY CONSTRUCTION: unknown kinds, unknown ttypes, malformed patches,
composites, and conditionals' branch content all degrade to weaker requirements
or NO-REQUIREMENT -- when in doubt the candidate is KEPT and apply_effect stays
the authority. Scope guard (the prereg's): no change to apply_effect's
semantics, no change to which plans are legal -- only to which candidates are
evaluated.

F4 (the index is honest about its own cost): the per-atom path is pure-python
set/int arithmetic -- no numpy, no elementwise comparison, no apply_effect call
anywhere in it; numpy appears ONLY in frame_signature, the once-per-call read.
Deterministic throughout; stdlib + numpy only.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from engines.egocentric import effects as _effects

__all__ = ["ASIG_FIELD", "ASIG_VERSION", "anchor_signature", "signature_of",
           "inverse_signature", "colour_universe", "frame_signature",
           "prune_candidates"]

# The field the mint stamps on the atom dict at write time. Anything already in
# the stream without it is derived on read -- the stored copy is a CACHE.
ASIG_FIELD = "asig"
ASIG_VERSION = 1

# The typed mechanisms whose application requirements this module knows how to
# bound. An atom carrying any OTHER ttype reads as NO-REQUIREMENT (never
# pruned): a mechanism this module cannot reason about must not be filtered.
_KNOWN_TTYPES = ("TRANSLATE", "ROTATE", "REFLECT", "SCALE", "COLOUR_PERM",
                 "OBJ_APPEAR", "OBJ_VANISH")

# NO-REQUIREMENT: dims 0 fit every frame, an empty palette is a subset of every
# frame's -- an atom carrying this signature is NEVER pruned.
_NO_REQ = {"v": ASIG_VERSION, "h": 0, "w": 0, "pal": [], "ck": ""}


# ── the signature: derived from atom content, pure python ─────────────────────

def _patch_dims(patch: Any) -> Optional[Tuple[int, int]]:
    """(h, w) of a list-of-lists patch, or None when it is not rectangular."""
    if not isinstance(patch, list) or not patch or not isinstance(patch[0], list):
        return None
    h, w = len(patch), len(patch[0])
    if w == 0 or any(not isinstance(row, list) or len(row) != w for row in patch):
        return None
    return h, w


def _patch_palette(patch: List[List[Any]]) -> Set[int]:
    return {int(v) for row in patch for v in row}


def _content_key(patch: Any) -> str:
    """The cheap content key: sha1 over the patch's nonzero MASK at its native
    size -- content-addressing, not cryptography. '' when the patch is unreadable."""
    dims = _patch_dims(patch)
    if dims is None:
        return ""
    bits = "".join("1" if int(v) != 0 else "0" for row in patch for v in row)
    blob = "%d,%d|%s" % (dims[0], dims[1], bits)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def _shape_bbox(shape: List[Any]) -> Tuple[int, int]:
    """Footprint of a normalized [dr, dc, colour] shape: effects' anchor scan
    requires max-offset + 1 rows/cols of frame."""
    return (max(int(s[0]) for s in shape) + 1,
            max(int(s[1]) for s in shape) + 1)


def _typed_requirement(atom: Dict[str, Any], raw_dims: Tuple[int, int],
                       raw_pal: Set[int]) -> Optional[Tuple[int, int, Set[int]]]:
    """What the TYPED application path needs of a frame: (h, w, palette).
    None means the typed path cannot fire at all (the raw exact-context scan
    stands alone). An UNKNOWN ttype returns the zero requirement -- a mechanism
    this module cannot bound must never cause a prune."""
    ttype = atom.get("ttype")
    if ttype not in _KNOWN_TTYPES:
        return 0, 0, set()                                # unbounded: never prune on it
    params = atom.get("params") or {}
    shape = params.get("shape") or []
    if ttype in ("OBJ_APPEAR", "OBJ_VANISH") or (ttype == "COLOUR_PERM" and shape):
        if not shape:
            return None                                   # shapeless: typed path inert
        h, w = _shape_bbox(shape)
        if ttype == "OBJ_APPEAR":                         # anchors on clear GROUND: fill only
            return h, w, {int(params.get("fill", 0))}
        return h, w, {int(s[2]) for s in shape}           # anchors on the shape's colours
    if ttype == "TRANSLATE":
        if (int(params.get("dx", 0)), int(params.get("dy", 0))) == (0, 0):
            return None                                   # a zero shift never fires
        if shape:
            h, w = _shape_bbox(shape)
            return h, w, {int(s[2]) for s in shape}
        fill = int(params.get("fill", 0))                 # ctx path: bind the non-fill object
        ctx = atom.get("context")
        dims = _patch_dims(ctx)
        if dims is None:
            return None
        rows = [i for i, row in enumerate(ctx) if any(int(v) != fill for v in row)]
        cols = [j for j in range(dims[1])
                if any(int(row[j]) != fill for row in ctx)]
        if not rows:
            return None                                   # nothing non-fill: cannot bind
        r0, r1, c0, c1 = rows[0], rows[-1], cols[0], cols[-1]
        pal = {int(ctx[i][j]) for i in range(r0, r1 + 1) for j in range(c0, c1 + 1)}
        return r1 - r0 + 1, c1 - c0 + 1, pal
    # ROTATE / REFLECT / SCALE / shapeless COLOUR_PERM scan for the EXACT
    # context patch -- the same requirement as the raw path.
    return raw_dims[0], raw_dims[1], set(raw_pal)


def anchor_signature(atom: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The atom's ANCHOR SIGNATURE, derived from content alone (JSON-safe):
    {"v", "h", "w", "pal", "ck"} -- the weakest requirement over every
    application path (min dims, intersected palettes), so a frame failing it
    fails EVERY path. Total: never raises; anything unreadable degrades to
    NO-REQUIREMENT (kept, never pruned)."""
    try:
        return _derive(atom)
    except Exception:
        return dict(_NO_REQ)


def _derive(atom: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(atom, dict):
        return dict(_NO_REQ)
    kind = atom.get("kind")
    if kind == "EFFECT":
        ctx = atom.get("context")
        dims = _patch_dims(ctx)
        if dims is None:
            return dict(_NO_REQ)
        h, w = dims                                       # the raw exact-context scan
        pal = _patch_palette(ctx)
        ck = _content_key(ctx)
        if atom.get("ttype") and atom.get("ttype") != "NONE":
            t = _typed_requirement(atom, dims, pal)       # typed OR raw can fire:
            if t is not None:                             # min dims, intersect palettes
                h, w, pal = min(h, t[0]), min(w, t[1]), pal & t[2]
        return {"v": ASIG_VERSION, "h": int(h), "w": int(w),
                "pal": sorted(int(v) for v in pal), "ck": ck}
    if kind == "EFFECT_IF":
        # The condition cells are ABSOLUTE coordinates: a frame too small for
        # them returns None unconditionally. A FALSE condition with no else
        # still returns the unchanged frame, so no colour is ever required.
        cells = (atom.get("condition") or {}).get("cells") or []
        if not cells:
            return dict(_NO_REQ)
        h = max(0, max(int(c[0]) for c in cells) + 1)
        w = max(0, max(int(c[1]) for c in cells) + 1)
        blob = json.dumps(sorted([int(c[0]), int(c[1]), int(c[2])] for c in cells),
                          separators=(",", ":"))
        ck = hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]
        return {"v": ASIG_VERSION, "h": h, "w": w, "pal": [], "ck": ck}
    # COMPOSITE / INERT / lexical / unknown kinds: no bound this module can
    # assert -- NO-REQUIREMENT, never pruned.
    return dict(_NO_REQ)


def _valid(sig: Any) -> bool:
    return (isinstance(sig, dict) and sig.get("v") == ASIG_VERSION
            and isinstance(sig.get("h"), int) and sig["h"] >= 0
            and isinstance(sig.get("w"), int) and sig["w"] >= 0
            and isinstance(sig.get("pal"), list)
            and all(isinstance(v, int) for v in sig["pal"])
            and isinstance(sig.get("ck"), str))


def signature_of(atom: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """THE READ SIDE: the stored mint-time signature when present and
    well-formed, else the same signature DERIVED on the spot -- backfill-on-
    read for every atom that predates the field. Never a migration; the stream
    stays the sole holder of truth and the signature is always rebuildable."""
    if isinstance(atom, dict):
        stored = atom.get(ASIG_FIELD)
        if _valid(stored):
            return stored
    return anchor_signature(atom)


def inverse_signature(atom: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The anchor signature of the atom's computable INVERSE (CK-2b), or None
    when there is no inverse. Mirrors effects.apply_inverse's construction
    exactly -- the inverse acts on the AFTER patch with the inverted mechanism
    -- so the backward frontier's applicability is bounded by the same rules.
    Pure python (invert_transform is dict arithmetic, no arrays)."""
    if not isinstance(atom, dict) or atom.get("kind") != "EFFECT":
        return None
    ttype = atom.get("ttype")
    if not ttype or ttype == "NONE":
        return None
    inv = _effects.invert_transform(ttype, atom.get("params") or {})
    if inv is None:
        return None
    ctx = atom.get("context")
    out = (atom.get("transform") or {}).get("after")
    if ctx is None or out is None:
        return None
    return anchor_signature({
        "kind": "EFFECT", "action": atom.get("action"),
        "context": out, "transform": {"before": out, "after": ctx},
        "changed": atom.get("changed"), "ttype": inv[0], "params": inv[1],
    })


def colour_universe(atom: Optional[Dict[str, Any]], resolver=None,
                    _depth: int = 0) -> Optional[Set[int]]:
    """Every colour this atom could WRITE into a frame, forward or inverse --
    a superset, used by the palette closure. None means UNKNOWN (the closure
    then stops pruning on palette entirely -- conservative). COMPOSITEs
    resolve their parts through `resolver` (an id -> atom lookup); a missing
    resolver or part reads UNKNOWN. Pure python; total (never raises)."""
    try:
        if not isinstance(atom, dict):
            return None
        kind = atom.get("kind")
        if kind == "EFFECT":
            out: Set[int] = set()
            transform = atom.get("transform") or {}
            for patch in (atom.get("context"), transform.get("before"),
                          transform.get("after")):
                if _patch_dims(patch) is not None:
                    out |= _patch_palette(patch)
            params = atom.get("params") or {}
            if "fill" in params:
                out.add(int(params["fill"]))
            for pair in params.get("mapping") or []:
                out |= {int(pair[0]), int(pair[1])}
            for s in params.get("shape") or []:
                out.add(int(s[2]))
            return out
        if kind == "EFFECT_IF":
            u: Set[int] = set()
            for branch in (atom.get("then"), atom.get("else")):
                if branch is None:
                    continue
                b = colour_universe(branch, resolver, _depth + 1)
                if b is None:
                    return None
                u |= b
            return u
        if kind == "COMPOSITE":
            if resolver is None or _depth > 16:
                return None
            u = set()
            for pid in atom.get("parts") or []:
                p = colour_universe(resolver(pid), resolver, _depth + 1)
                if p is None:
                    return None
                u |= p
            return u
        return set()                                      # INERT / lexical: writes nothing
    except Exception:
        return None                                       # unreadable: UNKNOWN, never a prune


# ── the per-call frame read (the ONLY numpy in this module) ───────────────────

def frame_signature(frames) -> Optional[Dict[str, Any]]:
    """The query side, computed ONCE per planner call: the max dims and the
    UNION palette over the target frames (workspace, and reference when there
    is one). None when no readable frame arrived -- the filter then keeps
    everything (conservative)."""
    hs: List[int] = []
    ws_: List[int] = []
    pal: Set[int] = set()
    for f in frames:
        if f is None:
            continue
        a = np.asarray(f)
        if a.ndim != 2 or a.size == 0:
            continue
        hs.append(int(a.shape[0]))
        ws_.append(int(a.shape[1]))
        pal.update(int(v) for v in np.unique(a))
    if not hs:
        return None
    return {"h": max(hs), "w": max(ws_), "pal": pal}


# ── THE PRE-FILTER (pure python: no numpy, no arrays, no apply_effect) ────────

def prune_candidates(ids: List[str], atoms: Dict[str, Optional[Dict[str, Any]]],
                     fsig: Optional[Dict[str, Any]], resolver=None,
                     bidirectional: bool = False) -> List[str]:
    """Prune the candidate ids to those whose signatures can possibly match --
    BEFORE any apply_effect call. O(1) set/dim comparisons per atom per pass;
    the palette closure runs to fixpoint (bounded by len(ids) passes). Order
    is preserved; fsig=None keeps everything. F2 is absolute: every atom that
    CAN apply -- on the frame, on any state reachable through kept candidates,
    or through its own inverse in bidirectional (reference) mode -- survives.
    An atom is pruned only when its dims can never fit (dims are search-
    invariant) or when no reachable palette covers any of its paths."""
    if fsig is None:
        return list(ids)
    fh, fw = int(fsig["h"]), int(fsig["w"])
    pal: Set[int] = set(fsig["pal"])
    reqs: Dict[str, Tuple[frozenset, Optional[frozenset]]] = {}
    pending: List[str] = []
    for aid in ids:
        atom = atoms.get(aid)
        sig = signature_of(atom)
        if sig["h"] > fh or sig["w"] > fw:
            continue                                      # can NEVER fit: pruned
        inv_pal: Optional[frozenset] = None
        if bidirectional:
            isig = inverse_signature(atom)
            if isig is not None and isig["h"] <= fh and isig["w"] <= fw:
                inv_pal = frozenset(isig["pal"])
        reqs[aid] = (frozenset(sig["pal"]), inv_pal)
        pending.append(aid)
    kept: Set[str] = set()
    top = False                                           # an UNKNOWN universe disables
    progress = True                                       # palette pruning (conservative)
    while progress and pending:
        progress = False
        nxt: List[str] = []
        for aid in pending:
            fwd, inv = reqs[aid]
            if not (top or fwd <= pal or (inv is not None and inv <= pal)):
                nxt.append(aid)
                continue
            kept.add(aid)
            progress = True
            u = colour_universe(atoms.get(aid), resolver)
            if u is None:
                top = True
            else:
                pal |= u
        pending = nxt
    return [aid for aid in ids if aid in kept]
